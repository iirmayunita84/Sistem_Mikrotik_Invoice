
import threading

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)

from datetime import datetime
from core.decorators import (
    admin_required,
    app_required,
    premium_required,
)
from core.config_core import (
    get_app_config,

)
from core.db import get_db, release_db
from services.wa_service import kirim_wa, pesan_lunas
from core.error_helper import log_error

from core.logic import (
     load_mikrotik_list, 
     sync_pelanggan_status,
     simpan_pelanggan,
)
from core.mikrotik_api import (
    update_comment_dhcp,
    update_comment_pppoe,
    update_pppoe_user,
    get_router_by_id,
)
from core.comment_parser import build_comment_from_dict
from core.mikrotik_core import (
    proses_pembayaran,
    konek_mikrotik,
)
from core.core_pelanggan import (
    get_pelanggan_by_ip,
    get_pelanggan_by_id,
    get_pelanggan_list,
    tambah_pelanggan,
    hapus_pelanggan,
    update_pelanggan,

)

bp = Blueprint("pelanggan", __name__)

# ============================================================
# HELPER FORMAT JATUH TEMPO
# FORMAT RESMI APLIKASI: DD/MM/YYYY
# ============================================================

def normalisasi_jatuh_tempo(value):
    """
    Normalisasi tanggal ke format resmi aplikasi:

        DD/MM/YYYY

    Menerima:
        DD/MM/YYYY
        YYYY-MM-DD

    Tidak menebak MM/DD/YYYY karena format tersebut
    dapat menyebabkan tanggal tertukar.
    """

    if not value:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    # ========================================================
    # FORMAT RESMI: DD/MM/YYYY
    # ========================================================

    try:
        dt = datetime.strptime(
            value,
            "%d/%m/%Y"
        )

        return dt.strftime("%d/%m/%Y")

    except ValueError:
        pass

    # ========================================================
    # FORMAT HTML DATE: YYYY-MM-DD
    # ========================================================

    try:
        dt = datetime.strptime(
            value,
            "%Y-%m-%d"
        )

        return dt.strftime("%d/%m/%Y")

    except ValueError:
        pass

    # Tidak menebak format lain
    return ""

def tanggal_valid(value):
    if not value:
        return False

    value = str(value).strip()

    try:
        datetime.strptime(
            value,
            "%d/%m/%Y"
        )
        return True

    except ValueError:
        return False

@bp.route("/tagihan/<pid>")
@admin_required
@app_required
def tagihan(pid):

    if "," in pid:
        pid = pid.split(",")[0].strip()

    user_id = session["user_id"]
    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )
    if not pelanggan:
        return render_template("tagihan.html", tidak_dikenal=True)

    nama = pelanggan.get("nama", "-")
    paket = pelanggan.get("paket", "-")
    harga = int(pelanggan.get("harga", 0))
    due = pelanggan.get("jatuh_tempo","-")
    no_hp = pelanggan.get("no_hp", "")

    telat = False


    if due and due != "-":

        # ========================================================
        # FORMAT RESMI: DD/MM/YYYY
        # ========================================================

        try:

            jt = datetime.strptime(
                due,
                "%d/%m/%Y"
            ).date()

            if datetime.now().date() > jt:
                telat = True

        except ValueError:

            # Format ISO hanya sebagai kompatibilitas
            try:

                jt = datetime.strptime(
                    due,
                    "%Y-%m-%d"
                ).date()

                if datetime.now().date() > jt:
                    telat = True

            except ValueError:
                telat = False
  

    user_id = pelanggan["user_id"]

    app_cfg = get_app_config(user_id)

    return render_template(
        "tagihan.html",
        app=app_cfg,
        tidak_dikenal=False,
        nama=nama,
        paket=paket,
        harga=harga,
        due=due,
        telat=telat,
        no_hp=no_hp
    )

@bp.route("/bayar/<pid>", methods=["GET", "POST"])
@app_required
def bayar(pid):

    user_id = session.get("user_id")

    if not user_id:
        flash(
            "❌ Sesi login tidak ditemukan",
            "danger"
        )

        return redirect(
            url_for("auth.login")
        )

    if "," in pid:
        pid = pid.split(",")[0].strip()

    # =====================================================
    # AMBIL DATA PELANGGAN
    # =====================================================

    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )

    if not pelanggan:

        flash(
            "❌ Pelanggan tidak ditemukan",
            "danger"
        )

        return redirect(
            url_for(
                "pelanggan.pelanggan_page"
            )
        )

    # =====================================================
    # CEK SUDAH LUNAS
    # =====================================================

    status = str(
        pelanggan.get("status", "")
    ).strip().upper()

    if status == "LUNAS":

        flash(
            "⚠️ Pelanggan sudah lunas",
            "warning"
        )

        return redirect(
            url_for(
                "pelanggan.pelanggan_page"
            )
        )

    # =====================================================
    # PROSES PEMBAYARAN
    # =====================================================

    result = proses_pembayaran(
        pid=pid,
        user_id=user_id,
        metode="Manual",
        admin=user_id
    )

    if not result.get("status"):

        flash(
            result.get(
                "msg",
                "Pembayaran gagal"
            ),
            "danger"
        )

        return redirect(
            url_for(
                "pelanggan.pelanggan_page"
            )
        )

    # =====================================================
    # AMBIL DATA TERBARU
    # =====================================================

    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )

    if not pelanggan:

        flash(
            "⚠️ Pembayaran berhasil tetapi "
            "data pelanggan tidak ditemukan.",
            "warning"
        )

        return redirect(
            url_for(
                "pelanggan.pelanggan_page"
            )
        )

    pelanggan = dict(pelanggan)

    print(
        "========================================"
    )
    print(
        "✅ PEMBAYARAN BERHASIL"
    )
    print(
        "ID     :", pelanggan.get("id")
    )
    print(
        "NAMA   :", pelanggan.get("nama")
    )
    print(
        "STATUS :", pelanggan.get("status")
    )
    print(
        "========================================"
    )

    # =====================================================
    # WHATSAPP
    # =====================================================

    def async_after_payment():

        try:

            config = get_app_config(
                user_id
            ).copy()

            if pelanggan.get("no_hp"):

                try:

                    pesan = pesan_lunas(
                        pelanggan,
                        config
                    )

                    kirim_wa(
                        pelanggan["no_hp"],
                        pesan
                    )

                    print(
                        "✅ WhatsApp pembayaran terkirim"
                    )

                except Exception as e:

                    error_id = log_error(
                        "kirim_wa",
                        e
                    )

                    print(
                        f"⚠️ WA gagal ({error_id})"
                    )

        except Exception as e:

            error_id = log_error(
                "async_after_payment",
                e
            )

            print(
                f"⚠️ Background error ({error_id})"
            )

    threading.Thread(
        target=async_after_payment,
        daemon=True
    ).start()

    # =====================================================
    # BUKA THERMAL
    # =====================================================

    flash(
        "✅ Pembayaran berhasil. Transaksi LUNAS.",
        "success"
    )

    return redirect(
        url_for(
            "invoice.print_thermal",
            pid=pid
        )
    )

@bp.route("/pelanggan")
@admin_required
@app_required
def pelanggan_page():
    user_id = session["user_id"]

    pelanggan = get_pelanggan_list(
        user_id=user_id
    )

    return render_template(
        "pelanggan.html",
        pelanggan=pelanggan
    )

@bp.route("/pelanggan/sinkron/<pid>")
@admin_required
@app_required
def pelanggan_sinkron(pid):

    try:
        user_id = session["user_id"]

        pelanggan = get_pelanggan_by_id(
            pid,
            user_id
        )

        if not pelanggan:
            flash("Pelanggan tidak ditemukan.", "warning")
            return redirect(
                url_for("pelanggan.pelanggan_page")
            )

        sync_pelanggan_status(
            user_id,
            pelanggan
        )

        flash(
            "Sinkron MikroTik berhasil.",
            "success"
        )

    except Exception as e:
        eid = log_error("pelanggan_sinkron", e)
        flash(f"Gagal sinkron: {eid}", "danger")


    return redirect(
        url_for("pelanggan.pelanggan_page")
    )

@bp.route("/pelanggan/tambah", methods=["GET", "POST"])
@app_required
def pelanggan_tambah():

    user_id = session.get("user_id")

    if not user_id:

        flash(
            "❌ Session user tidak ditemukan",
            "danger"
        )

        return redirect(
            url_for("auth.login")
        )


    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        tipe = (
            request.form.get(
                "tipe",
                "DHCP"
            )
            .strip()
            .upper()
        )


        data = {

            "router_id":
                request.form.get(
                    "router_id"
                ),

            "tipe":
                tipe,

            "nama":
                request.form.get(
                    "nama"
                ),

            "paket":
                request.form.get(
                    "paket"
                ),

            "harga":
                int(
                    request.form.get(
                        "harga",
                        0
                    ) or 0
                ),

            "status":
                request.form.get(
                    "status",
                    "AKTIF"
                ),

            "jatuh_tempo":
                normalisasi_jatuh_tempo(
                    request.form.get(
                        "jatuh_tempo"
                    )
                ),

            "no_hp":
                request.form.get(
                    "no_hp"
                ),

            "ip_address":
                (
                    request.form.get(
                        "ip_address"
                    ) or ""
                ).strip(),

            "mac_address":
                (
                    request.form.get(
                        "mac_address"
                    ) or ""
                ).strip(),

            "host":
                (
                    request.form.get(
                        "host"
                    ) or ""
                ).strip(),

            "pppoe_username":
                (
                    request.form.get(
                        "pppoe_username"
                    ) or ""
                ).strip(),

            "pppoe_password":
                (
                    request.form.get(
                        "pppoe_password"
                    ) or ""
                ).strip(),

            "usage_last":
                "0GB"
        }

        # ============================================================
        # VALIDASI JATUH TEMPO
        # ============================================================

        if not tanggal_valid(data["jatuh_tempo"]):

            flash(
                "❌ Format Jatuh Tempo harus DD/MM/YYYY.",
                "danger"
            )

            return render_template(
                "pelanggan_tambah.html",
                mikrotik=load_mikrotik_list(user_id)
            )
        # =====================================================
        # VALIDASI ROUTER
        # =====================================================

        if not data["router_id"]:

            flash(
                "❌ Router MikroTik wajib dipilih.",
                "danger"
            )

            return render_template(
                "pelanggan_tambah.html",
                mikrotik=load_mikrotik_list(user_id)
            )


        # =====================================================
        # VALIDASI PPPoE
        # =====================================================

        if tipe == "PPPOE":

            if not data["pppoe_username"]:

                flash(
                    "❌ PPPoE Username wajib diisi.",
                    "danger"
                )

                return render_template(
                    "pelanggan_tambah.html",
                    mikrotik=load_mikrotik_list(user_id)
                )


        # =====================================================
        # DHCP
        # IP DIISI → MAC OTOMATIS DARI MIKROTIK
        # =====================================================

        if tipe == "DHCP":

            if not data["ip_address"]:

                flash(
                    "❌ IP Address wajib diisi.",
                    "danger"
                )

                return render_template(
                    "pelanggan_tambah.html",
                    mikrotik=load_mikrotik_list(user_id)
                )


            # =================================================
            # CARI ROUTER
            # =================================================

            router = get_router_by_id(
                user_id,
                data["router_id"]
            )

            if not router:

                flash(
                    "❌ Router MikroTik tidak ditemukan.",
                    "danger"
                )

                return render_template(
                    "pelanggan_tambah.html",
                    mikrotik=load_mikrotik_list(user_id)
                )


            api = None
            client = None


            try:

                # =============================================
                # KONEK KE MIKROTIK
                # =============================================

                result = konek_mikrotik(router)

                if not result:

                    flash(
                        "❌ Gagal terhubung ke MikroTik.",
                        "danger"
                    )

                    return render_template(
                        "pelanggan_tambah.html",
                        mikrotik=load_mikrotik_list(user_id)
                    )


                api, client = result


                # =============================================
                # CARI DHCP LEASE BERDASARKAN IP
                # =============================================

                dhcp = api.get_resource(
                    "/ip/dhcp-server/lease"
                )


                rows = dhcp.get(
                    address=data["ip_address"]
                )


                if not rows:

                    flash(
                        f"❌ IP {data['ip_address']} "
                        "tidak ditemukan di DHCP Lease MikroTik.",
                        "danger"
                    )

                    return render_template(
                        "pelanggan_tambah.html",
                        mikrotik=load_mikrotik_list(user_id)
                    )


                lease = rows[0]


                # =============================================
                # AMBIL MAC OTOMATIS
                # =============================================

                data["mac_address"] = (
                    lease.get(
                        "mac-address",
                        ""
                    ) or ""
                ).strip()


                # =============================================
                # AMBIL HOST OTOMATIS
                # =============================================

                data["host"] = (
                    lease.get(
                        "host-name",
                        ""
                    ) or ""
                ).strip()


                if not data["mac_address"]:

                    flash(
                        f"❌ IP {data['ip_address']} ditemukan "
                        "tetapi MAC Address tidak tersedia.",
                        "danger"
                    )

                    return render_template(
                        "pelanggan_tambah.html",
                        mikrotik=load_mikrotik_list(user_id)
                    )


                print(
                    "========================================"
                )
                print(
                    "🔍 DHCP DITEMUKAN"
                )
                print(
                    "IP   :",
                    data["ip_address"]
                )
                print(
                    "MAC  :",
                    data["mac_address"]
                )
                print(
                    "HOST :",
                    data["host"]
                )
                print(
                    "========================================"
                )


            except Exception as e:

                error_id = log_error(
                    "cari_mac_otomatis",
                    e
                )

                flash(
                    f"❌ Gagal mencari DHCP MikroTik "
                    f"({error_id})",
                    "danger"
                )

                return render_template(
                    "pelanggan_tambah.html",
                    mikrotik=load_mikrotik_list(user_id)
                )


            finally:

                if client:

                    try:
                        client.disconnect()
                    except Exception:
                        pass


        # =====================================================
        # SIMPAN DATABASE
        # =====================================================

        pid = tambah_pelanggan(
            user_id,
            data
        )


        # =====================================================
        # BUAT IP BINDING HOTSPOT
        # =====================================================

        if tipe == "DHCP":

            api = None
            client = None

            try:

                router = get_router_by_id(
                    user_id,
                    data["router_id"]
                )


                if not router:

                    print(
                        "⚠️ Router tidak ditemukan "
                        "saat membuat IP Binding."
                    )

                else:

                    result = konek_mikrotik(
                        router
                    )


                    if not result:

                        print(
                            "⚠️ Gagal konek MikroTik "
                            "saat membuat IP Binding."
                        )

                    else:

                        api, client = result


                        binding = api.get_resource(
                            "/ip/hotspot/ip-binding"
                        )


                        # =====================================
                        # CEK IP SUDAH ADA
                        # =====================================

                        existing = binding.get(
                            address=data["ip_address"]
                        )


                        if existing:

                            print(
                                "ℹ️ IP Binding sudah ada:",
                                data["ip_address"]
                            )


                        else:

                            binding.add(

                                address=data[
                                    "ip_address"
                                ],

                                mac_address=data[
                                    "mac_address"
                                ],

                                type="bypassed",

                                comment=(
                                    f"pelanggan:"
                                    f"{data.get('nama', '')};"
                                    f"pid:{pid};"
                                    f"paket:"
                                    f"{data.get('paket', '')}"
                                )
                            )


                            print(
                                "========================================"
                            )
                            print(
                                "✅ IP BINDING BERHASIL DIBUAT"
                            )
                            print(
                                "IP   :",
                                data["ip_address"]
                            )
                            print(
                                "MAC  :",
                                data["mac_address"]
                            )
                            print(
                                "HOST :",
                                data.get("host", "")
                            )
                            print(
                                "TYPE : bypassed"
                            )
                            print(
                                "========================================"
                            )


            except Exception as e:

                error_id = log_error(
                    "buat_ip_binding",
                    e
                )

                print(
                    f"⚠️ IP Binding gagal dibuat "
                    f"({error_id})"
                )


            finally:

                if client:

                    try:
                        client.disconnect()
                    except Exception:
                        pass


        # =====================================================
        # LOG SIMPAN
        # =====================================================

        print(
            "========================================"
        )
        print(
            "✅ PELANGGAN BERHASIL DISIMPAN"
        )
        print(
            "ID       :",
            pid
        )
        print(
            "Nama     :",
            data.get("nama")
        )
        print(
            "Tipe     :",
            tipe
        )
        print(
            "IP       :",
            data.get("ip_address")
        )
        print(
            "MAC      :",
            data.get("mac_address")
        )
        print(
            "HOST     :",
            data.get("host")
        )
        print(
            "Router   :",
            data.get("router_id")
        )
        print(
            "========================================"
        )


        flash(
            "✅ Pelanggan berhasil ditambahkan.",
            "success"
        )


        return redirect(
            url_for(
                "pelanggan.pelanggan_page"
            )
        )


    # =====================================================
    # GET
    # =====================================================

    return render_template(
        "pelanggan_tambah.html",
        mikrotik=load_mikrotik_list(
            user_id
        )
    )

@bp.route("/pelanggan_edit/<pid>", methods=["GET", "POST"])
@app_required
def pelanggan_edit(pid):

    user_id = session.get("user_id")

    if not user_id:
        flash("❌ Session user tidak ditemukan", "danger")
        return redirect(url_for("auth.login"))

    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )

    if not pelanggan:
        flash(
            "❌ Pelanggan tidak ditemukan",
            "danger"
        )
        return redirect(
            url_for("pelanggan.pelanggan_page")
        )

    # =====================================================
    # SIMPAN USERNAME PPPoE LAMA
    # =====================================================

    old_pppoe_username = (
        pelanggan.get("pppoe_username") or ""
    ).strip()

    if request.method == "POST":

        tipe = (
            request.form.get(
                "tipe",
                pelanggan.get("tipe", "DHCP")
            )
            or "DHCP"
        ).strip().upper()

        # =================================================
        # AMBIL DATA FORM
        # =================================================

        pelanggan.update({

            "nama":
                request.form.get("nama"),

            "paket":
                request.form.get("paket"),

            "status":
                request.form.get("status"),

            "no_hp":
                request.form.get("no_hp"),

            "jatuh_tempo":
                normalisasi_jatuh_tempo(
                    request.form.get(
                        "jatuh_tempo"
                    )
                ),

            "tipe":
                tipe,

            "router_id":
                request.form.get(
                    "router_id"
                ),

            "ip_address":
                (
                    request.form.get(
                        "ip_address"
                    ) or ""
                ).strip(),

            "mac_address":
                (
                    request.form.get(
                        "mac_address"
                    ) or ""
                ).strip(),

            "host":
                (
                    request.form.get(
                        "host"
                    ) or ""
                ).strip(),

            "pppoe_username":
                (
                    request.form.get(
                        "pppoe_username"
                    ) or ""
                ).strip(),

            "pppoe_password":
                (
                    request.form.get(
                        "pppoe_password"
                    ) or ""
                ).strip(),
        })

        pelanggan["harga"] = int(
            request.form.get(
                "harga",
                0
            ) or 0
        )

        # ============================================================
        # VALIDASI JATUH TEMPO
        # ============================================================

        if not tanggal_valid(
            pelanggan.get("jatuh_tempo", "")
        ):

            flash(
                "❌ Format Jatuh Tempo harus DD/MM/YYYY.",
                "danger"
            )

            return render_template(
                "pelanggan_edit.html",
                pelanggan=pelanggan,
                mikrotik=load_mikrotik_list(user_id)
            )
        # =================================================
        # VALIDASI DHCP
        # =================================================

        if tipe == "DHCP":

            if not pelanggan["ip_address"]:

                flash(
                    "❌ IP Address wajib diisi untuk pelanggan DHCP.",
                    "danger"
                )

                return render_template(
                    "pelanggan_edit.html",
                    pelanggan=pelanggan,
                    mikrotik=load_mikrotik_list(user_id)
                )

        # =================================================
        # VALIDASI PPPoE
        # =================================================

        if tipe == "PPPOE":

            if not pelanggan["pppoe_username"]:

                flash(
                    "❌ PPPoE Username wajib diisi.",
                    "danger"
                )

                return render_template(
                    "pelanggan_edit.html",
                    pelanggan=pelanggan,
                    mikrotik=load_mikrotik_list(user_id)
                )

        # =================================================
        # UPDATE DATABASE
        # =================================================

        update_pelanggan(
            user_id,
            pid,
            pelanggan
        )

        # =================================================
        # UPDATE KE MIKROTIK
        # =================================================

        try:

            router = get_router_by_id(
                user_id,
                pelanggan["router_id"]
            )

            if not router:

                print(
                    "⚠️ Router tidak ditemukan:",
                    pelanggan["router_id"]
                )

            else:

                # =============================================
                # BANGUN COMMENT
                # =============================================

                comment = build_comment_from_dict({

                    "nama_pelanggan":
                        pelanggan.get(
                            "nama",
                            ""
                        ),

                    "paket":
                        pelanggan.get(
                            "paket",
                            ""
                        ),

                    "harga":
                        pelanggan.get(
                            "harga",
                            0
                        ),

                    "jatuh_tempo":
                        pelanggan.get(
                            "jatuh_tempo",
                            ""
                        ),

                    "no_hp":
                        pelanggan.get(
                            "no_hp",
                            ""
                        ),

                    "iface":
                        pelanggan.get(
                            "pppoe_username",
                            ""
                        ),

                    "usage":
                        pelanggan.get(
                            "usage",
                            "0 GB"
                        )
                })

                print(
                    "========================================"
                )
                print(
                    "COMMENT BARU:"
                )
                print(
                    comment
                )
                print(
                    "========================================"
                )

                # =============================================
                # PPPoE
                # =============================================

                if tipe == "PPPOE":

                    if old_pppoe_username:

                        berhasil_pppoe = update_pppoe_user(

                            router=router,

                            old_username=
                                old_pppoe_username,

                            new_username=
                                pelanggan.get(
                                    "pppoe_username",
                                    ""
                                ),

                            comment=comment,

                            password=
                                pelanggan.get(
                                    "pppoe_password",
                                    ""
                                ),

                            profile=
                                pelanggan.get(
                                    "paket",
                                    ""
                                )
                        )

                        if berhasil_pppoe:

                            print(
                                "✅ PPPoE SECRET BERHASIL DIUPDATE"
                            )

                        else:

                            print(
                                "❌ PPPoE Secret gagal diperbarui"
                            )

                    else:

                        print(
                            "⚠️ Username PPPoE lama tidak tersedia"
                        )

                # =============================================
                # DHCP
                # =============================================

                elif tipe == "DHCP":

                    ip_address = (
                        pelanggan.get(
                            "ip_address"
                        ) or ""
                    ).strip()

                    mac_address = (
                        pelanggan.get(
                            "mac_address"
                        ) or ""
                    ).strip()

                    # =========================================
                    # CARI MAC OTOMATIS JIKA KOSONG
                    # =========================================

                    if not mac_address:

                        print(
                            "🔍 MAC kosong, mencari berdasarkan IP:",
                            ip_address
                        )

                        api = None
                        client = None

                        try:

                            result = konek_mikrotik(
                                router
                            )

                            if not result:

                                raise Exception(
                                    "Gagal terhubung ke MikroTik."
                                )

                            api, client = result

                            dhcp = api.get_resource(
                                "/ip/dhcp-server/lease"
                            )

                            rows = dhcp.get(
                                address=ip_address
                            )

                            if not rows:

                                raise Exception(
                                    f"IP {ip_address} "
                                    "tidak ditemukan di DHCP Lease MikroTik."
                                )

                            lease = rows[0]

                            mac_address = (
                                lease.get(
                                    "mac-address",
                                    ""
                                ) or ""
                            ).strip()

                            host = (
                                lease.get(
                                    "host-name",
                                    ""
                                ) or ""
                            ).strip()

                            pelanggan["mac_address"] = mac_address
                            pelanggan["host"] = host

                            if not mac_address:

                                raise Exception(
                                    "MAC Address tidak tersedia "
                                    "pada DHCP Lease."
                                )

                            # Simpan MAC hasil pencarian
                            update_pelanggan(
                                user_id,
                                pid,
                                pelanggan
                            )

                            print(
                                "========================================"
                            )
                            print(
                                "🔍 DHCP DITEMUKAN"
                            )
                            print(
                                "IP   :",
                                ip_address
                            )
                            print(
                                "MAC  :",
                                mac_address
                            )
                            print(
                                "HOST :",
                                host
                            )
                            print(
                                "========================================"
                            )

                        except Exception as e:

                            error_id = log_error(
                                "cari_mac_edit",
                                e
                            )

                            print(
                                f"⚠️ Gagal mencari MAC "
                                f"({error_id})"
                            )

                        finally:

                            if client:

                                try:
                                    client.disconnect()
                                except Exception:
                                    pass

                    # =========================================
                    # UPDATE COMMENT DHCP
                    # =========================================

                    if mac_address:

                        berhasil_dhcp = update_comment_dhcp(

                            router,

                            mac_address,

                            comment
                        )

                        if berhasil_dhcp:

                            print(
                                "✅ COMMENT DHCP BERHASIL DIUPDATE"
                            )

                        else:

                            print(
                                "⚠️ COMMENT DHCP GAGAL DIUPDATE"
                            )

                    else:

                        print(
                            "⚠️ MAC Address tidak tersedia"
                        )

        except Exception as e:

            error_id = log_error(
                "update_comment_mikrotik",
                e
            )

            print(
                f"❌ Update MikroTik gagal ({error_id})"
            )

        # =================================================
        # SELESAI
        # =================================================

        flash(
            "✅ Pelanggan berhasil diperbarui.",
            "success"
        )

        return redirect(
            url_for(
                "pelanggan.pelanggan_page"
            )
        )

    # =====================================================
    # GET
    # =====================================================

    return render_template(
        "pelanggan_edit.html",
        pelanggan=pelanggan,
        mikrotik=load_mikrotik_list(user_id)
    )

@bp.route("/pelanggan/hapus/<pid>", methods=["GET", "POST"])
@admin_required
@app_required
def pelanggan_hapus(pid):
    try:
        user_id = session["user_id"]

        pelanggan = get_pelanggan_by_id(pid, user_id)

        if not pelanggan:
            flash("❌ Pelanggan tidak ditemukan", "warning")
            return redirect(url_for("pelanggan.pelanggan_page"))

        hapus_pelanggan(user_id, pid)

        flash("✅ Pelanggan berhasil dihapus", "success")

    except Exception as e:
        error_id = log_error("pelanggan_hapus_route", e)
        flash(f"❌ Gagal menghapus pelanggan ({error_id})", "danger")

    return redirect(url_for("pelanggan.pelanggan_page"))

@bp.route("/pelanggan/cari-mikrotik-ip", methods=["GET"])
@app_required
def cari_mikrotik_ip():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Session user tidak ditemukan."
        }), 401


    router_id = request.args.get("router_id", "").strip()
    ip = request.args.get("ip", "").strip()


    if not router_id:
        return jsonify({
            "success": False,
            "message": "Router MikroTik belum dipilih."
        }), 400


    if not ip:
        return jsonify({
            "success": False,
            "message": "IP Address belum diisi."
        }), 400


    try:

        # ==============================
        # CARI ROUTER
        # ==============================

        router = get_router_by_id(
            user_id,
            router_id
        )

        if not router:

            return jsonify({
                "success": False,
                "message": "Router tidak ditemukan."
            }), 404


        # ==============================
        # KONEK KE MIKROTIK
        # ==============================

        result = konek_mikrotik(router)

        if not result:

            return jsonify({
                "success": False,
                "message": "Gagal terhubung ke MikroTik."
            }), 500


        api, client = result


        try:

            # ==============================
            # CARI DHCP LEASE BERDASARKAN IP
            # ==============================

            dhcp = api.get_resource(
                "/ip/dhcp-server/lease"
            )

            rows = dhcp.get(
                address=ip
            )


            if not rows:

                return jsonify({
                    "success": False,
                    "message":
                        f"IP {ip} tidak ditemukan "
                        "di DHCP Lease MikroTik."
                })


            lease = rows[0]


            return jsonify({
                "success": True,

                "ip_address":
                    lease.get("address", ip),

                "mac_address":
                    lease.get("mac-address", ""),

                "host":
                    lease.get("host-name", "")
                    or lease.get("host-name", ""),

                "comment":
                    lease.get("comment", ""),

                "server":
                    lease.get("server", ""),

                "status":
                    lease.get("status", ""),

            })


        finally:

            # ==============================
            # TUTUP KONEKSI
            # ==============================

            try:
                client.disconnect()
            except Exception:
                pass


    except Exception as e:

        print(
            f"❌ Gagal cari MikroTik IP {ip}: {e}"
        )

        return jsonify({
            "success": False,
            "message":
                f"Gagal mencari data MikroTik: {str(e)}"
        }), 500

@bp.route("/pelanggan/cari-mikrotik", methods=["GET"])
@app_required
def cari_mikrotik():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "success": False,
            "message": "Session user tidak ditemukan."
        }), 401


    router_id = request.args.get(
        "router_id",
        ""
    ).strip()

    tipe = request.args.get(
        "tipe",
        ""
    ).strip().upper()


    if not router_id:
        return jsonify({
            "success": False,
            "message": "Router belum dipilih."
        }), 400


    if tipe not in ("DHCP", "PPPOE"):
        return jsonify({
            "success": False,
            "message": "Tipe pelanggan tidak valid."
        }), 400


    # ==================================================
    # CARI ROUTER
    # ==================================================

    router = get_router_by_id(
        user_id,
        router_id
    )


    if not router:

        return jsonify({
            "success": False,
            "message": "Router MikroTik tidak ditemukan."
        }), 404


    api = None
    client = None


    try:

        # ==================================================
        # KONEK MIKROTIK
        # ==================================================

        result = konek_mikrotik(router)

        if not result:

            return jsonify({
                "success": False,
                "message": "Gagal terhubung ke MikroTik."
            }), 500


        api, client = result


        # ==================================================
        # DHCP
        # ==================================================

        if tipe == "DHCP":

            ip = request.args.get(
                "ip",
                ""
            ).strip()


            if not ip:

                return jsonify({
                    "success": False,
                    "message": "IP Address belum diisi."
                }), 400


            resource = api.get_resource(
                "/ip/dhcp-server/lease"
            )


            rows = resource.get(
                address=ip
            )


            if not rows:

                return jsonify({
                    "success": False,
                    "message":
                        f"IP {ip} tidak ditemukan "
                        "di DHCP Lease MikroTik."
                }), 404


            lease = rows[0]


            return jsonify({

                "success": True,

                "tipe": "DHCP",

                "ip_address":
                    lease.get(
                        "address",
                        ip
                    ),

                "mac_address":
                    lease.get(
                        "mac-address",
                        ""
                    ),

                "host":
                    lease.get(
                        "host-name",
                        ""
                    ),

                "comment":
                    lease.get(
                        "comment",
                        ""
                    ),

                "server":
                    lease.get(
                        "server",
                        ""
                    ),

                "status":
                    lease.get(
                        "status",
                        ""
                    )

            })


        # ==================================================
        # PPPoE
        # ==================================================
        username = request.args.get(
            "username",
            ""
        ).strip()


        if not username:

            return jsonify({
                "success": False,
                "message": "PPPoE User belum diisi."
            }), 400


        # ==================================================
        # AMBIL DATA PPP SECRET
        # ==================================================

        resource = api.get_resource(
            "/ppp/secret"
        )


        rows = resource.get(
            name=username
        )


        if not rows:

            return jsonify({
                "success": False,
                "message":
                    f"PPPoE User '{username}' "
                    "tidak ditemukan di PPP Secret MikroTik."
            }), 404


        secret = rows[0]


        return jsonify({

            "success": True,

            "tipe": "PPPOE",

            "username":
                secret.get(
                    "name",
                    username
                ),

            "password":
                secret.get(
                    "password",
                    ""
                ),

            "profile":
                secret.get(
                    "profile",
                    ""
                ),

            "comment":
                secret.get(
                    "comment",
                    ""
                ),

            "service":
                secret.get(
                    "service",
                    ""
                ),

            "local_address":
                secret.get(
                    "local-address",
                    ""
                ),

            "remote_address":
                secret.get(
                    "remote-address",
                    ""
                ),

            "disabled":
                str(
                    secret.get(
                        "disabled",
                        "false"
                    )
                ).lower()
                in (
                    "true",
                    "yes",
                    "1"
                )

        })


    except Exception as e:

        print(
            "❌ ERROR CARI MIKROTIK:",
            repr(e)
        )


        return jsonify({
            "success": False,
            "message":
                f"Gagal mencari data MikroTik: {str(e)}"
        }), 500


    finally:

        if client:

            try:
                client.disconnect()
            except Exception:
                pass

@bp.route("/isolir", methods=["GET"])
def halaman_isolir():

    try:
        # ==================================================
        # USER LOGIN
        # ==================================================

        user_id = session.get("user_id")

        if not user_id:
            return render_template(
                "isolir.html",
                pelanggan=[],
                error="Sesi pengguna tidak ditemukan."
            ), 401

        print(
            f"[ISOLIR] Cek pelanggan untuk user: {user_id}"
        )

        # ==================================================
        # AMBIL SEMUA PELANGGAN YANG TERDAFTAR
        # ==================================================

        pelanggan_list = get_pelanggan_list(
            user_id=user_id
        )

        print(
            f"[ISOLIR] Total pelanggan terdaftar: "
            f"{len(pelanggan_list)}"
        )

        hasil = []

        hari_ini = datetime.now().date()

        # ==================================================
        # CEK SETIAP PELANGGAN
        # ==================================================

        for pelanggan in pelanggan_list:

            pelanggan = dict(pelanggan)

            # ------------------------------------------------
            # CARI TAGIHAN TERBARU
            # ------------------------------------------------

            conn = get_db()

            try:
                row = conn.execute(
                    """
                    SELECT
                        id,
                        bulan,
                        tahun,
                        jumlah,
                        status,
                        tanggal_bayar
                    FROM tagihan
                    WHERE pelanggan_id = ?
                      AND user_id = ?
                    ORDER BY tahun DESC, bulan DESC
                    LIMIT 1
                    """,
                    (
                        pelanggan.get("id"),
                        user_id,
                    )
                ).fetchone()

                tagihan = dict(row) if row else None

            finally:
                release_db(conn)

            # ------------------------------------------------
            # STATUS TAGIHAN
            # ------------------------------------------------

            status_tagihan = ""

            if tagihan:
                status_tagihan = str(
                    tagihan.get("status") or ""
                ).strip().upper()

            status_lunas = status_tagihan in (
                "LUNAS",
                "PAID",
                "SUDAH BAYAR",
                "SUDAH DIBAYAR"
            )

            # ------------------------------------------------
            # JATUH TEMPO
            # ------------------------------------------------

            due_raw = str(
                pelanggan.get("jatuh_tempo") or ""
            ).strip()

            jatuh_tempo = None

            if due_raw:

                try:
                    jatuh_tempo = datetime.strptime(
                        due_raw,
                        "%d/%m/%Y"
                    ).date()

                except ValueError:

                    try:
                        jatuh_tempo = datetime.strptime(
                            due_raw,
                            "%Y-%m-%d"
                        ).date()

                    except ValueError:
                        jatuh_tempo = None

            # ------------------------------------------------
            # TENTUKAN STATUS LAYANAN
            # ------------------------------------------------

            isolir = False
            layanan_normal = True

            if status_lunas:

                isolir = False
                layanan_normal = True

            elif status_tagihan in (
                "BELUM LUNAS",
                "BELUM BAYAR",
                "UNPAID"
            ):

                if jatuh_tempo and hari_ini >= jatuh_tempo:

                    isolir = True
                    layanan_normal = False

            # ------------------------------------------------
            # MASUKKAN HASIL
            # ------------------------------------------------

            pelanggan["tagihan"] = tagihan
            pelanggan["status_tagihan"] = status_tagihan
            pelanggan["isolir"] = isolir
            pelanggan["layanan_normal"] = layanan_normal

            pelanggan["jatuh_tempo"] = (
                jatuh_tempo.strftime("%d/%m/%Y")
                if jatuh_tempo
                else ""
            )

            hasil.append(pelanggan)

            print(
                f"[ISOLIR] {pelanggan.get('nama')} | "
                f"Tagihan: {status_tagihan or '-'} | "
                f"Jatuh tempo: "
                f"{pelanggan.get('jatuh_tempo') or '-'} | "
                f"Isolir: {isolir}"
            )

        # ==================================================
        # RENDER
        # ==================================================

        app_cfg = get_app_config(user_id)

        return render_template(
            "isolir.html",
            pelanggan=hasil,
            pelanggan_list=hasil,
            app=app_cfg,
            hari_ini=hari_ini.strftime("%d/%m/%Y")
        )

    except Exception as e:

        print(
            f"[ISOLIR] Error: {e}"
        )

        return render_template(
            "isolir.html",
            pelanggan=[],
            pelanggan_list=[],
            error=f"Gagal mengambil data pelanggan: {e}"
        ), 500



