# core/license_core.py

import uuid
import hashlib
import hmac
import secrets
import threading
import calendar
import json
import base64
import zlib

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from core.db import get_db, release_db
from secret_parts import _P1, _P2, _P3


# =========================================================
# CONFIG
# =========================================================

SECRET_KEY = _P1 + _P2 + _P3

MASTER_KEY = (
    _P3 +
    _P1 +
    _P2 +
    "Invoice2026"
)


# =========================================================
# LICENSE PACKAGE
# =========================================================

LICENSE_TRIAL = "TRIAL"
LICENSE_1_MONTH = "1_MONTH"
LICENSE_6_MONTH = "6_MONTH"
LICENSE_1_YEAR = "1_YEAR"
LICENSE_LIFETIME = "LIFETIME"


# =========================================================
# CACHE
# =========================================================

_LICENSE_CACHE = None
_CACHE_LOCK = threading.Lock()


# =========================================================
# DEVICE ID
# =========================================================

def get_device_id():
    mac = uuid.getnode()

    raw = f"MIKROTIK-INVOICE-{mac}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest().upper()

# =========================================================
# SECRET
# =========================================================
def get_secret():
    """
    Secret utama untuk membuat License Key.
    Harus sama dengan generator.
    """

    return _P2 + _P1 + _P3

def _get_secret_key():
    """
    Kompatibilitas dengan kode lama.
    """

    return get_secret()

# =========================================================
# EXPIRED
# =========================================================
def hitung_expired(paket):
    """
    Menghitung tanggal expired berdasarkan paket.
    """

    now = datetime.now()

    if paket == LICENSE_TRIAL:
        return (
            now + timedelta(days=2)
        ).strftime("%Y-%m-%d")

    elif paket == LICENSE_1_MONTH:
        return (
            now + relativedelta(months=1)
        ).strftime("%Y-%m-%d")

    elif paket == LICENSE_6_MONTH:
        return (
            now + relativedelta(months=6)
        ).strftime("%Y-%m-%d")

    elif paket == LICENSE_1_YEAR:
        return (
            now + relativedelta(years=1)
        ).strftime("%Y-%m-%d")

    elif paket == LICENSE_LIFETIME:
        return None

    return None

# =========================================================
# LICENSE PREFIX
# =========================================================
PREFIX = {
    LICENSE_TRIAL: "TR",
    LICENSE_1_MONTH: "M1",
    LICENSE_6_MONTH: "M6",
    LICENSE_1_YEAR: "Y1",
    LICENSE_LIFETIME: "LF",
}

# =========================================================
# PAKET DARI KODE
# =========================================================
def paket_dari_kode(kode):
    """
    Membaca paket dari prefix License Key.
    """

    if not kode:
        return None

    kode = kode.strip().upper()

    if kode.startswith("TR-"):
        return LICENSE_TRIAL

    if kode.startswith("M1-"):
        return LICENSE_1_MONTH

    if kode.startswith("M6-"):
        return LICENSE_6_MONTH

    if kode.startswith("Y1-"):
        return LICENSE_1_YEAR

    if kode.startswith("LF-"):
        return LICENSE_LIFETIME

    return None
	
# =========================================================
# LICENSE PAYLOAD
# =========================================================

def create_license_payload(device_id, paket, expired):
    """
    Membuat payload license.
    Dipertahankan untuk kompatibilitas dengan kode lama.
    """

    payload = {
        "device_id": device_id,
        "paket": paket,
        "expired": expired,
        "nonce": secrets.token_hex(8)
    }

    return payload	

# =========================================================
# SIGN LICENSE PAYLOAD
# =========================================================

def sign_payload(payload):
    """
    Membuat signature untuk payload license.
    """

    import json

    data = json.dumps(
        payload,
        sort_keys=True
    ).encode("utf-8")

    return hmac.new(
        MASTER_KEY.encode("utf-8"),
        data,
        hashlib.sha256
    ).hexdigest()


def decode_license(license_key):
    """
    Kompatibilitas dengan sistem license lama.
    """

    try:
        import base64
        import json

        raw = base64.urlsafe_b64decode(
            license_key.encode("utf-8")
        ).decode("utf-8")

        payload = json.loads(raw)

        return payload

    except Exception:
        return None
		
def format_license_key(encoded):
    """
    Kompatibilitas dengan sistem license lama.

    Mengubah string menjadi format:
    MIK-XXXX-XXXX-XXXX-XXXX
    """

    import zlib

    if not encoded:
        return None

    checksum = zlib.crc32(
        encoded.encode("utf-8")
    )

    raw = f"{encoded}{checksum}"

    raw = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest().upper()

    raw = raw[:20]

    bagian = [
        raw[i:i + 4]
        for i in range(0, 20, 4)
    ]

    return "MIK-" + "-".join(bagian)
		
def get_license_type(kode):
    """
    Alias kompatibilitas.
    """

    return paket_dari_kode(kode)

# =========================================================
# GENERATE LICENSE KEY
# =========================================================
def generate_license(device_id, paket):
    """
    Membuat License Key.

    Format:

    M1-XXXX-XXXX-XXXX-XXXX
    """

    secret = get_secret()

    raw = f"{paket}|{device_id}"

    raw_hash = hmac.new(
        secret.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()

    prefix = PREFIX.get(paket)

    if prefix is None:
        return None

    body = raw_hash[:16]

    return (
        f"{prefix}-"
        f"{body[0:4]}-"
        f"{body[4:8]}-"
        f"{body[8:12]}-"
        f"{body[12:16]}"
    )

# =========================================================
# SIGNATURE
# =========================================================
def generate_signature(kode, device_id, expired_at):
    """
    Membuat signature license.

    Signature menggunakan:

    kode
    device_id
    expired
    """

    payload = f"{kode}|{device_id}|{expired_at}"

    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

# =========================================================
# VALIDASI KODE AKTIVASI
# =========================================================
def validasi_kode_aktivasi(kode, device_id):
    """
    Validasi License Key berdasarkan:
    - Paket
    - Device ID
    - HMAC SHA256

    Format:
    M1-XXXX-XXXX-XXXX-XXXX
    M6-XXXX-XXXX-XXXX-XXXX
    Y1-XXXX-XXXX-XXXX-XXXX
    TR-XXXX-XXXX-XXXX-XXXX
    LF-XXXX-XXXX-XXXX-XXXX
    """

    try:
        if not kode or not device_id:
            return False

        # -------------------------------------------------
        # NORMALISASI
        # -------------------------------------------------

        kode = kode.strip().upper()
        device_id = device_id.strip().replace(" ", "").upper()

        # -------------------------------------------------
        # CEK FORMAT
        # -------------------------------------------------

        parts = kode.split("-")

        if len(parts) != 5:
            return False

        prefix = parts[0]

        # Setiap bagian harus 4 karakter
        if not all(len(x) == 4 for x in parts[1:]):
            return False

        # -------------------------------------------------
        # CEK PAKET
        # -------------------------------------------------

        prefix_map = {
            "TR": LICENSE_TRIAL,
            "M1": LICENSE_1_MONTH,
            "M6": LICENSE_6_MONTH,
            "Y1": LICENSE_1_YEAR,
            "LF": LICENSE_LIFETIME,
        }

        paket = prefix_map.get(prefix)

        if paket is None:
            return False

        # -------------------------------------------------
        # BUAT HASH YANG SAMA DENGAN GENERATOR
        # -------------------------------------------------

        secret = _get_secret_key()

        raw = f"{paket}|{device_id}"

        expected = hmac.new(
            secret.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256
        ).hexdigest().upper()[:16]

        # -------------------------------------------------
        # AMBIL BODY LICENSE
        # -------------------------------------------------

        license_body = "".join(parts[1:]).upper()

        # -------------------------------------------------
        # BANDINGKAN
        # -------------------------------------------------

        return hmac.compare_digest(
            license_body,
            expected
        )

    except Exception as e:

        print(
            f"[LICENSE] Validasi error: {e}"
        )

        return False

# =========================================================
# VALIDASI SIGNATURE
# =========================================================
def validasi_signature(
    kode,
    device_id,
    expired_at,
    signature
):
    """
    Memastikan signature license benar.
    """

    if not kode:
        return False

    if not device_id:
        return False

    if not signature:
        return False

    expected = generate_signature(
        kode,
        device_id,
        expired_at
    )

    return hmac.compare_digest(
        signature.lower(),
        expected.lower()
    )

# =========================================================
# VALIDASI EXPIRED
# =========================================================
def validasi_expired(
    paket,
    expired_at
):
    """
    Mengecek tanggal expired.
    """

    # Lifetime tidak memiliki tanggal expired
    if paket == LICENSE_LIFETIME:
        return True

    if not expired_at:
        return False

    try:

        exp_date = datetime.strptime(
            str(expired_at)[:10],
            "%Y-%m-%d"
        ).date()

        return date.today() <= exp_date

    except Exception:
        return False

# =========================================================
# PARSE LICENSE GABUNGAN
# =========================================================
def parse_license(text):
    """
    Membaca format:

    KODE|EXPIRED|SIGNATURE

    Return:

    {
        "kode": ...,
        "expired": ...,
        "signature": ...
    }

    """

    if not text:
        return None

    text = text.strip()

    bagian = text.split("|")

    if len(bagian) != 3:
        return None

    kode = bagian[0].strip().upper()
    expired = bagian[1].strip()
    signature = bagian[2].strip()

    if expired == "":
        expired = None

    if not kode:
        return None

    if not signature:
        return None

    return {
        "kode": kode,
        "expired": expired,
        "signature": signature
    }

# =========================================================
# VALIDASI LICENSE LENGKAP
# =========================================================
def validasi_license_lengkap(teks_license, device_id):
    """
    Validasi license format:

    KODE|EXPIRED|SIGNATURE

    Contoh:

    M1-XXXX-XXXX-XXXX-XXXX|2026-12-31|SIGNATURE
    """

    try:

        teks_license = teks_license.strip()

        # Pisahkan license
        parts = teks_license.split("|")

        if len(parts) != 3:
            return False, None, None

        kode = parts[0].strip().upper()
        expired_at = parts[1].strip()
        signature = parts[2].strip()

        # ==============================
        # CEK DEVICE + KODE
        # ==============================

        if not validasi_kode_aktivasi(
            kode,
            device_id
        ):
            return False, None, None

        paket = paket_dari_kode(kode)

        if paket is None:
            return False, None, None

        # ==============================
        # CEK LIFETIME
        # ==============================

        if paket == LICENSE_LIFETIME:

            # Lifetime harus memakai
            # expired = LIFETIME
            if expired_at.upper() != "LIFETIME":
                return False, None, None

            expired_value = None

        else:

            # Pastikan format tanggal
            try:

                datetime.strptime(
                    expired_at,
                    "%Y-%m-%d"
                )

            except Exception:

                return False, None, None

            expired_value = expired_at

        # ==============================
        # CEK SIGNATURE
        # ==============================

        payload = (
            f"{kode}|"
            f"{device_id}|"
            f"{expired_value}"
        )

        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            signature,
            expected_signature
        ):
            return False, None, None

        # ==============================
        # BERHASIL
        # ==============================

        return True, paket, expired_value

    except Exception as e:

        print(
            "[LICENSE VALIDATION ERROR]",
            e
        )

        return False, None, None

# =========================================================
# SIMPAN LICENSE - SECURE
# =========================================================
def simpan_license(
    kode,
    paket=None,
    expired_at=None
):
    """
    Menyimpan license ke database.

    ATURAN:
    1. Kode harus valid terhadap Device ID komputer.
    2. Paket harus sesuai dengan prefix kode.
    3. Expired dihitung dari paket jika tidak diberikan.
    4. License lama dihapus sebelum license baru disimpan.
    5. License yang tidak valid TIDAK akan masuk database.

    Return:
        True  = berhasil disimpan
        False = ditolak
    """

    try:

        # -------------------------------------------------
        # NORMALISASI
        # -------------------------------------------------

        kode = (kode or "").strip().upper()

        device_id = get_device_id()

        if not kode:
            print("[LICENSE] GAGAL: kode kosong")
            return False

        if not device_id:
            print("[LICENSE] GAGAL: Device ID kosong")
            return False

        # -------------------------------------------------
        # BACA PAKET DARI KODE
        # -------------------------------------------------

        paket_kode = paket_dari_kode(kode)

        if paket_kode is None:
            print("[LICENSE] GAGAL: paket dari kode tidak dikenali")
            return False

        # -------------------------------------------------
        # JIKA PAKET DIBERIKAN, HARUS SAMA
        # -------------------------------------------------

        if paket is not None:

            paket = str(paket).strip().upper()

            if paket != paket_kode:
                print(
                    "[LICENSE] GAGAL: paket tidak sesuai dengan kode"
                )
                return False

        else:
            paket = paket_kode

        # -------------------------------------------------
        # VALIDASI KODE TERHADAP DEVICE ID
        # -------------------------------------------------

        if not validasi_kode_aktivasi(
            kode,
            device_id
        ):

            print(
                "[LICENSE] GAGAL: kode tidak valid "
                "untuk Device ID ini"
            )

            return False

        # -------------------------------------------------
        # HITUNG EXPIRED
        # -------------------------------------------------

        if expired_at is None:

            expired_at = hitung_expired(
                paket
            )

        # -------------------------------------------------
        # NORMALISASI EXPIRED
        # -------------------------------------------------

        if expired_at is not None:

            expired_at = str(
                expired_at
            ).strip()

        # -------------------------------------------------
        # BUAT SIGNATURE DATABASE
        # -------------------------------------------------

        payload = (
            f"{kode}|"
            f"{device_id}|"
            f"{expired_at}"
        )

        signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # -------------------------------------------------
        # SIMPAN DATABASE
        # -------------------------------------------------

        conn = get_db()

        try:

            cur = conn.cursor()

            # Hanya satu license aktif
            cur.execute(
                "DELETE FROM licenses"
            )

            cur.execute("""
                INSERT INTO licenses (
                    id,
                    device_id,
                    kode,
                    paket,
                    expired_at,
                    signature,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                uuid.uuid4().hex,
                device_id,
                kode,
                paket,
                expired_at,
                signature,
                datetime.now().isoformat()
            ))

            conn.commit()

        except Exception:

            conn.rollback()

            raise

        finally:

            release_db(conn)

        # -------------------------------------------------
        # BERSIHKAN CACHE
        # -------------------------------------------------

        global _LICENSE_CACHE

        with _CACHE_LOCK:
            _LICENSE_CACHE = None

        print(
            "[LICENSE] License berhasil disimpan"
        )

        print(
            f"[LICENSE] Paket   : {paket}"
        )

        print(
            f"[LICENSE] Expired : {expired_at}"
        )

        return True

    except Exception as e:

        print(
            f"[LICENSE] Gagal menyimpan license: {e}"
        )

        return False

# =========================================================
# VALIDASI DATABASE
# =========================================================
def license_valid():
    """
    Validasi license yang tersimpan.

    Yang dicek:

    1. License tersedia
    2. Device ID sama
    3. Paket sesuai prefix kode
    4. Signature valid
    5. License belum expired
    """

    conn = None

    try:

        # =================================================
        # AMBIL LICENSE
        # =================================================

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                device_id,
                kode,
                paket,
                expired_at,
                signature
            FROM licenses
            LIMIT 1
        """)

        data = cur.fetchone()

        release_db(conn)
        conn = None

        # Tidak ada license
        if not data:
            return False

        device_id_db = data["device_id"]
        kode = data["kode"]
        paket = data["paket"]
        expired_at = data["expired_at"]
        signature = data["signature"]

        # =================================================
        # CEK DEVICE
        # =================================================

        current_device_id = get_device_id()

        if device_id_db != current_device_id:

            print("[LICENSE] Device ID tidak cocok")

            return False

        # =================================================
        # CEK PAKET DARI KODE
        # =================================================

        paket_dari_license = paket_dari_kode(kode)

        if paket_dari_license is None:

            print("[LICENSE] Prefix license tidak valid")

            return False

        if paket != paket_dari_license:

            print("[LICENSE] Paket tidak cocok")

            return False

        # =================================================
        # CEK SIGNATURE
        # =================================================

        payload = (
            f"{kode}|"
            f"{device_id_db}|"
            f"{expired_at}"
        )

        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            signature,
            expected_signature
        ):

            print("[LICENSE] Signature tidak valid")

            return False

        # =================================================
        # LIFETIME
        # =================================================

        if paket == LICENSE_LIFETIME:

            return True

        # =================================================
        # CEK EXPIRED
        # =================================================

        if not expired_at:

            print("[LICENSE] Tanggal expired kosong")

            return False

        try:

            exp_date = datetime.strptime(
                str(expired_at)[:10],
                "%Y-%m-%d"
            ).date()

        except Exception:

            print("[LICENSE] Format expired tidak valid")

            return False

        # License berlaku sampai tanggal expired
        if date.today() > exp_date:

            print("[LICENSE] License sudah expired")

            return False

        # =================================================
        # SEMUA VALID
        # =================================================

        return True

    except Exception as e:

        print("[LICENSE VALIDATION ERROR]", e)

        return False

    finally:

        if conn is not None:

            try:
                release_db(conn)
            except Exception:
                pass

# =========================================================
# COMPATIBILITY
# =========================================================
def check_license():
    return license_valid()

def save_license(license_key):
    return simpan_license(
        license_key
    )

def license_valid_local():
    return license_valid()

# =========================================================
# TRIAL
# =========================================================
def check_trial(trial_days=2):
    """
    Trial berdasarkan Device ID.
    """

    today = datetime.now().date()

    device_id = get_device_id()

    conn = get_db()

    try:

        cur = conn.cursor()

        cur.execute(
            """
            SELECT start_date
            FROM trial_info
            WHERE device_id=?
            """,
            (device_id,)
        )

        row = cur.fetchone()

        if row:

            start_date = datetime.strptime(
                row["start_date"],
                "%Y-%m-%d"
            ).date()

        else:

            start_date = today

            cur.execute(
                """
                INSERT INTO trial_info (
                    device_id,
                    start_date
                )
                VALUES (?, ?)
                """,
                (
                    device_id,
                    today.strftime("%Y-%m-%d")
                )
            )

            conn.commit()

    finally:
        release_db(conn)

    used = (
        today - start_date
    ).days

    remaining = (
        trial_days - used
    )

    return (
        remaining > 0,
        max(remaining, 0)
    )

# =========================================================
# LICENSE INFO
# =========================================================
def get_license_info(force=False):

    global _LICENSE_CACHE

    with _CACHE_LOCK:

        if _LICENSE_CACHE and not force:

            return _LICENSE_CACHE

    info = {
        "status": "NO_LICENSE",
        "expired": None,
        "type": None,
        "sisa": 0,
        "mode": "TRIAL"
    }

    conn = None

    try:

        conn = get_db()

        cur = conn.cursor()

        cur.execute("""
            SELECT
                paket,
                expired_at
            FROM licenses
            LIMIT 1
        """)

        row = cur.fetchone()

        release_db(conn)
        conn = None

        # =============================================
        # ADA LICENSE
        # =============================================

        if row:

            paket = row["paket"]
            expired = row["expired_at"]

            # Validasi license sebenarnya
            valid = license_valid()

            # Lifetime
            if paket == LICENSE_LIFETIME and valid:

                info.update({
                    "status": "ACTIVE",
                    "mode": "PREMIUM",
                    "type": paket,
                    "expired": "LIFETIME",
                    "sisa": "LIFETIME"
                })

            # License biasa
            elif valid:

                sisa = 0

                if expired:

                    exp_date = datetime.strptime(
                        str(expired)[:10],
                        "%Y-%m-%d"
                    ).date()

                    sisa = (
                        exp_date - date.today()
                    ).days

                    if sisa < 0:
                        sisa = 0

                info.update({
                    "status": "ACTIVE",
                    "mode": "PREMIUM",
                    "type": paket,
                    "expired": expired,
                    "sisa": sisa
                })

            else:

                info.update({
                    "status": "INVALID",
                    "mode": "LOCK",
                    "type": paket,
                    "expired": expired,
                    "sisa": 0
                })

        # =============================================
        # TIDAK ADA LICENSE â†’ CEK TRIAL
        # =============================================

        else:

            ok, sisa = check_trial()

            if ok:

                info.update({
                    "status": "TRIAL",
                    "mode": "TRIAL",
                    "sisa": sisa
                })

            else:

                info.update({
                    "status": "EXPIRED",
                    "mode": "LOCK",
                    "sisa": 0
                })

    except Exception as e:

        print("[LICENSE INFO ERROR]", e)

        info.update({
            "status": "INVALID",
            "mode": "LOCK"
        })

    finally:

        if conn is not None:

            try:
                release_db(conn)
            except Exception:
                pass

    with _CACHE_LOCK:

        _LICENSE_CACHE = info

    return info

# =========================================================
# APP LOCK
# =========================================================
def is_app_locked():
    """
    True  = aplikasi dikunci
    False = aplikasi boleh digunakan
    """

    info = get_license_info()

    status = str(
        info.get("status", "")
    ).upper()

    return status in (
        "EXPIRED",
        "LOCKED",
        "INVALID"
    )
# =========================================================
# LEGACY FUNCTION
# =========================================================
def is_active(lic):
    """
    Kompatibilitas dengan sistem license lama.
    """

    now = datetime.now()

    if lic.get("type") == "MONTHLY":

        last_day = calendar.monthrange(
            lic["year"],
            lic["month"]
        )[1]

        expired = datetime(
            lic["year"],
            lic["month"],
            last_day,
            23,
            59,
            59
        )

    else:

        expired = datetime(
            lic["year"],
            12,
            31,
            23,
            59,
            59
        )

    return now <= expired
