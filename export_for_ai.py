import sqlite3

conn = sqlite3.connect("kpm_tasks.db")
cursor = conn.cursor()

# Lấy dữ liệu cần thiết
cursor.execute(
    "SELECT id, name, status, assignee_name, deadline, description FROM tasks WHERE archived = 0"
)
rows = cursor.fetchall()

with open("tasks_context.txt", "w", encoding="utf-8") as f:
    for row in rows:
        f.write(
            f"ID: {row[0]} | Task: {row[1]} | Status: {row[2]} | Assignee: {row[3]} | Deadline: {row[4]}\n"
        )
        if row[5]:
            f.write(f"Desc: {row[5]}\n")
        f.write("-" * 40 + "\n")

conn.close()
print("✅ Đã xuất dữ liệu ra tasks_context.txt thành công!")