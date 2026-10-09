"""
ParkFlow Application Runner
"""
import os
import sys

from app import app, database

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  ParkFlow – Smart Parking Manager")
    print(f"  Data Structure: Python Stack (LIFO)")
    print(f"  Database Engine: {'PostgreSQL' if database.IS_POSTGRES else 'SQLite (parkflow.db)'}")
    print(f"  Server URL: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
