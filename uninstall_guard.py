# uninstall_guard.py
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
from werkzeug.security import check_password_hash
from security_config import UNINSTALL_PASSWORD_HASH

def main():
    root = tk.Tk()
    root.withdraw()

    pw = simpledialog.askstring(
        "Uninstall Aplikasi",
        "Masukkan password uninstall:",
        show="*"
    )

    if not pw:
        sys.exit(1)

    if check_password_hash(UNINSTALL_PASSWORD_HASH, pw):
        sys.exit(0)   # ✔ BOLEH UNINSTALL
    else:
        messagebox.showerror(
            "Ditolak",
            "❌ Password salah"
        )
        sys.exit(1)   # ❌ BATAL

if __name__ == "__main__":
    main()