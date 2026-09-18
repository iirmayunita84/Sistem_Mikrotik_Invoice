
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,

)

from core.decorators import (
    admin_required,
    app_required,
    premium_required,
)
from core.router_log import get_router_logs
from core.api import sinkron_semua_router
from core.logic import (
    load_mikrotik_list,
    sync_pelanggan_status,
)
from core.core_pelanggan import get_pelanggan_list
from services.inject_router_status import inject_router_status
from core.error_helper import log_error
from core.config_core import get_app_config
from services.router_service import (
    get_user_routers,
    get_router,
    add_router,
    update_router,
    delete_router,
)
bp = Blueprint("router", __name__)

@bp.route("/routers")
@admin_required
@app_required
def routers_page():
    try:
        user_id = session["user_id"]

        routers = inject_router_status(user_id)

        return render_template(
            "routers.html",
            routers=routers
        )

    except Exception as e:
        error_id = log_error("routers_page", e)
        flash(f"Gagal membuka daftar router ({error_id})", "danger")
        return redirect(url_for("misc.dashboard"))

@bp.route("/router/<rid>")
@admin_required
@app_required
def router_detail(rid):
    try:
        user_id = session["user_id"]

        router = get_router(rid)

        if not router:
            flash("Router tidak ditemukan", "warning")
            return redirect(url_for("router.routers_page"))

        routers_status = inject_router_status(user_id)

        router_status = next(
            (
                r for r in routers_status
                if str(r.get("id")) == str(rid)
            ),
            {}
        )

        pelanggan = [
            dict(p)
            for p in get_pelanggan(user_id)
            if str(p.get("router_id")) == str(rid)
        ]

        router.update(
            status=router_status.get("status", "unknown"),
            pelanggan=pelanggan
        )

        return render_template(
            "router_detail.html",
            router=router
        )

    except Exception as e:
        error_id = log_error("router_detail", e)
        flash(f"Gagal membuka router ({error_id})", "danger")
        return redirect(url_for("router.routers_page"))

@bp.route("/router-log")
def router_log():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    logs = get_router_logs(
        session["user_id"]
    )

    return render_template(
        "router_log.html",
        logs=logs
    )

@bp.route("/mikrotik")
@admin_required
@app_required
def mikrotik_list():

    try:
        routers = load_mikrotik_list(session["user_id"])

        return render_template(
            "mikrotik_list.html",
            routers=routers
        )

    except Exception as e:
        error_id = log_error("mikrotik_list", e)
        flash(f"Gagal memuat router ({error_id})", "danger")
        return redirect(url_for("misc.dashboard"))

@bp.route("/mikrotik/tambah", methods=["GET", "POST"])
@admin_required
@app_required
def mikrotik_tambah():
    user_id = session.get("user_id")

    if request.method == "POST":
        try:
            port = int(request.form.get("port", 8728))
        except ValueError:
            flash("Port tidak valid")
            return redirect(url_for("router.mikrotik_tambah")) # <-- Menggunakan router.

        print("REQUEST =", request.form)

        data = {
            "name": request.form.get("name"),
            "host": request.form.get("host"),
            "username": request.form.get("username"),
            "password": request.form.get("password"),
            "port": port
        }

        print("DATA =", data)
        add_router(user_id, data)
        flash("Router berhasil ditambahkan")
        return redirect(url_for("router.mikrotik_list")) # <-- Lebih aman menggunakan url_for

    return render_template("mikrotik_tambah.html")

@bp.route("/mikrotik/edit/<rid>", methods=["GET", "POST"])
@admin_required
@app_required
def mikrotik_edit(rid):
    user_id = session["user_id"]

    try:
        router = get_router(rid)

        if not router:
            flash("Router tidak ditemukan", "warning")
            return redirect(url_for("router.mikrotik_list"))

        if request.method == "POST":

            data = {
                "name": request.form.get("name", "").strip(),
                "host": request.form.get("host", "").strip(),
                "username": request.form.get("username", "").strip(),
                "password": request.form.get("password", ""),
                "port": int(request.form.get("port", 8728))
            }

            update_router(user_id, rid, data)

            flash("✅ Router berhasil diperbarui", "success")
            return redirect(url_for("router.mikrotik_list"))

        return render_template(
            "mikrotik_edit.html",
            router=router
        )

    except Exception as e:
        error_id = log_error("mikrotik_edit", e)
        flash(f"❌ Gagal mengubah router ({error_id})", "danger")
        return redirect(url_for("router.mikrotik_list"))

@bp.route("/mikrotik/hapus/<rid>")
@admin_required
@app_required
def mikrotik_hapus(rid):

    try:
        delete_router(rid)

        flash("Router berhasil dihapus", "success")

    except Exception as e:
        error_id = log_error("mikrotik_hapus", e)
        flash(f"Gagal menghapus router ({error_id})", "danger")

    return redirect(url_for("router.mikrotik_list"))

@bp.route("/sinkron")
@admin_required
@app_required
def sinkron():
    user_id = session["user_id"]

    try:
        sinkron_semua_router(user_id)
        flash("✅ Sinkron semua router berhasil", "success")
    except Exception as e:
        log_error("sinkron_router", e)
        flash("❌ Sinkron gagal", "danger")

    return redirect(url_for("misc.dashboard"))

@bp.route(
    "/sinkron-semua",
    methods=["POST"]
)
@admin_required
def sinkron_semua():
    try:
        user_id = session["user_id"]

        # =====================================
        # 1. SINKRON SEMUA ROUTER
        # =====================================

        print("🔄 Mulai sinkron semua router...")

        total = sinkron_semua_router(user_id)

        print(
            f"✅ Sinkron router selesai. "
            f"Total DHCP = {total}"
        )

        # =====================================
        # 2. AMBIL PELANGGAN TERBARU
        # =====================================

        pelanggan_list = get_pelanggan_list(
            user_id=user_id,
            use_cache=False
        )

        print(
            f"👥 Total pelanggan = "
            f"{len(pelanggan_list)}"
        )

        # =====================================
        # 3. SINKRON STATUS PPPoE
        # =====================================

        berhasil = 0
        gagal = 0

        for pelanggan in pelanggan_list:

            hasil = sync_pelanggan_status(
                user_id,
                pelanggan
            )

            if hasil:
                berhasil += 1
            else:
                gagal += 1

        print(
            f"✅ Status PPPoE berhasil = {berhasil}"
        )

        print(
            f"⚠️ Status PPPoE gagal = {gagal}"
        )

        flash(
            f"✅ Sinkron selesai. "
            f"DHCP: {total}, "
            f"PPPoE berhasil: {berhasil}, "
            f"gagal: {gagal}",
            "success"
        )

    except Exception as e:

        error_id = log_error(
            "sinkron_semua",
            e
        )

        flash(
            f"❌ Gagal sinkron ({error_id})",
            "danger"
        )

    return redirect(
        url_for("misc.dashboard")
    )

@bp.route("/pppoe")
@admin_required
@app_required
def pppoe_dashboard():
    user_id = session["user_id"]
    pelanggan = get_pelanggan(user_id)
    return render_template(
        "pppoe_dashboard.html",
        pelanggan=pelanggan
    )
