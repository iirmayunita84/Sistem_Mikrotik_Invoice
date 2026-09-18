# struk_pos.py
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import custom
import os

def buat_struk_pos(data, output="struk.pdf"):
    baris = [
        data["toko"],
        data["alamat"],
        "",
        f"Nama   : {data['nama']}",
        f"Paket  : {data['paket']}",
        f"Status : {data['status']}",
        "",
        "TAGIHAN",
        f"Rp {data['harga']:,}",
        "",
        "Scan QRIS untuk bayar",
        ""
    ]

    qr_height_mm = 45 if data.get("qris") else 0
    tinggi_mm = (len(baris) * 6) + qr_height_mm + 20

    PAGE_SIZE = custom(80 * mm, tinggi_mm * mm)
    c = canvas.Canvas(output, pagesize=PAGE_SIZE)
    width, height = PAGE_SIZE

    y = height - 10 * mm
    c.setFont("Helvetica", 9)

    # === TULIS TEKS ===
    for line in baris:
        c.drawCentredString(width / 2, y, line)
        y -= 6 * mm

    # === QRIS ===
    if data.get("qris") and os.path.exists(data["qris"]):
        qr_size = 45 * mm
        c.drawImage(
            data["qris"],
            (width - qr_size) / 2,
            y - qr_size,
            qr_size,
            qr_size,
            preserveAspectRatio=True
        )
        y -= qr_size + 5 * mm

    # === FOOTER ===
    c.drawCentredString(width / 2, y, "Terima kasih")
    y -= 6 * mm
    c.drawCentredString(width / 2, y, "Simpan struk ini")

    c.showPage()
    c.save()