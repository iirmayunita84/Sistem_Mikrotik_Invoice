"""
============================================================
REGISTER BLUEPRINTS
============================================================

Mikrotik Invoice

Fungsi:

1. Membuat routes/__init__.py bila belum ada
2. Scan seluruh *_routes.py
3. Membuat import blueprint
4. Menambahkan register_blueprint()
5. Tidak membuat duplikasi
6. Aman dijalankan berkali-kali

============================================================
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ROUTES_DIR = BASE_DIR / "routes"

WEB_FILE = BASE_DIR / "web.py"


# ==========================================================
# UTILITAS
# ==========================================================

def garis():
    print("=" * 60)


def baca(file):
    with open(file, "r", encoding="utf-8") as f:
        return f.read()


def tulis(file, isi):
    with open(file, "w", encoding="utf-8") as f:
        f.write(isi)


# ==========================================================
# CEK PROJECT
# ==========================================================

def cek_project():

    if not ROUTES_DIR.exists():
        print("Folder routes tidak ditemukan.")
        return False

    if not WEB_FILE.exists():
        print("web.py tidak ditemukan.")
        return False

    return True


# ==========================================================
# INIT ROUTES
# ==========================================================

def buat_init():

    init_file = ROUTES_DIR / "__init__.py"

    if init_file.exists():
        return

    tulis(
        init_file,
        "# Auto Generated\n"
    )

    print("Membuat routes/__init__.py")


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

        nama = file.stem

        hasil.append(
            {
                "file": file,
                "module": nama,
                "blueprint": nama.replace("_routes", "")
            }
        )

    return hasil


# ==========================================================
# CEK BLUEPRINT
# ==========================================================

def blueprint_name(file):

    isi = baca(file)

    cocok = re.search(
        r'Blueprint\(\s*[\'"](.+?)[\'"]',
        isi
    )

    if cocok:
        return cocok.group(1)

    return None
# ==========================================================
# GENERATOR IMPORT
# ==========================================================

def buat_import(module, blueprint):

    """
    Menghasilkan:

    from routes.invoice_routes import bp as invoice_bp
    """

    return (
        f"from routes.{module} "
        f"import bp as {blueprint}_bp"
    )


# ==========================================================
# GENERATOR REGISTER
# ==========================================================

def buat_register(blueprint):

    """
    Menghasilkan:

    app.register_blueprint(invoice_bp)
    """

    return (
        f"app.register_blueprint({blueprint}_bp)"
    )


# ==========================================================
# AMBIL IMPORT YANG SUDAH ADA
# ==========================================================

def import_existing(text):

    hasil = []

    pola = re.findall(
        r"from\s+routes\.(.+?)\s+import\s+bp\s+as\s+(.+)",
        text
    )

    for module, alias in pola:

        hasil.append(
            (
                module.strip(),
                alias.strip()
            )
        )

    return hasil


# ==========================================================
# AMBIL REGISTER YANG SUDAH ADA
# ==========================================================

def register_existing(text):

    hasil = []

    pola = re.findall(
        r"app\.register_blueprint\((.+?)\)",
        text
    )

    for item in pola:

        hasil.append(item.strip())

    return hasil


# ==========================================================
# BUILD IMPORT BARU
# ==========================================================

def build_imports(routes, text):

    existing = import_existing(text)

    hasil = []

    for item in routes:

        module = item["module"]

        blueprint = item["blueprint"]

        alias = blueprint + "_bp"

        if (module, alias) not in existing:

            hasil.append(
                buat_import(module, blueprint)
            )

    return hasil


# ==========================================================
# BUILD REGISTER BARU
# ==========================================================

def build_register(routes, text):

    existing = register_existing(text)

    hasil = []

    for item in routes:

        blueprint = item["blueprint"]

        reg = blueprint + "_bp"

        if reg not in existing:

            hasil.append(
                buat_register(blueprint)
            )

    return hasil


# ==========================================================
# TAMPILKAN HASIL SCAN
# ==========================================================

def tampilkan_routes(routes):

    garis()

    print("ROUTES DITEMUKAN")

    garis()

    for item in routes:

        print(
            f"{item['module']:<30}"
            f" -> {item['blueprint']}_bp"
        )

    garis()
# ==========================================================
# SISIPKAN IMPORT KE web.py
# ==========================================================

def sisip_import(web_text, imports):

    if not imports:
        return web_text

    marker = "app = Flask(__name__)"

    pos = web_text.find(marker)

    if pos == -1:
        print("Tidak menemukan app = Flask(__name__)")
        return web_text

    pos = web_text.find("\n", pos)

    block = "\n\n# ===== AUTO BLUEPRINT IMPORT =====\n"

    for imp in imports:
        block += imp + "\n"

    block += "# ================================\n"

    return (
        web_text[:pos + 1]
        + block
        + web_text[pos + 1:]
    )


# ==========================================================
# SISIPKAN REGISTER BLUEPRINT
# ==========================================================

def sisip_register(web_text, registers):

    if not registers:
        return web_text

    marker = "if __name__ == \"__main__\":"

    pos = web_text.find(marker)

    if pos == -1:

        marker = "if __name__ == '__main__':"

        pos = web_text.find(marker)

    if pos == -1:

        print("Tidak menemukan blok __main__")

        return web_text

    block = "\n\n# ===== AUTO REGISTER BLUEPRINT =====\n"

    for reg in registers:
        block += reg + "\n"

    block += "# ==================================\n\n"

    return (
        web_text[:pos]
        + block
        + web_text[pos:]
    )


# ==========================================================
# UPDATE web.py
# ==========================================================

def update_web(routes):

    print()

    print("Memperbarui web.py ...")

    web_text = baca(WEB_FILE)

    imports = build_imports(routes, web_text)

    registers = build_register(routes, web_text)

    if not imports and not registers:

        print("Tidak ada perubahan.")

        return

    if imports:

        print()

        print("Import Blueprint")

        for i in imports:
            print(" +", i)

        web_text = sisip_import(
            web_text,
            imports
        )

    if registers:

        print()

        print("Register Blueprint")

        for r in registers:
            print(" +", r)

        web_text = sisip_register(
            web_text,
            registers
        )

    tulis(
        WEB_FILE,
        web_text
    )

    print()

    print("web.py berhasil diperbarui.")

# ==========================================================
# MAIN
# ==========================================================

def main():

    garis()
    print("REGISTER BLUEPRINTS")
    garis()

    if not cek_project():
        return

    # pastikan routes/__init__.py ada
    buat_init()

    # scan semua file *_routes.py
    routes = scan_routes()

    if not routes:

        print("Tidak ada file route ditemukan.")

        return

    # tampilkan hasil scan
    tampilkan_routes(routes)

    # cek blueprint di setiap file
    print("\nMengecek Blueprint...\n")

    valid_routes = []

    for item in routes:

        bp = blueprint_name(item["file"])

        if bp:

            print(f"[OK] {item['module']} -> {bp}")

            valid_routes.append(item)

        else:

            print(f"[SKIP] {item['module']} (Blueprint tidak ditemukan)")

    if not valid_routes:

        print("\nTidak ada Blueprint yang valid.")

        return

    # update web.py
    update_web(valid_routes)

    garis()
    print("SELESAI")
    garis()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    main()