#services/wa_service.py
import os
from datetime import datetime
from urllib.parse import quote
from core.db import get_db, release_db
from core.core_pelanggan import get_pelanggan_list

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "wa_log")


# =========================
# FORMAT RUPIAH
# =========================
def format_rupiah(nominal):

    try:
        nominal = int(nominal)
    except:
        nominal = 0

    return "Rp {:,}".format(nominal).replace(",", ".")

# =========================
# FORMAT NOMOR HP
# =========================
def format_nomor(no):

    if not no:
        return ""

    no = str(no)

    no = no.replace(" ","")
    no = no.replace("-","")

    if not no.isdigit():
        return ""

    if no.startswith("0"):
        no = "62"+no[1:]

    elif not no.startswith("62"):
        no = "62"+no

    return no

# =========================
# KIRIM WA (LINK)
# =========================
def kirim_wa(no_hp, pesan):
    no = format_nomor(no_hp)

    if not no:
        return None

    return f"https://wa.me/{no}?text={quote(pesan)}"

# =========================
# PESAN TAGIHAN
# =========================
def pesan_tagihan(p, app_cfg):

    nama = p.get("nama", "")
    paket = p.get("paket", "")
    harga = format_rupiah(p.get("harga", 0))
    jt = p.get("jatuh_tempo", "-")

    store = app_cfg.get("store_name", "ISP")
    alamat = app_cfg.get("store_address", "")

    pesan = f"""
Halo {nama}

Tagihan internet anda:

Paket : {paket}
Tagihan : {harga}
Jatuh tempo : {jt}

Silakan lakukan pembayaran sebelum jatuh tempo.

{store}
{alamat}
"""

    return pesan.strip()

# =========================
# PESAN REMINDER
# =========================
def pesan_reminder(p, app_cfg, hari):

    nama = p.get("nama", "")
    paket = p.get("paket", "")
    harga = format_rupiah(p.get("harga", 0))
    jt = p.get("jatuh_tempo", "-")

    store = app_cfg.get("store_name", "ISP")

    if hari == -3:
        ket = "3 hari lagi"
    elif hari == -1:
        ket = "besok"
    elif hari == 0:
        ket = "hari ini"
    else:
        ket = ""

    pesan = f"""
Halo {nama}

Pengingat tagihan internet anda.

Paket : {paket}
Tagihan : {harga}
Jatuh tempo : {jt}

Tagihan akan jatuh tempo {ket}.

Mohon segera melakukan pembayaran.

{store}
"""

    return pesan.strip()

# =========================
# PESAN LUNAS
# =========================
def pesan_lunas(p, app_cfg):

    nama = p.get("nama", "")
    paket = p.get("paket", "")
    harga = format_rupiah(p.get("harga", 0))

    store = app_cfg.get("store_name", "ISP")

    pesan = f"""
Halo {nama}

Pembayaran internet anda telah kami terima.

Paket : {paket}
Total : {harga}

Status : LUNAS

Terima kasih telah melakukan pembayaran.

{store}
"""

    return pesan.strip()

# =========================
# LOAD LOG WA
# =========================
def get_log_wa():

    conn = get_db()

    try:

        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM wa_log
            ORDER BY tanggal DESC
        """)

        return [dict(r) for r in cur.fetchall()]

    finally:
        release_db(conn)

# =========================
# SIMPAN LOG WA
# =========================
def simpan_log_wa(pelanggan, jenis="REMINDER", hari=0):

    conn = get_db()

    try:

        cur = conn.cursor()

        cur.execute("""
            INSERT INTO wa_log
            (
                pelanggan_id,
                no_hp,
                jenis,
                pesan,
                tanggal
            )
            VALUES(?,?,?,?,?)
        """,(

            pelanggan.get("id"),

            pelanggan.get("no_hp"),

            jenis,

            f"Reminder H{hari}",

            datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ))

        conn.commit()

    finally:

        release_db(conn)

# =========================
# KIRIM + SIMPAN LOG
# =========================
def kirim_dan_log(
    pelanggan,
    pesan,
    hari=0
):

    url = kirim_wa(
        pelanggan.get("no_hp"),
        pesan
    )

    simpan_log_wa(
        pelanggan,
        "REMINDER",
        hari
    )

    return url

# =========================
# LIST REMINDER
# =========================
def reminder_wa_list(pelanggan_list, app_cfg, hari):

    links = []

    for p in pelanggan_list:

        if not p.get("no_hp"):
            continue

        pesan = pesan_reminder(p, app_cfg, hari)

        url = kirim_dan_log(
            p,
            pesan,
            hari
        )

        if not url:
            continue

        links.append({
            "nama": p.get("nama"),
            "no_hp": p.get("no_hp"),
            "url": url
        })

    return links

# =========================
# REMINDER MASSAL
# =========================
def kirim_reminder_massal(user_id, app_cfg, hari=0):

    try:

        from core.core_pelanggan import get_pelanggan_file

        pelanggan_list = get_pelanggan_list(user_id=user_id)

        links = reminder_wa_list(
            pelanggan_list,
            app_cfg,
            hari
        )

        print(
            f"WA Reminder : {len(links)} pelanggan"
        )

        return links

    except Exception as e:

        print(
            "WA reminder error:",
            e
        )

        return []