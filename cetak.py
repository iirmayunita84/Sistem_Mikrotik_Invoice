# file: cetak.py
from flask import send_file
from reportlab.pdfgen import canvas
import os
import tempfile

# Optional: ESC/POS printer (install dulu pip install python-escpos)
try:
    from escpos.printer import Usb
    ESC_POS_AVAILABLE = True
except ImportError:
    ESC_POS_AVAILABLE = False

def cetak_struk(pelanggan, ke_printer=False):
    """
    Cetak struk pelanggan
    - pelanggan: dict atau object pelanggan
    - ke_printer: True jika ingin langsung ke printer ESC/POS
    """
    # Ambil data
    nama = getattr(pelanggan, "nama", pelanggan.get("nama", ""))
    paket = getattr(pelanggan, "paket", pelanggan.get("paket", ""))
    harga = getattr(pelanggan, "harga", pelanggan.get("harga", 0))
    jatuh_tempo = getattr(pelanggan, "jatuh_tempo", pelanggan.get("jatuh_tempo", ""))
    no_hp = getattr(pelanggan, "no_hp", pelanggan.get("no_hp", ""))
    
    # Buat PDF sementara
    tmp_dir = tempfile.gettempdir()
    filename = os.path.join(tmp_dir, f"struk_{nama}.pdf")
    c = canvas.Canvas(filename, pagesize=(200, 250))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(10, 230, f"Nama      : {nama}")
    c.drawString(10, 215, f"Paket     : {paket}")
    c.drawString(10, 200, f"Harga     : Rp {harga:,}")
    c.drawString(10, 185, f"Jatuh Tempo: {jatuh_tempo}")
    c.drawString(10, 170, f"No HP     : {no_hp}")
    c.drawString(10, 150, "Terima kasih!")
    
    c.showPage()
    c.save()

    # Jika ingin cetak ke printer ESC/POS
    if ke_printer:
        if not ESC_POS_AVAILABLE:
            print("Library python-escpos belum diinstall!")
        else:
            try:
                p = Usb(0x04b8, 0x0202)  # Ganti sesuai printer kamu
                p.text(f"Nama      : {nama}\n")
                p.text(f"Paket     : {paket}\n")
                p.text(f"Harga     : Rp {harga:,}\n")
                p.text(f"Jatuh Tempo: {jatuh_tempo}\n")
                p.text(f"No HP     : {no_hp}\n")
                p.text("\nTerima kasih!\n")
                p.cut()
            except Exception as e:
                print("Gagal cetak ke printer:", e)

    # Kirim PDF ke browser
    return send_file(filename, as_attachment=True, download_name=f"struk_{nama}.pdf")