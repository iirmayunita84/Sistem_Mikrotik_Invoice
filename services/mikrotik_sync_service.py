# services/mikrotik_sync_service
import logging
from core.db import get_db
from core.comment_parser import parse_comment
from core.mikrotik_api import (
    connect_router,
    get_dhcp_leases
)
from services.router_service import get_user_routers, update_router_status
from core.dhcp_core import convert_dhcp_to_pelanggan
# ==============================
# Sinkron DHCP → database
# ==============================
def sync_dhcp_clients(user_id):
    from core.dhcp_core import simpan_dhcp_clients

    routers = get_user_routers(user_id)

    if not routers:
        print(f"⚠️ User {user_id} tidak memiliki router.")
        return 0

    total = 0

    for router in routers:
        try:
            logging.info(f"📡 Sinkron DHCP Router : {router['host']}")

            leases = get_dhcp_leases(router)

            jumlah = simpan_dhcp_clients(
                user_id=user_id,
                router_id=router["id"],
                leases=leases
            )

            total += jumlah

            logging.info(f"{router['host']} : {jumlah} DHCP disimpan")

        except Exception as e:
            print(f"❌ Router {router['host']} gagal : {e}")

    logging.info(f"Total DHCP User {user_id} = {total}")

    return total

# ==============================
# Cek Router Online
# ==============================
def is_router_online(router):

    try:
        api, pool = connect_router(router)
        pool.disconnect()

        update_router_status(router["id"], True)

        return True

    except Exception:

        update_router_status(router["id"], False)

        return False

def sync_all_routers(user_id=None):

    routers = get_user_routers(user_id)

    for router in routers:
        is_router_online(router)

    total_dhcp = sync_dhcp_clients(user_id)

    total_pelanggan = convert_dhcp_to_pelanggan(user_id)

    logging.info(
        f"DHCP={total_dhcp} | Pelanggan Baru={total_pelanggan}"
    )

    return total_pelanggan