# core\billing_core.py
import qrcode
from PIL import Image, ImageWin
import textwrap
from datetime import datetime, date
from routeros_api import RouterOsApiPool
import win32print
import win32ui
from core.db import get_db
from services.wa_service import kirim_dan_log
from core.mikrotik_api import get_router_by_id,set_pppoe_status



def get_transaksi():
    ensure_json_file(TRANSAKSI_FILE, {"transaksi": []})

    try:
        with open(TRANSAKSI_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("transaksi", [])
    except:
        return []

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
        logo_path = app.get("logo_path")

        if logo_path and os.path.exists(logo_path):
            try:
                im = Image.open(logo_path)
                im = im.resize((200, 100))

                hdc = win32ui.CreateDC()
                hdc.CreatePrinterDC(printer_name)

                ImageWin.Dib(im).draw(
                    hdc.GetHandleOutput(),
                    (0, 0, 200, 100)
                )
            except:
                pass

        # ===== HEADER =====
        p(app.get("store_name", "ISP INTERNET"))
        p(app.get("store_address", ""))
        p("="*32)

        # ===== DATA CUSTOMER =====
        p(f"User ID : {pelanggan.get('id','')}")
        p(f"Nama    : {pelanggan.get('nama','')}")
        p(f"Paket   : {pelanggan.get('paket','')}")

        # Tambah tanggal bayar hari ini
        p(f"Tgl Bayar: {datetime.now().strftime('%d-%m-%Y')}")

        p(f"Status  : {pelanggan.get('status','')}")
        p("-"*32)

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