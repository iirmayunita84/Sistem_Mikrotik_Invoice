#ore/transaksi_core.py
import uuid
from datetime import datetime

from core.db import get_db, release_db
from core.core_pelanggan import refresh_pelanggan_cache


# =========================================================
# SIMPAN TRANSAKSI
# =========================================================

def simpan_transaksi(data):

    conn = get_db()

    try:

        cur = conn.cursor()

        cur.execute("""
            INSERT INTO transaksi
            (
                id,
                user_id,
                tanggal,
                pelanggan_id,
                nama,
                paket,
                harga,
                metode,
                admin,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            data.get("id") or uuid.uuid4().hex[:8],

            data.get("user_id"),

            data.get("tanggal")
            or datetime.now().strftime("%d/%m/%Y %H:%M:%S"),

            data.get("pelanggan_id"),

            data.get("nama"),

            data.get("paket"),

            int(data.get("harga") or 0),

            data.get("metode"),

            data.get("admin"),

            data.get("status") or "LUNAS",
        ))

        conn.commit()

        print(
            "Transaksi tersimpan: "
            f"{data.get('nama')} | "
            f"Rp {int(data.get('harga') or 0):,}"
        )

        return True

    except Exception as e:

        conn.rollback()

        print(
            "Gagal simpan transaksi:",
            e
        )

        raise

    finally:

        release_db(conn)


# =========================================================
# 5 TRANSAKSI TERAKHIR
# Dipakai untuk Dashboard
# =========================================================

def get_transaksi_terakhir(user_id=None):

    conn = get_db()

    try:

        cur = conn.cursor()

        if user_id:

            cur.execute("""
                SELECT *
                FROM transaksi
                WHERE user_id=?
                ORDER BY rowid DESC
                LIMIT 5
            """, (user_id,))

        else:

            cur.execute("""
                SELECT *
                FROM transaksi
                ORDER BY rowid DESC
                LIMIT 5
            """)

        return [
            dict(row)
            for row in cur.fetchall()
        ]

    finally:

        release_db(conn)


# =========================================================
# SEMUA TRANSAKSI
# Dipakai halaman /transaksi
# =========================================================

def get_semua_transaksi(user_id=None):

    conn = get_db()

    try:

        cur = conn.cursor()

        if user_id:

            cur.execute("""
                SELECT *
                FROM transaksi
                WHERE user_id=?
                ORDER BY rowid DESC
            """, (user_id,))

        else:

            cur.execute("""
                SELECT *
                FROM transaksi
                ORDER BY rowid DESC
            """)

        return [
            dict(row)
            for row in cur.fetchall()
        ]

    finally:

        release_db(conn)


# =========================================================
# KOMPATIBILITAS
# Fungsi lama tetap tersedia
# =========================================================

def get_transaksi_list(user_id=None):

    return get_transaksi_terakhir(user_id)


# =========================================================
# SETELAH PEMBAYARAN
# =========================================================

def pembayaran_selesai(user_id):

    """
    Membersihkan cache pelanggan
    setelah pembayaran berhasil.
    """

    refresh_pelanggan_cache(user_id)

