# services/router_live_service.py

from core.mikrotik_core import konek_mikrotik
from services.router_service import get_user_routers

def ambil_pppoe_user(user_id):
    hasil = []

    routers = get_user_routers(user_id)

    for r in routers:
        api, conn = konek_mikrotik(r)
        if not api:
            continue

        try:
            secrets = api.get_resource('/ppp/secret').get()
        except:
            continue

        for s in secrets:
            hasil.append({
                "nama": s.get("name"),
                "profile": s.get("profile"),
                "router_id": r["id"]
            })

    return hasil