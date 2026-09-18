# core/db.py

import os
import sqlite3
import queue
import threading
from contextlib import contextmanager
# ==================================================
# PATH DATABASE (SATU SUMBER)
# ==================================================

APPDATA = os.getenv("APPDATA") or os.getcwd()
APP_FOLDER = os.path.join(APPDATA, "MikrotikInvoice")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_FILE = os.getenv(
    "DB_FILE",
    os.path.join(APP_FOLDER, "database.db")
)

# =========================
# CONFIG
# =========================
POOL_SIZE = 20
TIMEOUT = 30

# =========================
# Connection Pool
# =========================
_connection_pool = queue.Queue(maxsize=POOL_SIZE)
_lock = threading.Lock()

# Penanda pool sudah dibuat
_pool_initialized = False

def pool_status(prefix=""):
    try:
        available = _connection_pool.qsize()
    except:
        available = -1

    print(
        f"{prefix} "
        f"Pool={available}/{POOL_SIZE} "
        f"Thread={threading.active_count()}"
    )

@contextmanager
def db_connection():
    conn = get_db()

    try:
        yield conn
        conn.commit()

    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise

    finally:
        release_db(conn)

def init_pool():

    global _pool_initialized

    if _pool_initialized:
        return

    with _lock:

        if _pool_initialized:
            return

        if not os.path.exists(DB_FILE):
            open(DB_FILE, "a").close()

        while not _connection_pool.empty():
            try:
                conn = _connection_pool.get_nowait()
                conn.close()
            except:
                break

        for _ in range(POOL_SIZE):
            _connection_pool.put(create_connection())

        _pool_initialized = True

        print(f"[DB] Pool initialized = {POOL_SIZE}")

def get_db():

    if not _pool_initialized:
        init_pool()

    while True:

        try:
            conn = _connection_pool.get(timeout=TIMEOUT)
        except queue.Empty:
            return create_connection()

        try:
            conn.execute("SELECT 1")
            return conn

        except sqlite3.Error:

            try:
                conn.close()
            except Exception:
                pass

            return create_connection()

def release_db(conn):
    if conn is None:
        return

    try:
        conn.execute("SELECT 1")
    except sqlite3.Error:
        try:
            conn.close()
        except:
            pass

        conn = create_connection()

    try:
        conn.rollback()
    except sqlite3.Error:
        pass

    try:
        _connection_pool.put(conn, timeout=1)
    except queue.Full:
        conn.close()

def create_connection():

    conn = sqlite3.connect(
        DB_FILE,
        timeout=60,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    # ==================================================
    # SQLITE PRAGMA
    # ==================================================
    cur = conn.cursor()

    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=60000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.execute("PRAGMA cache_size=-64000")
    cur.execute("PRAGMA mmap_size=268435456")
    cur.execute("PRAGMA wal_autocheckpoint=1000")

    return conn

# ==================================================
# HELPER TAMBAH KOLOM AMAN (UNTUK MIGRASI)
# ==================================================
def tambah_kolom_jika_belum_ada(cur, tabel, kolom, tipe):
    cur.execute(f"PRAGMA table_info({tabel})")
    cols = [r[1] for r in cur.fetchall()]

    if kolom not in cols:
        cur.execute(
            f"ALTER TABLE {tabel} ADD COLUMN {kolom} {tipe}"
        )
        print(f"[DB] + {tabel}.{kolom}")

# ==================================================
# SAVE / UPDATE APP CONFIG AMAN UNTUK DB LAMA
# ==================================================
def save_app_config_safe(user_id, data):
    """
    Simpan / update konfigurasi aplikasi ke database.
    Jika kolom baru belum ada, otomatis ditambahkan.
    """
    with db_connection() as conn:
        cur = conn.cursor()

        # Pastikan kolom baru ada
        tambah_kolom_jika_belum_ada(cur, "app_config", "store_name", "TEXT")
        tambah_kolom_jika_belum_ada(cur, "app_config", "store_address", "TEXT")
        tambah_kolom_jika_belum_ada(cur, "app_config", "footer_message", "TEXT")
        tambah_kolom_jika_belum_ada(cur, "app_config", "default_account", "TEXT")
        tambah_kolom_jika_belum_ada(cur, "app_config", "logo_file", "TEXT")
        tambah_kolom_jika_belum_ada(cur, "app_config", "qris_file", "TEXT")

        # Simpan / update data
        cur.execute("""
            INSERT INTO app_config (
                user_id, store_name, store_address,
                footer_message, default_account,
                logo_file, qris_file
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                store_name=excluded.store_name,
                store_address=excluded.store_address,
                footer_message=excluded.footer_message,
                default_account=excluded.default_account,
                logo_file=excluded.logo_file,
                qris_file=excluded.qris_file
        """, (
            user_id,
            data.get("store_name", ""),
            data.get("store_address", ""),
            data.get("footer_message", ""),
            data.get("default_account", ""),
            data.get("logo_file", ""),
            data.get("qris_file", ""),
        ))
        conn.commit()

# ==================================================
# INIT DATABASE
# ==================================================
def init_db():

    first_install = not os.path.exists(DB_FILE)

    conn = create_connection()
    cur = conn.cursor()
    print("DATABASE =", DB_FILE)
    # ================= USERS =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS licenses(
        id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        kode TEXT NOT NULL,
        paket TEXT NOT NULL,
        expired_at TEXT,
        signature TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_license_device
    ON licenses(device_id)
    """)

    # ================= MIGRASI LICENSE =================
    tambah_kolom_jika_belum_ada(cur, "licenses", "paket", "TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trial_info(
        device_id TEXT PRIMARY KEY,
        start_date TEXT
    )
    """)

    # ================= APP CONFIG =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_config(
            user_id TEXT PRIMARY KEY,
            demo_start TEXT,
            demo_status TEXT,
            app_name TEXT,
            store_name TEXT,
            store_address TEXT,
            footer_message TEXT,
            default_account TEXT,
            logo_file TEXT,
            qris_file TEXT
        )
    """)

    # ================= MIGRASI KOLOM BARU =================
    tambah_kolom_jika_belum_ada(cur, "app_config", "store_name", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "app_config", "store_address", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "app_config", "footer_message", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "app_config", "default_account", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "app_config", "logo_file", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "app_config", "qris_file", "TEXT")


    # ================= ROUTERS =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS routers(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            host TEXT,
            username TEXT,
            password TEXT,
            port INTEGER DEFAULT 8728
        )
    """)

    tambah_kolom_jika_belum_ada(
        cur,
        "routers",
        "online",
        "INTEGER DEFAULT 0"
    )

    tambah_kolom_jika_belum_ada(
        cur,
        "routers",
        "status",
        "TEXT DEFAULT 'offline'"
    )

    tambah_kolom_jika_belum_ada(
        cur,
        "routers",
        "last_check",
        "TEXT"
    )
    # ================= PELANGGAN =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pelanggan(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            router_id TEXT,
            pppoe_username TEXT,
            nama TEXT,
            paket TEXT,
            harga INTEGER,
            status TEXT,
            jatuh_tempo TEXT,
            tanggal_bayar TEXT,
            no_hp TEXT,
            source TEXT,
            terakhir_sync TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # ================= ROUTER LOG =================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS router_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,
        router_id INTEGER,
        pelanggan_id INTEGER,

        nama TEXT,
        pppoe_username TEXT,
        ip_address TEXT,

        aksi TEXT,
        status TEXT,
        keterangan TEXT,

        created_at TEXT
    )
    """)
    # ================= MIGRASI PELANGGAN =================
    tambah_kolom_jika_belum_ada(
        cur,
        "pelanggan",
        "tipe",
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "mac_address", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, "pelanggan", 
        "ip_address", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "iface", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "usage", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "router_name", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "pppoe_password", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur,
        "pelanggan",
        "source",
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "last_seen", 
        "TEXT"
    )
    tambah_kolom_jika_belum_ada(
        cur, 
        "pelanggan", 
        "comment", 
        "TEXT"
    )
    # ================= TAGIHAN =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tagihan(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            pelanggan_id TEXT,
            bulan TEXT,
            tahun INTEGER,
            jumlah INTEGER,
            status TEXT,
            tanggal_bayar TEXT,
            UNIQUE(pelanggan_id, bulan, tahun)
        )
    """)

    # ================= TRANSAKSI =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transaksi(
            id TEXT PRIMARY KEY,
            tanggal TEXT,
            pelanggan_id TEXT,
            nama TEXT,
            paket TEXT,
            harga INTEGER,
            metode TEXT,
            admin TEXT
        )
    """)

    tambah_kolom_jika_belum_ada(
        cur,
        "transaksi",
        "user_id",
        "TEXT"
    )

    tambah_kolom_jika_belum_ada(
        cur,
        "transaksi",
        "status",
        "TEXT"
    )
    # ================= DHCP CLIENTS =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dhcp_clients(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            router_id TEXT,
            ip_address TEXT,
            mac_address TEXT,
            host_name TEXT,
            status TEXT,
            last_seen TEXT,
            nama TEXT,
            paket TEXT,
            harga INTEGER,
            due TEXT,
            no_hp TEXT,
            iface TEXT
        )
    """)

    # ================= MIGRASI DHCP CLIENTS =================

    tambah_kolom_jika_belum_ada(cur, "dhcp_clients", "due", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "dhcp_clients", "no_hp", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "dhcp_clients", "iface", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "dhcp_clients", "usage", "TEXT")
    tambah_kolom_jika_belum_ada(cur, "dhcp_clients", "comment", "TEXT")
    # ================= WA LOG =================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wa_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pelanggan_id TEXT,
            no_hp TEXT,
            jenis TEXT,
            pesan TEXT,
            tanggal TEXT
        )
    """)

    # ================= INDEX =================
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pelanggan_user ON pelanggan(user_id)")
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_pelanggan_router
    ON pelanggan(router_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_pelanggan_pppoe
    ON pelanggan(pppoe_username)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_pelanggan_status
    ON pelanggan(status)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_tagihan_pelanggan
    ON tagihan(pelanggan_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_routerlog_user
    ON router_log(user_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_routerlog_router
    ON router_log(router_id)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_routerlog_created
    ON router_log(created_at)
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tagihan_user ON tagihan(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tagihan_bulan ON tagihan(bulan, tahun)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tagihan_user ON tagihan(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tagihan_bulan ON tagihan(bulan, tahun)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dhcp_user ON dhcp_clients(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_router_user ON routers(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_router_host ON routers(host)")
    cur.execute("SELECT COUNT(*) FROM users")
    cur.execute("PRAGMA optimize")
    cur.execute("ANALYZE")

    conn.commit()
    conn.close()

    if first_install:
        print("🆕 Install pertama - database baru dibuat (kosong)")
    else:
        print("📦 Database sudah ada - mode production normal")

    init_pool()