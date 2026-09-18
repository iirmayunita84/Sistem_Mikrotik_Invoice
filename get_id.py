# get_id.py
import uuid, hashlib
mac = uuid.getnode()
print(hashlib.sha256(str(mac).encode()).hexdigest())