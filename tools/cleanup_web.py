"""
============================================================
 CLEANUP WEB.PY
 Mikrotik Invoice Refactor Tool
============================================================

Fungsi:

1. Membaca web.py
2. Membaca seluruh file di folder routes/
3. Mengetahui route yang sudah dipindahkan
4. Menghapus route tersebut dari web.py
5. Menyimpan hasil ke web.py.cleaned
6. Tidak mengubah web.py asli

============================================================
"""

import re
import shutil
from pathlib import Path
import ast

# ==========================================================
# KONFIGURASI
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

WEB_FILE = BASE_DIR / "web.py"

ROUTES_DIR = BASE_DIR / "routes"

OUTPUT_FILE = BASE_DIR / "web.py.cleaned"

BACKUP_DIR = BASE_DIR / "backup"

BACKUP_FILE = BACKUP_DIR / "web_before_cleanup.py"


# ==========================================================
# UTILITAS
# ==========================================================

def garis():
    print("=" * 60)


def banner():

    garis()

    print("MIKROTIK INVOICE")
    print("WEB.PY CLEANUP TOOL")

    print()

    print("Project :", BASE_DIR)
    print("Web.py  :", WEB_FILE)

    garis()


# ==========================================================
# CEK PROJECT
# ==========================================================

def check_project():

    if not WEB_FILE.exists():

        print("ERROR : web.py tidak ditemukan.")

        return False

    if not ROUTES_DIR.exists():

        print("ERROR : folder routes tidak ditemukan.")

        return False

    return True


# ==========================================================
# SCANNER
# ==========================================================

def scan_route_files():

    """
    Mengambil seluruh file route.
    """

    files = []

    for file in sorted(ROUTES_DIR.glob("*_routes.py")):

        files.append(file)

    return files


# ==========================================================
# BACA FILE
# ==========================================================

def read_text(file):

    return file.read_text(
        encoding="utf-8",
        errors="ignore"
    )


def write_text(file, content):

    file.write_text(
        content,
        encoding="utf-8"
    )


# ==========================================================
# BACKUP
# ==========================================================

def backup_web():

    BACKUP_DIR.mkdir(exist_ok=True)

    shutil.copy2(
        WEB_FILE,
        BACKUP_FILE
    )

    print()

    print("Backup dibuat :")

    print(BACKUP_FILE)

# ==========================================================
# PARSER ROUTES
# ==========================================================

def parse_routes_files():

    """
    Membaca file routes/
    dan mengambil daftar fungsi route.
    """

    routes = []


    for file in scan_route_files():

        content = read_text(file)


        # mencari decorator flask
        matches = re.findall(
            r'@app\.route\([^\n]+\)\s+def\s+(\w+)',
            content
        )


        for func in matches:

            routes.append(
                {
                    "file": file.name,
                    "function": func
                }
            )


    return routes



# ==========================================================
# PARSER WEB.PY
# ==========================================================


def parse_web_routes():

    """
    Membaca semua route yang masih ada
    di web.py
    """

    content = read_text(WEB_FILE)


    routes = []


    pattern = re.compile(
        r'(@app\.route\([^\n]+\).*?'
        r'\ndef\s+(\w+)\(.*?\):)',
        re.DOTALL
    )


    matches = pattern.findall(content)


    for block, name in matches:

        routes.append(
            {
                "function": name,
                "block": block
            }
        )


    return routes



# ==========================================================
# DETEKSI ROUTE PINDAHAN
# ==========================================================


def find_moved_routes():

    """
    Membandingkan route di routes/
    dengan route di web.py
    """

    moved = []


    route_files = parse_routes_files()

    web_routes = parse_web_routes()


    route_names = [
        r["function"]
        for r in route_files
    ]


    for route in web_routes:

        if route["function"] in route_names:

            moved.append(route)



    return moved

# ==========================================================
# MENENTUKAN FUNCTION YANG AKAN DIHAPUS
# ==========================================================


def get_functions_to_remove():

    """
    Menghasilkan daftar function
    yang sudah ada di routes/
    dan masih terdapat di web.py
    """

    remove_list = []


    moved_routes = find_moved_routes()


    for route in moved_routes:

        remove_list.append(
            {
                "function": route["function"],
                "block": route["block"]
            }
        )


    return remove_list



# ==========================================================
# CEK DETAIL FUNCTION
# ==========================================================


def show_remove_preview():

    """
    Menampilkan preview
    sebelum proses cleanup
    """

    functions = get_functions_to_remove()


    garis()

    print("FUNCTION YANG AKAN DIHAPUS")

    garis()


    if not functions:

        print("Tidak ada function ditemukan.")

        return



    for item in functions:

        print(
            "[REMOVE]",
            item["function"]
        )


    print()

    print(
        "Total:",
        len(functions),
        "function"
    )

    garis()

# ==========================================================
# CLEANER ENGINE
# ==========================================================


def remove_route_blocks(content, remove_list):

    """
    Menghapus blok route dari web.py

    content :
        isi file web.py

    remove_list :
        daftar function yang dihapus
    """


    cleaned = content


    for item in remove_list:


        function_name = item["function"]


        # mencari blok decorator sampai akhir function
        pattern = re.compile(
            r'(@app\.route\([^\n]+\).*?'
            r'\ndef\s+' +
            re.escape(function_name) +
            r'\(.*?\):.*?'
            r'(?=\n@app\.route|\ndef\s+|\Z))',
            re.DOTALL
        )


        cleaned, count = pattern.subn(
            "",
            cleaned
        )


        if count:

            print(
                "Removed:",
                function_name
            )

        else:

            print(
                "Tidak ditemukan:",
                function_name
            )


    return cleaned



# ==========================================================
# CLEAN WEB.PY
# ==========================================================


def clean_web_file():

    """
    Proses utama cleanup
    """


    backup_web()


    original = read_text(
        WEB_FILE
    )


    remove_list = get_functions_to_remove()


    if not remove_list:

        print()

        print(
            "Tidak ada route untuk dibersihkan."
        )

        return False



    print()

    garis()

    print(
        "MEMULAI CLEANUP"
    )

    garis()



    cleaned = remove_route_blocks(
        original,
        remove_list
    )



    write_text(
        OUTPUT_FILE,
        cleaned
    )



    print()

    garis()

    print(
        "Cleanup selesai"
    )

    print()

    print(
        "File hasil:"
    )

    print(
        OUTPUT_FILE
    )

    garis()


    return True

# ==========================================================
# AUTO BACKUP SYSTEM
# ==========================================================

from datetime import datetime



# ==========================================================
# BACKUP CONFIG
# ==========================================================

BACKUP_HISTORY = BACKUP_DIR / "backup_history.txt"



# ==========================================================
# CREATE AUTO BACKUP
# ==========================================================


def create_auto_backup():

    """
    Membuat backup otomatis web.py
    dengan timestamp
    """


    if not WEB_FILE.exists():

        print(
            "ERROR : web.py tidak ditemukan"
        )

        return None



    BACKUP_DIR.mkdir(
        exist_ok=True
    )



    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )



    backup_file = (
        BACKUP_DIR /
        f"web_before_cleanup_{timestamp}.py"
    )



    shutil.copy2(
        WEB_FILE,
        backup_file
    )



    save_backup_history(
        backup_file
    )



    print()

    print(
        "Backup otomatis dibuat:"
    )

    print(
        backup_file
    )


    return backup_file



# ==========================================================
# BACKUP HISTORY
# ==========================================================


def save_backup_history(file):

    """
    Menyimpan daftar backup
    """


    BACKUP_HISTORY.parent.mkdir(
        exist_ok=True
    )


    with open(
        BACKUP_HISTORY,
        "a",
        encoding="utf-8"
    ) as f:


        f.write(
            str(datetime.now())
            +
            " | "
            +
            str(file)
            +
            "\n"
        )



# ==========================================================
# LIST BACKUP
# ==========================================================


def list_backups():

    """
    Menampilkan semua backup
    """


    print()

    garis()

    print(
        "DAFTAR BACKUP"
    )

    garis()



    if not BACKUP_DIR.exists():

        print(
            "Belum ada backup."
        )

        return



    files = sorted(
        BACKUP_DIR.glob(
            "web_before_cleanup_*.py"
        )
    )



    for file in files:

        print(
            file.name
        )



    print()

    print(
        "Total backup:",
        len(files)
    )

    garis()

# ==========================================================
# GENERATE WEB.PY.CLEANED
# ==========================================================


def generate_cleaned_file():

    """
    Membuat file web.py.cleaned
    dari hasil proses cleanup
    """


    if not WEB_FILE.exists():

        print(
            "ERROR : web.py tidak ditemukan"
        )

        return False



    print()

    garis()

    print(
        "GENERATE WEB.PY.CLEANED"
    )

    garis()



    # backup sebelum proses

    create_auto_backup()



    original = read_text(
        WEB_FILE
    )



    remove_list = get_functions_to_remove()

    if not remove_list:

        print(
            "Tidak ada function lama."
        )


        write_text(
            OUTPUT_FILE,
            original
        )


        print()

        print(
            "web.py sudah bersih."
        )

        print(
            "Membuat salinan:"
        )

        print(
            OUTPUT_FILE
        )


        return True



    cleaned_content = remove_route_blocks(
        original,
        remove_list
    )

    write_text(
        OUTPUT_FILE,
        cleaned_content
    )


    if not validate_python_file(
        OUTPUT_FILE
    ):

        print(
            "File cleaned tidak valid."
        )

        return False


    if OUTPUT_FILE.exists():

        print()

        print(
            "SUCCESS"
        )

        print(
            "File berhasil dibuat:"
        )

        print(
            OUTPUT_FILE
        )

        print()

        print(
            "Ukuran file:",
            OUTPUT_FILE.stat().st_size,
            "bytes"
        )

        garis()

        return True



    else:

        print(
            "ERROR : gagal membuat file cleaned"
        )

        return False
# ==========================================================
# VALIDATE PYTHON SYNTAX
# ==========================================================


def validate_python_file(file):

    """
    Mengecek syntax Python
    """


    try:

        content = read_text(
            file
        )


        ast.parse(
            content
        )


        return True



    except SyntaxError as e:


        print()

        print(
            "SYNTAX ERROR:"
        )

        print(
            e
        )


        return False

# ==========================================================
# MAIN PROGRAM
# ==========================================================


def main():

    banner()


    # cek struktur project

    if not check_project():

        return



    # scan routes

    route_files = scan_route_files()



    print()

    garis()

    print(
        "FILE ROUTES DITEMUKAN"
    )

    garis()



    if not route_files:

        print(
            "Tidak ada file routes."
        )

    else:


        for file in route_files:

            print(
                "-",
                file.name
            )



    print()



    # tampilkan function pindahan

    show_remove_preview()



    print()



    # generate cleaned file

    success = generate_cleaned_file()



    print()



    garis()


    if success:

        print(
            "CLEANUP BERHASIL"
        )

        print()

        print(
            "Output:"
        )

        print(
            OUTPUT_FILE
        )


    else:

        print(
            "CLEANUP GAGAL"
        )


    garis()



# ==========================================================
# ENTRY POINT
# ==========================================================


if __name__ == "__main__":

    main()