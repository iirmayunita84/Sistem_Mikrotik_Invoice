# core/admin_core.py

import bcrypt
import uuid
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from core.db import get_db, release_db

def init_admin(default_password="admin123"):

    conn = get_db()

    try:
        cur = conn.cursor()

        cur.execute("""
        SELECT id
        FROM users
        WHERE is_admin=1
        LIMIT 1
        """)

        if cur.fetchone():
            return

        hashed = bcrypt.hashpw(
            default_password.encode(),
            bcrypt.gensalt()
        ).decode()

        cur.execute("""
        INSERT INTO users(
            id,
            username,
            password,
            is_admin,
            created_at
        )
        VALUES(?,?,?,?,?)
        """,(
            uuid.uuid4().hex,
            "admin",
            hashed,
            1,
            datetime.now().isoformat()
        ))

        conn.commit()

    finally:
        release_db(conn)

def verify_login(username,password):

    conn = get_db()

    try:

        cur = conn.cursor()

        cur.execute("""
        SELECT password
        FROM users
        WHERE username=?
        AND is_admin=1
        LIMIT 1
        """,(username,))

        row = cur.fetchone()

        if not row:
            return False

        return bcrypt.checkpw(
            password.encode(),
            row["password"].encode()
        )

    finally:
        release_db(conn)

def show_admin_login(on_success):
    init_admin()

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

    tk.Button(root, text="LOGIN", width=20, command=login).pack(pady=15)

    root.mainloop()

def show_change_password():

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

        if not verify_login("admin", old_pass.get()):
            messagebox.showerror("Gagal", "Password lama salah")
            return

        if len(new_pass.get()) < 6:
            messagebox.showerror("Gagal", "Password minimal 6 karakter")
            return

        if new_pass.get() != confirm_pass.get():
            messagebox.showerror("Gagal", "Password baru tidak cocok")
            return

        conn = None

        try:
            conn = get_db()
            cur = conn.cursor()

            hashed = bcrypt.hashpw(
                new_pass.get().encode(),
                bcrypt.gensalt()
            ).decode()

            cur.execute("""
                UPDATE users
                SET password=?
                WHERE username=? AND is_admin=1
            """, (
                hashed,
                "admin"
            ))

            conn.commit()

            messagebox.showinfo(
                "Sukses",
                "✅ Password admin berhasil diubah"
            )

            root.destroy()

        except Exception as e:

            if conn:
                conn.rollback()

            messagebox.showerror(
                "Error",
                str(e)
            )

        finally:

            if conn:
                release_db(conn)

    tk.Button(root, text="💾 SIMPAN PASSWORD", width=22,
              command=save_new_password).pack(pady=15)

    root.mainloop()