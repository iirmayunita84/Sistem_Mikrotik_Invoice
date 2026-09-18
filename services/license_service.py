# services/license_service.py
import json, os, uuid, calendar
from datetime import datetime
from utils.device_fingerprint import get_device_fingerprint
from core.license_expiry import is_active
from services import license_storage
from device_fingerprint import get_device_fingerprint

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_FILE = os.path.join(BASE_DIR, "licenses.json")


def load_licenses():
    if not os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "w") as f:
            json.dump({"licenses": []}, f, indent=2)
    with open(LICENSE_FILE, "r") as f:
        return json.load(f)


def save_licenses(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ==========================
# CEK MASA AKTIF
# ==========================
def is_license_active(lic):
    now = datetime.now()

    if lic["type"] == "MONTHLY":
        last_day = calendar.monthrange(lic["year"], lic["month"])[1]
        expired = datetime(lic["year"], lic["month"], last_day, 23, 59, 59)
    else:
        expired = datetime(lic["year"], 12, 31, 23, 59, 59)

    return now <= expired


# ==========================
# VALIDASI & AKTIVASI
# ==========================
def validate_and_use_license(code, user_id, request=None):
    data = license_storage.load()
    device = get_device_fingerprint()
    ip = request.remote_addr if request else None

    for lic in data["licenses"]:
        if lic["code"] != code:
            continue

        if lic.get("used"):
            return False, "❌ Kode lisensi sudah dipakai"

        if not is_active(lic):
            return False, "❌ Lisensi sudah kedaluwarsa"

        lic.update({
            "used": True,
            "used_by": user_id,
            "device": device,
            "ip": ip,
            "used_at": datetime.now().isoformat()
        })

        license_storage.save(data)
        return True, lic

    return False, "❌ Kode lisensi tidak valid"