from core.db import db_connection, init_db

# supaya connection pool aktif
init_db()

with db_connection() as conn:
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username=?", ("admin",))
    row = cur.fetchone()

    if not row:
        print("User admin tidak ditemukan")
        exit()

    uid = row["id"]

    print("UUID =", uid)

    cur.execute(
        "UPDATE routers SET user_id=? WHERE user_id='admin'",
        (uid,)
    )
    print("Routers :", cur.rowcount)

    cur.execute(
        "UPDATE dhcp_clients SET user_id=? WHERE user_id='admin'",
        (uid,)
    )
    print("DHCP :", cur.rowcount)

    cur.execute(
        "UPDATE pelanggan SET user_id=? WHERE user_id='admin'",
        (uid,)
    )
    print("Pelanggan :", cur.rowcount)

    cur.execute(
        "UPDATE tagihan SET user_id=? WHERE user_id='admin'",
        (uid,)
    )
    print("Tagihan :", cur.rowcount)

    conn.commit()

print("✅ Migrasi selesai")