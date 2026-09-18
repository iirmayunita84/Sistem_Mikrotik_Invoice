# services/pdf_service.py
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os


def rupiah(val):
    try:
        return f"Rp {int(val):,}".replace(",", ".")
    except:
        return "Rp 0"

def generate_invoice_pdf(pelanggan: dict, app_cfg: dict) -> BytesIO:
    """
    Generate PDF invoice (A4)
    Return: BytesIO buffer
    """

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # =========================
    # HEADER
    # =========================
    y = height - 30 * mm

    # LOGO (optional)
    logo_path = app_cfg.get("logo_file")
    if logo_path:
        logo_path = logo_path.lstrip("/")
        if os.path.exists(logo_path):
            c.drawImage(
                ImageReader(logo_path),
                20 * mm,
                y - 10 * mm,
                width=30 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(
        width - 20 * mm,
        y,
        app_cfg.get("store_name", "MIKROTIK INVOICE")
    )

    c.setFont("Helvetica", 9)
    c.drawRightString(
        width - 20 * mm,
        y - 5 * mm,
        app_cfg.get("store_address", "")
    )

    # =========================
    # INVOICE META
    # =========================
    y -= 25 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "INVOICE")

    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y - 6 * mm, f"No: {pelanggan.get('invoice_no','-')}")
    c.drawString(
        20 * mm,
        y - 11 * mm,
        f"Tanggal: {pelanggan.get('invoice_time', datetime.now().strftime('%d-%m-%Y %H:%M'))}"
    )

    # =========================
    # DATA PELANGGAN
    # =========================
    y -= 25 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Ditagihkan kepada:")

    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y - 6 * mm, f"Nama   : {pelanggan.get('nama','')}")
    c.drawString(20 * mm, y - 11 * mm, f"Paket  : {pelanggan.get('paket','')}")
    c.drawString(20 * mm, y - 16 * mm, f"Status : {pelanggan.get('status','')}")

    # =========================
    # TABEL TAGIHAN
    # =========================
    y -= 30 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Deskripsi")
    c.drawRightString(width - 20 * mm, y, "Jumlah")

    c.line(20 * mm, y - 2, width - 20 * mm, y - 2)

    c.setFont("Helvetica", 9)
    c.drawString(
        20 * mm,
        y - 10 * mm,
        f"Layanan Internet ({pelanggan.get('paket','')})"
    )
    c.drawRightString(
        width - 20 * mm,
        y - 10 * mm,
        rupiah(pelanggan.get("harga", 0))
    )

    # =========================
    # TOTAL
    # =========================
    y -= 25 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(
        width - 20 * mm,
        y,
        f"TOTAL: {rupiah(pelanggan.get('harga', 0))}"
    )

    # =========================
    # QRIS (optional)
    # =========================
    qris_path = app_cfg.get("qris_file")
    if qris_path:
        qris_path = qris_path.lstrip("/")
        if os.path.exists(qris_path):
            c.drawImage(
                ImageReader(qris_path),
                20 * mm,
                y - 45 * mm,
                width=35 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )
            c.setFont("Helvetica", 8)
            c.drawString(20 * mm, y - 50 * mm, "Scan untuk bayar")

    # =========================
    # FOOTER
    # =========================
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(
        width / 2,
        15 * mm,
        app_cfg.get("footer_message", "Terima kasih atas pembayaran Anda")
    )

    c.showPage()
    c.save()
    buffer.seek(0)

    return buffer