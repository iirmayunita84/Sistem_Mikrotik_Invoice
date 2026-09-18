import os
import textwrap
from datetime import datetime

import win32print
import win32ui

from PIL import Image, ImageWin

from flask import send_file
from reportlab.pdfgen import canvas

# Optional: ESC/POS printer
try:
    from escpos.printer import Usb
    ESC_POS_AVAILABLE = True
except ImportError:
    ESC_POS_AVAILABLE = False

def cetak_struk_80mm(pelanggan, app):
    printer_name = win32print.GetDefaultPrinter()

    hprinter = win32print.OpenPrinter(printer_name)

    try:
        win32print.StartDocPrinter(hprinter, 1, ("Struk", None, "RAW"))
        win32print.StartPagePrinter(hprinter)

        def p(text=""):
            # Auto wrap 32 karakter (80mm POS standard)
            wrapped = textwrap.fill(str(text), width=32)
            for line in wrapped.split("\n"):
                win32print.WritePrinter(
                    hprinter,
                    (line + "\n").encode("utf-8")
                )

        # ===== RESET PRINTER =====
        win32print.WritePrinter(hprinter, b"\x1b\x40")

        # ===== LOGO PRINT =====
        logo_file = app.get("logo_file")

        logo_path = None

        if logo_file:
            logo_path = os.path.join(
                app.get("UPLOAD_FOLDER", ""),
                logo_file
            )

        if logo_path and os.path.isfile(logo_path):
            try:
                im = Image.open(logo_path)
                im.thumbnail((220, 120))

                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)

                ImageWin.Dib(im).draw(
                    hdc.GetHandleOutput(),
                    (0, 0, im.width, im.height)
                )

            except Exception:
                pass

        # ===== HEADER =====
        p(app.get("store_name", "ISP INTERNET"))
        p(app.get("store_address", ""))
        p("="*32)

        # ===== DATA CUSTOMER =====
        p(f"User ID : {pelanggan.get('id', '')}")
        p(f"Nama    : {pelanggan.get('nama', '')}")
        p(f"Paket   : {pelanggan.get('paket', '')}")

        p(f"Tgl Bayar: {datetime.now().strftime('%d-%m-%Y')}")

        # Struk ini hanya dipanggil setelah pembayaran berhasil
        p("Status  : LUNAS")

        p("-" * 32)

        # ===== TOTAL =====
        win32print.WritePrinter(
            hprinter,
            b"\x1b\x45\x01"
        )

        harga = f"{pelanggan.get('harga',0):,}".replace(",", ".")
        p(f"TOTAL : Rp {harga}")

        win32print.WritePrinter(
            hprinter,
            b"\x1b\x45\x00"
        )

        p("="*32)

        # ===== FOOTER =====
        for line in app.get("footer_message","").split("\n"):
            p(line)

        p("\n\n")

        # CUT PAPER
        win32print.WritePrinter(
            hprinter,
            b"\x1d\x56\x42\x00"
        )

        win32print.EndPagePrinter(hprinter)
        win32print.EndDocPrinter(hprinter)

    finally:
        win32print.ClosePrinter(hprinter)