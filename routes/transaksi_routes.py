#routes/transaksi_routes.py
from flask import (
    Blueprint,
    render_template,
    session,
    flash,
    redirect,
    url_for,
)

from core.decorators import (
    admin_required,
    app_required,
)

from core.transaksi_core import (
    get_semua_transaksi,
)

from core.error_helper import log_error


bp = Blueprint("transaksi", __name__)


# =========================================================
# HALAMAN SEMUA TRANSAKSI
# =========================================================

@bp.route("/transaksi")
@admin_required
@app_required
def transaksi():

    try:

        user_id = session.get("user_id")

        if not user_id:

            flash(
                "Sesi pengguna tidak ditemukan.",
                "danger"
            )

            return redirect(
                url_for("misc.dashboard")
            )

        # Ambil SEMUA transaksi
        transaksi = get_semua_transaksi(user_id)

        # Total jumlah transaksi
        total_transaksi = len(transaksi)

        # Total pemasukan
        total_pemasukan = sum(
            int(t.get("harga") or 0)
            for t in transaksi
            if isinstance(t, dict)
        )

        return render_template(
            "transaksi.html",
            transaksi=transaksi,
            total_transaksi=total_transaksi,
            total_pemasukan=total_pemasukan
        )

    except Exception as e:

        error_id = log_error(
            "transaksi",
            e
        )

        flash(
            f"Gagal memuat transaksi ({error_id})",
            "danger"
        )

        return redirect(
            url_for("misc.dashboard")
        )

