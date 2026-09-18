import logging

from services.mikrotik_service import MikrotikClient
from core.router_log import simpan_router_log
from services.mikrotik_service import set_pppoe_status

log = logging.getLogger(__name__)

ISOLIR_LIST = "ISOLIR"
QUEUE_PREFIX = "ISOLIR-"
ISOLIR_COMMENT_PREFIX = "Billing Isolir"


def firewall_filter(api):
    return api.get_resource("/ip/firewall/filter")

def pastikan_rule_isolir(api):
    """
    Memastikan ada firewall filter:
    
    chain=forward
    src-address-list=ISOLIR
    action=drop
    
    Rule ditempatkan di posisi paling atas agar tidak
    dilewati oleh rule accept yang sudah ada.
    """

    try:

        fw_filter = firewall_filter(api)

        # Cari rule yang sudah ada
        rows = fw_filter.get(
            comment="Billing ISOLIR - BLOCK"
        )

        if rows:
            return True

        # Buat rule baru di posisi paling atas
        try:

            fw_filter.add(
                chain="forward",
                src_address_list="ISOLIR",
                action="drop",
                comment="Billing ISOLIR - BLOCK",
                place_before="0"
            )

        except Exception:

            # Beberapa versi RouterOS/API mungkin tidak
            # menerima place-before saat add.
            # Kalau gagal, jangan membuat rule yang
            # posisinya tidak jelas.
            log.exception(
                "❌ Gagal membuat firewall rule ISOLIR"
            )
            return False

        # Verifikasi rule benar-benar ada
        rows = fw_filter.get(
            comment="Billing ISOLIR - BLOCK"
        )

        if not rows:
            log.error(
                "❌ Firewall rule ISOLIR tidak ditemukan setelah dibuat"
            )
            return False

        log.info(
            "✅ Firewall rule ISOLIR siap"
        )

        return True

    except Exception:
        log.exception(
            "❌ Gagal memastikan firewall rule ISOLIR"
        )
        return False

def konek_router(router):

    client = MikrotikClient(
        host=router["host"],
        username=router["username"],
        password=router["password"],
        port=router.get("port", 8728)
    )

    if not client.connect():
        return None, None

    return client.api, client

def cari_ip_pppoe(api, username):

    if not username:
        return None

    try:

        active = api.get_resource("/ppp/active")

        rows = active.get(name=username)

        if not rows:
            return None

        return rows[0].get("address")

    except Exception as e:

        log.error(e)

        return None

def cari_ip_dhcp(api, pelanggan):

    try:

        # =================================================
        # IP YANG SUDAH TERSIMPAN DI DATABASE
        # =================================================

        ip_db = (
            pelanggan.get("ip_address")
            or pelanggan.get("ip")
            or ""
        ).strip()

        if ip_db:

            print(
                f"📌 Gunakan IP DHCP tersimpan: {ip_db}"
            )

            return ip_db

        # =================================================
        # BELUM ADA IP -> CARI BERDASARKAN MAC
        # =================================================

        lease = api.get_resource(
            "/ip/dhcp-server/lease"
        )

        mac = (
            pelanggan.get("mac_address")
            or pelanggan.get("mac")
            or ""
        ).strip()

        host = (
            pelanggan.get("host_name")
            or pelanggan.get("host")
            or ""
        ).strip()

        # -------------------------------------------------
        # 1. MAC
        # -------------------------------------------------

        if mac:

            print(
                f"🔎 Cari DHCP berdasarkan MAC: {mac}"
            )

            rows = lease.get(
                **{
                    "mac-address": mac
                }
            )

            if rows:

                found_ip = (
                    rows[0].get("address")
                    or ""
                ).strip()

                if found_ip:

                    print(
                        f"✅ DHCP ditemukan: "
                        f"{mac} → {found_ip}"
                    )

                    return found_ip

        # -------------------------------------------------
        # 2. HOSTNAME
        # -------------------------------------------------

        if host:

            print(
                f"🔎 Cari DHCP berdasarkan HOST: {host}"
            )

            rows = lease.get(
                **{
                    "host-name": host
                }
            )

            if rows:

                found_ip = (
                    rows[0].get("address")
                    or ""
                ).strip()

                if found_ip:

                    print(
                        f"✅ DHCP ditemukan: "
                        f"{host} → {found_ip}"
                    )

                    return found_ip

        print(
            f"⚠️ DHCP tidak ditemukan "
            f"MAC={mac} HOST={host}"
        )

    except Exception:

        log.exception(
            "❌ Gagal mencari DHCP lease"
        )

    return None

def ambil_ip_pelanggan(api, pelanggan):

    username = (
        pelanggan.get("pppoe_username")
        or ""
    ).strip()

    # ==========================================
    # PPPOE
    # ==========================================

    if username:

        ip = cari_ip_pppoe(
            api,
            username
        )

        if ip:
            return ip

    # ==========================================
    # DHCP
    #
    # IP DATABASE menjadi prioritas.
    # Ini penting supaya isolir tidak mengikuti
    # IP DHCP yang berubah-ubah.
    # ==========================================

    tipe = (
        pelanggan.get("tipe")
        or "DHCP"
    ).upper()

    if tipe == "DHCP":

        ip_db = (
            pelanggan.get("ip_address")
            or ""
        ).strip()

        if ip_db:
            return ip_db

        # Hanya fallback jika database belum memiliki IP.
        ip = cari_ip_dhcp(
            api,
            pelanggan
        )

        if ip:
            return ip

    return pelanggan.get(
        "ip_address"
    )

def firewall(api):

    return api.get_resource(
        "/ip/firewall/address-list"
    )

def queues(api):

    return api.get_resource(
        "/queue/simple"
    )

def secrets(api):

    return api.get_resource(
        "/ppp/secret"
    )

def nama_queue(pelanggan):

    username = pelanggan.get(
        "pppoe_username"
    )

    if username:

        return f"{QUEUE_PREFIX}{username}"

    return f"{QUEUE_PREFIX}{pelanggan['id']}"

def nama_firewall(pelanggan):

    username = pelanggan.get(
        "pppoe_username"
    )

    if username:

        return username

    return str(
        pelanggan["id"]
    )

def comment_isolir(pelanggan):

    pelanggan_id = pelanggan.get("id")

    mac = (
        pelanggan.get("mac_address")
        or pelanggan.get("mac")
        or ""
    )

    host = (
        pelanggan.get("host_name")
        or pelanggan.get("host")
        or ""
    )

    username = (
        pelanggan.get("pppoe_username")
        or ""
    )

    return (
        f"{ISOLIR_COMMENT_PREFIX} "
        f"| id={pelanggan_id} "
        f"| mac={mac} "
        f"| host={host} "
        f"| pppoe={username}"
    )

def firewall_exist(api, ip):

    if not ip:
        return False

    fw = firewall(api)

    rows = fw.get(
        list=ISOLIR_LIST,
        address=ip
    )

    return len(rows) > 0

def queue_exist(api, pelanggan):

    q = queues(api)

    rows = q.get(
        name=nama_queue(
            pelanggan
        )
    )

    return len(rows) > 0

def tambah_firewall_isolir(
    api,
    ip,
    pelanggan=None
):

    if not ip:
        return False

    try:

        if firewall_exist(
            api,
            ip
        ):
            return True

        fw = firewall(api)

        if pelanggan:

            comment = comment_isolir(
                pelanggan
            )

        else:

            comment = ISOLIR_COMMENT_PREFIX

        fw.add(
            list=ISOLIR_LIST,
            address=ip,
            comment=comment
        )

        log.info(
            f"🔴 IP masuk ISOLIR: {ip}"
        )

        return True

    except Exception:

        log.exception(
            "❌ Gagal menambah address-list ISOLIR"
        )

        return False

def hapus_firewall_isolir(api, ip):

    if not ip:
        return True

    try:

        fw = firewall(api)

        rows = fw.get(
            list=ISOLIR_LIST,
            address=ip
        )

        jumlah = 0

        for row in rows:

            row_id = (
                row.get(".id")
                or row.get("id")
            )

            if not row_id:

                log.warning(
                    f"⚠️ ID firewall tidak ditemukan: {row}"
                )

                continue

            fw.remove(
                **{
                    ".id": row_id
                }
            )

            jumlah += 1

        if jumlah:

            log.info(
                f"🧹 IP {ip} dihapus dari ISOLIR"
            )

        return True

    except Exception:

        log.exception(
            "❌ Gagal menghapus address-list ISOLIR"
        )

        return False

def hapus_semua_firewall_isolir_pelanggan(
    api,
    pelanggan,
    ip_sekarang=None
):

    try:

        fw = firewall(api)

        rows = fw.get(
            list=ISOLIR_LIST
        )

        pelanggan_id = str(
            pelanggan.get("id")
            or ""
        )

        mac = (
            pelanggan.get("mac_address")
            or pelanggan.get("mac")
            or ""
        )

        host = (
            pelanggan.get("host_name")
            or pelanggan.get("host")
            or ""
        )

        username = (
            pelanggan.get("pppoe_username")
            or ""
        )

        comment_target = comment_isolir(
            pelanggan
        )

        jumlah = 0

        for row in rows:

            address = row.get(
                "address"
            )

            comment = (
                row.get("comment")
                or ""
            )

            cocok = False

            # -------------------------------------------------
            # 1. IP yang sedang aktif
            # -------------------------------------------------

            if (
                ip_sekarang
                and address == ip_sekarang
            ):
                cocok = True

            # -------------------------------------------------
            # 2. COMMENT LENGKAP
            # -------------------------------------------------

            elif comment == comment_target:
                cocok = True

            # -------------------------------------------------
            # 3. ID PELANGGAN
            # -------------------------------------------------

            elif (
                pelanggan_id
                and f"id={pelanggan_id}" in comment
            ):
                cocok = True

            # -------------------------------------------------
            # 4. MAC
            # -------------------------------------------------

            elif (
                mac
                and f"mac={mac}" in comment
            ):
                cocok = True

            # -------------------------------------------------
            # 5. HOST
            # -------------------------------------------------

            elif (
                host
                and f"host={host}" in comment
            ):
                cocok = True

            # -------------------------------------------------
            # 6. PPPoE USERNAME
            # -------------------------------------------------

            elif (
                username
                and f"pppoe={username}" in comment
            ):
                cocok = True

            if not cocok:
                continue

            row_id = (
                row.get(".id")
                or row.get("id")
            )

            if not row_id:

                log.warning(
                    f"⚠️ ID firewall tidak ditemukan: {row}"
                )

                continue

            fw.remove(
                **{
                    ".id": row_id
                }
            )

            jumlah += 1

            log.info(
                f"🧹 ISOLIR dihapus: "
                f"IP={address} "
                f"COMMENT={comment}"
            )

        log.info(
            f"🧹 Total ISOLIR pelanggan "
            f"{pelanggan.get('nama')} "
            f"yang dihapus = {jumlah}"
        )

        return True

    except Exception:

        log.exception(
            "❌ Gagal membersihkan seluruh ISOLIR pelanggan"
        )

        return False

def buat_queue_isolir(
    api,
    pelanggan,
    ip
):

    if not ip:
        return False

    try:

        if queue_exist(
            api,
            pelanggan
        ):
            return True

        q = queues(api)

        q.add(
            name=nama_queue(
                pelanggan
            ),
            target=ip + "/32",
            max_limit="256k/256k",
            comment=comment_isolir(
                pelanggan
            )
        )

        log.info(
            f"🔴 Queue ISOLIR dibuat: "
            f"{nama_queue(pelanggan)} "
            f"target={ip}/32"
        )

        return True

    except Exception:

        log.exception(
            "❌ Gagal membuat queue ISOLIR"
        )

        return False

def hapus_queue_isolir(
    api,
    pelanggan
):

    try:

        q = queues(api)

        rows = q.get(
            name=nama_queue(
                pelanggan
            )
        )

        jumlah = 0

        for row in rows:

            row_id = (
                row.get(".id")
                or row.get("id")
            )

            if not row_id:

                log.warning(
                    f"⚠️ ID queue tidak ditemukan: {row}"
                )

                continue

            q.remove(
                **{
                    ".id": row_id
                }
            )

            jumlah += 1

        log.info(
            f"🧹 Queue {nama_queue(pelanggan)} "
            f"dihapus jumlah={jumlah}"
        )

        return True

    except Exception:

        log.exception(
            "❌ Gagal menghapus queue ISOLIR"
        )

        return False

def pastikan_isolir(
    api,
    pelanggan
):

    ip = ambil_ip_pelanggan(
        api,
        pelanggan
    )

    if not ip:
        return False

    ok1 = tambah_firewall_isolir(
        api,
        ip,
        pelanggan
    )

    ok2 = buat_queue_isolir(
        api,
        pelanggan,
        ip
    )

    return ok1 and ok2

def pastikan_aktif(
    api,
    pelanggan
):

    ip = ambil_ip_pelanggan(
        api,
        pelanggan
    )

    # Bersihkan semua address-list ISOLIR
    # milik pelanggan, termasuk IP lama.
    ok1 = hapus_semua_firewall_isolir_pelanggan(
        api,
        pelanggan,
        ip
    )

    # Hapus queue isolir.
    ok2 = hapus_queue_isolir(
        api,
        pelanggan
    )

    return ok1 and ok2

def proses_isolir(
    router,
    pelanggan,
    api=None,
    client=None
):

    own_connection = False

    try:

        if api is None:

            api, client = konek_router(
                router
            )

            if not api:
                return False

            own_connection = True

        ip = ambil_ip_pelanggan(
            api,
            pelanggan
        )

        log.info(
            f"[ISOLIR] "
            f"{pelanggan.get('nama')} "
            f"MAC={pelanggan.get('mac_address')} "
            f"IP={ip}"
        )

        if not ip:

            simpan_router_log(

                user_id=pelanggan["user_id"],

                router_id=router["id"],

                pelanggan_id=pelanggan["id"],

                nama=pelanggan.get("nama"),

                username=pelanggan.get(
                    "pppoe_username"
                ),

                ip="",

                aksi="ISOLIR",

                status="GAGAL",

                keterangan="IP pelanggan tidak ditemukan"
            )

            return False

        # -------------------------------------------------
        # PASTIKAN FIREWALL RULE ISOLIR
        # -------------------------------------------------

        if not pastikan_rule_isolir(api):

            log.error(
                f"❌ Firewall rule ISOLIR tidak siap "
                f"{pelanggan.get('nama')} "
                f"IP={ip}"
            )

            simpan_router_log(

                user_id=pelanggan["user_id"],

                router_id=router["id"],

                pelanggan_id=pelanggan["id"],

                nama=pelanggan.get("nama"),

                username=pelanggan.get(
                    "pppoe_username"
                ),

                ip=ip,

                aksi="ISOLIR",

                status="GAGAL",

                keterangan="Firewall rule ISOLIR tidak tersedia"
            )

            return False


        # -------------------------------------------------
        # TAMBAH ADDRESS LIST
        # -------------------------------------------------

        ok_fw = tambah_firewall_isolir(
            api,
            ip,
            pelanggan
        )


        # -------------------------------------------------
        # BUAT QUEUE
        # -------------------------------------------------

        ok_queue = buat_queue_isolir(
            api,
            pelanggan,
            ip
        )

        if not ok_fw or not ok_queue:

            log.error(
                f"❌ Gagal membuat isolir "
                f"{pelanggan.get('nama')} "
                f"IP={ip}"
            )

            return False

        simpan_router_log(

            user_id=pelanggan["user_id"],

            router_id=router["id"],

            pelanggan_id=pelanggan["id"],

            nama=pelanggan.get("nama"),

            username=pelanggan.get(
                "pppoe_username"
            ),

            ip=ip,

            aksi="ISOLIR",

            status="BERHASIL",

            keterangan="Firewall + Queue dibuat"
        )

        return True

    except Exception as e:

        log.exception(e)

        simpan_router_log(

            user_id=pelanggan["user_id"],

            router_id=router["id"],

            pelanggan_id=pelanggan["id"],

            nama=pelanggan.get("nama"),

            username=pelanggan.get(
                "pppoe_username"
            ),

            ip=pelanggan.get(
                "ip_address"
            ),

            aksi="ISOLIR",

            status="GAGAL",

            keterangan=str(e)
        )

        return False

    finally:

        if own_connection and client:

            try:

                client.disconnect()

            except Exception:

                pass

def hapus_isolir(
    router,
    pelanggan,
    api=None,
    client=None
):

    own_connection = False

    try:

        if api is None:

            api, client = konek_router(
                router
            )

            if not api:
                return False

            own_connection = True

        ip = ambil_ip_pelanggan(
            api,
            pelanggan
        )

        log.info(
            f"[BUKA ISOLIR] "
            f"{pelanggan.get('nama')} "
            f"IP_SEKARANG={ip}"
        )

        # -------------------------------------------------
        # HAPUS SEMUA ADDRESS LIST ISOLIR
        #
        # Termasuk IP lama DHCP jika IP pelanggan berubah.
        # -------------------------------------------------

        ok_fw = hapus_semua_firewall_isolir_pelanggan(
            api,
            pelanggan,
            ip
        )

        # -------------------------------------------------
        # HAPUS QUEUE
        # -------------------------------------------------

        ok_queue = hapus_queue_isolir(
            api,
            pelanggan
        )

        if not ok_fw or not ok_queue:

            log.error(
                f"❌ Gagal membuka isolir "
                f"{pelanggan.get('nama')} "
                f"IP={ip}"
            )

            return False

        simpan_router_log(

            user_id=pelanggan["user_id"],

            router_id=router["id"],

            pelanggan_id=pelanggan["id"],

            nama=pelanggan.get("nama"),

            username=pelanggan.get(
                "pppoe_username"
            ),

            ip=ip,

            aksi="BUKA ISOLIR",

            status="BERHASIL",

            keterangan="IP dikeluarkan dari ISOLIR + queue dihapus"
        )

        log.info(
            f"🟢 ISOLIR DIBUKA: "
            f"{pelanggan.get('nama')} "
            f"IP={ip}"
        )

        return True

    except Exception as e:

        log.exception(
            f"❌ Gagal buka isolir: {e}"
        )

        return False

    finally:

        if own_connection and client:

            try:

                client.disconnect()

            except Exception:

                pass

def cari_ip_pppoe_aktif(
    api,
    username
):

    try:

        active = api.get_resource(
            "/ppp/active"
        )

        data = active.get(
            name=username
        )

        if data:

            return data[0].get(
                "address"
            )

    except Exception as e:

        log.error(e)

    return None