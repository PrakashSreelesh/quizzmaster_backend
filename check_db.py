import os
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.database import engine
from sqlalchemy import text

print(f"DEBUG: DATABASE_URL = {settings.DATABASE_URL}")

with engine.connect() as conn:
    try:
        result = conn.execute(text("SELECT username, email FROM users"))
        users = result.fetchall()
        print(f"DEBUG: Users in DB ({len(users)}):")
        for u in users:
            print(f" - {u.username} ({u.email})")
    except Exception as e:
        print(f"ERROR: {e}")
