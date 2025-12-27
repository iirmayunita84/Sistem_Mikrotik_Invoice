import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json, os, subprocess
import routeros_api


CONFIG_FILE = "config.json"


# ===== UTIL =====
def load_config():
    if not os.path.exists(CONFIG_FILE):
        messagebox.showerror("Error", "config.json tidak ditemukan!")
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    messagebox.showinfo("Sukses", "Pengaturan berhasil disimpan!")


def test_ping(host):
    try:
        hasil = subprocess.run(["ping", "-n", "1", host],
                               capture_output=True, text=True)
        return hasil.returncode == 0
    except:
        return False


def test_api(host, port, user, password):
    try:
        conn = routeros_api.RouterOsApiPool(
            host, username=user, password=password,
            port=port, plaintext_login=True
        )
        api = conn.get_api()
        api.get_resource('/system/resource').get()
        conn.disconnect()
        return True
    except:
        return False



# ======= UI DARK MODE GLASS BLUE =======
def open_settings_window(root):

    cfg = load_config()
    if cfg is None:
        return

    # WINDOW STYLE
    win = tb.Toplevel(title="🔧 Pengaturan Sistem",
                      resizable=(False, False))
                      
    win.geometry("760x640")

    # GLASS EFFECT (semi transparan)
    try:
        win.wm_attributes("-alpha", 0.95)
    except:
        pass

    # FRAME UTAMA (GLASS + ROUNDED)
    main = tb.Frame(win, padding=15, bootstyle="dark")
    main.pack(fill="both", expand=True)

    # JUDUL
    tb.Label(
        main,
        text="⚙ Dashboard Pengaturan",
        font=("Segoe UI", 20, "bold"),
        bootstyle="info"
    ).pack(pady=10)

    # NOTEBOOK (TAB)
    nb = tb.Notebook(main, bootstyle="info")
    nb.pack(fill="both", expand=True)

    # ================= APP SETTING =================
    tab_app = tb.Frame(nb, padding=20)
    nb.add(tab_app, text="📱 App Setting")

    def line(lbl):
        tb.Label(tab_app, text=lbl, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))

    line("Nama Toko")
    e_name = tb.Entry(tab_app)
    e_name.insert(0, cfg["app"]["store_name"])
    e_name.pack(fill="x")

    line("Alamat Toko")
    e_addr = tb.Entry(tab_app)
    e_addr.insert(0, cfg["app"]["store_address"])
    e_addr.pack(fill="x")

    line("Footer Struk")
    e_footer = tk.Text(tab_app, height=4)
    e_footer.insert("1.0", cfg["app"]["footer_message"])
    e_footer.pack(fill="x")

    # LOGO PICKER
    line("Logo File")

    fr_logo = tb.Frame(tab_app)
    fr_logo.pack(fill="x")

    e_logo = tb.Entry(fr_logo)
    e_logo.insert(0, cfg["app"]["logo_file"])
    e_logo.pack(side="left", fill="x", expand=True)

    tb.Button(fr_logo, text="Browse", bootstyle="info-outline",
              command=lambda: browse(e_logo)).pack(side="left", padx=5)

    # QRIS PICKER
    line("QRIS File")

    fr_qris = tb.Frame(tab_app)
    fr_qris.pack(fill="x")

    e_qris = tb.Entry(fr_qris)
    e_qris.insert(0, cfg["app"]["qris_file"])
    e_qris.pack(side="left", fill="x", expand=True)

    tb.Button(fr_qris, text="Browse", bootstyle="info-outline",
              command=lambda: browse(e_qris)).pack(side="left", padx=5)

    # ================= ROUTER SETTING =================
    tab_router = tb.Frame(nb, padding=20)
    nb.add(tab_router, text="🌐 Router Setting")

    routers = cfg["routers"]

    tb.Label(tab_router, text="Pilih Router", font=("Segoe UI", 10, "bold")).pack(anchor="w")

    router_var = tk.StringVar(value=routers[0]["label"])
    cb_router = tb.Combobox(tab_router, values=[r["label"] for r in routers],
                            textvariable=router_var, state="readonly")
    cb_router.pack(fill="x")

    # FIELDS
    def field(lbl):
        tb.Label(tab_router, text=lbl, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))

    field("Host / IP")
    e_host = tb.Entry(tab_router)
    field("Port API")
    e_port = tb.Entry(tab_router)
    field("Username")
    e_user = tb.Entry(tab_router)
    field("Password")
    e_pass = tb.Entry(tab_router, show="*")

    def load_router(i):
        r = routers[i]
        e_host.delete(0, tk.END); e_host.insert(0, r["host"])
        e_port.delete(0, tk.END); e_port.insert(0, r["port"])
        e_user.delete(0, tk.END); e_user.insert(0, r["username"])
        e_pass.delete(0, tk.END); e_pass.insert(0, r["password"])

    load_router(0)

    e_host.pack(fill="x")
    e_port.pack(fill="x")
    e_user.pack(fill="x")
    e_pass.pack(fill="x")

    def router_changed(event):
        load_router(cb_router.current())

    cb_router.bind("<<ComboboxSelected>>", router_changed)

    # TEST BUTTON
    def test_conn():
        host = e_host.get()
        port = int(e_port.get())
        user = e_user.get()
        psw = e_pass.get()

        ping = test_ping(host)
        api = test_api(host, port, user, psw)

        msg = f"""
Ping: {'✔ OK' if ping else '❌ Gagal'}
API Login: {'✔ Terhubung' if api else '❌ Gagal'}
"""
        messagebox.showinfo("Hasil Test", msg)

    tb.Button(
        tab_router, text="🔍 Test Koneksi",
        bootstyle="info", padding=10,
        command=test_conn
    ).pack(pady=20)

    # ============ SAVE BUTTON ============
    def save_all():
        idx = cb_router.current()

        cfg["app"]["store_name"] = e_name.get()
        cfg["app"]["store_address"] = e_addr.get()
        cfg["app"]["footer_message"] = e_footer.get("1.0", "end").strip()
        cfg["app"]["logo_file"] = e_logo.get()
        cfg["app"]["qris_file"] = e_qris.get()

        cfg["routers"][idx]["host"] = e_host.get()
        cfg["routers"][idx]["port"] = int(e_port.get())
        cfg["routers"][idx]["username"] = e_user.get()
        cfg["routers"][idx]["password"] = e_pass.get()

        save_config(cfg)

    tb.Button(
        win, text="💾 Simpan Semua",
        bootstyle="success", padding=10,
        command=save_all
    ).pack(pady=10)


def browse(entry):
    f = filedialog.askopenfilename(filetypes=[("Gambar", "*.png;*.jpg;*.bmp")])
    if f:
        entry.delete(0, tk.END)
        entry.insert(0, f)
