# auto_pppoe.py
from core import get_pelanggan, get_router_by_id, set_pppoe_status

# Ambil semua pelanggan
pelanggan_list = get_pelanggan(fresh_from_mikrotik=False)

for p in pelanggan_list:
    router_id = p.get("mikrotik_id")
    username_pppoe = p.get("pppoe_user")

    if not router_id or not username_pppoe:
        continue  # skip kalau tidak ada PPPoE

    router = get_router_by_id(router_id)
    if not router:
        continue

    if p.get("status") == "Lunas":
        sukses = set_pppoe_status(router, username_pppoe, aktif=True)
        print(f"{p['nama']} -> PPPoE hidup ✅" if sukses else f"{p['nama']} -> PPPoE hidup ❌")
    else:
        sukses = set_pppoe_status(router, username_pppoe, aktif=False)
        print(f"{p['nama']} -> PPPoE mati ✅" if sukses else f"{p['nama']} -> PPPoE mati ❌")