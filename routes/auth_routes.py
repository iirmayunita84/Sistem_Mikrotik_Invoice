
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from core.license_core import (
    get_license_info,
    get_device_id,
    validasi_kode_aktivasi,
    simpan_license,
    paket_dari_kode,
    license_valid_local,
)

from core.auth import (
    verify_login,
    total_user,
    create_admin,
)
from core.decorators import app_required
from urllib.parse import quote
from core.error_helper import log_error

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():

    if total_user() == 0:
        # 🛠️ PERBAIKAN 1: Tambahkan redirect()
        return redirect(url_for("auth.setup"))

    if session.get("user_id"):
        return redirect(url_for("misc.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash(
                "⚠️ Username dan password wajib diisi.",
                "warning"
            )
            return redirect(url_for("auth.setup"))

        try:
            user = verify_login(username, password)

            if not user:
                flash(
                    "❌ Username atau password salah.",
                    "danger"
                )
                return redirect(url_for("auth.login"))

            user = dict(user)

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = "admin" if user.get("is_admin", 0) else "user"

            flash(
                "🔑 Login berhasil! Selamat datang kembali.",
                "success"
            )

            return redirect(url_for("misc.dashboard"))

        except Exception as e:
            error_id = log_error("setup", e)

            flash(
                f"⚠️ Terjadi kesalahan pada sistem ({error_id})",
                "danger"
            )

            return redirect(url_for("auth.setup"))

    return render_template("login.html")

@bp.route("/setup", methods=["GET", "POST"])
def setup():

    # Jika admin sudah ada, tidak boleh setup lagi
    if total_user() > 0:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        try:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("⚠️ Username dan password wajib diisi.", "warning")
                return render_template("setup.html")

            create_admin(username, password)

            flash("✅ Admin berhasil dibuat. Silakan login.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            error_id = log_error("setup_route", e)
            flash(f"⚠️ Terjadi kesalahan pada sistem ({error_id})", "danger")

    return render_template("setup.html")

@bp.route("/logout")
@app_required
def logout():
    session.clear()
    flash("Anda telah logout.", "success")
    return redirect(url_for("auth.login"))

@bp.route("/aktivasi", methods=["GET", "POST"])
def aktivasi():

    device_id = get_device_id()

    if request.method == "POST":

        try:

            license_key = request.form.get(
                "license_key",
                ""
            ).strip().upper()

            # =================================================
            # CEK KOSONG
            # =================================================

            if not license_key:

                flash(
                    "License key kosong",
                    "danger"
                )

                return redirect(
                    url_for("auth.aktivasi")
                )

            # =================================================
            # VALIDASI LICENSE
            # =================================================

            if not validasi_kode_aktivasi(
                license_key,
                device_id
            ):

                flash(
                    "License key tidak valid untuk perangkat ini",
                    "danger"
                )

                return redirect(
                    url_for("auth.aktivasi")
                )

            # =================================================
            # AMBIL PAKET
            # =================================================

            paket = paket_dari_kode(
                license_key
            )

            if not paket:

                flash(
                    "Paket tidak dikenali",
                    "danger"
                )

                return redirect(
                    url_for("auth.aktivasi")
                )

            # =================================================
            # SIMPAN LICENSE
            # =================================================

            simpan_license(
                license_key,
                paket
            )

            # =================================================
            # BERSIHKAN CACHE
            # =================================================

            get_license_info(force=True)

            # =================================================
            # CEK ULANG
            # =================================================

            if not license_valid_local():

                flash(
                    "License tersimpan tetapi gagal diverifikasi",
                    "danger"
                )

                return redirect(
                    url_for("auth.aktivasi")
                )

            flash(
                f"✅ Aktivasi berhasil ({paket})",
                "success"
            )

            return redirect(
                url_for("misc.dashboard")
            )

        except Exception as e:

            error_id = log_error(
                "aktivasi",
                e
            )

            flash(
                f"Gagal aktivasi ({error_id})",
                "danger"
            )

            return redirect(
                url_for("auth.aktivasi")
            )

    # =========================================================
    # GET
    # =========================================================

    license_ok = license_valid_local()

    return render_template(
        "aktivasi.html",
        device_id=device_id,
        device_id_encoded=quote(device_id),
        license_ok=license_ok
    )


