import os
import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)

from werkzeug.utils import secure_filename

from core.decorators import app_required
from core.config_core import (
    get_app_config,
    save_app_config,
)
from core.logic import load_mikrotik_list
from core.error_helper import log_error


bp = Blueprint("setting", __name__)


# ==========================================
# IZIN FILE UPLOAD
# ==========================================

ALLOWED_LOGO = {
    "png",
    "jpg",
    "jpeg",
    "bmp",
    "webp",
}

ALLOWED_QRIS = {
    "png",
    "jpg",
    "jpeg",
    "bmp",
    "webp",
}


def simpan_file_upload(file, allowed_ext):
    """
    Simpan file ke folder uploads aplikasi.
    Mengembalikan nama file yang disimpan.
    """

    if not file:
        return ""

    if not file.filename:
        return ""

    nama_asli = secure_filename(
        file.filename
    )

    if not nama_asli:
        return ""

    ext = os.path.splitext(
        nama_asli
    )[1].lower().lstrip(".")

    if ext not in allowed_ext:
        raise ValueError(
            f"Format file .{ext} tidak diperbolehkan."
        )

    nama_file = (
        f"{uuid.uuid4().hex}"
        f".{ext}"
    )

    upload_folder = current_app.config[
        "UPLOAD_FOLDER"
    ]

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    path_file = os.path.join(
        upload_folder,
        nama_file
    )

    file.save(path_file)

    return nama_file


@bp.route("/setting", methods=["GET", "POST"])
@app_required
def setting():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(
            url_for("auth.login")
        )

    # ==========================================
    # SIMPAN PENGATURAN
    # ==========================================

    if request.method == "POST":

        try:

            # Ambil konfigurasi lama
            old_cfg = get_app_config(
                user_id
            )

            # ==================================
            # DATA TEXT
            # ==================================

            data = {
                "store_name": request.form.get(
                    "store_name",
                    ""
                ).strip(),

                "store_address": request.form.get(
                    "store_address",
                    ""
                ).strip(),

                "footer_message": request.form.get(
                    "footer_message",
                    ""
                ).strip(),

                "default_account": request.form.get(
                    "default_account",
                    ""
                ).strip(),

                # PENTING:
                # pertahankan file lama
                "logo_file": old_cfg.get(
                    "logo_file",
                    ""
                ),

                "qris_file": old_cfg.get(
                    "qris_file",
                    ""
                ),
            }

            # ==================================
            # UPLOAD LOGO
            # ==================================

            logo = request.files.get(
                "logo"
            )

            if logo and logo.filename:

                logo_file = simpan_file_upload(
                    logo,
                    ALLOWED_LOGO
                )

                data["logo_file"] = logo_file

                print(
                    "✅ Logo tersimpan:",
                    logo_file
                )

            # ==================================
            # UPLOAD QRIS
            # ==================================

            qris = request.files.get(
                "qris"
            )

            if qris and qris.filename:

                qris_file = simpan_file_upload(
                    qris,
                    ALLOWED_QRIS
                )

                data["qris_file"] = qris_file

                print(
                    "✅ QRIS tersimpan:",
                    qris_file
                )

            # ==================================
            # SIMPAN DATABASE
            # ==================================

            save_app_config(
                user_id,
                data
            )

            print(
                "✅ Pengaturan toko tersimpan"
            )

            print(
                "LOGO :",
                data["logo_file"]
            )

            print(
                "QRIS :",
                data["qris_file"]
            )

            flash(
                "Pengaturan berhasil disimpan.",
                "success"
            )

        except Exception as e:

            error_id = log_error(
                "setting",
                e
            )

            print(
                "❌ Gagal menyimpan pengaturan:",
                e
            )

            flash(
                f"Gagal menyimpan pengaturan ({error_id})",
                "danger"
            )

        return redirect(
            url_for("setting.setting")
        )

    # ==========================================
    # TAMPILKAN PENGATURAN
    # ==========================================

    try:

        app_cfg = get_app_config(
            user_id
        )

        routers = load_mikrotik_list(
            user_id
        )

        return render_template(
            "setting.html",
            app=app_cfg,
            routers=routers
        )

    except Exception as e:

        error_id = log_error(
            "setting_page",
            e
        )

        flash(
            f"Gagal membuka pengaturan ({error_id})",
            "danger"
        )

        return redirect(
            url_for("misc.dashboard")
        )