import time

CACHE = {}

TTL = 10   # detik

def get_status(router):
    key = router["id"]

    now = time.time()

    if key in CACHE:

        if now - CACHE[key]["time"] < TTL:
            return CACHE[key]["online"]

    online = is_router_online(router)

    CACHE[key] = {
        "online": online,
        "time": now
    }

    return online