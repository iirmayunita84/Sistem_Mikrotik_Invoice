from core.db import db_connection

with db_connection() as conn:
    cur = conn.cursor()

    cur.execute("SELECT username, password FROM users")

    for row in cur.fetchall():
        print(dict(row))