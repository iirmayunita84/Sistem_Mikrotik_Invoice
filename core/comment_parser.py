from datetime import datetime
import re


DEFAULT_DATA = {
    "nama": "",
    "paket": "",
    "harga": 0,
    "due": "",
    "no_hp": "",
    "iface": "",
    "usage": "0GB",
}


ALIAS = {
    "nama": "nama",
    "name": "nama",

    "paket": "paket",
    "package": "paket",

    "harga": "harga",
    "price": "harga",

    "due": "due",
    "jatuh_tempo": "due",
    "tempo": "due",

    "no_hp": "no_hp",
    "hp": "no_hp",
    "phone": "no_hp",
    "wa": "no_hp",

    "iface": "iface",
    "interface": "iface",

    "usage": "usage",
}


def normalisasi_due(value):
    """
    Format resmi aplikasi:
        DD/MM/YYYY

    Yang diterima:
        DD/MM/YYYY
        YYYY-MM-DD

    Format MM/DD/YYYY TIDAK ditebak.
    """

    if value in (None, ""):
        return ""

    value = str(value).strip()

    # FORMAT RESMI: DD/MM/YYYY
    try:
        return datetime.strptime(
            value,
            "%d/%m/%Y"
        ).strftime("%d/%m/%Y")
    except ValueError:
        pass

    # FORMAT ISO: YYYY-MM-DD
    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).strftime("%d/%m/%Y")
    except ValueError:
        pass

    # Jangan menebak MM/DD/YYYY
    return ""


def parse_comment(comment):
    hasil = DEFAULT_DATA.copy()

    if not comment:
        return hasil

    for item in re.split(r"[;,]", str(comment)):
        item = item.strip()

        if not item:
            continue

        if "=" in item:
            key, value = item.split("=", 1)
        elif ":" in item:
            key, value = item.split(":", 1)
        else:
            continue

        key = key.strip().lower()
        value = value.strip()

        key = ALIAS.get(key)

        if not key:
            continue

        if key == "harga":

            angka = re.sub(r"[^\d]", "", value)

            hasil["harga"] = int(angka) if angka else 0

        elif key == "due":

            # ==========================================
            # NORMALISASI JATUH TEMPO
            # ==========================================

            hasil["due"] = normalisasi_due(value)

        else:

            hasil[key] = value

    return hasil


def build_comment_from_dict(data):
    """
    Mengubah dictionary menjadi comment MikroTik.

    Format tanggal resmi:
        DD/MM/YYYY
    """

    if not data:
        return ""

    mapping = {
        "nama_pelanggan": "nama",
        "paket": "paket",
        "harga": "harga",
        "jatuh_tempo": "due",
        "no_hp": "no_hp",
        "iface": "iface",
        "usage": "usage"
    }

    urutan = [
        "nama_pelanggan",
        "paket",
        "harga",
        "jatuh_tempo",
        "no_hp",
        "iface",
        "usage"
    ]

    parts = []

    # ==========================================
    # FIELD UTAMA
    # ==========================================

    for key in urutan:

        value = data.get(key)

        if value in (None, ""):
            continue

        output_key = mapping.get(key, key)

        # ==========================================
        # NORMALISASI JATUH TEMPO
        # ==========================================

        if key == "jatuh_tempo":

            value = normalisasi_due(value)

            # Jika tanggal tidak valid,
            # jangan kirim field due yang salah.
            if not value:
                continue

        # ==========================================
        # HARGA
        # ==========================================

        if key == "harga":

            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 0

        parts.append(
            "%s:%s" % (output_key, value)
        )

    # ==========================================
    # FIELD TAMBAHAN
    # ==========================================

    for key, value in sorted(data.items()):

        if key in urutan:
            continue

        if value in (None, ""):
            continue

        parts.append(
            "%s:%s" % (key, value)
        )

    return "; ".join(parts)