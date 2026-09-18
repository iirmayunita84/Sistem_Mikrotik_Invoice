
from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
)

from core.decorators import (
    admin_required,
    app_required,
)

from core.db import (
    get_db,
    release_db,
)

from core.error_helper import (
    log_error,
)


bp = Blueprint("pembayaran", __name__)


@bp.route("/pembayaran")
@admin_required
@app_required
def pembayaran_page():

    conn = get_db()

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

        cur = conn.cursor()

        cur.execute("""
            SELECT
                t.id,
                t.pelanggan_id,
                t.bulan,
                t.tahun,
                t.jumlah,
                t.status,
                t.tanggal_bayar,
                p.nama,
                p.paket,
                p.no_hp
            FROM tagihan t
            LEFT JOIN pelanggan p
                ON p.id = t.pelanggan_id
            WHERE t.user_id = ?
            ORDER BY
                CASE
                    WHEN UPPER(
                        COALESCE(t.status, '')
                    ) = 'LUNAS'
                    THEN 1
                    ELSE 0
                END,
                t.tahun DESC,
                t.bulan DESC,
                p.nama COLLATE NOCASE
        """, (user_id,))

        pembayaran_list = [
            dict(row)
            for row in cur.fetchall()
        ]

        total_pembayaran = sum(
            int(x.get("jumlah") or 0)
            for x in pembayaran_list
            if str(
                x.get("status") or ""
            ).upper()
            in (
                "LUNAS",
                "PAID",
                "SUDAH BAYAR",
            )
        )

        jumlah_lunas = sum(
            1
            for x in pembayaran_list
            if str(
                x.get("status") or ""
            ).upper()
            in (
                "LUNAS",
                "PAID",
                "SUDAH BAYAR",
            )
        )

        jumlah_belum = sum(
            1
            for x in pembayaran_list
            if str(
                x.get("status") or ""
            ).upper()
            not in (
                "LUNAS",
                "PAID",
                "SUDAH BAYAR",
            )
        )

        return render_template(
            "pembayaran.html",
            pembayaran_list=pembayaran_list,
            total_pembayaran=total_pembayaran,
            jumlah_lunas=jumlah_lunas,
            jumlah_belum=jumlah_belum,
        )

    except Exception as e:

        error_id = log_error(
            "pembayaran_page",
            e
        )

        flash(
            f"Gagal memuat pembayaran ({error_id})",
            "danger"
        )

        return redirect(
            url_for("misc.dashboard")
        )

    finally:

        release_db(conn)

