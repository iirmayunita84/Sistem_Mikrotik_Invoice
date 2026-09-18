from core.db import db_connection
from werkzeug.security import generate_password_hash

password_baru = "admin123"

with db_connection() as conn:
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password=?
        WHERE username='admin'
    """, (
        generate_password_hash(password_baru),
    ))

    conn.commit()

print("Password admin berhasil diubah")
print("Password baru: admin123")