import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageWin
import win32print, win32ui

# === Import dari utils_config ===
from utils_config import (
    load_config,
    get_logo_path,
    get_qris_path,
    get_store_info,
    get_pos_width,
    ensure_riwayat_dir
)

# ==== Load config global ====
cfg = load_config()
POS_WIDTH_PX = get_pos_width(cfg) * 8  # 1 mm ~ 8 px untuk thermal printer

# ==== Fonts ====
FONT_BOLD  = ImageFont.truetype("arialbd.ttf", 28)
FONT_BODY  = ImageFont.truetype("consola.ttf", 26)
FONT_SMALL = ImageFont.truetype("arial.ttf", 22)

# ==== Helper format rupiah ====
def format_rupiah(angka):
    try:
        angka = int(angka)
    except:
        angka = 0
    return f"Rp {angka:,.0f}".replace(",", ".")

# ==== Render Struk ====
def render_struk(data):
    img = Image.new("L", (POS_WIDTH_PX, 2000), 255)
    draw = ImageDraw.Draw(img)
    y = 20

    # --- Logo ---
    logo_path = get_logo_path(cfg)
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("L")
        logo = logo.resize((260, 120))
        x = (POS_WIDTH_PX - logo.width) // 2
        img.paste(logo, (x, y))
        y += logo.height + 20

    # --- Judul ---
    title = "===== STRUK PEMBAYARAN ====="
    bbox = draw.textbbox((0, 0), title, font=FONT_BOLD)
    draw.text(((POS_WIDTH_PX - bbox[2]) // 2, y), title, font=FONT_BOLD, fill=0)
    y += 60

    # --- Data Pelanggan ---
    details = [
        ("Nama", data.get("nama", "-")),
        ("IP MikroTik", data.get("ip_mikrotik", "-")),
        ("Paket", data.get("paket", "-")),
        ("Tagihan", format_rupiah(data.get("tagihan", "0"))),
        ("Usage", data.get("usage", "-")),
        ("No. HP", data.get("no_hp", "-")),
        ("Jatuh Tempo", data.get("jatuh_tempo", "-")),
        ("Tanggal", datetime.now().strftime("%d/%m/%Y")),
        ("Metode Bayar", data.get("metode", "Tunai")),
    ]

    for label, value in details:
        draw.text((30, y), f"{label:12}:", font=FONT_BODY, fill=0)
        draw.text((300, y), str(value), font=FONT_BODY, fill=0)
        y += 45

    # Garis pemisah
    y += 10
    draw.line((20, y, POS_WIDTH_PX - 20, y), fill=0, width=2)
    y += 30

    # --- Footer (ambil dari config.json) ---
    store_info = get_store_info(cfg)
    footer_lines = [
        store_info.get("footer", "Terima kasih telah membayar tepat waktu."),
        f"Alamat: {store_info.get('address', '-')}"
    ]
    for msg in footer_lines:
        bbox = draw.textbbox((0, 0), msg, font=FONT_SMALL)
        draw.text(((POS_WIDTH_PX - bbox[2]) // 2, y), msg, font=FONT_SMALL, fill=0)
        y += 35

    # --- QRIS ---
    qris_path = get_qris_path(cfg)
    if os.path.exists(qris_path):
        qr = Image.open(qris_path).convert("L")
        qr = qr.resize((260, 260))
        x = (POS_WIDTH_PX - qr.width) // 2
        img.paste(qr, (x, y))
        y += qr.height + 20

    return img.crop((0, 0, POS_WIDTH_PX, y))

# ==== Preview Struk di Tkinter ====
def preview_struk(data):
    img = render_struk(data)
    max_width = 350
    scale = max_width / img.width
    new_size = (int(img.width * scale), int(img.height * scale))
    img_preview = img.resize(new_size, Image.LANCZOS)

    top = tk.Toplevel()
    top.title("Preview Struk")

    imgtk = ImageTk.PhotoImage(img_preview)
    label = tk.Label(top, image=imgtk)
    label.image = imgtk
    label.pack()

    btn_cetak = ttk.Button(top, text="🖨️ Cetak Struk Sekarang",
                           command=lambda: [cetak_struk_win32print(data), top.destroy()])
    btn_cetak.pack(pady=10)

# ==== Cetak ke Printer (Win32) ====
def cetak_struk_win32print(data, printer_name=None):
    img = render_struk(data).convert("RGB")

    if not printer_name:
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )]

        def pilih_printer():
            nonlocal printer_name
            printer_name = combo.get()
            win.destroy()

        win = tk.Toplevel()
        win.title("Pilih Printer")
        win.geometry("350x120")
        tk.Label(win, text="Pilih printer:", font=("Arial", 10)).pack(pady=5)

        combo = ttk.Combobox(win, values=printers, state="readonly", width=40)
        combo.pack(pady=5)
        if printers:
            combo.current(0)

        btn_ok = ttk.Button(win, text="OK", command=pilih_printer)
        btn_ok.pack(pady=5)
        win.wait_window()

        if not printer_name:
            print("[INFO] Cetak dibatalkan.")
            return

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

        messagebox.showinfo("Berhasil", f"✅ Struk berhasil dicetak ke {printer_name}")
        print(f"[INFO] Struk berhasil dicetak ke {printer_name}")

    except Exception as e:
        messagebox.showerror("Error", f"Gagal cetak ke {printer_name}:\n{e}")
        print(f"[ERROR] Gagal cetak ke {printer_name}: {e}")
