#core/admin_login.py

import bcrypt, json, os
import tkinter as tk
from tkinter import messagebox
from werkzeug.security import check_password_hash
from core.db import db_connection

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "MikrotikInvoice")
os.makedirs(APP_FOLDER, exist_ok=True)

ADMIN_FILE = os.path.join(APP_FOLDER, "admin.json")

# ================== INIT ADMIN ==================
def init_admin(default_password="admin123"):
    """
    Buat admin.json jika belum ada
    """
    if os.path.exists(ADMIN_FILE):
        return

    hashed = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt()).decode()

    with open(ADMIN_FILE, "w") as f:
        json.dump({
            "username": "admin",
            "password": hashed
        }, f, indent=2)

# ================== VERIFY LOGIN ==================
def verify_login(username, password):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        user = cur.fetchone()

        if not user:
            return False

        return check_password_hash(
            user["password"],
            password
        )

# ================== GUI ==================
def show_admin_login(on_success):
    init_admin()  # pastikan admin ada

    root = tk.Tk()
    root.title("Login Admin")
    root.geometry("360x240")
    root.resizable(False, False)

    tk.Label(root, text="🔐 LOGIN ADMIN",
             font=("Segoe UI", 14, "bold")).pack(pady=15)

    tk.Label(root, text="Username").pack()
    entry_user = tk.Entry(root, width=30)
    entry_user.pack(pady=5)

    tk.Label(root, text="Password").pack()
    entry_pass = tk.Entry(root, width=30, show="*")
    entry_pass.pack(pady=5)

    def login():
        if verify_login(
            entry_user.get().strip(),
            entry_pass.get().strip()
        ):
            messagebox.showinfo("Sukses", "Login admin berhasil")
            root.destroy()
            on_success()
        else:
            messagebox.showerror("Gagal", "Username atau password salah")

def show_change_password():
    if not os.path.exists(ADMIN_FILE):
        messagebox.showerror("Error", "Data admin tidak ditemukan")
        return

    with open(ADMIN_FILE, "r") as f:
        admin = json.load(f)

    root = tk.Toplevel()
    root.title("Ganti Password Admin")
    root.geometry("380x280")
    root.resizable(False, False)

    tk.Label(root, text="🔁 GANTI PASSWORD ADMIN",
             font=("Segoe UI", 13, "bold")).pack(pady=12)

    tk.Label(root, text="Password Lama").pack()
    old_pass = tk.Entry(root, width=32, show="*")
    old_pass.pack(pady=4)

    tk.Label(root, text="Password Baru").pack()
    new_pass = tk.Entry(root, width=32, show="*")
    new_pass.pack(pady=4)

    tk.Label(root, text="Ulangi Password Baru").pack()
    confirm_pass = tk.Entry(root, width=32, show="*")
    confirm_pass.pack(pady=4)

    def save_new_password():
        if not bcrypt.checkpw(old_pass.get().encode(), admin["password"].encode()):
            messagebox.showerror("Gagal", "Password lama salah")
            return

        if len(new_pass.get()) < 6:
            messagebox.showerror("Gagal", "Password minimal 6 karakter")
            return

        if new_pass.get() != confirm_pass.get():
            messagebox.showerror("Gagal", "Password baru tidak cocok")
            return

        hashed = bcrypt.hashpw(new_pass.get().encode(), bcrypt.gensalt()).decode()
        admin["password"] = hashed

        with open(ADMIN_FILE, "w") as f:
            json.dump(admin, f, indent=2)

        messagebox.showinfo("Sukses", "✅ Password admin berhasil diubah")
        root.destroy()

    tk.Button(root, text="💾 SIMPAN PASSWORD", width=22, command=save_new_password).pack(pady=15)

    root.mainloop()