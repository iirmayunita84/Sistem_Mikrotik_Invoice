# core/mikrotik_core.py
import logging
import uuid
from core.logic import load_mikrotik_list, get_all_users
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from core.db import db_connection
from core.transaksi_core import (
    simpan_transaksi,
    get_transaksi_list,
    pembayaran_selesai,
)
from core.core_pelanggan import (
    get_pelanggan_list,
    update_pelanggan,
    refresh_pelanggan_cache,
)
from core.mikrotik_api import (
    binding_dhcp_pelanggan,
    update_comment_dhcp,
    update_comment_pppoe,
    update_pppoe_user,
    get_pelanggan_usage,
)
from core.isolir_core import proses_isolir, hapus_isolir
from services.mikrotik_service import set_pppoe_status, MikrotikClient
from core.comment_parser import parse_comment
# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

log = logging.getLogger("mikrotik_core")

def konek_mikrotik(router):

    try:

        if not router:
            return None, None

        if not router.get("host"):
            return None, None

        client = MikrotikClient(
            host=router["host"],
            username=router["username"],
            password=router["password"],
            port=router.get("port",8728),
        )

        if not client.connect():
            return None, None

        if client.api is None:
            return None, None

        return client.api, client

    except Exception as e:
        log.exception(e)
        return None, None

def cek_mikrotik_online(host):
    """
    Cek Mikrotik online dengan cara connect ke port API default (8728).
    """
    import socket
    try:
        sock = socket.create_connection((host, 8728), timeout=2)
        sock.close()
        return True
    except:
        return False

def hitung_status(due_str, disabled):

    try:

        if str(disabled).lower() in (
            "true",
            "yes",
            "1"
        ):
            return "NONAKTIF"

        if not due_str:
            return "JATUH TEMPO"

        due_str = str(due_str).strip()

        due = None

        # ====================================================
        # FORMAT RESMI: DD/MM/YYYY
        # ====================================================

        try:

            due = datetime.strptime(
                due_str,
                "%d/%m/%Y"
            ).date()

        except ValueError:

            # =================================================
            # ISO
            # =================================================

            try:

                due = datetime.strptime(
                    due_str,
                    "%Y-%m-%d"
                ).date()

            except ValueError:
                return "JATUH TEMPO"

        today = date.today()

        if today > due:
            return "JATUH TEMPO"

        return "AKTIF"

    except Exception:
        return "JATUH TEMPO"


def auto_blokir_router(router):

    api = None
    client = None

    try:

        # =====================================================
        # KONEK ROUTER SEKALI
        # =====================================================

        api, client = konek_mikrotik(router)

        if not api:

            print(
                f"❌ Router {router.get('host', '-')}"
                f" offline"
            )

            return

        # =====================================================
        # AMBIL DATA PELANGGAN
        # =====================================================

        with db_connection() as db:

            cur = db.cursor()

            cur.execute("""
                SELECT
                    p.id,
                    p.user_id,
                    p.router_id,
                    p.nama,
                    p.pppoe_username,
                    p.ip_address,
                    p.mac_address,
                    p.status,
                    p.jatuh_tempo,

                    (
                        SELECT status
                        FROM tagihan t
                        WHERE t.pelanggan_id = p.id
                        ORDER BY tahun DESC, bulan DESC
                        LIMIT 1
                    ) AS tagihan_status

                FROM pelanggan p

                WHERE p.router_id = ?

            """, (router["id"],))

            rows = [
                dict(row)
                for row in cur.fetchall()
            ]

        # =====================================================
        # COUNTER
        # =====================================================

        total_blokir = 0
        total_aktif = 0
        total_gagal = 0
        total_lewati = 0

        print(
            f"📋 DATA PELANGGAN ROUTER "
            f"{router.get('host', '-')}: {len(rows)}"
        )

        # =====================================================
        # TANGGAL HARI INI
        # =====================================================

        from datetime import datetime, date

        today = date.today()

        # =====================================================
        # PROSES PELANGGAN
        # =====================================================

        for r in rows:

            identitas = (
                r.get("pppoe_username")
                or r.get("nama")
                or r.get("ip_address")
                or "-"
            )

            try:

                # =================================================
                # STATUS TAGIHAN
                # =================================================

                status_tagihan = (
                    str(
                        r.get("tagihan_status")
                    ).strip().upper()
                    if r.get("tagihan_status")
                    else ""
                )

                # =================================================
                # TANGGAL JATUH TEMPO
                #
                # STANDAR UTAMA:
                # DD/MM/YYYY
                #
                # Kompatibilitas:
                # YYYY-MM-DD
                # =================================================

                jatuh_tempo_raw = (
                    str(r.get("jatuh_tempo")).strip()
                    if r.get("jatuh_tempo")
                    else ""
                )

                jatuh_tempo = None

                if jatuh_tempo_raw:

                    # ---------------------------------------------
                    # FORMAT UTAMA: DD/MM/YYYY
                    # ---------------------------------------------

                    try:

                        jatuh_tempo = datetime.strptime(
                            jatuh_tempo_raw,
                            "%d/%m/%Y"
                        ).date()

                    except ValueError:

                        # -----------------------------------------
                        # KOMPATIBILITAS: YYYY-MM-DD
                        # -----------------------------------------

                        try:

                            jatuh_tempo = datetime.strptime(
                                jatuh_tempo_raw,
                                "%Y-%m-%d"
                            ).date()

                        except ValueError:

                            jatuh_tempo = None

                # =================================================
                # 1. TAGIHAN LUNAS
                # =================================================
                #
                # LUNAS selalu aktif.
                # Tidak peduli tanggal jatuh tempo.
                # =================================================

                if status_tagihan in (
                    "LUNAS",
                    "PAID",
                    "SUDAH BAYAR"
                ):

                    berhasil = hapus_isolir(
                        router,
                        r,
                        api=api,
                        client=client
                    )

                    if berhasil:

                        with db_connection() as db:

                            db.execute("""
                                UPDATE pelanggan
                                SET status = 'AKTIF'
                                WHERE id = ?
                                AND user_id = ?
                            """, (
                                r["id"],
                                r["user_id"]
                            ))

                            db.commit()

                        total_aktif += 1

                        print(
                            f"🔓 AKTIF: {identitas} | "
                            f"TAGIHAN LUNAS"
                        )

                    else:

                        total_gagal += 1

                    continue

                # =================================================
                # 2. BELUM LUNAS
                # =================================================

                if status_tagihan == "BELUM LUNAS":

                    # -------------------------------------------------
                    # TIDAK ADA JATUH TEMPO
                    #
                    # Jangan mengambil keputusan isolir.
                    # -------------------------------------------------

                    if not jatuh_tempo:

                        total_lewati += 1

                        print(
                            f"⏭️ LEWATI: {identitas} | "
                            f"BELUM LUNAS | "
                            f"Jatuh tempo tidak tersedia"
                        )

                        continue

                    # -------------------------------------------------
                    # BELUM JATUH TEMPO
                    #
                    # WAJIB AKTIF.
                    #
                    # Jika sebelumnya terlanjur ISOLIR karena
                    # kesalahan tanggal, buka kembali isolir.
                    # -------------------------------------------------

                    if today < jatuh_tempo:

                        berhasil = hapus_isolir(
                            router,
                            r,
                            api=api,
                            client=client
                        )

                        if berhasil:

                            with db_connection() as db:

                                db.execute("""
                                    UPDATE pelanggan
                                    SET status = 'AKTIF'
                                    WHERE id = ?
                                    AND user_id = ?
                                """, (
                                    r["id"],
                                    r["user_id"]
                                ))

                                db.commit()

                            total_aktif += 1

                            print(
                                f"🔓 AKTIF: {identitas} | "
                                f"BELUM JATUH TEMPO | "
                                f"Jatuh tempo "
                                f"{jatuh_tempo.strftime('%d/%m/%Y')} | "
                                f"Hari ini "
                                f"{today.strftime('%d/%m/%Y')}"
                            )

                        else:

                            total_gagal += 1

                            print(
                                f"❌ Gagal membuka isolir: "
                                f"{identitas} | "
                                f"BELUM JATUH TEMPO"
                            )

                        continue

                    # -------------------------------------------------
                    # SUDAH JATUH TEMPO
                    #
                    # today == jatuh_tempo
                    # ATAU
                    # today > jatuh_tempo
                    # -------------------------------------------------

                    print(
                        f"⚠️ JATUH TEMPO: {identitas} | "
                        f"BELUM LUNAS | "
                        f"Jatuh tempo "
                        f"{jatuh_tempo.strftime('%d/%m/%Y')} | "
                        f"Hari ini "
                        f"{today.strftime('%d/%m/%Y')}"
                    )

                    berhasil = proses_isolir(
                        router,
                        r,
                        api=api,
                        client=client
                    )

                    if berhasil:

                        with db_connection() as db:

                            db.execute("""
                                UPDATE pelanggan
                                SET status = 'ISOLIR'
                                WHERE id = ?
                                AND user_id = ?
                            """, (
                                r["id"],
                                r["user_id"]
                            ))

                            db.commit()

                        total_blokir += 1

                        print(
                            f"🔒 ISOLIR: {identitas} | "
                            f"SUDAH JATUH TEMPO"
                        )

                    else:

                        total_gagal += 1

                    continue

                # =================================================
                # 3. TIDAK ADA TAGIHAN
                #
                # Fallback menggunakan jatuh tempo pelanggan.
                # =================================================

                if not status_tagihan:

                    # -------------------------------------------------
                    # Tidak ada jatuh tempo
                    # -------------------------------------------------

                    if not jatuh_tempo:

                        total_lewati += 1

                        print(
                            f"⏭️ LEWATI: {identitas} | "
                            f"Tidak ada tagihan dan "
                            f"jatuh tempo tidak tersedia"
                        )

                        continue

                    # -------------------------------------------------
                    # Belum jatuh tempo
                    # -------------------------------------------------

                    if today < jatuh_tempo:

                        berhasil = hapus_isolir(
                            router,
                            r,
                            api=api,
                            client=client
                        )

                        if berhasil:

                            with db_connection() as db:

                                db.execute("""
                                    UPDATE pelanggan
                                    SET status = 'AKTIF'
                                    WHERE id = ?
                                    AND user_id = ?
                                """, (
                                    r["id"],
                                    r["user_id"]
                                ))

                                db.commit()

                            total_aktif += 1

                            print(
                                f"🔓 AKTIF: {identitas} | "
                                f"Tidak ada tagihan | "
                                f"Belum jatuh tempo "
                                f"{jatuh_tempo.strftime('%d/%m/%Y')}"
                            )

                        else:

                            total_gagal += 1

                        continue

                    # -------------------------------------------------
                    # Sudah jatuh tempo
                    # -------------------------------------------------

                    print(
                        f"⚠️ JATUH TEMPO: {identitas} | "
                        f"Tidak ada tagihan | "
                        f"Jatuh tempo "
                        f"{jatuh_tempo.strftime('%d/%m/%Y')} | "
                        f"Hari ini "
                        f"{today.strftime('%d/%m/%Y')}"
                    )

                    berhasil = proses_isolir(
                        router,
                        r,
                        api=api,
                        client=client
                    )

                    if berhasil:

                        with db_connection() as db:

                            db.execute("""
                                UPDATE pelanggan
                                SET status = 'ISOLIR'
                                WHERE id = ?
                                AND user_id = ?
                            """, (
                                r["id"],
                                r["user_id"]
                            ))

                            db.commit()

                        total_blokir += 1

                        print(
                            f"🔒 ISOLIR: {identitas} | "
                            f"LEWAT JATUH TEMPO"
                        )

                    else:

                        total_gagal += 1

                    continue

                # =================================================
                # 4. STATUS TAGIHAN LAIN
                # =================================================

                total_lewati += 1

                print(
                    f"⏭️ LEWATI: {identitas} | "
                    f"Status tagihan: {status_tagihan}"
                )

            except Exception as e:

                total_gagal += 1

                print(
                    f"❌ Gagal proses "
                    f"{identitas}: {e}"
                )

        # =====================================================
        # HASIL
        # =====================================================

        print(
            f"[Router {router.get('host', '-')}] "
            f"Blokir:{total_blokir} "
            f"Aktif:{total_aktif} "
            f"Lewati:{total_lewati} "
            f"Gagal:{total_gagal}"
        )

    except Exception as e:

        print(
            f"❌ Auto blokir router "
            f"{router.get('host', '-')} gagal: {e}"
        )

    finally:

        if client:

            try:
                client.disconnect()

            except Exception:
                pass


def sukses(msg="Pembayaran berhasil"):
    return {
        "status": True,
        "msg": msg
    }

def gagal(msg):
    return {
        "status": False,
        "msg": msg
    }

def proses_pembayaran(pid, user_id, metode="Cash", admin="System"):

    pelanggan = ambil_pelanggan(
        pid,
        user_id
    )

    if not pelanggan:
        return gagal(
            "Pelanggan tidak ditemukan"
        )

    router = cari_router(
        user_id,
        pelanggan
    )

    if not router:
        return gagal(
            "Router tidak ditemukan"
        )

    api = None
    conn = None

    try:

        print("1. konek router")

        api, conn = konek_mikrotik(
            router
        )

        if not api:
            return gagal(
                "Router Offline"
            )

        # =====================================
        # HITUNG JATUH TEMPO BARU
        # =====================================

        print("DEBUG JATUH TEMPO DATABASE :", pelanggan.get("jatuh_tempo"))

        bulan_depan = hitung_jatuh_tempo_baru(
            pelanggan["jatuh_tempo"]
        )

        print("DEBUG BULAN DEPAN          :", bulan_depan.strftime("%d/%m/%Y"))

        print("2. update router")

        update_router(
            api,
            router,
            pelanggan,
            bulan_depan
        )

        print("3. update hapus_isolir")

        berhasil_aktif = hapus_isolir(
            router,
            pelanggan,
            api=api,
            client=conn
        )

        if not berhasil_aktif:

            return gagal(
                "Pembayaran berhasil, tetapi gagal membuka isolir pelanggan"
            )

        print("4. update database")

        tanggal_bayar = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        update_database_pembayaran(
            pelanggan,
            bulan_depan
        )

        # =====================================
        # AMBIL DATA TERBARU
        # =====================================

        pelanggan_terbaru = ambil_pelanggan(
            pid,
            user_id
        )

        if not pelanggan_terbaru:
            return gagal(
                "Data pelanggan setelah pembayaran tidak ditemukan"
            )

        print("5. simpan transaksi")

        simpan_transaksi({
            "user_id": user_id,
            "pelanggan_id": pelanggan_terbaru["id"],
            "nama": pelanggan_terbaru["nama"],
            "paket": pelanggan_terbaru["paket"],
            "harga": pelanggan_terbaru["harga"],
            "metode": metode,
            "admin": admin,
            "status": "LUNAS",
        })

        print("✅ Transaksi LUNAS berhasil disimpan")

        return sukses()

    except Exception as e:

        log.exception(
            "proses_pembayaran gagal"
        )

        return gagal(
            str(e)
        )

    finally:

        if conn:

            try:
                conn.disconnect()

            except Exception:
                pass

def ambil_pelanggan(pid, user_id):

    with db_connection() as db:

        cur = db.cursor()

        cur.execute("""
            SELECT *
            FROM pelanggan
            WHERE id=?
            AND user_id=?
        """, (
            pid,
            user_id
        ))

        row = cur.fetchone()

    return dict(row) if row else None

def hitung_jatuh_tempo_baru(jatuh_tempo):

    if not jatuh_tempo:
        tanggal = datetime.now()

    else:
        try:
            tanggal = datetime.strptime(
                str(jatuh_tempo).strip(),
                "%d/%m/%Y"
            )

        except ValueError:

            try:
                tanggal = datetime.strptime(
                    str(jatuh_tempo).strip(),
                    "%Y-%m-%d"
                )

            except ValueError:
                tanggal = datetime.now()

    return tanggal + relativedelta(months=1)

def update_router(api, router, pelanggan, bulan_depan):

    comment = buat_comment_router(
        pelanggan,
        bulan_depan
    )

    try:
        update_dhcp(api, pelanggan, comment)
    except Exception as e:
        log.exception("Update DHCP gagal")

    try:
        update_pppoe(api, router, pelanggan, comment)
    except Exception as e:
        log.exception("Update PPPoE gagal")

def cari_router(user_id, pelanggan):

    routers = load_mikrotik_list(user_id)

    return next(
        (
            r for r in routers
            if str(r["id"]) == str(pelanggan["router_id"])
        ),
        None
    )

def cari_dhcp_lease(api, pelanggan):

    lease = api.get_resource(
        "/ip/dhcp-server/lease"
    )

    host = (
        pelanggan.get("host")
        or pelanggan.get("host_name")
    )

    mac = (
        pelanggan.get("mac_address")
        or pelanggan.get("mac")
    )

    ip = pelanggan.get("ip_address")

    rows = []

    # Cari berdasarkan MAC
    if mac:

        rows = lease.get(
            **{"mac-address": mac}
        )

    # Kalau tidak ditemukan, cari hostname
    if not rows and host:

        rows = lease.get(
            **{"host-name": host}
        )

    # Kalau masih tidak ditemukan, cari IP
    if not rows and ip:

        rows = lease.get(
            address=ip
        )

    # Tidak ditemukan
    if not rows:
        return None

    return (
        rows[0].get(".id")
        or rows[0].get("id")
    )

def set_dhcp_comment(api, lease_id, comment):

    lease = api.get_resource("/ip/dhcp-server/lease")

    lease.set(
        id=lease_id,
        comment=comment
    )

def enable_dhcp(api, lease_id):

    lease = api.get_resource("/ip/dhcp-server/lease")

    lease.set(
        id=lease_id,
        disabled="no"
    )

def buat_comment_router(pelanggan, bulan_depan):

    return (
        f"nama:{pelanggan.get('nama','')};"
        f"paket:{pelanggan.get('paket','')};"
        f"harga:{pelanggan.get('harga',0)};"
        f"due:{bulan_depan.strftime('%d/%m/%Y')};"
        f"no_hp:{pelanggan.get('no_hp','')};"
        f"iface:{pelanggan.get('iface','')};"
        f"usage:{pelanggan.get('usage','0GB')}"
    )

def update_dhcp(api, pelanggan, comment):

    try:

        lease_id = cari_dhcp_lease(
            api,
            pelanggan
        )

        if not lease_id:
            return

        set_dhcp_comment(
            api,
            lease_id,
            comment
        )

        enable_dhcp(
            api,
            lease_id
        )

    except Exception as e:
        log.error(f"DHCP gagal : {e}")

def update_pppoe(api, router, pelanggan, comment):

    try:

        sid = cari_secret_pppoe(
            api,
            pelanggan
        )

        if not sid:
            return

        set_pppoe_comment(
            api,
            sid,
            comment
        )

        enable_pppoe(
            api,
            sid
        )

        aktifkan_pppoe(
            router,
            pelanggan
        )
    except Exception as e:
        log.exception(e)

def update_pppoe_secret(api, data):

    username = (data.get("pppoe_username") or "").strip()

    if not username:
        raise ValueError("Username PPPoE kosong")

    password = data.get("pppoe_password") or ""
    profile = data.get("paket") or "default"
    nama = data.get("nama") or ""
    harga = data.get("harga") or 0
    due = data.get("jatuh_tempo") or ""
    no_hp = data.get("no_hp") or ""

    comment = (
        f"nama={nama},"
        f"paket={profile},"
        f"harga={harga},"
        f"due={due},"
        f"no_hp={no_hp}"
    )

    secrets = api.get_resource("/ppp/secret")

    existing = secrets.get(
        name=username
    )

    # =================================
    # JIKA SUDAH ADA → UPDATE
    # =================================

    if existing:

        user = existing[0]

        secret_id = (
            user.get(".id")
            or user.get("id")
        )

        if not secret_id:
            raise Exception(
                f"ID PPPoE tidak ditemukan: {user}"
            )

        secrets.set(
            id=secret_id,
            password=password,
            profile=profile,
            service="pppoe",
            comment=comment
        )

        print(
            f"🔄 PPPoE berhasil diupdate: {username}"
        )

        return {
            "success": True,
            "action": "update",
            "username": username
        }

    # =================================
    # JIKA BELUM ADA → BUAT BARU
    # =================================

    secrets.add(
        name=username,
        password=password,
        profile=profile,
        service="pppoe",
        comment=comment,
        disabled="no"
    )

    print(
        f"➕ PPPoE berhasil dibuat: {username}"
    )

    return {
        "success": True,
        "action": "create",
        "username": username
    }

def sync_pelanggan_pppoe(router, data):

    try:

        api, client = konek_mikrotik(router)

        if not api:

            print("❌ Tidak dapat terhubung ke MikroTik")

            return {
                "success": False,
                "message": "Router tidak dapat dihubungi"
            }

        result = update_pppoe_secret(api, data)

        return result

    except Exception as e:

        print("❌ GAGAL SYNC PPPoE:", str(e))

        return {
            "success": False,
            "message": str(e)
        }

    finally:

        try:

            if client:
                client.close()

        except Exception:
            pass

def cari_secret_pppoe(api, pelanggan):

    username = pelanggan.get("pppoe_username")

    if not username:
        return None

    secret = api.get_resource("/ppp/secret")

    rows = secret.get(name=username)

    if not rows:
        return None

    return rows[0].get(".id") or rows[0].get("id")

def set_pppoe_comment(
        api,
        secret_id,
        comment
):

    secret = api.get_resource("/ppp/secret")

    secret.set(
        id=secret_id,
        comment=comment
    )

def enable_pppoe(
        api,
        secret_id
):

    secret = api.get_resource("/ppp/secret")

    secret.set(
        id=secret_id,
        disabled="no"
    )

def aktifkan_pppoe(
        router,
        pelanggan
):

    username = pelanggan.get("pppoe_username")

    if username:

        set_pppoe_status(
            router,
            username,
            aktif=True
        )

def update_database_pembayaran(
        pelanggan,
        bulan_depan
):


    print(">>> UPDATE DATABASE")
    print("ID :", pelanggan["id"])
    print("USER :", pelanggan["user_id"])

    tanggal_bayar = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    jatuh_tempo_baru = bulan_depan.strftime("%d/%m/%Y")

    with db_connection() as db:

        cur = db.cursor()

        cur.execute("""
        UPDATE pelanggan
        SET
            status=?,
            jatuh_tempo=?,
            tanggal_bayar=?,
            updated_at=?
        WHERE id=?
        AND user_id=?
        """, (
            "LUNAS",
            jatuh_tempo_baru,
            tanggal_bayar,
            datetime.now().isoformat(),
            pelanggan["id"],
            pelanggan["user_id"]
        ))

        print("ROWCOUNT PELANGGAN =", cur.rowcount)

        cur.execute("""
            UPDATE tagihan
            SET
                status='LUNAS',
                tanggal_bayar=?
            WHERE pelanggan_id=?
            AND status='BELUM LUNAS'
        """, (
            tanggal_bayar,
            pelanggan["id"],
        ))

        print("ROWCOUNT TAGIHAN =", cur.rowcount)

        db.commit()

        refresh_pelanggan_cache(
            pelanggan["user_id"]
        )

    print("📅 Tanggal Bayar :", tanggal_bayar)
    print("📅 Jatuh Tempo   :", jatuh_tempo_baru)

def tarik_semua_pelanggan(api, router_id):
    if not api:
        print("API TIDAK TERKONEK!")
        return []

    hasil = []

    try:
        # ==========================
        # DHCP LEASE
        # ==========================
        leases = api.get_resource("/ip/dhcp-server/lease").get()

        for l in leases:

            if str(l.get("dynamic", "")).lower() in ["true", "yes", "1"]:
                continue

            comment = (l.get("comment") or "").strip()

            if not comment:
                continue

            parsed = parse_comment(comment)

            if not parsed.get("nama"):
                continue

            hasil.append({
                "tipe": "DHCP",
                "router_id": router_id,
                "pppoe_username": "",
                "nama": parsed.get("nama"),
                "paket": parsed.get("paket"),
                "harga": int(parsed.get("harga", 0)),
                "due": parsed.get("due"),
                "no_hp": parsed.get("no_hp", ""),
                "iface": parsed.get("iface", ""),
                "usage": parsed.get("usage") or "0GB",
                "ip": l.get("address"),
                "mac": l.get("mac-address"),
                "host": l.get("host-name", ""),
                "status": hitung_status(
                    parsed.get("due"),
                    l.get("disabled")
                ),
            })

        # ==========================
        # PPPoE SECRET
        # ==========================

        secrets = api.get_resource(
            "/ppp/secret"
        ).get()

        for s in secrets:

            comment = (
                s.get("comment") or ""
            ).strip()

            parsed = parse_comment(
                comment
            )

            username = (
                s.get("name")
                or ""
            ).strip()

            # Jangan masukkan secret kosong
            if not username:
                continue

            hasil.append({
                "tipe": "PPPOE",

                "router_id": router_id,

                "pppoe_username": username,

                "nama": parsed.get(
                    "nama"
                ) or username,

                "paket": parsed.get(
                    "paket"
                ) or s.get(
                    "profile",
                    ""
                ),

                "harga": int(
                    parsed.get(
                        "harga",
                        0
                    ) or 0
                ),

                "due": parsed.get(
                    "due"
                ),

                "no_hp": parsed.get(
                    "no_hp",
                    ""
                ),

                "iface": parsed.get(
                    "iface",
                    ""
                ),

                "usage": parsed.get(
                    "usage"
                ) or "0GB",

                "ip": "",

                "mac": "",

                "host": "",

                "status": hitung_status(
                    parsed.get("due"),
                    s.get("disabled")
                ),
            })

        print("TOTAL PELANGGAN =", len(hasil))

        return hasil

    except Exception as e:
        print("Gagal tarik pelanggan:", e)
        return []

def sinkron_binding_dhcp_user(user_id):
    """
    Binding DHCP hanya untuk pelanggan yang SUDAH TERDAFTAR
    di database.

    Unknown DHCP device tidak akan otomatis dibuat sebagai pelanggan.
    """

    total_static = 0

    try:
        pelanggan_list = get_pelanggan_list(
            user_id,
            use_cache=False
        )

        if not pelanggan_list:
            print(
                "   Tidak ada pelanggan untuk DHCP binding."
            )
            return 0

        routers = load_mikrotik_list(user_id)

        for router in routers:

            router_id = router.get("id")

            print(
                f"\n🔐 DHCP STATIC BINDING "
                f"ROUTER: {router.get('host')}"
            )

            pelanggan_router = [
                p for p in pelanggan_list
                if str(p.get("router_id")) == str(router_id)
                and str(
                    p.get("tipe") or ""
                ).upper() == "DHCP"
            ]

            if not pelanggan_router:
                continue

            api = None
            client = None

            try:
                api, client = konek_mikrotik(router)

                for pelanggan in pelanggan_router:

                    mac = (
                        pelanggan.get("mac_address")
                        or pelanggan.get("mac")
                        or ""
                    ).strip()

                    if not mac:
                        print(
                            f"⏭️ {pelanggan.get('nama')} "
                            "tidak memiliki MAC."
                        )
                        continue

                    nama = pelanggan.get("nama") or "-"

                    print(
                        f"🔎 Binding DHCP: "
                        f"{nama} | MAC={mac}"
                    )

                    hasil = binding_dhcp_pelanggan(
                        api,
                        pelanggan
                    )

                    if not hasil.get("success"):
                        print(
                            f"⚠️ Binding gagal "
                            f"{nama}: "
                            f"{hasil.get('message')}"
                        )
                        continue

                    ip = hasil.get("ip_address")
                    mac_final = hasil.get("mac_address")

                    if not ip:
                        print(
                            f"⚠️ {nama}: "
                            "binding berhasil tetapi IP kosong."
                        )
                        continue

                    # ==========================================
                    # SIMPAN IP + MAC KE DATABASE
                    # ==========================================

                    pelanggan_update = dict(pelanggan)

                    pelanggan_update["ip_address"] = ip
                    pelanggan_update["mac_address"] = (
                        mac_final or mac
                    )

                    update_pelanggan(
                        user_id,
                        pelanggan.get("id"),
                        pelanggan_update
                    )

                    total_static += 1

                    print(
                        f"✅ STATIC TERSIMPAN | "
                        f"{nama} | "
                        f"IP={ip} | "
                        f"MAC={pelanggan_update['mac_address']}"
                    )

            except Exception as e:
                print(
                    f"❌ Gagal DHCP binding router "
                    f"{router.get('host')}: {e}"
                )

            finally:
                try:
                    if client:
                        client.disconnect()
                except Exception:
                    pass

        return total_static

    except Exception as e:
        print(
            f"❌ Gagal mengambil pelanggan "
            f"user {user_id}: {e}"
        )
        return 0