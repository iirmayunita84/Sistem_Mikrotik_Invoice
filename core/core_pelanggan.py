# core/core_pelanggan.py

import uuid
from datetime import datetime
from core.db import get_db, release_db
# ==========================================
# NORMALISASI TANGGAL
# ==========================================
def normalisasi_jatuh_tempo(value):
    if value in (None, ""):
        return ""

    value = str(value).strip()

    # DD/MM/YYYY
    try:
        return datetime.strptime(
            value,
            "%d/%m/%Y"
        ).strftime("%d/%m/%Y")
    except ValueError:
        pass

    # YYYY-MM-DD
    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
    except ValueError:
        pass

    # Format lain dianggap tidak valid
    return ""
# ================= CACHE =================
CACHE_PELANGGAN = {}
# ================= GET / CACHE =================
def get_pelanggan_list(user_id, use_cache=True):

    global CACHE_PELANGGAN

    if not user_id:
        return []

    if use_cache:
        cache = CACHE_PELANGGAN.get(user_id)
        if cache is not None:
            return cache

    data = get_pelanggan_file(user_id) or []
    CACHE_PELANGGAN[user_id] = data
    return data

def refresh_pelanggan_cache(user_id):

    global CACHE_PELANGGAN

    data = get_pelanggan_file(user_id) or []
    CACHE_PELANGGAN[user_id] = data
    return data

def simpan_pelanggan(user_id, data):
    from core.logic import simpan_pelanggan as logic_simpan_pelanggan
    return logic_simpan_pelanggan(user_id, data)

# ================= FILE / DB RAW =================
def get_pelanggan_file(user_id=None):

    conn = get_db()

    try:
        cur = conn.cursor()

        if user_id:
            cur.execute(
                "SELECT * FROM pelanggan WHERE user_id=? ORDER BY nama",
                (user_id,)
            )
        else:
            cur.execute(
                "SELECT * FROM pelanggan ORDER BY nama"
            )

        return [dict(r) for r in cur.fetchall()]

    finally:
        release_db(conn)

def get_pelanggan_by_id(pid, user_id=None):

    conn = get_db()

    try:
        cur = conn.cursor()

        if user_id:
            cur.execute(
                """
                SELECT *
                FROM pelanggan
                WHERE id=?
                AND user_id=?
                """,
                (pid, user_id)
            )
        else:
            cur.execute(
                """
                SELECT *
                FROM pelanggan
                WHERE id=?
                """,
                (pid,)
            )

        row = cur.fetchone()

        if not row:
            return None

        pelanggan = dict(row)

        # ==========================================
        # AMBIL TANGGAL BAYAR TERAKHIR
        # ==========================================

        cur.execute(
            """
            SELECT tanggal_bayar
            FROM tagihan
            WHERE pelanggan_id=?
            AND tanggal_bayar IS NOT NULL
            AND tanggal_bayar != ''
            ORDER BY id DESC
            LIMIT 1
            """,
            (pid,)
        )

        bayar = cur.fetchone()

        if bayar:
            pelanggan["tanggal_bayar"] = (
                bayar["tanggal_bayar"]
                if isinstance(bayar, dict)
                else bayar[0]
            )
        else:
            # Jika belum ada tanggal bayar di tabel tagihan,
            # gunakan tanggal bayar yang tersimpan di pelanggan
            pelanggan["tanggal_bayar"] = (
                pelanggan.get("tanggal_bayar")
                or "-"
            )

        # ==========================================
        # PEMAKAIAN
        # ==========================================

        usage = (
            pelanggan.get("usage")
            or pelanggan.get("usage_last")
            or "0GB"
        )

        if str(usage).lower() in ("none", "", "-", "null"):
            usage = "0GB"

        pelanggan["usage"] = str(usage)
        pelanggan["usage_invoice"] = str(usage)

        return pelanggan

    finally:
        release_db(conn)
 
def get_pelanggan_by_ip(ip_address):
    """
    Mencari pelanggan berdasarkan IP Address.
    Menggunakan database pool project.
    """

    if not ip_address:
        return None

    conn = None

    try:

        conn = get_db()

        row = conn.execute(
            """
            SELECT *
            FROM pelanggan
            WHERE ip_address = ?
            LIMIT 1
            """,
            (ip_address,)
        ).fetchone()

        if not row:
            return None

        return dict(row)

    except Exception as e:

        print(
            f"❌ Gagal mencari pelanggan berdasarkan IP "
            f"{ip_address}: {e}"
        )

        return None

    finally:

        if conn:
            try:
                release_db(conn)
            except Exception:
                pass

# ================= CRUD =================

def tambah_pelanggan(user_id, data):

    conn = get_db()

    try:
        cur = conn.cursor()

        now = datetime.now().isoformat()
        pid = uuid.uuid4().hex[:8]
        jatuh_tempo = normalisasi_jatuh_tempo(
            data.get("jatuh_tempo")
        )
        tipe = (
            data.get("tipe") or "DHCP"
        ).strip().upper()

        cur.execute("""
            INSERT INTO pelanggan
            (
                id,
                user_id,
                router_id,
                tipe,
                pppoe_username,
                pppoe_password,
                nama,
                paket,
                harga,
                status,
                jatuh_tempo,
                tanggal_bayar,
                no_hp,
                ip_address,
                mac_address,
                iface,
                usage,
                comment,
                created_at,
                updated_at
            )
            VALUES (
                ?,?,?,?,?,?,
                ?,?,?,?,
                ?,?,?,?,
                ?,?,?,?,
                ?,?
            )
        """, (
            pid,
            user_id,
            data.get("router_id"),

            tipe,

            data.get("pppoe_username") or "",
            data.get("pppoe_password") or "",

            data.get("nama"),
            data.get("paket"),
            int(data.get("harga") or 0),

            data.get("status", "AKTIF"),
            jatuh_tempo,
            None,

            data.get("no_hp") or "",

            data.get("ip_address") or "",
            data.get("mac_address") or "",

            data.get("iface") or "",
            data.get("usage", "0GB"),

            data.get("comment") or "",

            now,
            now
        ))

        conn.commit()

        CACHE_PELANGGAN.pop(
            user_id,
            None
        )

        print("=" * 50)
        print("✅ PELANGGAN BERHASIL DISIMPAN")
        print("ID       :", pid)
        print("Nama     :", data.get("nama"))
        print("Tipe     :", tipe)
        print("IP       :", data.get("ip_address"))
        print("MAC      :", data.get("mac_address"))
        print("Router   :", data.get("router_id"))
        print("=" * 50)

        return pid

    finally:
        release_db(conn)

def hapus_pelanggan(user_id, pid):

    conn=get_db()

    try:

        cur=conn.cursor()

        cur.execute("""
        DELETE FROM pelanggan
        WHERE id=?
        AND user_id=?
        """,(
            pid,
            user_id
        ))

        conn.commit()

        CACHE_PELANGGAN.pop(user_id, None)

    finally:
        release_db(conn)

def update_operasional(user_id, pid, status):

    conn = get_db()

    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE pelanggan
            SET
                status=?,
                updated_at=?
            WHERE id=?
            AND user_id=?
        """, (
            status,
            datetime.now().isoformat(),
            pid,
            user_id
        ))

        conn.commit()

        CACHE_PELANGGAN.pop(user_id, None)

    finally:
        release_db(conn)

def update_pelanggan(user_id, pid, data):

    conn = get_db()

    try:
        cur = conn.cursor()

        now = datetime.now().isoformat()

        tipe = (
            data.get("tipe") or "DHCP"
        ).strip().upper()

        # ==========================================
        # NORMALISASI JATUH TEMPO
        # ==========================================


        jatuh_tempo = normalisasi_jatuh_tempo(
            data.get("jatuh_tempo")
        )

        # ==========================================
        # UPDATE DATABASE
        # ==========================================

        cur.execute("""
            UPDATE pelanggan
            SET

                router_id=?,

                tipe=?,

                pppoe_username=?,
                pppoe_password=?,

                nama=?,
                paket=?,
                harga=?,
                status=?,

                no_hp=?,
                jatuh_tempo=?,

                ip_address=?,
                mac_address=?,

                iface=?,
                usage=?,

                updated_at=?

            WHERE id=?
            AND user_id=?
        """, (

            data.get("router_id"),

            tipe,

            data.get("pppoe_username") or "",
            data.get("pppoe_password") or "",

            data.get("nama"),
            data.get("paket"),
            int(data.get("harga") or 0),
            data.get("status", "AKTIF"),

            data.get("no_hp") or "",
            jatuh_tempo,

            data.get("ip_address") or "",
            data.get("mac_address") or "",

            data.get("iface") or "",
            data.get("usage", "0GB"),

            now,

            pid,
            user_id
        ))

        conn.commit()

        # ==========================================
        # BERSIHKAN CACHE
        # ==========================================

        CACHE_PELANGGAN.pop(
            user_id,
            None
        )

        print("=" * 50)
        print("🔄 PELANGGAN BERHASIL DIUPDATE")
        print("ID       :", pid)
        print("Tipe     :", tipe)
        print("Nama     :", data.get("nama"))
        print("Jatuh Tempo :", jatuh_tempo)
        print("=" * 50)

    finally:
        release_db(conn)

def generate_invoice_bulanan(pelanggan):
    """
    Membuat tagihan bulanan jika belum ada.

    pelanggan = dict pelanggan
    """

    conn = get_db()

    try:
        cur = conn.cursor()

        sekarang = datetime.now()

        bulan = f"{sekarang.month:02d}"
        tahun = sekarang.year

        # cek apakah invoice sudah ada
        cur.execute("""
            SELECT id
            FROM tagihan
            WHERE pelanggan_id=?
            AND bulan=?
            AND tahun=?
        """, (
            pelanggan["id"],
            bulan,
            tahun
        ))

        if cur.fetchone():
            return False

        cur.execute("""
            INSERT INTO tagihan(
                id,
                user_id,
                pelanggan_id,
                bulan,
                tahun,
                jumlah,
                status,
                tanggal_bayar
            )
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            uuid.uuid4().hex[:8],
            pelanggan["user_id"],
            pelanggan["id"],
            bulan,
            tahun,
            int(pelanggan.get("harga", 0)),
            "BELUM LUNAS",
            None
        ))

        conn.commit()

        print(
            f"🧾 Invoice dibuat : "
            f"{pelanggan['nama']} "
            f"{bulan} {tahun}"
        )

        return True

    finally:
        release_db(conn)

def get_transaksi_list(user_id=None):

    conn = get_db()

    try:
        cur = conn.cursor()

        if user_id:
            cur.execute("""
                SELECT *
                FROM transaksi
                WHERE user_id=?
                ORDER BY tanggal DESC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT *
                FROM transaksi
                ORDER BY tanggal DESC
            """)

        return [dict(r) for r in cur.fetchall()]

    finally:
        release_db(conn)

def generate_invoice_semua(user_id):
    pelanggan = get_pelanggan_list(user_id=user_id)

    total = 0

    for p in pelanggan:
        if generate_invoice_bulanan(p):
            total += 1

    print(f"Total invoice dibuat : {total}")

    return total