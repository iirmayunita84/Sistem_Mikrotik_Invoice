# core/router_utils.py
import socket

def cek_mikrotik_online(host):
    try:
        sock = socket.create_connection((host, 8728), timeout=2)
        sock.close()
        return True
    except:
        return False