# core/api.py

from core.logic import (
    get_app_config,
    simpan_pelanggan,
    auto_blokir_jatuh_tempo,
    reset_tagihan_bulanan,
    load_mikrotik_list
)
from services.mikrotik_sync_service import sync_all_routers
from core.mikrotik_api import set_pppoe_status
from services.router_service import get_user_routers
from core.dhcp_core import convert_dhcp_to_pelanggan

def sinkron_semua_router(user_id=None):
    """
    Sinkron semua router ke database.
    """

    routers = get_user_routers(user_id)

    if user_id:
        routers = [r for r in routers if r.get("user_id") == user_id]

    total_router = len(routers)

    if total_router == 0:
        print("⚠️ Tidak ada router ditemukan")
        return 0

    print(f"🔄 Mulai sinkron {total_router} router...")

    # Sinkron DHCP dari semua router
    sync_all_routers(user_id=user_id)

    print("✅ Sinkron semua router selesai")

    return total_router

def cek_status_semua_router():
    routers = get_user_routers(user_id)
    hasil = []

    from services.mikrotik_sync_service import is_router_online

    for r in routers:
        status = is_router_online(r)
        hasil.append({
            "router": r.get("name"),
            "host": r.get("host"),
            "online": status
        })

    return hasil