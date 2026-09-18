import re
import os
from datetime import datetime
from io import BytesIO

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    current_app,
)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.utils import ImageReader

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.error_helper import log_error

from core.core_pelanggan import (
    get_pelanggan_by_id,
)

from core.config_core import (
    get_app_config,
)

from core.decorators import (
    admin_required,
    app_required,
    premium_required,
)


bp = Blueprint(
    "invoice",
    __name__
)


# ==========================================================
# FONT PDF
# ==========================================================

FONT_NAME = "JetBrainsMono"

FONT_FILE = os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ),
    "static",
    "JetBrainsMono-Regular.ttf"
)


try:

    pdfmetrics.registerFont(
        TTFont(
            FONT_NAME,
            FONT_FILE
        )
    )

except Exception:

    FONT_NAME = "Helvetica"


# ==========================================================
# INVOICE HTML
# ==========================================================
@bp.route("/invoice/<pid>")
@admin_required
@app_required
def invoice(pid):

    user_id = session["user_id"]

    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )

    if not pelanggan:
        flash(
            "Data pelanggan tidak ditemukan",
            "danger"
        )

        return redirect(
            url_for("pelanggan.pelanggan_page")
        )

    app_cfg = get_app_config(user_id)

    pelanggan = siapkan_data_invoice(pelanggan)

    return render_template(
        "invoice.html",
        pelanggan=pelanggan,
        app=app_cfg,
        tanggal_bayar=pelanggan.get(
            "tanggal_bayar_invoice",
            "-"
        )
    )
# ==========================================================
# PDF INVOICE
# ==========================================================
def cek_halaman(c, y, tinggi=60):

    if y < tinggi:

        c.showPage()

        c.setFont(
            FONT_NAME,
            10
        )

        return A5[1] - 40

    return y

@bp.route("/invoice/pdf/<pid>")
@admin_required
@premium_required
def cetak_pdf(pid):

    user_id = session["user_id"]

    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )
    pelanggan = siapkan_data_invoice(pelanggan)

    if not pelanggan:

        flash(
            "Data tidak ditemukan",
            "danger"
        )

        return redirect(
            url_for("pelanggan.pelanggan_page")
        )

    app_cfg = get_app_config(
        user_id
    )

    # ======================================================
    # DATA INVOICE
    # ======================================================

    pelanggan = dict(pelanggan)

    status_invoice = (
        pelanggan.get("status")
        or "BELUM BAYAR"
    ).upper()

    pppoe_username = (
        pelanggan.get("pppoe_username")
        or "-"
    )

    ip_address = (
        pelanggan.get("ip_address")
        or "-"
    )

    no_hp = (
        pelanggan.get("no_hp")
        or "-"
    )

    jatuh_tempo = (
        pelanggan.get("jatuh_tempo")
        or "-"
    )

    buffer = BytesIO()

    c = canvas.Canvas(
        buffer,
        pagesize=A5
    )

    w, h = A5

    y = h - 40


    # ======================================================
    # LOGO
    # ======================================================

    logo = app_cfg.get(
        "logo_file"
    )

    if logo:

        logo_full = os.path.join(
            current_app.config.get(
                "UPLOAD_FOLDER",
                ""
            ),
            logo
        )

        if os.path.isfile(logo_full):

            try:

                c.drawImage(
                    ImageReader(
                        logo_full
                    ),
                    w / 2 - 40,
                    y - 60,
                    width=80,
                    height=60,
                    preserveAspectRatio=True,
                    mask="auto"
                )

                y -= 75

            except Exception as e:

                log_error(
                    "logo_pdf",
                    e
                )


    # ======================================================
    # HEADER
    # ======================================================

    c.setFont(
        FONT_NAME,
        18
    )

    c.drawCentredString(
        w / 2,
        y,
        "INVOICE PEMBAYARAN"
    )

    y -= 30


    invoice_no = (
        datetime.now().strftime("%Y%m%d")
        + "-"
        + str(
            pelanggan["id"]
        )[-4:]
    )


    c.setFont(
        FONT_NAME,
        10
    )

    c.drawString(
        40,
        y,
        f"No Invoice : {invoice_no}"
    )

    y -= 25


    # ======================================================
    # DATA
    # ======================================================

    fields = [

        f"ID           : {pelanggan.get('id', '')}",

        f"Nama         : {pelanggan.get('nama', '')}",

        f"Paket        : {pelanggan.get('paket', '')}",

        f"Status       : {pelanggan.get('status_invoice', '')}",

        f"Jatuh Tempo  : {pelanggan.get('jatuh_tempo_invoice', '-')}",

        f"Tanggal Bayar: {pelanggan.get('tanggal_bayar_invoice', '-')}",

        f"Pemakaian    : {pelanggan.get('usage_invoice', '0GB')}",

        f"PPPoE        : {pelanggan.get('pppoe_invoice', '-')}",

        f"IP           : {pelanggan.get('ip_invoice', '-')}",

        f"No HP        : {pelanggan.get('no_hp_invoice', '-')}",

    ]

    line_height = 18


    for item in fields:

        y = cek_halaman(
            c,
            y
        )

        c.drawString(
            40,
            y,
            item
        )

        y -= line_height


    # ======================================================
    # TOTAL
    # ======================================================

    harga = (
        f"Rp {int(pelanggan.get('harga', 0)):,}"
        .replace(",", ".")
    )

    y -= 10

    c.setFont(
        FONT_NAME,
        14
    )

    c.drawCentredString(
        w / 2,
        y,
        "TOTAL PEMBAYARAN"
    )

    y -= 25

    c.setFont(
        FONT_NAME,
        20
    )

    c.drawCentredString(
        w / 2,
        y,
        harga
    )

    y -= 30

    c.line(
        30,
        y,
        w - 30,
        y
    )

    y -= 25


    # ======================================================
    # QRIS
    # ======================================================

    qris = app_cfg.get(
        "qris_file"
    )

    if qris:

        qris_full = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            qris
        )

        if os.path.isfile(qris_full):

            try:

                QR = 120

                y = cek_halaman(
                    c,
                    y,
                    QR + 50
                )

                c.drawImage(
                    ImageReader(
                        qris_full
                    ),
                    w / 2 - QR / 2,
                    y - QR,
                    width=QR,
                    height=QR,
                    preserveAspectRatio=True,
                    mask="auto"
                )

                y -= QR + 15

                c.setFont(
                    FONT_NAME,
                    9
                )

                c.drawCentredString(
                    w / 2,
                    y,
                    "Scan QRIS untuk pembayaran"
                )

                y -= 20

            except Exception as e:

                log_error(
                    "qris_pdf",
                    e
                )


    # ======================================================
    # FOOTER
    # ======================================================

    footer = app_cfg.get(
        "footer_message",
        ""
    )

    c.setFont(
        FONT_NAME,
        8
    )

    for line in footer.splitlines():

        y = cek_halaman(
            c,
            y
        )

        c.drawCentredString(
            w / 2,
            y,
            line
        )

        y -= 12


    c.showPage()
    c.save()

    buffer.seek(0)


    nama = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        pelanggan["nama"]
    )


    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_{nama}.pdf",
        mimetype="application/pdf"
    )

# ==========================================================
# THERMAL 80MM
# ==========================================================
@bp.route("/print-thermal/<pid>")
@admin_required
@app_required
def print_thermal(pid):

    user_id = session["user_id"]

    pelanggan = get_pelanggan_by_id(
        pid,
        user_id
    )

    if not pelanggan:
        flash(
            "Data pelanggan tidak ditemukan",
            "danger"
        )

        return redirect(
            url_for("pelanggan.pelanggan_page")
        )

    app_cfg = get_app_config(user_id)

    # ==========================================
    # UBAH KE DICT
    # ==========================================

    pelanggan = dict(pelanggan)

    # ==========================================
    # STATUS
    # ==========================================

    if str(pelanggan.get("status", "")).upper() != "LUNAS":
        pelanggan["status"] = "LUNAS"

    # ==========================================
    # TANGGAL BAYAR
    # AMBIL DARI DATABASE
    # BUKAN datetime.now()
    # ==========================================

    pelanggan["tanggal_bayar"] = (
        pelanggan.get("tanggal_bayar")
        or "-"
    )

    # ==========================================
    # CETAK STRUK
    # ==========================================

    return render_template(
        "invoice.html",
        pelanggan=pelanggan,
        app=app_cfg
    )

def siapkan_data_invoice(pelanggan):

    pelanggan = dict(pelanggan)

    # STATUS
    pelanggan["status_invoice"] = (
        pelanggan.get("status")
        or "BELUM BAYAR"
    ).upper()

    # PPPoE
    pelanggan["pppoe_invoice"] = (
        pelanggan.get("pppoe_username")
        or "-"
    )

    # IP
    pelanggan["ip_invoice"] = (
        pelanggan.get("ip_address")
        or "-"
    )

    # NO HP
    pelanggan["no_hp_invoice"] = (
        pelanggan.get("no_hp")
        or "-"
    )

    # JATUH TEMPO
    pelanggan["jatuh_tempo_invoice"] = (
        pelanggan.get("jatuh_tempo")
        or "-"
    )

    # TANGGAL BAYAR
    pelanggan["tanggal_bayar_invoice"] = (
        pelanggan.get("tanggal_bayar")
        or "-"
    )

    # PEMAKAIAN
    usage = (
        pelanggan.get("usage")
        or pelanggan.get("usage_last")
        or "0GB"
    )

    if str(usage).lower() in (
        "none",
        "",
        "-",
        "null"
    ):
        usage = "0GB"

    pelanggan["usage_invoice"] = str(usage)

    return pelanggan