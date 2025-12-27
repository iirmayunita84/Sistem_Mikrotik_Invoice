import os, sys, json
from datetime import datetime
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageWin
import win32print, win32ui

# ==================== CONFIG =====================
def resource_path(filename: str) -> str:
    if getattr(sys, "frozen", False):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, filename)

def load_config(config_filename="config.json") -> Dict[str, Any]:
    path = resource_path(config_filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

cfg = load_config()

# ==================== SETTING FONT =====================
FONT_BOLD  = ImageFont.truetype("arialbd.ttf", 28)
FONT_BODY  = ImageFont.truetype("consola.ttf", 26)  # monospace supaya titik dua sejajar
FONT_SMALL = ImageFont.truetype("arial.ttf", 22)

POS_WIDTH_MM = int(cfg["app"].get("pos_width_mm", 80))
DPI = 8   # 1mm ≈ 8px pada thermal 203dpi
POS_WIDTH_PX = POS_WIDTH_MM * DPI

# ==================== FORMAT RUPIAH =====================
def format_rupiah(angka: Any) -> str:
    try:
        return "Rp {:,}".format(int(angka)).replace(",", ".")
    except:
        return f"Rp {angka}"

# ==================== RENDER STRUK =====================
def render_struk(data: Dict[str, Any]) -> Image.Image:
    img = Image.new("L", (POS_WIDTH_PX, 2000), 255)
    draw = ImageDraw.Draw(img)
    y = 20

    # Logo
    logo_path = resource_path(cfg["app"].get("logo_file", "assets/logo.bmp"))
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("L")
        logo = logo.resize((250, 120))
        x = (POS_WIDTH_PX - logo.width) // 2
        img.paste(logo, (x, y))
        y += logo.height + 20

    # Judul
    title = "===== STRUK PEMBAYARAN ====="
    bbox = draw.textbbox((0, 0), title, font=FONT_BOLD)
    draw.text(((POS_WIDTH_PX - bbox[2]) // 2, y), title, font=FONT_BOLD, fill=0)
    y += 50

    # Detail
    details = [
        ("Nama", data.get("nama", "-")),
        ("IP MikroTik", data.get("ip_mikrotik", "-")),
        ("Paket", data.get("paket", "-")),
        ("Tagihan", format_rupiah(data.get("tagihan", "0"))),
        ("Usage", data.get("usage", "0MB/0MB")),
        ("No. HP", data.get("no_hp", "-")),
        ("Jatuh Tempo", data.get("jatuh_tempo", "-")),
        ("Tanggal", datetime.now().strftime("%d/%m/%Y")),
        ("Metode Bayar", data.get("metode", "Tunai")),
    ]
    for label, value in details:
        draw.text((20, y), f"{label:12}: {value}", font=FONT_BODY, fill=0)
        y += 40

    y += 10
    draw.line((20, y, POS_WIDTH_PX - 20, y), fill=0, width=2)
    y += 20

    # Footer
    footer_msg = cfg["app"].get("footer_message", "Terima kasih telah membayar.")
    for msg in footer_msg.split("\n"):
        bbox = draw.textbbox((0, 0), msg, font=FONT_SMALL)
        draw.text(((POS_WIDTH_PX - bbox[2]) // 2, y), msg, font=FONT_SMALL, fill=0)
        y += 30

    y += 20

    # QRIS
    qris_path = resource_path(cfg["app"].get("qris_file", "assets/qris.png"))
    if os.path.exists(qris_path):
        qr = Image.open(qris_path).convert("L")
        qr = qr.resize((250, 250))
        x = (POS_WIDTH_PX - qr.width) // 2
        img.paste(qr, (x, y))
        y += qr.height + 20
        msg = "Scan QRIS untuk pembayaran digital"
        bbox = draw.textbbox((0, 0), msg, font=FONT_SMALL)
        draw.text(((POS_WIDTH_PX - bbox[2]) // 2, y), msg, font=FONT_SMALL, fill=0)
        y += 40

    return img.crop((0, 0, POS_WIDTH_PX, y))

# ==================== PREVIEW STRUK =====================
def preview_struk(data: Dict[str, Any]):
    img = render_struk(data)

    top = tk.Toplevel()
    top.title("Preview Struk")

    max_width = 300
    scale = max_width / img.width
    new_size = (int(img.width * scale), int(img.height * scale))
    img_preview = img.resize(new_size, Image.LANCZOS)

    imgtk = ImageTk.PhotoImage(img_preview)
    lbl = tk.Label(top, image=imgtk)
    lbl.image = imgtk
    lbl.pack()

    btn = ttk.Button(top, text="🖨️ Cetak Struk Sekarang",
                     command=lambda: [cetak_struk_win32print(data), top.destroy()])
    btn.pack(pady=10)

# ==================== CETAK KE PRINTER =====================
def cetak_struk_win32print(data: Dict[str, Any], printer_name: Optional[str] = None):
    img = render_struk(data).convert("RGB")

    # Popup pilih printer jika tidak ada
    if not printer_name:
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )]

        def pilih():
            nonlocal printer_name
            printer_name = combo.get()
            win.destroy()

        win = tk.Toplevel()
        win.title("Pilih Printer")
        tk.Label(win, text="Pilih printer:", font=("Arial", 10)).pack(pady=5)
        combo = ttk.Combobox(win, values=printers, state="readonly", width=40)
        combo.pack(pady=5)
        if printers: combo.current(0)
        ttk.Button(win, text="OK", command=pilih).pack(pady=5)
        win.wait_window()
        if not printer_name: return

    try:
        hprinter = win32print.OpenPrinter(printer_name)
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)

        hdc.StartDoc("Struk Pembayaran")
        hdc.StartPage()

        dib = ImageWin.Dib(img)
        dib.draw(hdc.GetHandleOutput(), (0, 0, img.width, img.height))

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
        win32print.ClosePrinter(hprinter)

        messagebox.showinfo("Berhasil", f"✅ Struk dicetak ke {printer_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal cetak ke {printer_name}:\n{e}")

# ==================== MAIN APP =====================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Sistem Invoice MikroTik")

    sample_data = {
        "nama": "Budi Santoso",
        "ip_mikrotik": "192.168.2.10",
        "paket": "Internet 20Mbps",
        "tagihan": 150000,
        "usage": "2.3GB/10GB",
        "no_hp": "08123456789",
        "jatuh_tempo": "10/10/2025",
        "metode": "QRIS"
    }

    ttk.Button(root, text="👁️ Preview Struk", command=lambda: preview_struk(sample_data)).pack(pady=20)
    root.mainloop()
