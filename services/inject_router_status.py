# services/inject_router_status.py
import subprocess
import platform
from services.router_service import get_router_status
from services.mikrotik_sync_service import is_router_online

def inject_router_status(user_id):
    return get_router_status(user_id)

# Contoh pemakaian langsung
if __name__ == "__main__":
    user_id = "user123"
    routers = inject_router_status(user_id)
    for r in routers:
        print(f"{r['name']} ({r['host']}): {r['status']}")