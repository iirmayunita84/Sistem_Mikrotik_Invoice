import os, json, bcrypt

ADMIN_FILE = "data/admin.json"

def init_admin(default_password="admin123"):
    os.makedirs("data", exist_ok=True)
    if os.path.exists(ADMIN_FILE):
        return
    hashed = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()
    with open(ADMIN_FILE, "w") as f:
        json.dump({"username":"admin","password":hashed}, f, indent=2)

def verify_login(username, password):
    if not os.path.exists(ADMIN_FILE):
        return False
    with open(ADMIN_FILE, "r") as f:
        data = json.load(f)
    if username != data["username"]:
        return False
    return bcrypt.checkpw(password.encode(), data["password"].encode())

def change_password(old_pass, new_pass):
    with open(ADMIN_FILE, "r") as f:
        data = json.load(f)
    if not bcrypt.checkpw(old_pass.encode(), data["password"].encode()):
        return False
    hashed = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
    data["password"] = hashed
    with open(ADMIN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True