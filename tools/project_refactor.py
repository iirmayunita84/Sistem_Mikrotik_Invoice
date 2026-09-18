"""
===========================================================
 PROJECT REFACTOR
 Mikrotik Invoice
===========================================================

Script utama untuk menjalankan seluruh proses refactor.

Urutan kerja:

1. Backup project
2. Split routes
3. Extract imports
4. Register blueprints
5. Check duplicate routes
6. Cleanup web.py (opsional)

===========================================================
"""

import subprocess
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = BASE_DIR / "tools"


def garis():
    print("=" * 60)


def jalankan(script):
    """
    Menjalankan script di folder tools
    """

    file_script = TOOLS_DIR / script

    if not file_script.exists():
        print(f"[SKIP] {script} tidak ditemukan")
        return False

    print(f"\nMenjalankan {script}")

    try:
        subprocess.run(
            [sys.executable, str(file_script)],
            check=True,
            cwd=str(BASE_DIR)
        )

        print(f"[OK] {script}")

        return True

    except subprocess.CalledProcessError:

        print(f"[ERROR] {script}")

        return False

# ==========================================================
# MENU
# ==========================================================

MENU = """
============================================================
           MIKROTIK INVOICE REFACTOR TOOL
============================================================

[1] Backup Project

[2] Split Routes

[3] Extract Imports

[4] Register Blueprints

[5] Check Duplicate Routes

[6] Cleanup web.py

[7] Jalankan Semua

[0] Keluar

============================================================
"""


def menu():

    while True:

        garis()
        print(MENU)

        pilih = input("Pilih menu : ").strip()

        if pilih == "1":

            jalankan("backup_project.py")

        elif pilih == "2":

            jalankan("split_routes.py")

        elif pilih == "3":

            jalankan("extract_imports.py")

        elif pilih == "4":

            jalankan("register_blueprints.py")

        elif pilih == "5":

            jalankan("check_routes.py")

        elif pilih == "6":

            jawab = input(
                "Cleanup web.py? (y/n) : "
            ).lower()

            if jawab == "y":
                jalankan("cleanup_web.py")

        elif pilih == "7":

            full_refactor()

        elif pilih == "0":

            print("\nSelesai.\n")
            break

        else:

            print("Menu tidak dikenal.")

# ==========================================================
# FULL REFACTOR
# ==========================================================

def full_refactor():

    garis()
    print("MEMULAI FULL REFACTOR")
    garis()

    urutan = [

        "backup_project.py",

        "split_routes.py",

        "extract_imports.py",

        "fix_imports.py",

        "fix_blueprints.py",

        "register_blueprints.py",

        "fix_web_import.py",

        "check_routes.py",

        "verify_project.py",

    ]

    berhasil = 0

    gagal = 0

    for script in urutan:

        ok = jalankan(script)

        if ok:

            berhasil += 1

        else:

            gagal += 1

            print("\nProses dihentikan karena terjadi error.")
            break

    garis()

    print("HASIL REFACTOR")

    print(f"Berhasil : {berhasil}")

    print(f"Gagal    : {gagal}")

    garis()

    if gagal == 0:

        jawab = input(
            "\nSemua proses berhasil.\n"
            "Ingin menjalankan cleanup_web.py ? (y/n): "
        ).lower()

        if jawab == "y":

            jalankan("cleanup_web.py")

            print("\nCleanup selesai.")

    else:

        print("\nPerbaiki error terlebih dahulu.")

# ==========================================================
# MAIN
# ==========================================================

def cek_folder():

    wajib = [
        "web.py",
        "tools",
        "routes",
        "core",
        "services",
    ]

    hilang = []

    for item in wajib:

        if not (BASE_DIR / item).exists():
            hilang.append(item)

    if hilang:

        garis()

        print("PROJECT TIDAK VALID")

        print()

        for x in hilang:
            print("Tidak ditemukan :", x)

        garis()

        return False

    return True


def banner():

    garis()

    print("MIKROTIK INVOICE")

    print("Automatic Refactor Tool")

    print()

    print("Folder :", BASE_DIR)

    garis()


def main():

    banner()

    if not cek_folder():

        input("\nTekan ENTER untuk keluar...")
        return

    menu()

    garis()

    print("Refactor selesai.")

    garis()


if __name__ == "__main__":

    main()