
from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    request,
)

from datetime import datetime

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


bp = Blueprint("laporan", __name__)


# =========================================================
# HALAMAN LAPORAN
# =========================================================

@bp.route("/laporan")
@admin_required
@app_required
def laporan_page():

    conn = get_db()

    try:

        # =================================================
        # USER LOGIN
        # =================================================

        user_id = session.get("user_id")

        if not user_id:

            flash(
                "Sesi pengguna tidak ditemukan.",
                "danger"
            )

            return redirect(
                url_for("misc.dashboard")
            )

        # =================================================
        # FILTER BULAN / TAHUN
        # =================================================

        sekarang = datetime.now()

        try:
            bulan = int(
                request.args.get(
                    "bulan",
                    sekarang.month
                )
            )
        except (ValueError, TypeError):
            bulan = sekarang.month

        try:
            tahun = int(
                request.args.get(
                    "tahun",
                    sekarang.year
                )
            )
        except (ValueError, TypeError):
            tahun = sekarang.year


        if bulan < 1 or bulan > 12:
            bulan = sekarang.month

        bulan_db = str(bulan).zfill(2)

        if tahun < 2000 or tahun > 2100:
            tahun = sekarang.year

        # =================================================
        # NAMA BULAN
        # =================================================

        nama_bulan = [
            "",
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember",
        ]

        bulan_nama = nama_bulan[bulan]

        # =================================================
        # TOTAL PELANGGAN
        # =================================================

        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM pelanggan
            WHERE user_id = ?
        """, (user_id,))

        total_pelanggan = int(
            cur.fetchone()[0] or 0
        )

        # =================================================
        # LAPORAN TAGIHAN BULAN TERPILIH
        # =================================================

        cur.execute("""
            SELECT
                COUNT(*) AS jumlah,
                COALESCE(SUM(jumlah), 0) AS nominal
            FROM tagihan
            WHERE user_id = ?
              AND bulan = ?
              AND tahun = ?
        """, (
            user_id,
            bulan_db,
            tahun,
        ))

        row = cur.fetchone()

        total_tagihan = int(
            row["jumlah"] or 0
        )

        nominal_tagihan = int(
            row["nominal"] or 0
        )

        # =================================================
        # TAGIHAN LUNAS
        # =================================================

        cur.execute("""
            SELECT
                COUNT(*) AS jumlah,
                COALESCE(SUM(jumlah), 0) AS nominal
            FROM tagihan
            WHERE user_id = ?
              AND bulan = ?
              AND tahun = ?
              AND UPPER(
                    TRIM(
                        COALESCE(status, '')
                    )
                  ) IN (
                    'LUNAS',
                    'PAID',
                    'SUDAH BAYAR',
                    'SUDAH DIBAYAR'
                  )
        """, (
            user_id,
            bulan_db,
            tahun,
        ))

        row = cur.fetchone()

        jumlah_lunas = int(
            row["jumlah"] or 0
        )

        nominal_lunas = int(
            row["nominal"] or 0
        )

        # =================================================
        # TAGIHAN BELUM LUNAS
        # =================================================

        cur.execute("""
            SELECT
                COUNT(*) AS jumlah,
                COALESCE(SUM(jumlah), 0) AS nominal
            FROM tagihan
            WHERE user_id = ?
              AND bulan = ?
              AND tahun = ?
              AND UPPER(
                    TRIM(
                        COALESCE(status, '')
                    )
                  ) NOT IN (
                    'LUNAS',
                    'PAID',
                    'SUDAH BAYAR',
                    'SUDAH DIBAYAR'
                  )
        """, (
            user_id,
            bulan_db,
            tahun,
        ))

        row = cur.fetchone()

        jumlah_belum = int(
            row["jumlah"] or 0
        )

        nominal_belum = int(
            row["nominal"] or 0
        )

        # =================================================
        # TRANSAKSI BULAN TERPILIH
        #
        # Menggunakan tanggal_bayar jika tersedia.
        # =================================================

        cur.execute("""
            SELECT
                COUNT(*) AS jumlah,
                COALESCE(SUM(harga), 0) AS nominal
            FROM transaksi
            WHERE user_id = ?
              AND tanggal IS NOT NULL
              AND tanggal != ''
              AND (
                    substr(tanggal, 1, 4) = ?
                    AND substr(tanggal, 6, 2) = ?
                  )
        """, (
            user_id,
            str(tahun),
            str(bulan).zfill(2),
        ))

        row = cur.fetchone()

        total_transaksi = int(
            row["jumlah"] or 0
        )

        total_transaksi_nominal = int(
            row["nominal"] or 0
        )

        # =================================================
        # TRANSAKSI BERDASARKAN METODE
        # =================================================

        cur.execute("""
            SELECT
                COALESCE(
                    metode,
                    'Tidak diketahui'
                ) AS metode,

                COUNT(*) AS jumlah,

                COALESCE(
                    SUM(harga),
                    0
                ) AS nominal

            FROM transaksi

            WHERE user_id = ?

            GROUP BY metode

            ORDER BY nominal DESC
        """, (user_id,))

        metode_list = [
            dict(row)
            for row in cur.fetchall()
        ]

        # =================================================
        # LAPORAN TAHUNAN
        # =================================================

        laporan_tahunan = []

        for nomor_bulan in range(1, 13):

            cur.execute("""
                SELECT
                    COUNT(*) AS jumlah,
                    COALESCE(SUM(jumlah), 0) AS nominal
                FROM tagihan
                WHERE user_id = ?
                  AND bulan = ?
                  AND tahun = ?
            """, (
                user_id,
                str(nomor_bulan).zfill(2),
                tahun,
            ))

            row_tagihan = cur.fetchone()

            jumlah_tagihan_bulan = int(
                row_tagihan["jumlah"] or 0
            )

            nominal_tagihan_bulan = int(
                row_tagihan["nominal"] or 0
            )

            # ---------------------------------------------
            # LUNAS
            # ---------------------------------------------

            cur.execute("""
                SELECT
                    COUNT(*) AS jumlah,
                    COALESCE(SUM(jumlah), 0) AS nominal
                FROM tagihan
                WHERE user_id = ?
                  AND bulan = ?
                  AND tahun = ?
                  AND UPPER(
                        TRIM(
                            COALESCE(status, '')
                        )
                      ) IN (
                        'LUNAS',
                        'PAID',
                        'SUDAH BAYAR',
                        'SUDAH DIBAYAR'
                      )
            """, (
                user_id,
                str(nomor_bulan).zfill(2),
                tahun,
            ))

            row_lunas = cur.fetchone()

            jumlah_lunas_bulan = int(
                row_lunas["jumlah"] or 0
            )

            nominal_lunas_bulan = int(
                row_lunas["nominal"] or 0
            )

            laporan_tahunan.append({
                "bulan": nomor_bulan,
                "nama_bulan": nama_bulan[nomor_bulan],
                "jumlah_tagihan": jumlah_tagihan_bulan,
                "nominal_tagihan": nominal_tagihan_bulan,
                "jumlah_lunas": jumlah_lunas_bulan,
                "nominal_lunas": nominal_lunas_bulan,
                "jumlah_belum": (
                    jumlah_tagihan_bulan
                    - jumlah_lunas_bulan
                ),
                "nominal_belum": (
                    nominal_tagihan_bulan
                    - nominal_lunas_bulan
                ),
            })

        # =================================================
        # TOTAL TAHUNAN
        # =================================================

        total_tahunan_tagihan = sum(
            x["nominal_tagihan"]
            for x in laporan_tahunan
        )

        total_tahunan_lunas = sum(
            x["nominal_lunas"]
            for x in laporan_tahunan
        )

        total_tahunan_belum = sum(
            x["nominal_belum"]
            for x in laporan_tahunan
        )

        # =================================================
        # TAMPILKAN LAPORAN
        # =================================================

        return render_template(
            "laporan.html",

            # Filter
            bulan=bulan,
            tahun=tahun,
            bulan_nama=bulan_nama,

            # Pelanggan
            total_pelanggan=total_pelanggan,

            # Bulanan
            total_tagihan=total_tagihan,
            nominal_tagihan=nominal_tagihan,

            jumlah_lunas=jumlah_lunas,
            nominal_lunas=nominal_lunas,

            jumlah_belum=jumlah_belum,
            nominal_belum=nominal_belum,

            total_transaksi=total_transaksi,
            total_transaksi_nominal=(
                total_transaksi_nominal
            ),

            metode_list=metode_list,

            # Tahunan
            laporan_tahunan=laporan_tahunan,
            total_tahunan_tagihan=(
                total_tahunan_tagihan
            ),
            total_tahunan_lunas=(
                total_tahunan_lunas
            ),
            total_tahunan_belum=(
                total_tahunan_belum
            ),
        )

    except Exception as e:

        error_id = log_error(
            "laporan_page",
            e
        )

        flash(
            f"Gagal memuat laporan ({error_id})",
            "danger"
        )

        return redirect(
            url_for("misc.dashboard")
        )

    finally:

        release_db(conn)

