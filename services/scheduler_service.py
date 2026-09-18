# services/scheduler_service.py
import threading
import time
from core import get_pelanggan, reminder_wa_list

def update_router_status():

    users = get_all_users()

    for u in users:

        routers = get_user_routers(u["id"])

        for r in routers:

            online = is_router_online(r)

            update_status_router(
                r["id"],
                online
            )

def update_data_pelanggan():
    try:
        get_pelanggan(fresh_from_mikrotik=True)
    except Exception as e:
        print("Sinkron gagal:", e)

def auto_wa_reminder():
    while True:
        try:
            for h in (-3, -1, 0):
                reminder_wa_list(h)
        except Exception as e:
            print("Reminder gagal:", e)
        time.sleep(3600)

def start_background_jobs():
    threading.Thread(target=update_data_pelanggan, daemon=True).start()
    threading.Thread(target=auto_wa_reminder, daemon=True).start()