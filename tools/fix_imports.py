"""
===========================================================
 FIX IMPORTS
 Mikrotik Invoice Refactor Tool
===========================================================

Fungsi:

1. Scan seluruh file routes
2. Membaca import yang sudah ada
3. Membaca symbol yang digunakan
4. Menambahkan import yang hilang
5. Menghapus import duplikat (opsional)

===========================================================
"""

import ast
from pathlib import Path

# ==========================================================
# CONFIG
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ROUTES_DIR = BASE_DIR / "routes"

# ==========================================================
# UTILITAS
# ==========================================================

def garis():

    print("=" * 60)


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
# SCAN ROUTES
# ==========================================================

def scan_routes():

    """
    Mengambil seluruh file *_routes.py
    """

    if not ROUTES_DIR.exists():

        return []

    return sorted(
        ROUTES_DIR.glob("*_routes.py")
    )


# ==========================================================
# CEK SYNTAX PYTHON
# ==========================================================

def check_python_syntax(file):

    """
    Memastikan file tidak memiliki syntax error.
    """

    try:

        ast.parse(
            read_text(file)
        )

        return True

    except SyntaxError as e:

        print()

        print("SYNTAX ERROR")
        print("File  :", file.name)
        print("Baris :", e.lineno)
        print("Kolom :", e.offset)

        if e.text:
            print(e.text.rstrip())

        print(e.msg)

        return False


# ==========================================================
# LOAD FILE
# ==========================================================

def load_route(file):

    """
    Membaca isi file route.
    """

    if not file.exists():
        return ""

    return read_text(file)


# ==========================================================
# SAVE FILE
# ==========================================================

def save_route(file, content):

    """
    Menyimpan perubahan.
    """

    write_text(
        file,
        content
    )


# ==========================================================
# REPORT
# ==========================================================

def print_header():

    garis()

    print("FIX IMPORTS")

    print()

    print("Folder Routes :")

    print(ROUTES_DIR)

    garis()

# ==========================================================
# PARSE IMPORT
# ==========================================================

def extract_imports(content):

    """
    Mengambil seluruh import
    dari sebuah file Python.
    """

    imports = []

    try:

        tree = ast.parse(content)

    except SyntaxError:

        return imports

    for node in tree.body:

        if isinstance(node, ast.Import):

            source = ast.get_source_segment(
                content,
                node
            )

            if source:
                imports.append(source.strip())

        elif isinstance(node, ast.ImportFrom):

            source = ast.get_source_segment(
                content,
                node
            )

            if source:
                imports.append(source.strip())

    return imports


# ==========================================================
# PARSE SYMBOL
# ==========================================================

def extract_used_names(content):

    """
    Mengambil seluruh symbol
    yang digunakan.
    """

    names = set()

    try:

        tree = ast.parse(content)

    except SyntaxError:

        return names

    IGNORE = {

        "app",
        "bp",

        "True",
        "False",
        "None",

        "__name__",

        "print",
        "len",
        "str",
        "int",
        "float",
        "dict",
        "list",
        "set",
        "tuple",
        "range",
        "enumerate",
        "zip",
        "min",
        "max",
        "sum",
        "open",
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Name):

            if node.id not in IGNORE:

                names.add(
                    node.id
                )

    return names


# ==========================================================
# PARSE FUNCTION
# ==========================================================

def extract_functions(content):

    """
    Mengambil semua nama fungsi.
    """

    funcs = []

    try:

        tree = ast.parse(content)

    except SyntaxError:

        return funcs

    for node in tree.body:

        if isinstance(
            node,
            ast.FunctionDef
        ):

            funcs.append(
                node.name
            )

    return funcs


# ==========================================================
# PARSE BLUEPRINT
# ==========================================================

def has_blueprint(content):

    """
    Mengecek apakah file
    sudah memiliki Blueprint.
    """

    return (
        "Blueprint("
        in content
    )


# ==========================================================
# PARSE ROUTE
# ==========================================================

def extract_routes(content):

    """
    Mengambil daftar route.
    """

    routes = []

    try:

        tree = ast.parse(content)

    except SyntaxError:

        return routes

    for node in tree.body:

        if not isinstance(
            node,
            ast.FunctionDef
        ):
            continue

        for dec in node.decorator_list:

            if not isinstance(
                dec,
                ast.Call
            ):
                continue

            func = dec.func

            if not hasattr(
                func,
                "attr"
            ):
                continue

            if func.attr != "route":
                continue

            if not dec.args:
                continue

            arg = dec.args[0]

            if isinstance(
                arg,
                ast.Constant
            ):

                routes.append(
                    arg.value
                )

    return routes


# ==========================================================
# SUMMARY
# ==========================================================

def analyze_route(file):

    """
    Analisa satu file route.
    """

    content = load_route(file)

    return {

        "file": file,

        "content": content,

        "imports": extract_imports(content),

        "names": extract_used_names(content),

        "functions": extract_functions(content),

        "routes": extract_routes(content),

        "blueprint": has_blueprint(content),

    }
# ==========================================================
# DATABASE IMPORT PROJECT
# ==========================================================

PROJECT_IMPORTS = {

    # ===== Flask =====

    "Blueprint":
        "from flask import Blueprint",

    "request":
        "from flask import request",

    "session":
        "from flask import session",

    "redirect":
        "from flask import redirect",

    "url_for":
        "from flask import url_for",

    "flash":
        "from flask import flash",

    "jsonify":
        "from flask import jsonify",

    "abort":
        "from flask import abort",

    "render_template":
        "from flask import render_template",

    "send_file":
        "from flask import send_file",

    "send_from_directory":
        "from flask import send_from_directory",

    # ===== Login =====

    "login_required":
        "from flask_login import login_required",

    # ===== Core =====

    "get_pelanggan":
        "from core.core_pelanggan import get_pelanggan",

    "get_pelanggan_list":
        "from core.core_pelanggan import get_pelanggan_list",

    "load_mikrotik_list":
        "from core.mikrotik_core import load_mikrotik_list",

    "kirim_wa":
        "from services.wa_service import kirim_wa",
}


# ==========================================================
# CARI IMPORT YANG HILANG
# ==========================================================

def find_missing_imports(existing, used):

    missing = []

    existing = set(existing)

    for symbol in sorted(used):

        if symbol not in PROJECT_IMPORTS:
            continue

        imp = PROJECT_IMPORTS[symbol]

        if imp not in existing:
            missing.append(imp)

    return missing


# ==========================================================
# SISIPKAN IMPORT
# ==========================================================

def insert_imports(content, imports):

    if not imports:
        return content

    lines = content.splitlines()

    last_import = -1

    for i, line in enumerate(lines):

        s = line.strip()

        if (
            s.startswith("import ")
            or
            s.startswith("from ")
        ):
            last_import = i

    # Tidak ada import sama sekali
    if last_import == -1:

        header = []

        header.extend(imports)

        header.append("")

        header.extend(lines)

        return "\n".join(header)

    # Sisipkan setelah import terakhir

    lines[last_import + 1:last_import + 1] = (
        imports + [""]
    )

    return "\n".join(lines)


# ==========================================================
# FIX SATU FILE
# ==========================================================

def fix_file(file):

    print()

    print("Checking :", file.name)

    if not check_python_syntax(file):

        print("SKIP")

        return False

    info = analyze_route(file)

    missing = find_missing_imports(

        info["imports"],

        info["names"]

    )

    if not missing:

        print("OK")

        return True

    content = insert_imports(

        info["content"],

        missing

    )

    save_route(

        file,

        content

    )

    print("Import ditambahkan :")

    for x in missing:

        print(" +", x)

    return True


# ==========================================================
# FIX SEMUA ROUTES
# ==========================================================

def fix_all_routes():

    files = scan_routes()

    if not files:

        print("Route tidak ditemukan.")

        return

    ok = 0

    fail = 0

    for file in files:

        if fix_file(file):

            ok += 1

        else:

            fail += 1

    garis()

    print("HASIL")

    print("Berhasil :", ok)

    print("Gagal    :", fail)

    garis()

# ==========================================================
# MAIN PROCESS
# ==========================================================

def fix_imports():

    print_header()

    files = scan_routes()

    if not files:

        print("Tidak ada file routes ditemukan.")
        garis()
        return

    total = len(files)

    berhasil = 0

    gagal = 0

    for file in files:

        if fix_file(file):

            berhasil += 1

        else:

            gagal += 1

    garis()

    print("LAPORAN")

    print()

    print(f"Total File     : {total}")

    print(f"Berhasil       : {berhasil}")

    print(f"Gagal          : {gagal}")

    garis()

    if gagal == 0:

        print("SEMUA IMPORT SUDAH DIPERBAIKI")

    else:

        print("MASIH ADA FILE YANG BERMASALAH")

    garis()


# ==========================================================
# MAIN
# ==========================================================

def main():

    fix_imports()


if __name__ == "__main__":

    main()