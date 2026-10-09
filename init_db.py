"""
Standalone database initialization script for ParkFlow.
Can be run locally or against remote PostgreSQL (Neon/Vercel Postgres) by setting DATABASE_URL.
"""
import os
import sys

import database

def main():
    print("Initializing ParkFlow database...")
    print(f"Target Engine: {'PostgreSQL' if database.IS_POSTGRES else 'SQLite (' + database.SQLITE_DB_PATH + ')'}")
    try:
        database.init_db()
        slots = database.get_all_slots()
        stack_slots = database.get_stack_slots()
        print(f"Success! {len(slots)} slots verified.")
        print(f"Stack initialized with {len(stack_slots)} available slots. Top slot (peek): {stack_slots[-1] if stack_slots else 'None'}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
