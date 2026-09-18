#buat_admin.py
import sqlite3
import os
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash

db_file = os.path.join(
    os.getenv("APPDATA"),
    "MikrotikInvoice",
    "database.db"
)

conn = sqlite3.connect(db_file)
cur = conn.cursor()

username = "admin"
password = "admin123"

cur.execute(
    "SELECT COUNT(*) FROM users WHERE username=?",
    (username,)
)

if cur.fetchone()[0] == 0:
    cur.execute("""
        INSERT INTO users(
            id,
            username,
            password,
            is_admin,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        uuid.uuid4().hex,
        username,
        generate_password_hash(password),
        1,
        datetime.now().isoformat()
    ))

    conn.commit()
    print("✅ Admin berhasil dibuat")
else:
    print("ℹ️ Admin sudah ada")

conn.close()