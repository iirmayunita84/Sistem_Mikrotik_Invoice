from datetime import datetime
from core.db import db_connection


def simpan_router_log(
    user_id,
    router_id,
    pelanggan_id,
    nama,
    username,
    ip,
    aksi,
    status="BERHASIL",
    keterangan=""
):

    with db_connection() as db:

        cur = db.cursor()

        cur.execute("""
            INSERT INTO router_log(
                user_id,
                router_id,
                pelanggan_id,
                nama,
                pppoe_username,
                ip_address,
                aksi,
                status,
                keterangan,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """,(
            user_id,
            router_id,
            pelanggan_id,
            nama,
            username,
            ip,
            aksi,
            status,
            keterangan,
            datetime.now().isoformat()
        ))


        db.commit()

def get_router_logs(user_id=None, limit=500):

    with db_connection() as db:

        cur = db.cursor()

        if user_id:

            cur.execute("""
                SELECT *
                FROM router_log
                WHERE user_id=?
                ORDER BY id DESC
                LIMIT ?
            """,(user_id, limit))

        else:

            cur.execute("""
                SELECT *
                FROM router_log
                ORDER BY id DESC
                LIMIT ?
            """,(limit,))

        rows = cur.fetchall()

    return [dict(x) for x in rows]