import os
import sys

# Ensure project root directory is in sys.path so modules like app, services, database can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app

# Vercel serverless entrypoint
# The 'app' object is exposed as the WSGI callable
if __name__ == "__main__":
    app.run()
