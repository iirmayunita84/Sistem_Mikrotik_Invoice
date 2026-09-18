# core/logic.py
import uuid
from datetime import datetime
from core.db import (
    db_connection,
    get_db,
    release_db
)
from core.license_core import check_license, license_valid, license_valid_local
from core.comment_parser import parse_comment
from services.mikrotik_service import set_pppoe_status
from services.router_service import get_user_routers
from services.mikrotik_sync_service import sync_dhcp_clients

def get_app_config(user_id):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM app_config WHERE user_id=?", (user_id,))
        row = cur.fetchone()
    return dict(row) if row else {}
def get_mikrotik(user_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM routers
        WHERE user_id=?
    """, (user_id,))

    rows = cur.fetchall()

    release_db(conn)

    return [dict(r) for r in rows]
def get_user_id(username):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT id
            FROM users
            WHERE username=?
        """, (username,))

        row = cur.fetchone()

        return row["id"] if row else None
def get_or_create_user(username, password="", is_admin=True):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        row = cur.fetchone()

        if row:
            return dict(row)

        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        cur.execute("""
            INSERT INTO users
            (
                id,
                username,
                password,
                is_admin,
                created_at
            )
            VALUES (?,?,?,?,?)
        """, (
            user_id,
            username,
            password,
            int(is_admin),
            now
        ))


        return {
            "id": user_id,
            "username": username,
            "password": password,
            "is_admin": int(is_admin),
            "created_at": now
        }
def get_all_users():
    try:
        with db_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT 
                    id,
                    username
                FROM users
            """)

            return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        print("ERROR get_all_users:", e)
        return []
def get_user_by_username(username):
    from core.db import db_connection

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )
        row = cur.fetchone()

        return dict(row) if row else None
def load_users():
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users")
        return cur.fetchall()
def cek_demo(user_id):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT demo_start, demo_status FROM app_config WHERE user_id=?", (user_id,))
        cfg = cur.fetchone()

    if not cfg:
        return True, 2

    if cfg["demo_status"] == "PREMIUM":
        return False, 0

    demo_start = cfg["demo_start"]

    # 🔥 FIX UTAMA: validasi tipe data
    if not demo_start:
        return True, 2

    if not isinstance(demo_start, str):
        demo_start = str(demo_start)

    try:
        start = datetime.fromisoformat(demo_start)
    except Exception:
        return True, 2

    sisa = 2 - (datetime.now() - start).days
    return sisa > 0, max(sisa, 0)
def sisa_hari_demo(user_id):
    return cek_demo(user_id)[1]
def is_user_premium(user_id):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT demo_status FROM app_config WHERE user_id=?", (user_id,))
        row = cur.fetchone()
    return bool(row and row["demo_status"] == "PREMIUM")
def set_premium(user_id):
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE app_config SET demo_status='PREMIUM' WHERE user_id=?", (user_id,))
def boleh_masuk(user_id):

    # 🔥 Premium lokal selalu menang
    if license_valid_local():
        return True, "PREMIUM", None

    # 🔥 Jika ada license key valid
    if check_license():
        set_premium(user_id)
        return True, "PREMIUM", None

    # 🔥 Cek status premium di DB
    if is_user_premium(user_id):
        return True, "PREMIUM", None

    # 🔥 Cek demo dari DB
    ok_demo, sisa = cek_demo(user_id)

    if ok_demo:
        return True, "TRIAL", sisa

    # 🔒 Jika semua gagal
    return False, "LOCK", 0
def load_mikrotik_list(user_id):
    with db_connection() as db:
        cur = db.cursor()

        cur.execute("""
            SELECT
                id,
                name,
                host,
                username,
                password,
                port
            FROM routers
            WHERE user_id=?
        """, (user_id,))

        routers = []

        for r in cur.fetchall():

            router = dict(r)

            test_router = {
                "host": router["host"],
                "username": router["username"],
                "password": router.get("password") or "",
                "port": router.get("port") or 8728
            }

            online = False
            mikrotik_conn = None

            try:
                from core.mikrotik_core import konek_mikrotik

                api, mikrotik_conn = konek_mikrotik(test_router)

                if api:
                    online = True

            except Exception as e:
                print("CEK ONLINE ERROR:", e)

            finally:
                if mikrotik_conn:
                    try:
                        mikrotik_conn.disconnect()
                    except:
                        pass

            print(
                "STATUS ROUTER:",
                router["host"],
                "ONLINE=",
                online
            )

            routers.append({
                "id": router["id"],
                "name": router.get("name"),
                "label": router.get("name") or router["host"],
                "host": router["host"],
                "username": router["username"],
                "password": router["password"],
                "port": router.get("port", 8728),
                "status": "ONLINE" if online else "OFFLINE"
            })
        return routers

def simpan_dhcp_clients(user_id, router_id, leases):
    total_insert = 0
    total_update = 0
    total_skip = 0

    with db_connection() as conn:
        cur = conn.cursor()

        for l in leases:

            ip = l.get("address", "")
            mac = l.get("mac-address", "")
            host = l.get("host-name", "")
            status = str(l.get("status", "")).strip().lower()

            # Data hasil parse comment
            nama = (l.get("nama") or "").strip()
            paket = (l.get("paket") or "").strip()

            # Lewati lease yang tidak memiliki data pelanggan
            if not nama or not paket:
                total_skip += 1
                continue

            harga = l.get("harga")
            due = str(l.get("due") or "")
            no_hp = l.get("no_hp", "")
            iface = l.get("iface", "")

            now = datetime.now().isoformat()

            cur.execute("""
                SELECT id
                FROM dhcp_clients
                WHERE user_id=?
                  AND router_id=?
                  AND mac_address=?
            """, (user_id, router_id, mac))

            row = cur.fetchone()

            if row:

                cur.execute("""
                    UPDATE dhcp_clients
                    SET
                        ip_address=?,
                        host_name=?,
                        status=?,
                        nama=?,
                        paket=?,
                        harga=?,
                        due=?,
                        no_hp=?,
                        iface=?,
                        last_seen=?
                    WHERE id=?
                """, (
                    ip,
                    host,
                    status,
                    nama,
                    paket,
                    harga,
                    due,
                    no_hp,
                    iface,
                    now,
                    row["id"]
                ))

                total_update += 1

            else:

                cur.execute("""
                    INSERT INTO dhcp_clients(
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
                        iface
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    str(uuid.uuid4()),
                    user_id,
                    router_id,
                    ip,
                    mac,
                    host,
                    status,
                    now,
                    nama,
                    paket,
                    harga,
                    due,
                    no_hp,
                    iface
                ))

                total_insert += 1

    print("DHCP SYNC DONE")
    print("INSERT:", total_insert)
    print("UPDATE:", total_update)
    print("SKIP:", total_skip)

    return total_insert + total_update

def generate_pelanggan_dari_dhcp(user_id):

    total_baru = 0
    total_update = 0

    print("DEBUG CONVERT USER_ID =", user_id)

    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM dhcp_clients
            WHERE user_id=?
        """, (user_id,))

        clients = cur.fetchall()

        print("JUMLAH DHCP UNTUK CONVERT =", len(clients))

        if not clients:
            print("⚠️ Tidak ada DHCP client")
            return 0

        now = datetime.now().isoformat()

        for c in clients:

            nama = (c["nama"] or "").strip()

            if not nama:
                continue

            cur.execute("""
                SELECT id
                FROM pelanggan
                WHERE user_id=?
                AND router_id=?
                AND nama=?
            """, (
                user_id,
                c["router_id"],
                nama
            ))

            row = cur.fetchone()

            if row:

                cur.execute("""
                    UPDATE pelanggan
                    SET
                        paket=?,
                        harga=?,
                        status=?,
                        no_hp=?,
                        ip_address=?,
                        mac_address=?,
                        source=?,
                        terakhir_sync=?,
                        updated_at=?
                    WHERE id=?
                """, (
                    c["paket"],
                    c["harga"],
                    "AKTIF",
                    c["no_hp"],
                    c["ip_address"],
                    c["mac_address"],
                    "DHCP",
                    now,
                    now,
                    row["id"]
                ))

                total_update += 1

            else:

                # ==========================================
                # INSERT PELANGGAN BARU
                # ==========================================

                cur.execute("""
                    INSERT INTO pelanggan (
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
                        source,
                        terakhir_sync,
                        created_at,
                        updated_at
                    )
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    str(uuid.uuid4()),
                    user_id,
                    c["router_id"],
                    "",
                    nama,
                    c["paket"],
                    c["harga"],
                    "AKTIF",
                    c["due"],
                    c["no_hp"],
                    c["ip_address"],
                    c["mac_address"],
                    "DHCP",
                    now,
                    now,
                    now
                ))

                total_baru += 1

        conn.commit()

    print("PELANGGAN BARU :", total_baru)
    print("PELANGGAN UPDATE :", total_update)

    return total_baru + total_update
def simpan_pelanggan(user_id, data_list):
    with db_connection() as conn:
        cur = conn.cursor()

        for p in data_list:
            now = datetime.now().isoformat()
            pid = p.get("id") or str(uuid.uuid4())

            # ==========================================
            # NORMALISASI JATUH TEMPO
            # ==========================================
            jatuh_tempo = (p.get("jatuh_tempo") or "").strip()

            # Hanya terima DD/MM/YYYY atau YYYY-MM-DD.
            if jatuh_tempo:
                try:
                    jatuh_tempo = datetime.strptime(
                        jatuh_tempo,
                        "%d/%m/%Y"
                    ).strftime("%d/%m/%Y")
                except ValueError:
                    try:
                        jatuh_tempo = datetime.strptime(
                            jatuh_tempo,
                            "%Y-%m-%d"
                        ).strftime("%d/%m/%Y")
                    except ValueError:
                        jatuh_tempo = ""

            # Jika data baru tidak mempunyai tanggal valid,
            # pertahankan tanggal yang sudah tersimpan.
            if not jatuh_tempo:
                cur.execute(
                    "SELECT jatuh_tempo FROM pelanggan WHERE id=?",
                    (pid,)
                )
                old_due = cur.fetchone()

                if old_due and old_due["jatuh_tempo"]:
                    jatuh_tempo = old_due["jatuh_tempo"]
            cur.execute(
                "SELECT id FROM pelanggan WHERE id=?",
                (pid,)
            )
            exists = cur.fetchone()

            if exists:
                cur.execute("""
                    UPDATE pelanggan
                    SET
                        router_id=?,
                        pppoe_username=?,
                        nama=?,
                        paket=?,
                        harga=?,
                        status=?,
                        jatuh_tempo=?,
                        tanggal_bayar=?,
                        no_hp=?,
                        source=?,
                        terakhir_sync=?,
                        ip_address=?,
                        mac_address=?,
                        iface=?,
                        usage=?,
                        router_name=?,
                        pppoe_password=?,
                        last_seen=?,
                        comment=?,
                        updated_at=?
                    WHERE id=?
                """, (
                    p.get("router_id"),
                    p.get("pppoe_username"),
                    p.get("nama"),
                    p.get("paket"),
                    int(p.get("harga", 0)),
                    p.get("status", "AKTIF"),
                    jatuh_tempo,
                    p.get("tanggal_bayar"),
                    p.get("no_hp"),
                    p.get("source"),
                    p.get("terakhir_sync"),
                    p.get("ip_address"),
                    p.get("mac_address"),
                    p.get("iface"),
                    p.get("usage"),
                    p.get("router_name"),
                    p.get("pppoe_password"),
                    p.get("last_seen"),
                    p.get("comment"),
                    now,
                    pid
                ))

            else:
                cur.execute("""
                    INSERT INTO pelanggan (
                        id,
                        user_id,
                        router_id,
                        pppoe_username,
                        nama,
                        paket,
                        harga,
                        status,
                        jatuh_tempo,
                        tanggal_bayar,
                        no_hp,
                        source,
                        terakhir_sync,
                        ip_address,
                        mac_address,
                        iface,
                        usage,
                        router_name,
                        pppoe_password,
                        last_seen,
                        comment,
                        created_at,
                        updated_at
                    )
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    pid,
                    user_id,
                    p.get("router_id"),
                    p.get("pppoe_username"),
                    p.get("nama"),
                    p.get("paket"),
                    int(p.get("harga", 0)),
                    p.get("status", "AKTIF"),
                    jatuh_tempo,
                    p.get("tanggal_bayar"),
                    p.get("no_hp"),
                    p.get("source"),
                    p.get("terakhir_sync"),
                    p.get("ip_address"),
                    p.get("mac_address"),
                    p.get("iface"),
                    p.get("usage"),
                    p.get("router_name"),
                    p.get("pppoe_password"),
                    p.get("last_seen"),
                    p.get("comment"),
                    now,
                    now
                ))

        conn.commit()

def get_pelanggan_list(user_id, use_cache=False):
    from core.db import DB_FILE

    print("DATABASE =", DB_FILE)

    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM pelanggan")
        print(
            "TOTAL PELANGGAN =",
            cur.fetchone()[0]
        )

        bulan = datetime.now().strftime("%m")
        tahun = datetime.now().year

        cur.execute("""
            SELECT
                p.id,
                p.nama,
                p.paket,
                p.harga,
                p.status,
                p.router_id,
                p.pppoe_username,
                p.mac_address,
                p.ip_address,
                p.no_hp,
                p.jatuh_tempo,
                p.source,

                COALESCE(
                    t.status,
                    'BELUM LUNAS'
                ) AS tagihan_status,

                t.tanggal_bayar

            FROM pelanggan p

            LEFT JOIN tagihan t
                ON t.pelanggan_id = p.id
                AND t.bulan = ?
                AND t.tahun = ?

            WHERE p.user_id=?

            ORDER BY p.nama

        """, (
            bulan,
            tahun,
            user_id
        ))

        return [
            dict(row)
            for row in cur.fetchall()
        ]

def generate_tagihan(user_id):
    """
    Buat tagihan baru dari DHCP client bound
    """

    total_dibuat = 0

    bulan = datetime.now().strftime("%m")
    tahun = datetime.now().year


    with db_connection() as conn:

        cur = conn.cursor()


        cur.execute("""
            SELECT *
            FROM dhcp_clients
            WHERE user_id=?
            AND status='bound'
        """, (user_id,))


        clients = cur.fetchall()


        print("DHCP UNTUK TAGIHAN =", len(clients))


        for c in clients:

            pid = c["id"]


            cur.execute("""
                SELECT id
                FROM tagihan
                WHERE pelanggan_id=?
                AND bulan=?
                AND tahun=?
            """, (
                pid,
                bulan,
                tahun
            ))


            if cur.fetchone():
                continue


            cur.execute("""
                INSERT INTO tagihan
                (
                    id,
                    user_id,
                    pelanggan_id,
                    bulan,
                    tahun,
                    jumlah,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                pid,
                bulan,
                tahun,
                c["harga"],
                "BELUM LUNAS"
            ))


            total_dibuat += 1


    print(
        "TAGIHAN BARU DIBUAT =",
        total_dibuat
    )


    return total_dibuat
def reset_tagihan_bulanan(user_id):
    """Reset semua tagihan jadi BELUM LUNAS di awal bulan"""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE tagihan SET status='BELUM LUNAS' WHERE user_id=?", (user_id,))
def auto_unlock_lunas(user_id):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT pelanggan_id
            FROM tagihan
            WHERE status='LUNAS' AND user_id=?
        """, (user_id,))

        rows = cur.fetchall()

        for r in rows:
            cur.execute(
                "UPDATE pelanggan SET status='AKTIF' WHERE id=?",
                (r["pelanggan_id"],)
            )


        return [dict(r) for r in rows]
def auto_blokir_router(router):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT p.id, p.pppoe_username, t.status AS tagihan_status
            FROM pelanggan p
            LEFT JOIN tagihan t ON t.pelanggan_id = p.id
            WHERE p.router_id=?
        """, (router["id"],))

        rows = cur.fetchall()

        total_blokir = 0
        total_aktif = 0

        for r in rows:
            username = r["pppoe_username"]

            if not username:
                continue

            try:
                if r["tagihan_status"] == "BELUM LUNAS":
                    set_pppoe_status(router, username, aktif=False)
                    cur.execute(
                        "UPDATE pelanggan SET status='NONAKTIF' WHERE id=?",
                        (r["id"],)
                    )
                    total_blokir += 1

                elif r["tagihan_status"] == "LUNAS":
                    set_pppoe_status(router, username, aktif=True)
                    cur.execute(
                        "UPDATE pelanggan SET status='AKTIF' WHERE id=?",
                        (r["id"],)
                    )
                    total_aktif += 1

            except Exception as e:
                print(f"Gagal update {username}: {e}")

        print(
            f"[{router['host']}] Blokir={total_blokir} Aktif={total_aktif}"
        )

        return {
            "blokir": total_blokir,
            "aktif": total_aktif
        }
def auto_blokir_jatuh_tempo(user_id):
    """Blokir pelanggan yang tagihannya belum lunas"""
    with db_connection() as conn:
        cur = conn.cursor()
        bulan = datetime.now().strftime("%m")
        tahun = datetime.now().year

        cur.execute("""
            SELECT p.id, p.router_id, p.pppoe_username
            FROM pelanggan p
            JOIN tagihan t ON t.pelanggan_id = p.id
            WHERE t.status='BELUM LUNAS' AND t.bulan=? AND t.tahun=? AND p.user_id=?
        """, (bulan, tahun, user_id))

        for r in cur.fetchall():
            cur.execute("UPDATE pelanggan SET status='NONAKTIF' WHERE id=?", (r["id"],))
            if r["router_id"] and r["pppoe_username"]:

                router = get_router_by_id(
                    user_id,
                    p.get("router_id")
                )
                if router:
                    try:
                        set_pppoe_status(router, r["pppoe_username"], aktif=False)
                    except Exception as e:
                        print("Gagal blokir router:", e)
def auto_sinkron_status_mikrotik():
    """
    Sinkron status pelanggan berdasarkan tagihan bulan berjalan.
    Dipanggil scheduler harian.
    """

    with db_connection() as conn:
        cur = conn.cursor()
        bulan = datetime.now().strftime("%m")
        tahun = datetime.now().year

        cur.execute("""
            SELECT t.status as tagihan_status,
                   p.id as pelanggan_id,
                   p.router_id,
                   p.pppoe_username
            FROM tagihan t
            JOIN pelanggan p ON p.id = t.pelanggan_id
            WHERE t.bulan=? AND t.tahun=?
        """, (bulan, tahun))

        rows = cur.fetchall()
        total_blokir = 0
        total_buka = 0

        for r in rows:
            router_id = r["router_id"]
            username = r["pppoe_username"]
            if not router_id or not username:
                continue

            router = get_router_by_id(
                user_id,
                p.get("router_id")
            )
            if not router:
                continue

            try:
                if r["tagihan_status"] == "BELUM LUNAS":
                    set_pppoe_status(router, username, aktif=False)
                    cur.execute("UPDATE pelanggan SET status='NONAKTIF' WHERE id=?", (r["pelanggan_id"],))
                    total_blokir += 1
                elif r["tagihan_status"] == "LUNAS":
                    set_pppoe_status(router, username, aktif=True)
                    cur.execute("UPDATE pelanggan SET status='AKTIF' WHERE id=?", (r["pelanggan_id"],))
                    total_buka += 1
            except Exception as e:
                print("❌ Gagal sinkron:", e)

        return {
            "blokir": total_blokir,
            "aktif": total_buka
        }
    print(f"Blokir: {total_blokir} | Aktifkan: {total_buka}")

def generate_invoice_no(user_id):
    tanggal = datetime.now().strftime("%d/%m/%Y")
    pid = str(pelanggan.get("id", ""))[:6].upper()
    return f"INV-{tanggal}-{pid}"

def sync_pelanggan_status(user_id, pelanggan):

    try:
        # DHCP tidak perlu diproses sebagai PPPoE
        tipe = str(pelanggan.get("tipe") or "").upper()

        if tipe != "PPPOE":
            print(
                f"⏭️ Lewati status PPPoE: "
                f"{pelanggan.get('nama', '-')} "
                f"(tipe={tipe})"
            )
            return True

        router_id = pelanggan.get("router_id")
        username = pelanggan.get("pppoe_username")
        status = pelanggan.get("status")

        if not router_id or not username:
            return False

        router = get_router_by_id(
            user_id,
            router_id
        )

        if not router:
            return False

        aktif = status in ("AKTIF", "LUNAS")

        set_pppoe_status(
            user_id,
            router_id,
            username,
            aktif
        )

        return True

    except Exception as e:

        print(
            "❌ sync_pelanggan_status gagal:",
            e
        )

        return False

__all__ = [
    "get_or_create_user",
    "load_users",
    "cek_demo",
    "sisa_hari_demo",
    "is_user_premium",
    "set_premium",
    "get_app_config",
    "simpan_pelanggan",
    "get_router_by_id",
    "load_mikrotik_list",
    "generate_invoice_no",
    "boleh_masuk",
    "simpan_dhcp_clients",
    "sync_pelanggan_status",
    "get_all_users",
]

