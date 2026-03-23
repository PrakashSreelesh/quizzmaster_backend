import sqlite3
import os

db_path = "quiz_platform.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(quizzes)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns in quizzes table: {columns}")
    conn.close()
else:
    print(f"Database file NOT FOUND at {db_path}")
