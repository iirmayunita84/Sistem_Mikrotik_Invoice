# cek_router.py
from core.db import db_connection

with db_connection() as conn:
    cur = conn.cursor()

    print("=== STRUKTUR TABEL ROUTERS ===")

    cur.execute("PRAGMA table_info(routers)")
    for row in cur.fetchall():
        print(dict(row))

    print("\n=== DATA ROUTERS ===")

    cur.execute("SELECT * FROM routers")
    for row in cur.fetchall():
        print(dict(row))