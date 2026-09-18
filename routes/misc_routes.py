import os
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory,
    current_app
)
from werkzeug.security import generate_password_hash
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

from core.db import db_connection
from core.core_pelanggan import (
    get_pelanggan_by_id,
    get_pelanggan_list,
    tambah_pelanggan,
    update_pelanggan,
    hapus_pelanggan,
)
from core.transaksi_core import (
    get_transaksi_terakhir,
)
from core.logic import (
    boleh_masuk,
    get_all_users,
    load_mikrotik_list,
)
from core.license_core import (
    get_device_id,
    validasi_kode_aktivasi,
    simpan_license,
    paket_dari_kode,
    get_license_info,
    license_valid_local,
)
from core.config_core import (
    get_app_config,
    save_app_config,
)
from core.mikrotik_api import get_router_by_id
from core.mikrotik_core import (
    auto_blokir_router,
    proses_pembayaran,
    konek_mikrotik,
    tarik_semua_pelanggan,
)
from core.decorators import (
    admin_required,
    app_required,
    premium_required,
)

from core.error_helper import log_error
from services.mikrotik_service import (
    set_pppoe_status,
    is_router_online,
    tarik_dhcp,
    tarik_wireless,
    update_comment_mikrotik,
)

from services.mikrotik_sync_service import (
    is_router_online as is_router_online_sync,
)

from services.wa_service import (
    kirim_wa,
    pesan_reminder,
    simpan_log_wa,
)

bp = Blueprint("misc", __name__)

@bp.route("/")
def root():
    return redirect(url_for("misc.dashboard"))

@bp.route("/lupa-password", methods=["GET", "POST"])
def lupa_password():

    if request.method == "POST":

        username = request.form.get("username")
        kode = request.form.get("kode")
        password_baru = request.form.get("password_baru")

        # kode reset default
        RESET_CODE = "MIKROTIK2026"

        if kode != RESET_CODE:
            flash("❌ Kode reset salah")
            return redirect("/lupa-password")


        with db_connection() as conn:

            cur = conn.cursor()

            cur.execute("""
                SELECT id 
                FROM users
                WHERE username=? 
                AND is_admin=1
            """, (username,))

            user = cur.fetchone()


            if not user:
                flash("❌ Admin tidak ditemukan")
                return redirect("/lupa-password")


            password_hash = generate_password_hash(
                password_baru
            )


            cur.execute("""
                UPDATE users
                SET password=?
                WHERE id=?
            """, (
                password_hash,
                user["id"]
            ))

            conn.commit()


        flash("✅ Password berhasil diganti")
        return redirect("/login")


    return render_template(
        "lupa_password.html"
    )


@bp.route("/dashboard")
@admin_required
@app_required
def dashboard():

    user_id = session["user_id"]

    try:

        # =====================================================
        # AMBIL DATA PELANGGAN
        # =====================================================

        pelanggan = [
            dict(p)
            for p in get_pelanggan_list(user_id)
        ]

        total_pelanggan = len(pelanggan)


        # =====================================================
        # STATISTIK STATUS PELANGGAN
        # =====================================================

        pelanggan_aktif = 0
        pelanggan_isolir = 0
        pelanggan_jatuh_tempo = 0

        pelanggan_jatuh_tempo_list = []


        for p in pelanggan:

            status = str(
                p.get("status") or ""
            ).strip().upper()

            due = str(
                p.get("jatuh_tempo")
                or p.get("due")
                or ""
            ).strip()


            # -------------------------------
            # AKTIF
            # -------------------------------

            if status == "AKTIF":

                pelanggan_aktif += 1


            # -------------------------------
            # ISOLIR
            # -------------------------------

            elif status == "ISOLIR":

                pelanggan_isolir += 1


            # -------------------------------
            # JATUH TEMPO
            # -------------------------------

            elif status in (
                "JATUH TEMPO",
                "TERLAMBAT",
                "BELUM BAYAR"
            ):

                pelanggan_jatuh_tempo += 1

                pelanggan_jatuh_tempo_list.append(p)


        # =====================================================
        # TAGIHAN
        # =====================================================

        total_tagihan = 0
        total_sudah_bayar = 0
        total_belum_bayar = 0
        belum_bayar = 0


        with db_connection() as conn:

            cur = conn.cursor()

            # Ambil tagihan bulan berjalan
            bulan_ini = datetime.now().strftime("%m")
            tahun_ini = datetime.now().year

            cur.execute("""
                SELECT
                    pelanggan_id,
                    jumlah,
                    status
                FROM tagihan
                WHERE user_id=?
                  AND bulan=?
                  AND tahun=?
            """, (
                user_id,
                bulan_ini,
                tahun_ini
            ))

            tagihan_rows = cur.fetchall()


            # Buat index berdasarkan pelanggan
            tagihan_map = {}

            for row in tagihan_rows:

                tagihan_map[
                    str(row["pelanggan_id"])
                ] = row


        # Hitung statistik berdasarkan tagihan
        for p in pelanggan:

            harga = int(
                p.get("harga") or 0
            )

            pelanggan_id = str(
                p.get("id") or ""
            )

            tagihan = tagihan_map.get(
                pelanggan_id
            )


            # Jika belum ada record tagihan,
            # gunakan harga pelanggan sebagai tagihan
            if not tagihan:

                total_tagihan += harga

                total_belum_bayar += harga

                belum_bayar += 1

                continue


            jumlah = int(
                tagihan["jumlah"] or harga or 0
            )

            status_tagihan = str(
                tagihan["status"] or ""
            ).strip().upper()


            total_tagihan += jumlah


            if status_tagihan == "LUNAS":

                total_sudah_bayar += jumlah

            else:

                total_belum_bayar += jumlah

                belum_bayar += 1


        # =====================================================
        # JENIS KONEKSI
        # =====================================================

        total_dhcp = 0
        total_pppoe = 0


        for p in pelanggan:

            tipe = str(
                p.get("tipe") or ""
            ).strip().upper()


            if tipe == "DHCP":

                total_dhcp += 1


            elif tipe == "PPPOE":

                total_pppoe += 1


        # =====================================================
        # TRANSAKSI TERAKHIR
        # =====================================================

        transaksi = [
            dict(t)
            for t in get_transaksi_terakhir(user_id)
        ]

        # =====================================================
        # STATUS ROUTER
        # =====================================================

        routers_status = []

        try:
            routers = load_mikrotik_list(user_id)
        except Exception as e:
            log_error(
                "dashboard_load_router",
                e
            )
            routers = []

        for router in routers:

            host = router.get("host") or "-"

            online = False

            try:
                # PENTING:
                # Gunakan fungsi dari mikrotik_sync_service
                # karena fungsi ini menerima data router (dict).
                online = is_router_online_sync(router)

            except Exception as e:
                log_error(
                    "dashboard_router_status",
                    e
                )

            routers_status.append({
                "id": router.get("id"),

                "label": (
                    router.get("name")
                    or router.get("label")
                    or host
                ),

                "host": host,

                "status": (
                    "ONLINE"
                    if online
                    else "OFFLINE"
                ),

                "online": online
            })

        # =====================================================
        # STATUS WHATSAPP
        # =====================================================

        wa_status = False

        try:

            app_cfg = get_app_config(user_id)

            if app_cfg:

                wa_status = bool(
                    app_cfg.get("wa_enabled")
                    or app_cfg.get("whatsapp_enabled")
                    or app_cfg.get("whatsapp")
                )

        except Exception as e:

            log_error(
                "dashboard_wa_status",
                e
            )


        # =====================================================
        # LISENSI
        # =====================================================

        license_info = get_license_info()

        ok, mode, sisa = boleh_masuk(
            user_id
        )


        # =====================================================
        # RENDER DASHBOARD
        # =====================================================

        return render_template(

            "dashboard.html",

            # -----------------------------------------------
            # DATA PELANGGAN
            # -----------------------------------------------

            pelanggan=pelanggan,

            total_pelanggan=total_pelanggan,

            pelanggan_aktif=pelanggan_aktif,

            pelanggan_isolir=pelanggan_isolir,

            pelanggan_jatuh_tempo=
                pelanggan_jatuh_tempo,

            pelanggan_jatuh_tempo_list=
                pelanggan_jatuh_tempo_list,


            # -----------------------------------------------
            # KEUANGAN
            # -----------------------------------------------

            total_tagihan=total_tagihan,

            total_sudah_bayar=
                total_sudah_bayar,

            total_belum_bayar=
                total_belum_bayar,

            belum_bayar=belum_bayar,


            # -----------------------------------------------
            # KONEKSI
            # -----------------------------------------------

            total_dhcp=total_dhcp,

            total_pppoe=total_pppoe,


            # -----------------------------------------------
            # TRANSAKSI
            # -----------------------------------------------

            transaksi=transaksi,


            # -----------------------------------------------
            # ROUTER
            # -----------------------------------------------

            routers_status=routers_status,


            # -----------------------------------------------
            # WHATSAPP
            # -----------------------------------------------

            wa_status=wa_status,


            # -----------------------------------------------
            # LISENSI44
            # -----------------------------------------------

            license_info=license_info,

            mode=mode,

            sisa_hari=sisa,

            device_id=get_device_id(),

        )


    except Exception as e:

        error_id = log_error(
            "dashboard",
            e
        )

        flash(
            f"Gagal memuat dashboard ({error_id})",
            "danger"
        )

        return redirect(
            url_for("misc.dashboard")
        )


@bp.route("/favicon.ico")
def favicon():
    return send_from_directory(STATIC_DIR, "favicon.ico")

@bp.route("/admin")
@admin_required
@app_required
def admin():
    user_id = session["user_id"]

    try:
        routers = load_mikrotik_list(user_id)

        data = []

        for router in routers:
            api = None
            conn = None

            try:
                api, conn = konek_mikrotik(router)

                if api:
                    data.extend(
                        tarik_semua_pelanggan(
                            api,
                            router["id"]
                        )
                    )

            except Exception as e:
                log_error("admin_router", e)

            finally:
                if conn:
                    try:
                        conn.disconnect()
                    except Exception:
                        pass

        total_pelanggan = len(data)

        total_tagihan = sum(
            int(p.get("harga") or 0)
            for p in data
            if str(p.get("status", "")).lower() != "lunas"
        )

        pelanggan_belum_bayar = sum(
            1
            for p in data
            if str(p.get("status", "")).lower() != "lunas"
        )

        transaksi_terakhir = get_transaksi_terakhir(user_id)

        _, mode, sisa = boleh_masuk(user_id)

        return render_template(
            "admin.html",
            data=data,
            total_pelanggan=total_pelanggan,
            total_tagihan=total_tagihan,
            pelanggan_belum_bayar=pelanggan_belum_bayar,
            transaksi_terakhir=transaksi_terakhir,
            routers=routers,
            mode=mode,
            sisa=sisa,
            device_id=get_device_id(),
        )

    except Exception as e:
        error_id = log_error("admin", e)
        flash(
            f"Gagal membuka halaman admin ({error_id})",
            "danger"
        )
        return redirect(url_for("misc.dashboard"))

@bp.route("/blokir")
@admin_required
@premium_required
def blokir():
    user_id = session.get("user_id")

    try:
        routers = load_mikrotik_list(user_id)

        for router in routers:
            auto_blokir_router(router)

        flash("Auto blokir selesai", "success")

    except Exception as e:
        error_id = log_error("blokir", e)
        flash(
            f"Gagal menjalankan auto blokir ({error_id})",
            "danger"
        )

    return redirect(url_for("misc.dashboard"))

@bp.route('/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

@bp.route("/tarik-pppoe")
@admin_required
@app_required
def tarik_pppoe_route():

    user_id = session["user_id"]

    routers = load_mikrotik_list(user_id)

    total = 0

    for router in routers:

        conn = None

        try:

            api, conn = konek_mikrotik(router)

            data = []

            if api:
                data = tarik_semua_pelanggan(
                    api,
                    router["id"]
                )

            total += len(data)

        except Exception as e:

            log_error("tarik_pppoe_route", e)

        finally:

            if conn:

                try:
                    conn.disconnect()
                except Exception:
                    pass

    flash(f"PPPoE berhasil ditarik ({total} user)", "success")

    return redirect(url_for("misc.admin"))

@bp.route("/tarik-wireless")
@admin_required
def tarik_wireless_route():
    user_id = session["user_id"]

    routers = load_mikrotik_list(user_id)

    total = 0

    for router in routers:

        conn = None

        try:
            api, conn = konek_mikrotik(router)

            data = []

            if api:
                data = tarik_wireless(
                    api,
                    router["id"]
                )

            total += len(data)

        except Exception as e:
            log_error("tarik_wireless_route", e)

        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

    flash(
        f"Wireless berhasil ditarik ({total} user)",
        "success"
    )

    return redirect(url_for("misc.admin"))

@bp.route("/toggle_pppoe", methods=["POST"])
@admin_required
def toggle_pppoe():
    p_id = request.form.get("pelanggan_id")
    action = request.form.get("action")  # "on" atau "off"

    pelanggan_list = get_pelanggan_list(session["user_id"])
    p = next((x for x in pelanggan_list if x["id"] == p_id), None)

    if not p:
        flash("❌ Pelanggan tidak ditemukan")
        return redirect("/admin")

    if not p.get("pppoe_username"):
        flash(f"❌ PPPoE user untuk {p['nama']} belum dibuat")
        return redirect("/admin")

    try:

        router = get_router_by_id(
            session["user_id"],
            p.get("router_id")
        )
        if not router:
            flash(f"❌ Router untuk {p['nama']} tidak ditemukan")
            return redirect("/admin")

        set_pppoe_status(router, p["pppoe_username"], aktif=(action=="on"))
        flash(f"✅ PPPoE {p['nama']} {'hidup' if action=='on' else 'mati'}")
    except Exception as e:
        log_error("toggle_pppoe", e)
        flash(f"❌ Gagal mengubah PPPoE {p['nama']}")

    return redirect("/admin")

@bp.route("/ajax/toggle_pppoe", methods=["POST"])
@admin_required
def ajax_toggle_pppoe():
    try:
        p_id = request.form.get("pelanggan_id")
        action = request.form.get("action")
        if not p_id or action not in ("on","off"):
            return jsonify({"status":"error","msg":"Data tidak valid"})
        pelanggan_list = [
            dict(p) for p in get_pelanggan_list(session["user_id"])
        ]
        p = next((x for x in pelanggan_list if x["id"] == p_id), None)
        if not p or not p.get("pppoe_username"):
            return jsonify({"status":"error","msg":"PPPoE user tidak ditemukan"})

        router = get_router_by_id(
            session["user_id"],
            p.get("router_id")
        )

        if not router:
            return jsonify({
                "status": "error",
                "msg": "Router tidak ditemukan"
            })
        set_pppoe_status(
            router,
            p["pppoe_username"],
            aktif=(action=="on")
        )
        return jsonify({"status":"ok"})
    except Exception as e:
        error_id = log_error("ajax_toggle_pppoe", e)
        return jsonify({"status":"error","msg":f"Terjadi error ({error_id})"})

@bp.route("/lunas/<pid>")
@app_required
def lunas(pid):

    user_id = session.get("user_id")

    result = proses_pembayaran(
        pid=pid,
        user_id=user_id,
        metode="Manual",
        admin=user_id
    )

    if result["status"]:
        flash("Pembayaran berhasil", "success")
    else:
        flash(result["msg"], "danger")

    return redirect(
        url_for("pelanggan.pelanggan_page")
    )

@bp.route("/reset-bulanan")
@admin_required
@premium_required
def reset_manual():

    user_id = session.get("user_id")

    routers = load_mikrotik_list(user_id)

    pelanggan_list = get_pelanggan_list(user_id=user_id)

    restored = 0

    for router in routers:

        if not is_router_online(router):
            continue

        conn = None

        try:
            api, conn = konek_mikrotik(router)

            leases = tarik_dhcp(api)

            for p in leases:

                match = next(
                    (
                        x for x in pelanggan_list
                        if x.get("ip") == p.get("ip")
                    ),
                    None
                )

                if not match:
                    continue

                try:

                    if p["tipe"] == "PPPOE" and p.get("username"):

                        set_pppoe_status(
                            router,
                            p["username"],
                            aktif=True
                        )

                    elif p["tipe"] == "DHCP":

                        dhcp_res = api.get_resource(
                            "/ip/dhcp-server/lease"
                        )

                        items = dhcp_res.get(
                            address=p["ip"]
                        )

                        if items:
                            dhcp_res.set(
                                id=items[0][".id"],
                                disabled="no"
                            )

                    restored += 1

                except Exception as e:
                    error_id = log_error(
                        "reset_manual_item",
                        e
                    )
                    print(
                        f"Restore gagal ({error_id})"
                    )

        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

    if restored:
        flash(
            f"✅ {restored} pelanggan berhasil di-restore"
        )
    else:
        flash(
            "❌ Tidak ada pelanggan yang berhasil di-restore"
        )

    return redirect(url_for("misc.admin"))

@bp.route("/auto-blokir")
@admin_required
@premium_required
def auto_blokir():
    user_id = session.get("user_id")

    routers = load_mikrotik_list(user_id)

    for router in routers:
        auto_blokir_router(router)

    flash("✅ Auto blokir dijalankan")
    return redirect("/admin")

@bp.route("/wa-reminder/<hari>")
@admin_required
@premium_required
def wa_reminder(hari):

    user_id = session.get("user_id")

    if not user_id:
        return "User tidak ditemukan", 401

    try:
        hari = int(hari)
    except (ValueError, TypeError):
        return "Parameter hari tidak valid", 400

    app_cfg = get_app_config(user_id)

    # Ambil semua pelanggan
    semua_pelanggan = get_pelanggan_list(
        user_id=user_id
    )

    # ==========================================================
    # TENTUKAN TANGGAL REMINDER
    # ==========================================================

    today = datetime.now().date()

    # hari = -3  -> 3 hari lagi
    # hari = -1  -> besok
    # hari =  0  -> hari ini
    target_date = today - timedelta(days=hari)

    pelanggan = []

    for p in semua_pelanggan:

        # Harus memiliki nomor HP
        if not p.get("no_hp"):
            continue

        # Ambil jatuh tempo
        jatuh_tempo_str = str(
            p.get("jatuh_tempo") or ""
        ).strip()

        if not jatuh_tempo_str:
            continue

        try:
            jatuh_tempo = datetime.strptime(
                jatuh_tempo_str,
                "%d/%m/%Y"
            ).date()

        except (ValueError, TypeError):
            continue

        # Cocokkan tanggal
        if jatuh_tempo != target_date:
            continue

        pelanggan.append(p)

    print(
        f"WA REMINDER HARI {hari} | "
        f"TARGET {target_date.strftime('%d/%m/%Y')} | "
        f"PELANGGAN {len(pelanggan)}"
    )

    # ==========================================================
    # KIRIM WA
    # ==========================================================

    links = []

    for p in pelanggan:

        try:

            pesan = pesan_reminder(
                p,
                app_cfg,
                hari
            )

            link = kirim_wa(
                p["no_hp"],
                pesan
            )

            simpan_log_wa(
                p,
                hari
            )

            router = get_router_by_id(
                user_id,
                p.get("router_id")
            )

            if router and p.get("pppoe_username"):

                update_comment_mikrotik(
                    router,
                    p["pppoe_username"],
                    f"REMINDER {hari}"
                )

            links.append({
                "nama": p.get("nama"),
                "paket": p.get("paket"),
                "no_hp": p.get("no_hp"),
                "url": link
            })

        except Exception as e:

            error_id = log_error(
                "wa_reminder",
                e
            )

            print(
                f"⚠️ Gagal kirim WA "
                f"{p.get('nama')} "
                f"({error_id})"
            )

    return render_template(
        "wa_list.html",
        links=links,
        hari=hari
    )

@bp.route("/api/dhcp/live")
@admin_required
def api_dhcp_live():
    user_id = session["user_id"]

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ip_address, mac_address, host_name,
                   status, last_seen, nama, router_id
            FROM dhcp_clients
            WHERE user_id=?
            ORDER BY last_seen DESC
            LIMIT 200
        """, (user_id,))

        data = [dict(r) for r in cur.fetchall()]

    return jsonify(data)


