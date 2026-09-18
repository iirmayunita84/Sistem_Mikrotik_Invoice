#core/mikrotik_api.py
import logging
import ipaddress
from routeros_api import RouterOsApiPool
from core.db import get_db, release_db
from datetime import datetime
from core.comment_parser import parse_comment
from dateutil.relativedelta import relativedelta
from contextlib import contextmanager

def get_router_by_id(user_id, router_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, host, port, username, password
        FROM routers
        WHERE id=? AND user_id=?
    """, (router_id, user_id))

    row = cur.fetchone()

    release_db(conn)

    return dict(row) if row else None

def connect_router(router):

    pool = RouterOsApiPool(
        host=router["host"],
        username=router["username"],
        password=router.get("password", ""),
        port=int(router.get("port", 8728)),
        plaintext_login=True
    )

    api = pool.get_api()

    return api, pool

def normalize_mac(mac):
    if not mac:
        return ""

    return (
        str(mac)
        .strip()
        .upper()
        .replace("-", ":")
    )

def get_dhcp_lease_by_mac(
    api,
    mac_address
):

    if not api or not mac_address:
        return None

    try:

        mac = normalize_mac(
            mac_address
        )

        lease = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        rows = lease.get(
            **{
                "mac-address": mac
            }
        )

        if not rows:
            return None

        return rows[0]

    except Exception:

        logging.exception(
            "❌ Gagal mencari DHCP lease berdasarkan MAC"
        )

        return None

def get_dhcp_lease_by_ip(
    api,
    ip_address
):

    if not api or not ip_address:
        return None

    try:

        lease = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        rows = lease.get(
            address=str(
                ip_address
            ).strip()
        )

        if not rows:
            return None

        return rows[0]

    except Exception as e:

        logging.exception(
            "❌ Gagal mencari DHCP lease IP %s: %s",
            ip_address,
            e
        )

        return None

def make_dhcp_lease_static(
    api,
    lease_id
):

    if not api or not lease_id:
        return False

    try:

        lease = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        lease.call(
            "make-static",
            {
                ".id": lease_id
            }
        )

        logging.info(
            "✅ DHCP lease menjadi STATIC: %s",
            lease_id
        )

        return True

    except Exception as e:

        logging.exception(
            "❌ Gagal make-static DHCP lease %s: %s",
            lease_id,
            e
        )

        return False

def set_dhcp_lease_comment(
    api,
    lease_id,
    comment
):

    if not api or not lease_id:
        return False

    try:

        lease = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        lease.set(
            **{
                ".id": lease_id,
                "comment": comment or ""
            }
        )

        return True

    except Exception as e:

        logging.exception(
            "❌ Gagal update comment DHCP: %s",
            e
        )

        return False

def get_all_dhcp_leases(api):

    if not api:
        return []

    try:

        lease = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        rows = lease.get()

        return rows or []

    except Exception as e:

        logging.exception(
            "❌ Gagal mengambil seluruh DHCP lease: %s",
            e
        )

        return []

def sync_dhcp_static_bindings(
    api,
    pelanggan_list
):
    """
    SINKRONISASI DHCP STATIC FINAL.

    Hanya satu koneksi MikroTik digunakan.

    Alur:

        MikroTik
           ↓
        ambil semua lease
           ↓
        index berdasarkan MAC
           ↓
        cocokkan pelanggan
           ↓
        dynamic → static
           ↓
        hasil IP + MAC
    """

    hasil = []

    if not api:
        return hasil

    if not pelanggan_list:
        return hasil

    try:

        # ==================================================
        # AMBIL SEMUA DHCP LEASE SEKALI
        # ==================================================

        leases = get_all_dhcp_leases(
            api
        )

        if not leases:

            logging.info(
                "Tidak ada DHCP lease."
            )

            return hasil

        # ==================================================
        # INDEX MAC
        # ==================================================

        lease_by_mac = {}

        for lease_row in leases:

            mac = normalize_mac(
                lease_row.get(
                    "mac-address"
                )
            )

            if not mac:
                continue

            lease_by_mac[mac] = lease_row

        logging.info(
            "📡 Total DHCP lease: %s",
            len(lease_by_mac)
        )

        # ==================================================
        # COCOKKAN PELANGGAN
        # ==================================================

        for pelanggan in pelanggan_list:

            tipe = str(
                pelanggan.get("tipe")
                or "DHCP"
            ).upper()

            if tipe != "DHCP":
                continue

            mac = normalize_mac(
                pelanggan.get(
                    "mac_address"
                )
                or pelanggan.get("mac")
            )

            if not mac:

                logging.warning(
                    "⚠️ Pelanggan %s belum memiliki MAC",
                    pelanggan.get("nama")
                )

                continue

            lease_row = lease_by_mac.get(
                mac
            )

            if not lease_row:

                logging.info(
                    "⚠️ DHCP tidak ditemukan | "
                    "%s | MAC=%s",
                    pelanggan.get("nama"),
                    mac
                )

                continue

            # ==================================================
            # ID LEASE
            # ==================================================

            lease_id = (
                lease_row.get(".id")
                or lease_row.get("id")
            )

            if not lease_id:
                continue

            # ==================================================
            # IP
            # ==================================================

            ip = str(
                lease_row.get("address")
                or ""
            ).strip()

            if not ip:
                continue

            # ==================================================
            # MAC SEBENARNYA
            # ==================================================

            real_mac = normalize_mac(
                lease_row.get(
                    "mac-address"
                )
                or mac
            )

            # ==================================================
            # CEK DYNAMIC
            # ==================================================

            dynamic = str(
                lease_row.get("dynamic")
                or ""
            ).lower()

            static_ok = True

            # ==================================================
            # DYNAMIC → STATIC
            # ==================================================

            if dynamic in (
                "yes",
                "true",
                "1"
            ):

                logging.info(
                    "🔄 MAKE STATIC | "
                    "%s | MAC=%s | IP=%s",
                    pelanggan.get("nama"),
                    real_mac,
                    ip
                )

                static_ok = make_dhcp_lease_static(
                    api,
                    lease_id
                )

            if not static_ok:

                logging.error(
                    "❌ Gagal make-static | "
                    "%s | MAC=%s | IP=%s",
                    pelanggan.get("nama"),
                    real_mac,
                    ip
                )

                continue

            # ==================================================
            # HASIL
            # ==================================================

            hasil.append({

                "pelanggan_id":
                    pelanggan.get("id"),

                "ip":
                    ip,

                "mac":
                    real_mac,

                "lease_id":
                    lease_id,

                "static":
                    True

            })

            logging.info(
                "🔒 DHCP STATIC OK | "
                "%s | MAC=%s | IP=%s",
                pelanggan.get("nama"),
                real_mac,
                ip
            )

        return hasil

    except Exception:

        logging.exception(
            "❌ Sinkronisasi DHCP static gagal"
        )

        return hasil

def binding_dhcp_pelanggan(api, pelanggan):
    """
    Binding DHCP pelanggan yang sudah dikenal.

    Aturan:
    1. Jika pelanggan belum punya IP:
       MAC -> cari lease -> ambil IP -> make-static.
    2. Jika pelanggan sudah punya IP:
       gunakan IP lama sebagai acuan.
       Jika MAC ditemukan di IP berbeda, JANGAN mengubah IP.
    3. Hanya pelanggan yang sudah ada di database yang boleh dibinding.
    """

    if not api:
        return {
            "success": False,
            "message": "API MikroTik tidak tersedia."
        }

    if not pelanggan:
        return {
            "success": False,
            "message": "Data pelanggan kosong."
        }

    mac = normalize_mac(
        pelanggan.get("mac_address")
        or pelanggan.get("mac")
    )

    old_ip = (
        pelanggan.get("ip_address")
        or pelanggan.get("ip")
        or ""
    ).strip()

    if not mac:
        return {
            "success": False,
            "message": "MAC address pelanggan belum tersedia."
        }

    lease = None

    # =========================================================
    # 1. JIKA SUDAH PUNYA IP, PERTAHANKAN IP LAMA
    # =========================================================
    if old_ip:
        lease = get_dhcp_lease_by_ip(api, old_ip)

        if lease:
            lease_mac = normalize_mac(
                lease.get("mac-address")
                or lease.get("mac")
                or ""
            )

            # IP lama ditemukan tetapi MAC berbeda
            if lease_mac and lease_mac != mac:
                return {
                    "success": False,
                    "message": (
                        "IP pelanggan sudah tersimpan sebagai "
                        f"{old_ip}, tetapi MAC pada lease berbeda "
                        f"({lease_mac}). IP tidak diubah."
                    ),
                    "ip_address": old_ip,
                    "mac_address": mac
                }

        else:
            # IP lama tidak ditemukan.
            # Cek MAC hanya untuk mendeteksi apakah MAC pindah IP.
            lease_by_mac = get_dhcp_lease_by_mac(api, mac)

            if lease_by_mac:
                new_ip = (
                    lease_by_mac.get("address")
                    or lease_by_mac.get("ip")
                    or ""
                ).strip()

                if new_ip and new_ip != old_ip:
                    return {
                        "success": False,
                        "message": (
                            f"MAC {mac} ditemukan di IP {new_ip}, "
                            f"sedangkan IP pelanggan tersimpan {old_ip}. "
                            "IP tidak diubah otomatis."
                        ),
                        "ip_address": old_ip,
                        "mac_address": mac
                    }

                lease = lease_by_mac
            else:
                return {
                    "success": False,
                    "message": (
                        f"Lease untuk IP {old_ip} / MAC {mac} "
                        "tidak ditemukan."
                    ),
                    "ip_address": old_ip,
                    "mac_address": mac
                }

    # =========================================================
    # 2. PELANGGAN BELUM PUNYA IP -> CARI BERDASARKAN MAC
    # =========================================================
    else:
        lease = get_dhcp_lease_by_mac(api, mac)

        if not lease:
            return {
                "success": False,
                "message": (
                    f"MAC {mac} belum ditemukan pada DHCP lease."
                ),
                "mac_address": mac
            }

    # =========================================================
    # 3. AMBIL DATA LEASE
    # =========================================================
    lease_id = (
        lease.get(".id")
        or lease.get("id")
    )

    if not lease_id:
        return {
            "success": False,
            "message": "ID lease MikroTik tidak ditemukan."
        }

    real_mac = normalize_mac(
        lease.get("mac-address")
        or lease.get("mac")
        or mac
    )

    real_ip = (
        lease.get("address")
        or lease.get("ip")
        or old_ip
        or ""
    ).strip()

    if not real_ip:
        return {
            "success": False,
            "message": "IP address DHCP tidak ditemukan."
        }

    # =========================================================
    # 4. PENGAMAN IP
    # =========================================================
    if old_ip and real_ip != old_ip:
        return {
            "success": False,
            "message": (
                f"IP lama {old_ip} berbeda dengan lease {real_ip}. "
                "IP pelanggan tidak diubah otomatis."
            ),
            "ip_address": old_ip,
            "mac_address": real_mac
        }

    # =========================================================
    # 5. CEK DYNAMIC
    # =========================================================
    dynamic = str(
        lease.get("dynamic", "")
    ).lower() in ("yes", "true", "1")

    if dynamic:
        try:
            make_dhcp_lease_static(api, lease_id)
        except Exception as e:
            return {
                "success": False,
                "message": (
                    f"Gagal mengubah DHCP lease menjadi static: {e}"
                ),
                "ip_address": real_ip,
                "mac_address": real_mac
            }

    # =========================================================
    # 6. COMMENT PELANGGAN
    # =========================================================
    comment = pelanggan.get("comment") or ""

    if comment:
        try:
            set_dhcp_lease_comment(
                api,
                lease_id,
                comment
            )
        except Exception as e:
            print(
                "[DHCP] Warning update comment:",
                e
            )

    print(
        f"[DHCP BINDING OK] "
        f"MAC={real_mac} | "
        f"IP={real_ip} | "
        f"STATIC=YES"
    )

    return {
        "success": True,
        "lease_id": lease_id,
        "mac_address": real_mac,
        "ip_address": real_ip,
        "static": True
    }

def sync_dhcp_ip_binding(api, pelanggan):
    """
    Sinkronisasi binding DHCP ke object pelanggan.
    Tidak mengubah database secara langsung.
    """

    result = binding_dhcp_pelanggan(
        api,
        pelanggan
    )

    if not result.get("success"):
        print(
            "[DHCP BINDING GAGAL]",
            result.get("message")
        )
        return pelanggan

    pelanggan["mac_address"] = (
        result.get("mac_address")
        or pelanggan.get("mac_address")
    )

    pelanggan["ip_address"] = (
        result.get("ip_address")
        or pelanggan.get("ip_address")
    )

    return pelanggan

def ip_cocok_target(ip_address, target):
    """
    Mengecek apakah IP pelanggan termasuk target Simple Queue.

    Mendukung:
    192.168.3.9
    192.168.3.9/32
    192.168.3.0/24
    """
    if not ip_address or not target:
        return False

    ip_address = str(ip_address).strip()
    target = str(target).strip()

    # MikroTik kadang memberikan beberapa target
    # dalam satu field
    targets = target.split(",")

    try:
        ip_obj = ipaddress.ip_address(ip_address)

        for item in targets:
            item = item.strip()

            if not item:
                continue

            # Hilangkan prefix target jika ada
            try:
                if "/" in item:
                    network = ipaddress.ip_network(
                        item,
                        strict=False
                    )

                    if ip_obj in network:
                        return True

                else:
                    if ip_obj == ipaddress.ip_address(item):
                        return True

            except ValueError:
                continue

    except ValueError:
        return False

    return False

def get_usage_queue_gb(api, ip_address):
    """
    Mengambil total counter upload + download
    dari Simple Queue berdasarkan IP pelanggan.

    Return:
        float -> GB
    """

    if not api or not ip_address:
        return 0.0

    try:

        queue_resource = api.get_resource(
            "/queue/simple"
        )

        queues = queue_resource.call(
            "print",
            {
                "stats": ""
            }
        )

        for queue in queues:

            target = (
                queue.get("target")
                or queue.get("dst")
                or ""
            )

            if not ip_cocok_target(
                ip_address,
                target
            ):
                continue

            bytes_value = queue.get("bytes")

            if not bytes_value:
                return 0.0

            # RouterOS biasanya:
            # bytes = upload/download
            parts = str(bytes_value).split("/")

            total_bytes = 0

            for part in parts:

                part = str(part).strip()

                try:
                    total_bytes += int(part)

                except (ValueError, TypeError):
                    pass

            usage_gb = (
                total_bytes / (1024 ** 3)
            )

            return round(
                usage_gb,
                2
            )

        return 0.0

    except Exception as e:

        logging.exception(
            "Gagal mengambil usage queue: %s",
            e
        )

        return 0.0

def get_pppoe_active_ip(api, username):
    """
    Mengambil IP address PPPoE yang sedang aktif
    berdasarkan username.
    """

    if not api or not username:
        return ""

    try:

        active = api.get_resource(
            "/ppp/active"
        ).get(
            name=username
        )

        if not active:
            return ""

        user = active[0]

        return (
            user.get("address")
            or user.get("remote-address")
            or ""
        )

    except Exception as e:

        logging.exception(
            "Gagal mengambil IP PPPoE %s: %s",
            username,
            e
        )

        return ""

def get_pelanggan_usage(api, pelanggan):
    """
    Mengambil usage pelanggan berdasarkan tipe.

    DHCP:
        menggunakan ip_address / ip

    PPPoE:
        menggunakan IP aktif dari /ppp/active
    """

    if not api or not pelanggan:
        return 0.0

    tipe = str(
        pelanggan.get("tipe") or ""
    ).upper()

    # ==========================================
    # DHCP
    # ==========================================

    if tipe == "DHCP":

        ip_address = (
            pelanggan.get("ip_address")
            or pelanggan.get("ip")
            or ""
        )

        if not ip_address:
            return 0.0

        return get_usage_queue_gb(
            api,
            ip_address
        )

    # ==========================================
    # PPPOE
    # ==========================================

    if tipe == "PPPOE":

        username = (
            pelanggan.get("pppoe_username")
            or pelanggan.get("pppoe_user")
            or ""
        )

        if not username:
            return 0.0

        ip_address = get_pppoe_active_ip(
            api,
            username
        )

        if not ip_address:
            return 0.0

        print(
            f"📡 PPPoE {username} "
            f"→ IP {ip_address}"
        )

        return get_usage_queue_gb(
            api,
            ip_address
        )

    return 0.0

def get_dhcp_leases(router):

    api, pool = connect_router(router)

    try:

        leases = api.get_resource(
            "/ip/dhcp-server/lease"
        ).get()

        for lease in leases:

            comment = (lease.get("comment") or "").strip()

            if not comment:
                continue

            data = parse_comment(comment)

            logging.debug("COMMENT = %s", comment)
            logging.debug("HASIL PARSE = %s", data)

            if not data.get("nama"):
                continue

            lease.update(data)

            logging.debug("HASIL PARSE = %s", data)

            data = parse_comment(comment)

            if not data.get("nama"):
                continue

            lease.update(data)
        return leases

    finally:
        pool.disconnect()

def get_comment_by_ip(router, ip):

    api, pool = connect_router(router)

    try:

        queues = api.get_resource("/queue/simple").get()

        for q in queues:

            if q.get("target","").startswith(ip):

                return q.get("comment")

        return None

    finally:
        pool.disconnect()

@contextmanager
def with_router(router):

    api, pool = connect_router(router)

    try:
        yield api
    finally:
        pool.disconnect()

def update_due_by_ip(router, ip):
    api, pool = connect_router(router)

    queues = api.get_resource('/queue/simple').get()

    for q in queues:
        if ip in q.get('target', ''):

            comment = q.get('comment', '')

            if 'due:' not in comment:
                continue

            old_due = comment.split('due:')[1].split(';')[0]

            try:
                dt = datetime.strptime(old_due,"%d/%m/%Y")
            except:
                continue

            new_due = (dt + relativedelta(months=1)).strftime("%d/%m/%Y")

            new_comment = comment.replace(old_due, new_due)

            api.get_resource('/queue/simple').set(
                **{'.id': q['.id'], 'comment': new_comment}
            )

    pool.disconnect()

def update_comment_pppoe(router, username, comment):

    pool = None

    try:

        api, pool = connect_router(router)

        secrets = api.get_resource("/ppp/secret")

        users = secrets.get(name=username)

        if users:
            secrets.set(
                **{
                    ".id": users[0][".id"],
                    "comment": comment
                }
            )

        return True

    except Exception as e:
        print("Gagal update PPPoE comment:", e)
        return False

    finally:
        if pool:
            pool.disconnect()

def update_pppoe_user(
    router,
    old_username,
    new_username,
    comment=None,
    password=None,
    profile=None
):
    """
    Update PPP Secret MikroTik.

    Bisa mengubah:
    - username
    - password
    - comment
    - profile
    """

    pool = None

    try:

        api, pool = connect_router(router)

        ppp = api.get_resource(
            "/ppp/secret"
        )

        # ==========================================
        # CARI USERNAME LAMA
        # ==========================================

        users = ppp.get(
            name=old_username
        )

        if not users:

            print(
                "❌ PPPoE username tidak ditemukan:",
                old_username
            )

            return False


        user = users[0]


        # ==========================================
        # DATA UPDATE
        # ==========================================

        data = {
            ".id": user[".id"]
        }


        # ==========================================
        # UPDATE USERNAME
        # ==========================================

        if new_username:

            data["name"] = new_username


        # ==========================================
        # UPDATE PASSWORD
        # ==========================================

        if password:

            data["password"] = password


        # ==========================================
        # UPDATE COMMENT
        # ==========================================

        if comment is not None:

            data["comment"] = comment


        # ==========================================
        # UPDATE PROFILE / PAKET
        # ==========================================

        if profile:

            data["profile"] = profile


        # ==========================================
        # KIRIM UPDATE KE MIKROTIK
        # ==========================================

        print("========================================")
        print("🔄 UPDATE PPPoE SECRET")
        print("ID      :", user[".id"])
        print("Username:", new_username)
        print("Profile :", profile)
        print("Comment :", comment)
        print("========================================")

        ppp.set(
            **data
        )


        print(
            "✅ PPPoE Secret berhasil diperbarui"
        )


        return True


    except Exception as e:

        print(
            "❌ Gagal update PPPoE Secret:",
            repr(e)
        )

        return False


    finally:

        if pool:

            try:

                pool.disconnect()

            except Exception:

                pass

def update_comment_dhcp(router, mac_address, comment):

    pool = None

    try:

        api, pool = connect_router(router)

        leases = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        # ==========================================
        # CARI DHCP LEASE BERDASARKAN MAC ADDRESS
        # ==========================================

        data = leases.get(
            **{
                "mac-address": mac_address
            }
        )

        if not data:

            print(
                "❌ DHCP Lease tidak ditemukan:",
                mac_address
            )

            return False

        lease = data[0]

        print(
            "🔎 DHCP LEASE DITEMUKAN:",
            lease
        )

        # ==========================================
        # AMBIL ID MIKROTIK
        # ==========================================

        lease_id = (
            lease.get(".id")
            or lease.get("id")
        )

        if not lease_id:

            print(
                "❌ DHCP Lease tidak memiliki ID:",
                lease
            )

            return False

        print(
            "🔑 DHCP ID:",
            lease_id
        )

        # ==========================================
        # UPDATE COMMENT
        # ==========================================

        leases.set(
            **{
                ".id": lease_id,
                "comment": comment
            }
        )

        print(
            "✅ Comment DHCP berhasil diupdate"
        )

        print(
            "   MAC     :",
            mac_address
        )

        print(
            "   ID      :",
            lease_id
        )

        print(
            "   COMMENT :",
            comment
        )

        return True

    except Exception as e:

        print(
            "❌ Update DHCP gagal:",
            e
        )

        return False

    finally:

        if pool:

            try:
                pool.disconnect()

            except Exception:
                pass

def set_pppoe_status(user_id, router_id, username, aktif=True):

    router = get_router_by_id(user_id, router_id)

    if not router:
        raise Exception("Router tidak ditemukan")

    api, pool = connect_router(router)

    try:

        ppp = api.get_resource("/ppp/secret")

        users = ppp.get(name=username)

        if not users:
            raise Exception(
                f"User PPPoE tidak ditemukan: {username}"
            )

        user = users[0]

        secret_id = (
            user.get(".id")
            or user.get("id")
        )

        if not secret_id:
            raise Exception(
                f"ID PPPoE tidak ditemukan: {user}"
            )

        ppp.set(
            **{
                ".id": secret_id,
                "disabled": "false" if aktif else "true"
            }
        )

        print(
            f"✅ PPPoE {username} "
            f"{'AKTIF' if aktif else 'NONAKTIF'}"
        )

        return True

    finally:
        pool.disconnect()