
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


bp = Blueprint("tagihan_page", __name__)


@bp.route("/tagihan")
@admin_required
@app_required
def tagihan_page():

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
                p.no_hp,
                p.jatuh_tempo
            FROM tagihan t
            LEFT JOIN pelanggan p
                ON p.id = t.pelanggan_id
            WHERE t.user_id = ?
            ORDER BY
                t.tahun DESC,
                t.bulan DESC,
                p.nama COLLATE NOCASE
        """, (user_id,))

        tagihan_list = [
            dict(row)
            for row in cur.fetchall()
        ]

        total_tagihan = len(tagihan_list)

        total_nilai = sum(
            int(x.get("jumlah") or 0)
            for x in tagihan_list
        )

        belum_bayar = [
            x
            for x in tagihan_list
            if str(x.get("status") or "").upper()
            not in (
                "LUNAS",
                "PAID",
                "SUDAH BAYAR",
            )
        ]

        total_belum_bayar = sum(
            int(x.get("jumlah") or 0)
            for x in belum_bayar
        )

        return render_template(
            "tagihan_list.html",
            tagihan_list=tagihan_list,
            total_tagihan=total_tagihan,
            total_nilai=total_nilai,
            belum_bayar=belum_bayar,
            total_belum_bayar=total_belum_bayar,
        )

    except Exception as e:

        error_id = log_error(
            "tagihan_page",
            e
        )

        flash(
            f"Gagal memuat tagihan ({error_id})",
            "danger"
        )

        return redirect(
            url_for("misc.dashboard")
        )

    finally:

        release_db(conn)

