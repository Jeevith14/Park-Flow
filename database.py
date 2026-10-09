"""
=============================================================================
PARKFLOW DATABASE ADAPTER (database.py)
=============================================================================
Academic Topic: Dual-Engine Database Persistence for Serverless Deployment
Engines Supported:
1. Neon PostgreSQL / Vercel Postgres (when DATABASE_URL is set in environment)
2. SQLite (local & serverless /tmp fallback: parkflow.db)

Key Design:
- Serverless-Ready: In serverless environments (like Vercel), function memory
  is ephemeral. All stack operations and vehicle allocations are committed
  transactionally to persistent storage.
- Read-Only Filesystem Safe: Automatically detects Vercel / AWS Lambda environment
  and uses /tmp/parkflow.db to prevent read-only filesystem crash.
- URL Parser & Pure-Python Driver: Uses pg8000 (pure Python) first to ensure
  100% binary compatibility on Linux serverless containers without requiring libpq.
=============================================================================
"""

import os
import sys
import sqlite3
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

TOTAL_SLOTS = 20

# Detect Database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Serverless-safe SQLite path:
# AWS Lambda / Vercel functions have a read-only root filesystem.
# Only /tmp is writable.
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(BASE_DIR, os.W_OK):
    SQLITE_DB_PATH = "/tmp/parkflow.db"
else:
    SQLITE_DB_PATH = os.path.join(BASE_DIR, "parkflow.db")

IS_POSTGRES = False


def connect_postgres(url: str):
    """
    Connect to PostgreSQL using pg8000 (pure Python) or psycopg2.
    Safely parses URL and strips query parameters from database name.
    """
    parsed = urllib.parse.urlsplit(url)
    user = urllib.parse.unquote(parsed.username) if parsed.username else ""
    password = urllib.parse.unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname
    port = parsed.port or 5432
    # Ensure database name does not contain query string
    database_name = parsed.path.lstrip("/").split("?")[0] if parsed.path else "neondb"

    # 1. Try pg8000 first (pure Python, zero C dependencies, works in any serverless container)
    try:
        import pg8000.dbapi
        import ssl
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        conn = pg8000.dbapi.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database_name,
            ssl_context=ssl_ctx
        )
        return conn, "postgres"
    except Exception as e_pg8000:
        # 2. Try psycopg2 as fallback
        try:
            import psycopg2
            # Normalise scheme
            norm_url = url
            if norm_url.startswith("postgres://"):
                norm_url = norm_url.replace("postgres://", "postgresql://", 1)
            conn = psycopg2.connect(norm_url)
            return conn, "postgres"
        except Exception as e_psycopg2:
            raise Exception(f"PostgreSQL connection failed: pg8000: {e_pg8000}; psycopg2: {e_psycopg2}")


def get_connection():
    """
    Establish and return a database connection.
    Attempts PostgreSQL if DATABASE_URL is present, otherwise safely falls back to SQLite.
    """
    global IS_POSTGRES
    if DATABASE_URL and ("postgres" in DATABASE_URL.lower()):
        try:
            conn, engine = connect_postgres(DATABASE_URL)
            IS_POSTGRES = True
            return conn, "postgres"
        except Exception as e:
            print(f"[Warning] Failed to connect to PostgreSQL ({e}). Falling back to SQLite at {SQLITE_DB_PATH}.")
            IS_POSTGRES = False

    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    IS_POSTGRES = False
    return conn, "sqlite"


def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False, commit: bool = True):
    """
    Execute a SQL query adapting placeholders for SQLite (?) or PostgreSQL (%s).
    """
    conn, engine = get_connection()
    try:
        cur = conn.cursor()
        
        # Replace ? with %s if using Postgres
        if engine == "postgres":
            query = query.replace("?", "%s")
        else:
            query = query.replace("%s", "?")
            
        cur.execute(query, params)

        result = None
        if fetch_one:
            row = cur.fetchone()
            if row is not None:
                if engine == "postgres" and not isinstance(row, dict):
                    cols = [col[0] for col in cur.description]
                    result = dict(zip(cols, row))
                elif engine == "sqlite":
                    result = dict(row)
                else:
                    result = row
        elif fetch_all:
            rows = cur.fetchall()
            if engine == "postgres" and rows and not isinstance(rows[0], dict):
                cols = [col[0] for col in cur.description]
                result = [dict(zip(cols, r)) for r in rows]
            elif engine == "sqlite":
                result = [dict(r) for r in rows]
            else:
                result = rows

        if commit:
            conn.commit()
            
        cur.close()
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise e


def init_db():
    """
    Initialize database schema and seed empty slots + full parking stack.
    Safe against exceptions to prevent crashing the serverless worker.
    """
    try:
        conn, engine = get_connection()
        cur = conn.cursor()

        if engine == "postgres":
            # PostgreSQL schema
            cur.execute("""
                CREATE TABLE IF NOT EXISTS parking_slots (
                    slot_number INT PRIMARY KEY,
                    is_occupied BOOLEAN DEFAULT FALSE,
                    vehicle_no VARCHAR(50),
                    owner_name VARCHAR(100),
                    vehicle_type VARCHAR(50),
                    parked_at TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stack_items (
                    position INT PRIMARY KEY,
                    slot_number INT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_history (
                    id SERIAL PRIMARY KEY,
                    vehicle_no VARCHAR(50) NOT NULL,
                    owner_name VARCHAR(100) NOT NULL,
                    vehicle_type VARCHAR(50) NOT NULL,
                    slot_number INT NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    duration_minutes INT,
                    status VARCHAR(20) NOT NULL
                );
            """)
        else:
            # SQLite schema
            cur.execute("""
                CREATE TABLE IF NOT EXISTS parking_slots (
                    slot_number INTEGER PRIMARY KEY,
                    is_occupied INTEGER DEFAULT 0,
                    vehicle_no TEXT,
                    owner_name TEXT,
                    vehicle_type TEXT,
                    parked_at TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stack_items (
                    position INTEGER PRIMARY KEY,
                    slot_number INTEGER NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_no TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    vehicle_type TEXT NOT NULL,
                    slot_number INTEGER NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    duration_minutes INTEGER,
                    status TEXT NOT NULL
                );
            """)

        conn.commit()

        # Check if slots are seeded
        cur.execute("SELECT COUNT(*) FROM parking_slots")
        slot_count = cur.fetchone()[0]

        if slot_count == 0:
            for i in range(1, TOTAL_SLOTS + 1):
                if engine == "postgres":
                    cur.execute("INSERT INTO parking_slots (slot_number, is_occupied) VALUES (%s, FALSE)", (i,))
                else:
                    cur.execute("INSERT INTO parking_slots (slot_number, is_occupied) VALUES (?, 0)", (i,))
            conn.commit()

        # Check if stack is seeded
        cur.execute("SELECT COUNT(*) FROM stack_items")
        stack_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM parking_slots WHERE is_occupied = TRUE OR is_occupied = 1")
        occupied_count = cur.fetchone()[0]

        if stack_count == 0 and occupied_count == 0:
            slots_desc = list(range(TOTAL_SLOTS, 0, -1))
            for pos, slot_no in enumerate(slots_desc):
                if engine == "postgres":
                    cur.execute("INSERT INTO stack_items (position, slot_number) VALUES (%s, %s)", (pos, slot_no))
                else:
                    cur.execute("INSERT INTO stack_items (position, slot_number) VALUES (?, ?)", (pos, slot_no))
            conn.commit()

        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Warning] init_db encountered an issue: {e}")


def get_stack_slots() -> List[int]:
    """
    Retrieve available slots ordered from bottom to top (list order for ParkingStack).
    """
    rows = execute_query("SELECT slot_number FROM stack_items ORDER BY position ASC", fetch_all=True)
    return [r["slot_number"] for r in rows] if rows else []


def save_stack_slots(slots_list: List[int]) -> None:
    """
    Persist the full stack state into stack_items table.
    slots_list is ordered from bottom to top.
    """
    conn, engine = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM stack_items")
    for pos, slot_no in enumerate(slots_list):
        if engine == "postgres":
            cur.execute("INSERT INTO stack_items (position, slot_number) VALUES (%s, %s)", (pos, slot_no))
        else:
            cur.execute("INSERT INTO stack_items (position, slot_number) VALUES (?, ?)", (pos, slot_no))
    conn.commit()
    cur.close()
    conn.close()


def get_all_slots() -> List[Dict[str, Any]]:
    """
    Get all 20 slots ordered by slot_number with current occupancy and vehicle details.
    """
    return execute_query("SELECT * FROM parking_slots ORDER BY slot_number ASC", fetch_all=True) or []


def get_active_vehicles() -> List[Dict[str, Any]]:
    """
    Get all currently parked vehicles.
    """
    return execute_query(
        "SELECT * FROM vehicle_history WHERE status = 'Parked' ORDER BY entry_time DESC",
        fetch_all=True
    ) or []


def get_vehicle_history(search: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get complete vehicle parking history with optional search filtering.
    """
    if search:
        s = f"%{search.strip().upper()}%"
        return execute_query(
            """
            SELECT * FROM vehicle_history 
            WHERE UPPER(vehicle_no) LIKE ? OR UPPER(owner_name) LIKE ?
            ORDER BY id DESC
            """,
            (s, s),
            fetch_all=True
        ) or []
    return execute_query("SELECT * FROM vehicle_history ORDER BY id DESC", fetch_all=True) or []


def find_active_vehicle(vehicle_no: str) -> Optional[Dict[str, Any]]:
    """
    Find if a vehicle is currently parked.
    """
    return execute_query(
        "SELECT * FROM vehicle_history WHERE UPPER(vehicle_no) = ? AND status = 'Parked'",
        (vehicle_no.strip().upper(),),
        fetch_one=True
    )


def park_vehicle_in_db(vehicle_no: str, owner_name: str, vehicle_type: str, slot_number: int, entry_time: str):
    """
    Record vehicle parking in slots table and vehicle_history table.
    """
    conn, engine = get_connection()
    cur = conn.cursor()
    
    if engine == "postgres":
        cur.execute("""
            UPDATE parking_slots 
            SET is_occupied = TRUE, vehicle_no = %s, owner_name = %s, vehicle_type = %s, parked_at = %s
            WHERE slot_number = %s
        """, (vehicle_no, owner_name, vehicle_type, entry_time, slot_number))
        
        cur.execute("""
            INSERT INTO vehicle_history (vehicle_no, owner_name, vehicle_type, slot_number, entry_time, status)
            VALUES (%s, %s, %s, %s, %s, 'Parked')
        """, (vehicle_no, owner_name, vehicle_type, slot_number, entry_time))
    else:
        cur.execute("""
            UPDATE parking_slots 
            SET is_occupied = 1, vehicle_no = ?, owner_name = ?, vehicle_type = ?, parked_at = ?
            WHERE slot_number = ?
        """, (vehicle_no, owner_name, vehicle_type, entry_time, slot_number))
        
        cur.execute("""
            INSERT INTO vehicle_history (vehicle_no, owner_name, vehicle_type, slot_number, entry_time, status)
            VALUES (?, ?, ?, ?, ?, 'Parked')
        """, (vehicle_no, owner_name, vehicle_type, slot_number, entry_time))

    conn.commit()
    cur.close()
    conn.close()


def exit_vehicle_from_db(slot_number: int, exit_time: str, duration_minutes: int):
    """
    Record vehicle exit in slots table and vehicle_history table.
    """
    conn, engine = get_connection()
    cur = conn.cursor()

    if engine == "postgres":
        cur.execute("""
            UPDATE parking_slots 
            SET is_occupied = FALSE, vehicle_no = NULL, owner_name = NULL, vehicle_type = NULL, parked_at = NULL
            WHERE slot_number = %s
        """, (slot_number,))

        cur.execute("""
            UPDATE vehicle_history 
            SET status = 'Exited', exit_time = %s, duration_minutes = %s
            WHERE slot_number = %s AND status = 'Parked'
        """, (exit_time, duration_minutes, slot_number))
    else:
        cur.execute("""
            UPDATE parking_slots 
            SET is_occupied = 0, vehicle_no = NULL, owner_name = NULL, vehicle_type = NULL, parked_at = NULL
            WHERE slot_number = ?
        """, (slot_number,))

        cur.execute("""
            UPDATE vehicle_history 
            SET status = 'Exited', exit_time = ?, duration_minutes = ?
            WHERE slot_number = ? AND status = 'Parked'
        """, (exit_time, duration_minutes, slot_number))

    conn.commit()
    cur.close()
    conn.close()


def reset_all_parking_data():
    """
    Reset all slots, clear active records, and rebuild the full 20-slot stack.
    """
    conn, engine = get_connection()
    cur = conn.cursor()

    if engine == "postgres":
        cur.execute("UPDATE parking_slots SET is_occupied = FALSE, vehicle_no = NULL, owner_name = NULL, vehicle_type = NULL, parked_at = NULL")
        cur.execute("UPDATE vehicle_history SET status = 'Exited' WHERE status = 'Parked'")
        cur.execute("DELETE FROM stack_items")
        
        slots_desc = list(range(TOTAL_SLOTS, 0, -1))
        for pos, slot_no in enumerate(slots_desc):
            cur.execute("INSERT INTO stack_items (position, slot_number) VALUES (%s, %s)", (pos, slot_no))
    else:
        cur.execute("UPDATE parking_slots SET is_occupied = 0, vehicle_no = NULL, owner_name = NULL, vehicle_type = NULL, parked_at = NULL")
        cur.execute("UPDATE vehicle_history SET status = 'Exited' WHERE status = 'Parked'")
        cur.execute("DELETE FROM stack_items")
        
        slots_desc = list(range(TOTAL_SLOTS, 0, -1))
        for pos, slot_no in enumerate(slots_desc):
            cur.execute("INSERT INTO stack_items (position, slot_number) VALUES (?, ?)", (pos, slot_no))

    conn.commit()
    cur.close()
    conn.close()
