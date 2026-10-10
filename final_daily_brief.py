import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timedelta

conn = sqlite3.connect('kpm_tasks.db')
c = conn.cursor()

# Get current date
today = datetime.now().strftime('%Y-%m-%d')

# Total tasks
c.execute('SELECT COUNT(*) FROM tasks')
total = c.fetchone()[0]

# Status counts
c.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC')
status_data = c.fetchall()

# Overdue tasks (deadline < today, not archived, not completed)
c.execute("""
    SELECT id, name, assignee_name, deadline, status 
    FROM tasks 
    WHERE deadline < ? AND archived = 0 AND completed_date IS NULL
    ORDER BY deadline ASC
    LIMIT 3
""", (today,))
overdue = c.fetchall()

# New tasks today (tasks created today)
c.execute("""
    SELECT id, name, assignee_name, status 
    FROM tasks 
    WHERE DATE(updated_at) = ? AND archived = 0
""", (today,))
new_today = c.fetchall()

# Recent status changes (last 24h)
c.execute("""
    SELECT id, name, status, updated_at 
    FROM tasks 
    WHERE DATE(updated_at) = ? AND archived = 0
    ORDER BY updated_at DESC
""", (today,))
recent = c.fetchall()

# Top 3 critical tasks (not done, closest deadline)
c.execute("""
    SELECT id, name, assignee_name, deadline, status 
    FROM tasks 
    WHERE archived = 0 AND completed_date IS NULL AND status NOT IN ('Done', 'Completed')
    ORDER BY deadline ASC
    LIMIT 3
""")
top_priority = c.fetchall()

# Calculate summary metrics
done = sum(c for s, c in status_data if s in ['Done', 'Completed'])
in_progress = sum(c for s, c in status_data if s in ['Processing', 'Testing', 'Solution', 'Ready For QA'])
pending = sum(c for s, c in status_data if s in ['New', 'Pending', 'Pause'])

# Generate concise brief following sumarize.md format
brief = []
brief.append("## 📊 OVERVIEW")
brief.append(f"- Total Tasks: {total} | Done: {done} | In Progress: {in_progress} | Pending: {pending}")
brief.append(f"- Status: {', '.join(f'{s[:3]}:{c}' for s, c in status_data[:5])}...")
brief.append("")

brief.append("## 🚨 RISKS & OVERDUE")
if overdue:
    for t in overdue:
        days_overdue = (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(t[3][:10], '%Y-%m-%d')).days
        brief.append(f"- [{t[0]}] - {t[1][:40]} | {t[2]} | DL: {t[3][:10]} | {days_overdue}d overdue, status={t[4]}")
else:
    brief.append("- None")
brief.append("")

brief.append("## 🔄 DAILY CHANGES")
if new_today:
    brief.append(f"- New: {len(new_today)} tasks added today")
    for t in new_today[:2]:
        brief.append(f"  * [{t[0]}] - {t[1][:30]} | {t[2]}")
else:
    brief.append("- New: None")

if recent:
    brief.append("- Status Updates:")
    for t in recent[:3]:
        brief.append(f"  * [{t[0]}] - {t[1][:30]} | {t[2]}")
else:
    brief.append("- Status Updates: None")
brief.append("")

brief.append("## 🎯 NEXT PRIORITIES")
if top_priority:
    for i, t in enumerate(top_priority, 1):
        deadline = datetime.strptime(t[3][:10], '%Y-%m-%d')
        days_until = (deadline - datetime.strptime(today, '%Y-%m-%d')).days
        brief.append(f"{i}. [{t[0]}] - {t[1][:40]} | {t[2]} | DL: {t[3][:10]} ({days_until}d)")
else:
    brief.append("- No urgent priorities")

# Print the brief
print("\n".join(brief))
print(f"\n=== WORD COUNT: {sum(len(line.split()) for line in brief)} ===")

conn.close()