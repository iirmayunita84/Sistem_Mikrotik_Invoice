from core.db import DB_FILE, create_connection

print("DATABASE =", DB_FILE)

conn = create_connection()
cur = conn.cursor()

cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""")

tables = cur.fetchall()

print("=== DAFTAR TABEL ===")
for t in tables:
    print(t["name"])
print("\n=== USERS ===")

try:
    cur.execute("""
        SELECT id, username, is_admin
        FROM users
    """)

    rows = cur.fetchall()

    print("Jumlah user:", len(rows))

    for row in rows:
        print(dict(row))

except Exception as e:
    print("ERROR:", e)

conn.close()