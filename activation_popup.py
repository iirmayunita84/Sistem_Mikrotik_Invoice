# activation_popup.py
import tkinter as tk
from tkinter import messagebox
import os, sys
import webbrowser
import urllib.parse

from license_core import (
    get_device_id,
    generate_license,
    save_license
)

def open_shopee():
    device_id = get_device_id()
    pesan = f"Halo Admin, saya mau beli license.%0ADevice ID:%0A{device_id}"

    link = (
        "https://shopee.co.id/"
        "Software-Billing-Wifi-Mikrotik-Auto-Tagihan-"
        "Cetak-Struk-Thermal-80mm-Installer-"
        "khusus-Windows-10-11-"
        "i.92697971.48601034359"
    )

    url = link + "?msg=" + urllib.parse.quote(pesan)
    webbrowser.open(url)

def open_whatsapp_admin(device_id):
    nomor_admin = "6282116090241"  # TANPA +
    pesan = (
        "Halo Admin 👋\n"
        "Saya mau aktivasi aplikasi.\n\n"
        f"Device ID:\n{device_id}"
    )

    url = (
        f"https://wa.me/{nomor_admin}"
        f"?text={urllib.parse.quote(pesan)}"
    )

    webbrowser.open(url)

def show_activation_popup(days_left=0):
    device_id = get_device_id()

    root = tk.Tk()
    root.title("Aktivasi Aplikasi")
    root.geometry("480x360")
    root.resizable(False, False)

    if days_left > 0:
        tk.Label(
            root,
            text=f"⏳ Trial aktif, sisa {days_left} hari",
            fg="orange"
        ).pack(pady=5)

    # DEVICE ID
    tk.Label(root, text="DEVICE ID").pack()
    e = tk.Entry(root, width=60, justify="center")
    e.insert(0, device_id)
    e.config(state="readonly")
    e.pack(pady=5)

    def copy_id():
        root.clipboard_clear()
        root.clipboard_append(device_id)
        messagebox.showinfo("Copied", "✅ Device ID disalin")

    tk.Button(root, text="📋 Copy Device ID", command=copy_id).pack(pady=5)

    # LICENSE INPUT
    tk.Label(root, text="Masukkan License Key").pack(pady=5)
    lic = tk.Entry(root, width=60)
    lic.pack()

    # AKTIVASI
    def activate():
        key = lic.get().strip()
        if not key:
            messagebox.showwarning("Kosong", "License belum diisi")
            return

        if key == generate_license(device_id):
            save_license(key)
            messagebox.showinfo(
                "Sukses",
                "✅ Aktivasi berhasil\nAplikasi akan restart"
            )
            root.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            messagebox.showerror("Gagal", "❌ License tidak valid")

    tk.Button(
        root,
        text="🔓 AKTIVASI",
        width=30,
        command=activate
    ).pack(pady=8)

    # BELI LICENSE
    tk.Button(
        root,
        text="🛒 BELI LICENSE SEKARANG",
        width=30,
        command=open_shopee
    ).pack(pady=5)

    root.mainloop()