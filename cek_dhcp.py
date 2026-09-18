from core.db import init_db, db_connection

# buat koneksi pool dulu
init_db()

with db_connection() as conn:
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        id,
        nama,
        paket,
        harga,
        due,
        ip_address,
        mac_address
    FROM pelanggan
    LIMIT 20
    """)

    for x in cur.fetchall():
        print(dict(x))