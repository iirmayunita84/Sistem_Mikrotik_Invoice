# core/dhcp_core.py

from uuid import uuid4
from datetime import datetime
from core.comment_parser import parse_comment
from core.db import get_db, release_db


# ==========================================================
# SIMPAN DHCP CLIENT
# ==========================================================

def simpan_dhcp_clients(user_id, router_id, leases):

    db = get_db()

    try:

        cur = db.cursor()

        total = 0

        for lease in leases:

            comment = (lease.get("comment") or "").strip()

            if not comment:
                continue

            data = parse_comment(comment)

            if not data.get("nama"):
                continue

            nama = data.get("nama", "")
            paket = data.get("paket", "")
            harga = data.get("harga", 0)
            due = data.get("due", "")
            no_hp = data.get("no_hp", "")
            iface = data.get("iface", "")
            usage = data.get("usage", "0GB")

            lease_id = lease.get("id") or uuid4().hex

            # ==================================================
            # PENTING:
            # Jika tanggal dari MikroTik valid, gunakan.
            #
            # Jika tanggal kosong/tidak valid, jangan menimpa
            # tanggal yang sudah ada di database.
            # ==================================================

            if not due:

                old = cur.execute(
                    """
                    SELECT due
                    FROM dhcp_clients
                    WHERE id = ?
                    """,
                    (lease_id,)
                ).fetchone()

                if old and old[0]:
                    due = old[0]

            cur.execute("""

                INSERT OR REPLACE INTO dhcp_clients(

                    id,
                    user_id,
                    router_id,
                    ip_address,
                    mac_address,
                    host_name,
                    status,
                    last_seen,
                    nama,
                    paket,
                    harga,
                    due,
                    no_hp,
                    iface,
                    usage,
                    comment

                )

                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

            """, (

                lease_id,

                user_id,

                router_id,

                lease.get("address"),

                lease.get("mac-address"),

                lease.get("host-name"),

                lease.get("status"),

                datetime.now().isoformat(),

                nama,

                paket,

                harga,

                due,

                no_hp,

                iface,

                usage,

                lease.get("comment", "")

            ))

            total += 1

        db.commit()

    except Exception:

        db.rollback()

        raise

    finally:

        release_db(db)

    return total

# ==========================================================
# GET DHCP
# ==========================================================
def get_dhcp_clients(user_id):

    db = get_db()

    try:

        cur = db.cursor()

        cur.execute("""

            SELECT *

            FROM dhcp_clients

            WHERE user_id=?

            ORDER BY nama

        """,(user_id,))

        return cur.fetchall()

    finally:

        release_db(db)

# ==========================================================
# DHCP -> PELANGGAN
# ==========================================================
def convert_dhcp_to_pelanggan(user_id):

    db = get_db()

    try:

        cur = db.cursor()

        cur.execute("""
            SELECT *
            FROM dhcp_clients
            WHERE user_id=?
            AND comment IS NOT NULL
            AND comment <> ''
        """, (user_id,))

        dhcps = cur.fetchall()

        total_insert = 0
        total_update = 0

        for d in dhcps:

            row = None

            # =====================================
            # Cari berdasarkan MAC Address
            # =====================================
            mac = (d["mac_address"] or "").strip()

            if mac:
                cur.execute("""
                    SELECT id
                    FROM pelanggan
                    WHERE user_id=?
                    AND router_id=?
                    AND mac_address=?
                """, (
                    user_id,
                    d["router_id"],
                    mac
                ))
                row = cur.fetchone()

            # =====================================
            # Kalau belum ketemu cari berdasarkan IP
            # =====================================
            if not row:

                cur.execute("""
                    SELECT id
                    FROM pelanggan
                    WHERE user_id=?
                    AND router_id=?
                    AND ip_address=?
                """, (
                    user_id,
                    d["router_id"],
                    d["ip_address"]
                ))

                row = cur.fetchone()

            # =====================================
            # Kalau belum ketemu cari berdasarkan Nama
            # =====================================
            if not row:

                cur.execute("""
                    SELECT id
                    FROM pelanggan
                    WHERE user_id=?
                    AND router_id=?
                    AND nama=?
                """, (
                    user_id,
                    d["router_id"],
                    d["nama"]
                ))

                row = cur.fetchone()

            # =====================================
            # UPDATE
            # =====================================
            # =====================================
            # JATUH TEMPO
            # =====================================
            due = (d["due"] or "").strip()

            # Jika tanggal dari DHCP kosong/invalid,
            # pertahankan tanggal pelanggan yang sudah ada.
            if row and not due:
                cur.execute("""
                    SELECT jatuh_tempo
                    FROM pelanggan
                    WHERE id=?
                """, (row["id"],))

                old_due = cur.fetchone()

                if old_due and old_due["jatuh_tempo"]:
                    due = old_due["jatuh_tempo"]

            if row:

                print(f"🔄 UPDATE : {d['nama']}")

                cur.execute("""
                    UPDATE pelanggan
                    SET
                        nama=?,
                        paket=?,
                        harga=?,
                        jatuh_tempo=?,
                        no_hp=?,
                        ip_address=?,
                        mac_address=?,
                        iface=?,
                        usage=?,
                        comment=?,
                        updated_at=?
                    WHERE id=?
                """, (
                    d["nama"] or d["host_name"] or d["ip_address"],
                    d["paket"],
                    d["harga"] or 0,
                    due,
                    d["no_hp"],
                    d["ip_address"],
                    d["mac_address"],
                    d["iface"],
                    d["usage"],
                    d["comment"],
                    datetime.now().isoformat(),
                    row["id"]
                ))

                total_update += 1
                continue

            # =====================================
            # INSERT
            # =====================================
            print(f"➕ INSERT : {d['nama']}")

            cur.execute("""
                INSERT INTO pelanggan(

                    id,
                    user_id,
                    router_id,
                    pppoe_username,
                    nama,
                    paket,
                    harga,
                    status,
                    jatuh_tempo,
                    no_hp,
                    ip_address,
                    mac_address,
                    iface,
                    usage,
                    source,
                    comment,
                    created_at,
                    updated_at

                )

                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

            """, (

                uuid4().hex,

                user_id,

                d["router_id"],

                "",

                d["nama"] or d["host_name"] or d["ip_address"],

                d["paket"],

                d["harga"] or 0,

                "Belum Bayar",

                d["due"],

                d["no_hp"],

                d["ip_address"],

                d["mac_address"],

                d["iface"],

                d["usage"],

                "DHCP",

                d["comment"],

                datetime.now().isoformat(),

                datetime.now().isoformat()

            ))

            total_insert += 1

        db.commit()
        cur.execute("""
        SELECT user_id, COUNT(*) AS total
        FROM pelanggan
        GROUP BY user_id
        """)

        print("===== DATA PELANGGAN =====")
        for r in cur.fetchall():
            print(dict(r))
        print("==========================")
        print("=" * 50)
        print(f"JUMLAH DHCP UNTUK CONVERT = {len(dhcps)}")
        print(f"PELANGGAN BARU   : {total_insert}")
        print(f"PELANGGAN UPDATE : {total_update}")
        print("=" * 50)

        return total_insert

    except Exception:

        db.rollback()
        raise

    finally:

        release_db(db)