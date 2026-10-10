import sqlite3
import requests
import html
import json
import re
import sys
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()   

# Đảm bảo in tiếng Việt và emoji không bị lỗi UnicodeEncodeError trên Windows CMD
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def clean_description(raw_desc_str):
    """Làm sạch triệt để chuỗi JSON/HTML description thành Plain Text ngắn gọn"""
    if not raw_desc_str:
        return ""

    data = raw_desc_str

    # 1. Thử decode JSON liên tục nếu dữ liệu bị mã hóa chuỗi nhiều lần (Double/Triple JSON string)
    for _ in range(3):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                break
        else:
            break

    extracted_texts = []

    # 2. Trường hợp là danh sách khối EditorJS (list of dicts)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Lấy text trong item["data"]["text"]
                text_val = item.get("data", {}).get("text", "")
                if text_val:
                    extracted_texts.append(str(text_val))
            elif isinstance(item, str):
                extracted_texts.append(item)

    # 3. Trường hợp là dictionary đơn lẻ
    elif isinstance(data, dict):
        text_val = data.get("text", "") or data.get("data", {}).get("text", "")
        if text_val:
            extracted_texts.append(str(text_val))

    # 4. Trường hợp là văn bản thuần / HTML string
    elif isinstance(data, str):
        extracted_texts.append(data)

    # Ghép các dòng lại thành một văn bản duy nhất
    combined_text = "\n".join(extracted_texts) if extracted_texts else str(data)

    # 5. Dọn dẹp thẻ HTML, ký tự mã hóa và khoảng trắng dư thừa
    clean_text = re.sub(r"<[^>]+>", " ", combined_text)  # Bỏ thẻ HTML như <code>, <b>
    clean_text = html.unescape(clean_text)  # Decode &quot;, &amp;
    clean_text = clean_text.replace('\\"', '"').replace("\\n", "\n")
    clean_text = re.sub(r"[ \t]+", " ", clean_text)  # Xóa bớt khoảng trắng vô nghĩa
    clean_text = re.sub(r"\n\s*\n", "\n", clean_text)  # Xóa dòng trống thừa

    return clean_text.strip()

# 1. Cấu hình thông tin API
URL = os.getenv("URL")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Cookie": "tk_or=%22%22; tk_lr=%22%22",
}

# Cấu hình Token và Chat ID Telegram của bạn
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Bảng ánh xạ ID người dùng sang tên thực tế (Dựa theo danh sách task assign trên web)
# Bạn có thể điều chỉnh lại tên cho đúng với ID tương ứng trong team của bạn
USER_MAP = {
    1: "admin",
3: "yiqi",
5: "emma",
6: "kei",
31: "janetran",
1073: "nguyenvankien",
2084: "dinhtuan",
3085: "bacnguyen",
4093: "hongmanh",
4100: "spencer",
4101: "donovan",
4103: "daryl",
4105: "wind",
4119: "freya",
4131: "mark",
4133: "joel_low",
4137: "minn_hoang",
4139: "edward",
4144: "danny",
4151: "anand",
4152: "joanne",
4155: "Skye",
4156: "rogerteo",
4163: "likun",
4165: "fizly",
4171: "Claudine",
4172: "neo_trunganh",
4173: "davidlooi",
4175: "garygay",
4176: "Rizwan",
4179: "Annie",
4182: "harley_pham",
4188: "JianZhe",
4190: "ap_stpl",
4191: "Flora",
4192: "Alvin",
4195: "Rachael",
4197: "nurhanis",
4199: "shawnumipig",
4200: "mia_vu",
4203: "Simon",
4204: "johnlim",
4208: "Rose",
4209: "mary_ngoctu",
4211: "rachel",
4212: "stpl_admin",
4213: "suri_tran",
4217: "tina",
4218: "jf_liu",
4219: "Sunny",
4220: "jasmine_sim",
4221: "Jayson_Chua@simplifiedtec.com",
4222: "aloysius_chan",
4224: "jacqueline",
4225: "Claude",
4226: "kimlee",
    # Các ID khác hệ thống sẽ tự hiển thị dạng "User #ID" nếu chưa có trong map
}


def setup_database():
  """Khởi tạo database SQLite gồm bảng tasks, task_history và comments"""
  conn = sqlite3.connect("kpm_tasks.db")
  cursor = conn.cursor()

  # 1. Bảng lưu trạng thái task
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            project_id INTEGER,
            project_name TEXT,
            status TEXT,
            assignee_id INTEGER,
            assignee_name TEXT,
            start_date TEXT,
            deadline TEXT,
            completed_date TEXT,
            archived INTEGER,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

  # 2. Bảng lưu lịch sử thay đổi task
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            field_changed TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

  # 3. Bảng lưu comments của task (dựa theo cấu trúc JSON bạn cung cấp)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            content TEXT,
            create_date TEXT,
            creator_id INTEGER,
            creator_name TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

  conn.commit()
  conn.close()


def send_telegram_notification(title, detail_text, task_id, assignee=""):
  """Gửi thông báo sang Telegram"""
  task_url = f"https://kpm.oanglelab.com/task/{task_id}"
  message = (
      f"<b>{title}</b>\n\n"
      f"📌 <b>Chi tiết:</b> {detail_text}\n"
      f"👤 <b>Người phụ trách:</b> {assignee}\n"
      f"🔗 <a href='{task_url}'>Xem Task trên KPM</a>"
  )
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message,
      "parse_mode": "HTML",
      "disable_web_page_preview": True,
  }
  try:
    requests.post(url, json=payload)
  except Exception as e:
    print(f"Lỗi gửi Telegram: {e}")


def fetch_and_save_tasks():
  print("Đang tải dữ liệu từ KPM...")
  response = requests.get(URL, headers=HEADERS)

  if response.status_code != 200:
    print(f"❌ Kết nối thất bại. Mã lỗi HTTP: {response.status_code}")
    return

  tasks_data = response.json()
  print(f"✅ Tải thành công {len(tasks_data)} tasks.")

  conn = sqlite3.connect("kpm_tasks.db")
  cursor = conn.cursor()

  for item in tasks_data:
    task_id = item.get("id")
    name = item.get("name")
    raw_desc = item.get("description", "")
    description = str(raw_desc) if raw_desc else ""

    project_id = item.get("projectId")
    project_name = item.get("projectName")
    status = item.get("list", {}).get("name", "Unknown")

    assignee_id = item.get("userId")
    USER_MAP = {}  # Thêm mapping user của bạn nếu có
    assignee_name = (
        USER_MAP.get(assignee_id, f"User #{assignee_id}")
        if assignee_id
        else "Unassigned"
    )

    start_date = item.get("startDate")
    deadline = item.get("deadline")
    completed_date = item.get("completedDate")
    archived = 1 if item.get("archived") else 0

    # --- 1. XỬ LÝ LƯU TASK & KIỂM TRA BIẾN ĐỘNG ---
    cursor.execute(
        "SELECT status, assignee_name FROM tasks WHERE id = ?", (task_id,)
    )
    old_task = cursor.fetchone()

    if old_task:
      old_status, old_assignee = old_task[0], old_task[1]
      if old_status != status:
        send_telegram_notification(
            f"🔔 Task #{task_id} Đổi Trạng Thái",
            f"Từ <b>{old_status}</b> ➔ <b>{status}</b> ({name})",
            task_id,
            assignee_name,
        )
        cursor.execute(
            """
                INSERT INTO task_history (task_id, field_changed, old_value, new_value)
                VALUES (?, 'status', ?, ?)
            """,
            (task_id, old_status, status),
        )
    else:
      send_telegram_notification(
          f"✨ Task Mới Được Tạo #{task_id}",
          f"Tên Task: <b>{name}</b>",
          task_id,
          assignee_name,
      )
      cursor.execute(
          """
            INSERT INTO task_history (task_id, field_changed, old_value, new_value)
            VALUES (?, 'created', NULL, 'New Task')
        """,
          (task_id,),
      )

    # Upsert vào bảng tasks
    cursor.execute(
        """
        INSERT INTO tasks 
        (id, name, description, project_id, project_name, status, assignee_id, assignee_name, start_date, deadline, completed_date, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            status=excluded.status,
            assignee_id=excluded.assignee_id,
            assignee_name=excluded.assignee_name,
            deadline=excluded.deadline,
            completed_date=excluded.completed_date,
            archived=excluded.archived,
            updated_at=CURRENT_TIMESTAMP
    """,
        (
            task_id,
            name,
            description,
            project_id,
            project_name,
            status,
            assignee_id,
            assignee_name,
            start_date,
            deadline,
            completed_date,
            archived,
        ),
    )

    # --- 2. XỬ LÝ LƯU COMMENTS ---
    comments_list = item.get("comments", [])
    for comment in comments_list:
      comment_id = comment.get("id")
      comment_content = comment.get("content")
      create_date = comment.get("createDate")
      creator_id = comment.get("creatorId")

      # Lấy tên người comment từ object 'creator'
      creator_obj = comment.get("creator")
      creator_name = (
          creator_obj.get("displayName") if creator_obj else "Unknown"
      )

      # Kiểm tra xem comment này đã tồn tại chưa để phát hiện comment mới
      cursor.execute("SELECT id FROM comments WHERE id = ?", (comment_id,))
      existing_comment = cursor.fetchone()

      if not existing_comment:
        # Nếu là comment mới, bạn có thể bắn thông báo Telegram nếu muốn
        print(f"💬 Phát hiện comment mới #{comment_id} từ {creator_name}")
        # send_telegram_notification(f"💬 Comment mới trên Task #{task_id}", f"<b>{creator_name}</b> đã bình luận.", task_id, assignee_name)

      # Lưu hoặc cập nhật comment vào database
      cursor.execute(
          """
            INSERT INTO comments (id, task_id, content, create_date, creator_id, creator_name)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                content=excluded.content,
                create_date=excluded.create_date
        """,
          (
              comment_id,
              task_id,
              comment_content,
              create_date,
              creator_id,
              creator_name,
          ),
      )

  conn.commit()
  conn.close()
  print("✅ Đã cập nhật xong dữ liệu Tasks và Comments vào kpm_tasks.db!")


if __name__ == "__main__":
  setup_database()
  fetch_and_save_tasks()