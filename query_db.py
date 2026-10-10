# query_db.py
import sqlite3
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("kpm_tasks.db")
cursor = conn.cursor()

cursor.execute("SELECT id, name, status, assignee_name FROM tasks")
for row in cursor.fetchall():
    print(row)

conn.close()