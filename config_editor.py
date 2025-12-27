import os, json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import win32print
from librouteros import connect

CONFIG_FILE = "config.json"

# ===================== LOAD & SAVE =====================
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"app": {}, "routers": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ===================== FILE / FOLDER PICKER =====================
def pilih_file(entry, tipe):
    path = filedialog.askopenfilename(title=f"Pilih file {tipe}",
                                      filetypes=[("Gambar", "*.png *.jpg *.bmp *.gif"), ("Semua File", "*.*")])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

def pilih_folder(entry_var):
    path = filedialog.askdirectory()
    if path:
        entry_var.set(path)

# ===================== APP SETTING =====================
def open_app_setting(parent):
    cfg = load_config()
    win = tk.Toplevel(parent)
    win.title("⚙️ App Setting")
    win.geometry("500x450")

    tk.Label(win, text="⚙️ Pengaturan Aplikasi", font=("Arial", 14, "bold"), fg="darkgreen").pack(pady=10)

    fields = {
        "Nama Toko": cfg["app"].get("store_name",""),
        "Alamat": cfg["app"].get("store_address",""),
        "Pesan Footer": cfg["app"].get("footer_message",""),
        "Logo File": cfg["app"].get("logo_file",""),
        "QRIS File": cfg["app"].get("qris_file",""),
        "POS Width": str(cfg["app"].get("pos_width_mm",80))
    }

    entries = {}
    for lbl, val in fields.items():
        tk.Label(win, text=lbl+":", font=("Arial",10,"bold")).pack(anchor="w", pady=2)
        ent = tk.Entry(win, width=50)
        ent.insert(0,val)
        ent.pack(pady=2)
        entries[lbl] = ent
        if "File" in lbl:
            tk.Button(win, text="📂 Browse", bg="lightblue", font=("Arial",9,"bold"),
                      command=lambda e=ent,l=lbl: pilih_file(e,l.lower())).pack(pady=2)

    def simpan_app():
        cfg["app"]["store_name"] = entries["Nama Toko"].get()
        cfg["app"]["store_address"] = entries["Alamat"].get()
        cfg["app"]["footer_message"] = entries["Pesan Footer"].get()
        cfg["app"]["logo_file"] = entries["Logo File"].get()
        cfg["app"]["qris_file"] = entries["QRIS File"].get()
        cfg["app"]["pos_width_mm"] = int(entries["POS Width"].get() or 80)
        save_config(cfg)
        messagebox.showinfo("Berhasil","✅ App Setting berhasil disimpan!")

    tk.Button(win, text="💾 Simpan App Setting", bg="green", fg="white", font=("Arial",10,"bold"),
              command=simpan_app).pack(pady=10)

# ===================== ROUTER SETTING =====================
def load_router_list(cfg, tree):
    for row in tree.get_children():
        tree.delete(row)
    for r in cfg.get("routers",[]):
        tree.insert("", "end", values=(r.get("id"), r.get("label"), r.get("host"), r.get("username"), r.get("port")))

def open_router_setting(parent):
    cfg = load_config()
    win = tk.Toplevel(parent)
    win.title("🌐 Router Accounts")
    win.geometry("600x450")

    tk.Label(win, text="🌐 Daftar Router", font=("Arial",14,"bold"), fg="blue").pack(pady=10)

    columns = ("id","label","host","username","port")
    tree = ttk.Treeview(win, columns=columns, show="headings", height=12)
    for col in columns:
        tree.heading(col, text=col.upper())
        tree.column(col,width=120)
    tree.pack(fill="both", expand=True, pady=10)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)

    def tambah_router():
        win2 = tk.Toplevel(win)
        win2.title("Tambah Router")
        win2.geometry("300x250")
        tk.Label(win2, text="Tambah Router Baru", font=("Arial",12,"bold")).pack(pady=10)
        fields = {}
        for lbl in ["ID Router","Label","IP Address","Port","Username","Password"]:
            tk.Label(win2,text=lbl+":", font=("Arial",10,"bold")).pack(anchor="w")
            ent = tk.Entry(win2, show="*" if lbl=="Password" else None)
            if lbl=="Port": ent.insert(0,"8728")
            ent.pack()
            fields[lbl] = ent
        def simpan():
            cfg["routers"].append({
                "id": fields["ID Router"].get(),
                "label": fields["Label"].get(),
                "host": fields["IP Address"].get(),
                "port": int(fields["Port"].get() or 8728),
                "username": fields["Username"].get(),
                "password": fields["Password"].get()
            })
            save_config(cfg)
            load_router_list(cfg, tree)
            win2.destroy()
        tk.Button(win2,text="💾 Simpan",bg="green",fg="white",font=("Arial",10,"bold"),command=simpan).pack(pady=10)

    def hapus_router():
        sel = tree.selection()
        if not sel: return
        rid = tree.item(sel[0],"values")[0]
        if not messagebox.askyesno("Hapus Router",f"Yakin hapus router '{rid}'?"): return
        cfg["routers"] = [r for r in cfg["routers"] if r["id"] != rid]
        save_config(cfg)
        load_router_list(cfg, tree)

    tk.Button(btn_frame,text="➕ Tambah",bg="green",fg="white",font=("Arial",10,"bold"),command=tambah_router).pack(side="left", padx=5)
    tk.Button(btn_frame,text="❌ Hapus",bg="red",fg="white",font=("Arial",10,"bold"),command=hapus_router).pack(side="left", padx=5)

    load_router_list(cfg, tree)

# ===================== GLOBAL CONFIG =====================
def open_global_config(parent,cfg):
    win = tk.Toplevel(parent)
    win.title("⚙️ Global Config")
    win.geometry("650x550")

    tk.Label(win, text="💻 SISTEM MIKROTIK INVOICE", font=("Arial",16,"bold"), fg="darkblue").pack(pady=15)

    frame = tk.Frame(win, padx=10,pady=10)
    frame.pack(fill="both", expand=True)

    # Tombol cepat
    btn_frame = tk.Frame(frame)
    btn_frame.pack(fill="x", pady=10)
    tk.Button(btn_frame, text="⚙️ App Setting", bg="green", fg="white",
              font=("Arial",10,"bold"), width=18, command=lambda: open_app_setting(win)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="🌐 Router Setting", bg="blue", fg="white",
              font=("Arial",10,"bold"), width=18, command=lambda: open_router_setting(win)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="👥 Daftar Pelanggan", bg="orange", fg="white",
              font=("Arial",10,"bold"), width=18, command=lambda: messagebox.showinfo("Info","Fungsi pelanggan belum tersedia")).pack(side="left", padx=5)

    # Store name / address / riwayat folder
    for lbl, var, default in [("🏪 Nama Toko","store_name",""),
                               ("📍 Alamat","store_address",""),
                               ("📁 Folder Riwayat Invoice","riwayat_dir","riwayat_invoice")]:
        tk.Label(frame, text=lbl+":", font=("Arial",10,"bold")).pack(anchor="w", pady=2)
        v = tk.StringVar(value=cfg["app"].get(default,""))
        e = tk.Entry(frame,textvariable=v)
        e.pack(fill="x", pady=3)
        if lbl=="📁 Folder Riwayat Invoice":
            tk.Button(frame,text="📂 Pilih Folder",bg="lightblue",font=("Arial",9,"bold"),
                      command=lambda v=v: pilih_folder(v)).pack(pady=2)
        setattr(win,var,v)

    # Router default
    tk.Label(frame, text="🌐 Router Default:", font=("Arial",10,"bold")).pack(anchor="w", pady=2)
    router_var = tk.StringVar(value=cfg["app"].get("default_account",""))
    router_names = [r["id"] for r in cfg["routers"]]
    ttk.Combobox(frame,textvariable=router_var,values=router_names,state="readonly").pack(fill="x", pady=3)
    win.router_default = router_var

    # Printer default
    tk.Label(frame, text="🖨️ Printer Default:", font=("Arial",10,"bold")).pack(anchor="w", pady=2)
    printer_var = tk.StringVar(value=cfg["app"].get("printer",""))
    printers = [p[2] for p in win32print.EnumPrinters(2)] or ["Tidak ada printer"]
    ttk.Combobox(frame,textvariable=printer_var,values=printers,state="readonly").pack(fill="x", pady=3)
    win.printer_default = printer_var

    # Simpan tombol
    def save_all():
        cfg["app"]["store_name"] = win.store_name.get()
        cfg["app"]["store_address"] = win.store_address.get()
        cfg["app"]["riwayat_dir"] = win.riwayat_dir.get()
        cfg["app"]["default_account"] = win.router_default.get()
        cfg["app"]["printer"] = win.printer_default.get()
        save_config(cfg)
        messagebox.showinfo("Sukses","✅ Global config berhasil disimpan!")

    tk.Button(frame,text="💾 Simpan Global Config",bg="darkgreen",fg="white",
              font=("Arial",11,"bold"), width=30, command=save_all).pack(pady=15)
