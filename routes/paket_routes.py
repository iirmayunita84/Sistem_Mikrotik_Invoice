from flask import Blueprint, render_template, session, redirect, url_for, flash

from core.decorators import admin_required, app_required
from core.db import get_db, release_db
from core.error_helper import log_error

bp = Blueprint("paket", __name__)

@bp.route("/paket")
def paket_page():

    conn = get_db()

    try:

        user_id = session.get("user_id")

        if not user_id:
            flash("Sesi pengguna tidak ditemukan.", "danger")
            return redirect(url_for("misc.dashboard"))

        cur = conn.cursor()

        cur.execute("""
            SELECT
                paket,
                COUNT(*) AS jumlah_pelanggan,
                COALESCE(SUM(harga), 0) AS total_nilai
            FROM pelanggan
            WHERE user_id = ?
              AND paket IS NOT NULL
              AND TRIM(paket) != ''
            GROUP BY paket
            ORDER BY paket COLLATE NOCASE
        """, (user_id,))

        paket_list = [
            dict(row)
            for row in cur.fetchall()
        ]

        return render_template(
            "paket.html",
            paket_list=paket_list
        )

    except Exception as e:

        error_id = log_error("paket", e)

        flash(
            f"Gagal memuat data paket ({error_id})",
            "danger"
        )

        return redirect(url_for("misc.dashboard"))

    finally:

        release_db(conn)

