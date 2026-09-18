import requests
import time

BASE = "http://127.0.0.1:5000"

print("=== AUTO WA REMINDER START ===")

for hari in [-3, -1, 0]:
    try:
        url = f"{BASE}/wa-reminder/{hari}"
        r = requests.get(url, timeout=10)
        print("OK:", url, r.status_code)
        time.sleep(3)  # jeda biar browser gak berat
    except Exception as e:
        print("ERROR:", hari, e)

print("=== SELESAI ===")