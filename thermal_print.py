# thermal_print.py
import win32print
import win32ui
from PIL import Image, ImageWin

def cetak_thermal(data):
    printer_name = win32print.GetDefaultPrinter()

    hprinter = win32print.OpenPrinter(printer_name)
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)

    hdc.StartDoc("Struk Pembayaran")
    hdc.StartPage()

    y = 10
    line_height = 30

    def text(txt, size=24, bold=False):
        nonlocal y
        font = win32ui.CreateFont({
            "name": "Courier New",
            "height": size,
            "weight": 700 if bold else 400
        })
        hdc.SelectObject(font)
        hdc.TextOut(10, y, txt)
        y += line_height

    # ===== HEADER =====
    text(data["toko"], 32, True)
    text(data["alamat"])
    text("-" * 32)

    # ===== DATA =====
    text(f"Nama   : {data['nama']}")
    text(f"Paket  : {data['paket']}")
    text(f"Status : {data['status']}")
    text("-" * 32)

    text("TOTAL", 28, True)
    text(f"Rp {data['harga']:,}", 28, True)

    text("")
    text("Scan QRIS untuk bayar")

    # ===== QRIS =====
    if data.get("qris"):
        img = Image.open(data["qris"])
        img = img.resize((280, 280))  # pas 80mm

        dib = ImageWin.Dib(img)
        dib.draw(hdc.GetHandleOutput(), (10, y, 290, y + 280))
        y += 300

    text("")
    text("Terima kasih")
    text("Simpan struk ini")

    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()
    win32print.ClosePrinter(hprinter)