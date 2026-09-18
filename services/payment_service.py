# services/payment_service.py
"""
Semua logika pembayaran
- Manual (cash / transfer)
- Status invoice
- Hook ke PPPoE (nanti)
TIDAK BOLEH import Flask / Blueprint
"""

from datetime import datetime
from core.logic import (
    get_pelanggan,
    simpan_pelanggan
)


# =========================
# STATUS ENUM
# =========================
STATUS_UNPAID = "Belum Lunas"
STATUS_PAID = "Lunas"


# =========================
# BAYAR MANUAL
# =========================
def bayar_manual(user_id: str, pelanggan_id: str, metode="Manual") -> bool:
    """
    Tandai pelanggan sebagai LUNAS (manual / transfer)
    """
    data = get_pelanggan(user_id)
    pelanggan = next((p for p in data if p["id"] == pelanggan_id), None)

    if not pelanggan:
        raise ValueError("Pelanggan tidak ditemukan")

    pelanggan["status"] = STATUS_PAID
    pelanggan["metode_bayar"] = metode
    pelanggan["tanggal_bayar"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    simpan_pelanggan(user_id, data)
    return True

# =========================
# BATALKAN PEMBAYARAN
# =========================
def batalkan_pembayaran(user_id: str, pelanggan_id: str) -> bool:
    """
    Kembalikan status ke BELUM LUNAS
    """
    data = get_pelanggan(user_id)
    pelanggan = next((p for p in data if p["id"] == pelanggan_id), None)

    if not pelanggan:
        raise ValueError("Pelanggan tidak ditemukan")

    pelanggan["status"] = STATUS_UNPAID
    pelanggan.pop("tanggal_bayar", None)
    pelanggan.pop("metode_bayar", None)

    simpan_pelanggan(user_id, data)
    return True

# =========================
# CEK STATUS PEMBAYARAN
# =========================
def is_lunas(pelanggan: dict) -> bool:
    return pelanggan.get("status") == STATUS_PAID