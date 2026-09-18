# core/utils.py
from datetime import datetime
from core.logic import cek_demo, is_user_premium
from core.core_pelanggan import get_pelanggan_list

def get_transaksi_list():
    data = get_pelanggan_list()

    transaksi = [
        p for p in data
        if p.get("status") in ("Lunas", "Aktif")
        and p.get("tanggal_bayar")
    ]

    transaksi.sort(
        key=lambda x: x["tanggal_bayar"],
        reverse=True
    )

    return transaksi

def boleh_masuk(user_id):
    """
    Return:
    (ok, mode, sisa_hari)
    ok   : True / False
    mode : 'TRIAL' | 'PREMIUM' | 'EXPIRED'
    """
    # Premium selalu boleh
    if is_user_premium(user_id):
        return True, "PREMIUM", 0

    # Cek demo / trial
    aktif, sisa = cek_demo(user_id)
    if aktif:
        return True, "TRIAL", sisa

    return False, "EXPIRED", 0

def parse_comment(comment):
    """
    Parser comment Mikrotik yang tahan banting
    Format fleksibel: key:value; key:value
    """
    hasil = {
        "nama": "",
        "paket": "",
        "harga": 0,
        "due": None,
        "no_hp": "",
        "iface": "",
        "usage": "0GB"
    }

    if not comment:
        return hasil

    parts = comment.split(";")

    for part in parts:
        if ":" not in part:
            continue

        key, value = part.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "nama":
            hasil["nama"] = value
        elif key == "paket":
            hasil["paket"] = value
        elif key == "harga":
            try:
                hasil["harga"] = int(value)
            except:
                hasil["harga"] = 0
        elif key == "due":
            try:
                hasil["due"] = datetime.strptime(value, "%Y-%m-%d").date()
            except:
                hasil["due"] = None
        elif key == "no_hp":
            hasil["no_hp"] = value
        elif key == "iface":
            hasil["iface"] = value
        elif key == "usage":
            hasil["usage"] = value

    return hasil

def build_comment_from_dict(d):
    return ";".join([f"{k}:{v}" for k,v in d.items()])