"""
============================================================
CHECK ROUTES
============================================================

Mikrotik Invoice

Fungsi:

1. Scan seluruh folder routes
2. Membaca semua *_routes.py
3. Mengambil semua route
4. Mengambil nama fungsi
5. Digunakan oleh checker pada Bagian berikutnya

============================================================
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ROUTES_DIR = BASE_DIR / "routes"

# ==========================================================
# UTILITAS
# ==========================================================

def garis():
    print("=" * 60)

# ==========================================================
# BANNER
# ==========================================================

def banner():

    garis()

    print("MIKROTIK INVOICE")
    print("ROUTE CHECK TOOL")

    print()

    print("Project :")
    print(BASE_DIR)

    print()

    print("Routes :")
    print(ROUTES_DIR)

    garis()

def baca(file):
    with open(file, "r", encoding="utf-8") as f:
        return f.read()


# ==========================================================
# CEK PROJECT
# ==========================================================

def cek_project():

    if not ROUTES_DIR.exists():

        print("Folder routes tidak ditemukan.")

        return False

    return True


# ==========================================================
# SCAN ROUTES
# ==========================================================

def scan_routes():

    hasil = []

    for file in sorted(
        ROUTES_DIR.glob("*_routes.py")
    ):

        if file.name == "__init__.py":
            continue

        hasil.append(file)

    return hasil

def scan_route_files():

    return scan_routes()

# ==========================================================
# INFO FILE
# ==========================================================

def info_file(file):

    try:

        ukuran = file.stat().st_size

    except:

        ukuran = 0

    return {

        "nama": file.name,

        "path": file,

        "ukuran": ukuran

    }


# ==========================================================
# TAMPILKAN FILE
# ==========================================================

def tampilkan_file(files):

    garis()

    print("FILE ROUTES")

    garis()

    for file in files:

        info = info_file(file)

        print(
            f"{info['nama']:<35}"
            f"{info['ukuran']:>8} byte"
        )

    garis()


# ==========================================================
# CARI BLUEPRINT
# ==========================================================

def cari_blueprint(text):

    cocok = re.search(

        r'Blueprint\s*\(\s*[\'"](.+?)[\'"]',

        text

    )

    if cocok:

        return cocok.group(1)

    return None


# ==========================================================
# AMBIL SEMUA ROUTE
# ==========================================================

def ambil_routes(text):

    hasil = []

    pola = re.findall(

        r'@(?:\w+_bp|app|bp)\.route\(\s*[\'"](.+?)[\'"]',

        text

    )


    for route in pola:

        hasil.append(
            route.strip()
        )


    return hasil

# ==========================================================
# PARSE ROUTE OBJECT
# ==========================================================

def parse_routes(file):

    hasil = []

    text = baca(file)


    pola = re.findall(
        r'@(?:\w+_bp|app|bp)\.route\(\s*[\'"]([^\'"]+)',
        text
    )


    fungsi = re.findall(
        r'def\s+([a-zA-Z0-9_]+)\s*\(',
        text
    )


    sudah = set()


    for index, url in enumerate(pola):


        if url in sudah:
            continue


        sudah.add(url)


        nama_function = (
            fungsi[index]
            if index < len(fungsi)
            else "unknown"
        )


        hasil.append({

            "url": url,

            "function": nama_function,

            "file": file.name

        })


    return hasil
# ==========================================================
# AMBIL SEMUA FUNCTION
# ==========================================================

def ambil_function(text):

    hasil = []

    pola = re.findall(

        r'^def\s+([a-zA-Z0-9_]+)\s*\(',

        text,

        re.MULTILINE

    )

    for nama in pola:

        hasil.append(nama)

    return hasil


# ==========================================================
# BACA SEMUA FILE ROUTE
# ==========================================================

def baca_semua(files):

    data = []

    for file in files:

        isi = baca(file)

        data.append({

            "file": file,

            "nama": file.name,

            "blueprint": cari_blueprint(isi),

            "routes": ambil_routes(isi),

            "functions": ambil_function(isi),

            "text": isi

        })

    return data

# ==========================================================
# PEMERIKSAAN DUPLIKASI DAN VALIDASI
# ==========================================================

def check_duplicate_routes():
    """
    Mengecek apakah ada URL route yang sama
    di beberapa file.
    """

    garis()
    print("MEMERIKSA DUPLIKAT ROUTE")
    garis()

    route_map = {}

    total = 0

    for file in scan_route_files():

        routes = parse_routes(file)

        for r in routes:

            total += 1

            url = r["url"]

            if url not in route_map:
                route_map[url] = []

            route_map[url].append(r)

    duplicate = {}

    for url, items in route_map.items():

        if len(items) > 1:
            duplicate[url] = items

    print(f"Total Route : {total}")
    print(f"URL Unik    : {len(route_map)}")
    print(f"Duplikat    : {len(duplicate)}")

    garis()

    if duplicate:

        print("DUPLIKAT DITEMUKAN\n")

        for url, items in sorted(duplicate.items()):

            print(url)

            for item in items:

                print(
                    f"   {item['file']}  ->  {item['function']}"
                )

            print()

    else:

        print("Tidak ada route duplikat.")

    return duplicate


# ==========================================================
# VALIDASI ROUTE
# ==========================================================

def validate_routes():

    garis()
    print("VALIDASI ROUTE")
    garis()

    kosong = []
    tanpa_decorator = []
    tanpa_function = []

    for file in scan_route_files():

        routes = parse_routes(file)

        if not routes:
            kosong.append(file.name)
            continue

        isi = file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        if not re.search(
            r'@\w+_bp\.route|@app\.route|@bp\.route',
            isi
        ):
            tanpa_decorator.append(file.name)
        if "def " not in isi:
            tanpa_function.append(file.name)

    if kosong:

        print("\nFile tanpa route :")

        for f in kosong:
            print("  -", f)

    if tanpa_decorator:

        print("\nFile tanpa decorator :")

        for f in tanpa_decorator:
            print("  -", f)

    if tanpa_function:

        print("\nFile tanpa function :")

        for f in tanpa_function:
            print("  -", f)

    if (
        not kosong and
        not tanpa_decorator and
        not tanpa_function
    ):

        print("Semua route valid.")

    garis()


# ==========================================================
# RINGKASAN
# ==========================================================

def summary():

    garis()
    print("RINGKASAN")
    garis()

    files = scan_route_files()

    total_file = len(files)
    total_route = 0

    for f in files:

        total_route += len(parse_routes(f))

    print(f"Jumlah file route : {total_file}")
    print(f"Jumlah route      : {total_route}")

    garis()
# ==========================================================
# EXPORT LAPORAN
# ==========================================================

def save_report(duplicate):
    """
    Menyimpan hasil pengecekan ke logs/routes_report.txt
    """

    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    report_file = logs_dir / "routes_report.txt"

    lines = []

    lines.append("=" * 60)
    lines.append("MIKROTIK INVOICE")
    lines.append("ROUTE VALIDATION REPORT")
    lines.append("=" * 60)
    lines.append("")

    total_route = 0
    total_file = 0

    for file in scan_route_files():

        routes = parse_routes(file)

        total_file += 1
        total_route += len(routes)

    lines.append(f"Total File Route : {total_file}")
    lines.append(f"Total Route      : {total_route}")
    lines.append(f"Duplicate URL    : {len(duplicate)}")
    lines.append("")

    if duplicate:

        lines.append("DAFTAR DUPLIKAT")
        lines.append("-" * 60)

        for url, items in sorted(duplicate.items()):

            lines.append(url)

            for item in items:

                lines.append(
                    f"   {item['file']} -> {item['function']}"
                )

            lines.append("")

    else:

        lines.append("Tidak ditemukan route yang duplikat.")

    report_file.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print()
    print("Laporan disimpan ke:")
    print(report_file)


# ==========================================================
# MAIN
# ==========================================================

def main():

    banner()

    if not ROUTES_DIR.exists():

        print("Folder routes tidak ditemukan.")
        return

    duplicate = check_duplicate_routes()

    validate_routes()

    summary()

    save_report(duplicate)

    garis()

    if duplicate:

        print("SELESAI (ADA DUPLIKAT ROUTE)")

    else:

        print("SELESAI (SEMUA ROUTE VALID)")

    garis()


# ==========================================================

if __name__ == "__main__":
    main()