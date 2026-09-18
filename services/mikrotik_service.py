# mikrotik_service.py
import socket

try:
    from routeros_api import RouterOsApiPool
except ImportError:
    RouterOsApiPool = None


# ===============================
# CEK ROUTER ONLINE (FAST CHECK)
# ===============================
def cek_router_online(host, port=8728, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.create_connection((host, port))
        s.close()
        return True
    except Exception:
        return False

# ===============================
# CLIENT MIKROTIK
# ===============================
class MikrotikClient:
    def __init__(self, host, username, password, port=8728):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.api = None
        self.connection = None

    def connect(self):
        try:
            self.connection = RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                plaintext_login=True,
                use_ssl=False
            )
            self.api = self.connection.get_api()
            return True
        except Exception as e:
            print(f"[ERROR] Gagal konek ke {self.host}: {e}")
            return False

    def disconnect(self):
        try:
            if self.connection:
                self.connection.disconnect()
        except:
            pass

    def get_leases_with_comment(self):
        if not self.api:
            return []
        try:
            leases = self.api.get_resource('/ip/dhcp-server/lease').get()
            filtered = [l for l in leases if validate_comment(l.get('comment', ''))]
            for l in filtered:
                l['parsed'] = parse_comment(l.get('comment', ''))
            return filtered
        except Exception as e:
            print(f"[ERROR] Gagal ambil leases: {e}")
            return []

    def get_monthly_usage_gb(self, ip_addr):
        """Hitung total usage per IP dari queue simple (upload+download)"""
        if not self.api or not ip_addr:
            return 0.0
        try:
            queues = self.api.get_resource('/queue/simple').call('print', {'stats': ''})
            for q in queues:
                target = q.get('target', '') or q.get('dst', '')
                if ip_in_target(ip_addr, target):
                    tb = q.get('bytes')
                    if tb:
                        parts = tb.split('/')
                        total_bytes = sum(int(p) for p in parts if p.isdigit())
                        return round(total_bytes / (1024**3), 2)
        except:
            pass
        return 0.0

    def get_interface_usage_gb(self, interface_name=None):
        """Hitung usage per interface (upload+download)"""
        if not self.api:
            return {} if interface_name is None else 0.0
        usage = {}
        try:
            interfaces = self.api.get_resource('/interface').get()
            for intf in interfaces:
                name = intf.get('name')
                if interface_name and name != interface_name:
                    continue
                rx = int(intf.get('rx-byte', 0))
                tx = int(intf.get('tx-byte', 0))
                usage_gb = round((rx + tx) / (1024**3), 2)
                usage[name] = usage_gb
            if interface_name:
                return usage.get(interface_name, 0.0)
            return usage
        except:
            return {} if interface_name is None else 0.0

    # ---- New: set comment helpers ----
    def set_lease_comment_by_id(self, lease_id, comment):
        if not self.api or not lease_id:
            return False
        try:
            self.api.get_resource('/ip/dhcp-server/lease').call('set', {'.id': lease_id, 'comment': comment})
            return True
        except Exception as e:
            print(f"[ERROR] Gagal set comment (.id={lease_id}): {e}")
            return False

    def set_lease_comment_by_address(self, address, comment):
        if not self.api or not address:
            return False
        try:
            res = self.api.get_resource('/ip/dhcp-server/lease')
            leases = res.get()
            target = next((l for l in leases if l.get('address') == address), None)
            if not target:
                print(f"[WARN] Lease untuk address {address} tidak ditemukan.")
                return False
            lease_id = target.get('.id')
            return self.set_lease_comment_by_id(lease_id, comment)
        except Exception as e:
            print(f"[ERROR] Gagal set comment (address={address}): {e}")
            return False

# ===============================
# SERVICE FUNCTION (UNTUK CORE)
# ===============================
def set_pppoe_status(router, pppoe_username, aktif=True):
    """
    router = dict hasil dari DB:
    {
        host,
        username,
        password,
        port
    }
    """
    client = MikrotikClient(
        host=router.get("host"),
        username=router.get("username"),
        password=router.get("password"),
        port=router.get("port", 8728),
    )

    if not client.connect():
        return False

    result = client.set_pppoe_status(pppoe_username, aktif)
    client.disconnect()
    return result

def is_router_online(host, port=8728):
    return cek_router_online(host, port)

def tarik_dhcp(api):
    try:
        return api.get_resource("/ip/dhcp-server/lease").get()
    except Exception:
        return []

def tarik_wireless(api):
    try:
        wlan = api.get_resource("/interface/wireless/registration-table")

        hasil = []

        for i in wlan.get():
            hasil.append({
                "mac": i.get("mac-address"),
                "ip": i.get("last-ip"),
                "signal": i.get("signal-strength"),
                "interface": i.get("interface"),
            })

        return hasil

    except Exception:
        return []

def tambah_address_list(router, ip_address):

    client = MikrotikClient(
        host=router.get("host"),
        username=router.get("username"),
        password=router.get("password"),
        port=router.get("port",8728),
    )

    if not client.connect():
        return False

    try:
        firewall = client.api.get_resource(
            "/ip/firewall/address-list"
        )

        firewall.add(
            list="pelanggan_isolir",
            address=ip_address,
            comment="ISOLIR BELUM LUNAS"
        )

        return True

    except Exception as e:
        print("Firewall error:", e)
        return False

    finally:
        client.disconnect()

def update_comment_mikrotik(router, username, comment):
    api, conn = konek_mikrotik(router)

    try:
        secret = api.get_resource("/ppp/secret")

        data = secret.get(name=username)

        if data:
            secret.set(
                id=data[0][".id"],
                comment=comment
            )

        return True

    finally:
        conn.disconnect()