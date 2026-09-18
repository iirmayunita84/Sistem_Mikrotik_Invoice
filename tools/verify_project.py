# verify_project.py   
"""
===========================================================
 VERIFY PROJECT
 Mikrotik Invoice Refactor Tool
===========================================================

Fungsi:

1. Cek struktur project
2. Validasi syntax Python
3. Cek Blueprint
4. Cek duplicate route
5. Cek import dasar

===========================================================
"""


from pathlib import Path
import ast
import re

# ==========================================================
# CONFIG
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

WEB_FILE = BASE_DIR / "web.py"

ROUTES_DIR = BASE_DIR / "routes"

# ==========================================================
# IGNORE FILE
# ==========================================================

IGNORE_FILES = {
    "web1.py",
    "web_debug.py",
    "web_backup_old.py",
    "web_before_clean_routes.py",
    "web_full_backup.py",
}

IGNORE_KEYWORDS = (
    "backup",
    "before_clean",
    "debug",
)

# ==========================================================
# UTIL
# ==========================================================
def garis():

    print("=" * 60)

def read_text(file):

    return file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

# ==========================================================
# CHECK FILE PYTHON
# ==========================================================
def check_python_syntax(file):

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

        return True, None


    except SyntaxError as e:

        return False, str(e)

def scan_python_files():

    files = []

    folders = [
        BASE_DIR,
        BASE_DIR / "routes",
        BASE_DIR / "core",
        BASE_DIR / "services",
        BASE_DIR / "utils",
    ]

    for folder in folders:

        if not folder.exists():
            continue

        for py in folder.glob("*.py"):

            name = py.name.lower()

            # abaikan file internal python
            if name.startswith("__"):
                continue

            # abaikan file tertentu
            if py.name in IGNORE_FILES:
                continue

            # abaikan file backup/debug
            if any(keyword in name for keyword in IGNORE_KEYWORDS):
                continue

            files.append(py)

    return sorted(set(files))
# ==========================================================
# VERIFY SYNTAX
# ==========================================================
def verify_syntax():


    print()

    print(
        "CHECK PYTHON SYNTAX"
    )


    errors = []


    for file in scan_python_files():


        ok, error = check_python_syntax(
            file
        )


        if ok:

            print(
                "[OK]",
                file.name
            )


        else:

            print(
                "[ERROR]",
                file.name
            )

            errors.append(
                {
                    "file": file,
                    "error": error
                }
            )


    return errors

# ==========================================================
# VERIFY BLUEPRINT
# ==========================================================
def verify_blueprints():


    print()

    print(
        "CHECK BLUEPRINT"
    )


    errors = []


    for file in ROUTES_DIR.glob(
        "*_routes.py"
    ):


        content = read_text(
            file
        )

        if not re.search(
            r'bp\s*=\s*Blueprint\(',
            content
        ):

            print(
                "[ERROR]",
                file.name,
                "tidak memiliki Blueprint"
            )


            errors.append(
                file.name
            )


        else:


            print(
                "[OK]",
                file.name
            )


    return errors

# ==========================================================
# CHECK DUPLICATE ROUTE
# ==========================================================
def check_duplicate_routes():

    print()
    print("CHECK DUPLICATE ROUTES")

    routes = {}
    duplicate = []

    pattern = re.compile(
        r'@\w+\.route\s*\(\s*[rf]?[\'"]([^\'"]+)',
        re.MULTILINE
    )

    for file in scan_python_files():

        content = read_text(file)

        matches = pattern.findall(content)

        for route in matches:

            if route not in routes:
                routes[route] = []

            routes[route].append(file.name)

    for route, files in sorted(routes.items()):

        unique_files = sorted(set(files))

        if len(unique_files) > 1:

            duplicate.append({
                "route": route,
                "files": unique_files
            })

            print(
                "[DUPLICATE]",
                route,
                "->",
                ", ".join(unique_files)
            )

    if not duplicate:
        print("[OK] Tidak ada duplicate route")

    return duplicate

# ==========================================================
# CHECK WEB REGISTER
# ==========================================================
def check_web_register():

    print()
    print("CHECK WEB BLUEPRINT REGISTER")

    if not WEB_FILE.exists():

        print("[ERROR] web.py tidak ditemukan")
        return False

    content = read_text(WEB_FILE)

    semua_ok = True

    # Scan semua file route
    for file in sorted(ROUTES_DIR.glob("*_routes.py")):

        # auth_routes.py -> auth_bp
        nama = file.stem.replace("_routes", "")
        bp_name = f"{nama}_bp"

        # import yang seharusnya ada
        import_text = (
            f"from routes.{file.stem} import bp as {bp_name}"
        )

        # register yang seharusnya ada
        register_text = (
            f"app.register_blueprint({bp_name})"
        )

        # -----------------------------
        # cek import
        # -----------------------------
        if import_text not in content:

            print(f"[ERROR] Import belum ada : {bp_name}")
            semua_ok = False

        else:

            print(f"[OK] Import : {bp_name}")

        # -----------------------------
        # cek register
        # -----------------------------
        if register_text not in content:

            print(f"[ERROR] Register belum ada : {bp_name}")
            semua_ok = False

        else:

            print(f"[OK] Register : {bp_name}")

    return semua_ok

# ==========================================================
# REPORT
# ==========================================================
def verify_project():


    garis()

    print(
        "VERIFY PROJECT"
    )

    garis()



    syntax_error = verify_syntax()

    blueprint_error = verify_blueprints()

    duplicate_error = check_duplicate_routes()

    register_error = not check_web_register()



    garis()

    print(
        "HASIL VERIFIKASI"
    )

    garis()



    gagal = 0



    if syntax_error:

        print(
            "Syntax Error :",
            len(syntax_error)
        )

        gagal += 1


    else:

        print(
            "Syntax : OK"
        )



    if blueprint_error:

        print(
            "Blueprint Error :",
            len(blueprint_error)
        )

        gagal += 1


    else:

        print(
            "Blueprint : OK"
        )



    if duplicate_error:

        print(
            "Duplicate Route :",
            len(duplicate_error)
        )

        gagal += 1


    else:

        print(
            "Duplicate Route : OK"
        )



    if register_error:

        print(
            "Register Blueprint : ERROR"
        )

        gagal += 1


    else:

        print(
            "Register Blueprint : OK"
        )



    garis()



    if gagal == 0:


        print(
            "PROJECT VALID ✅"
        )


    else:


        print(
            "PROJECT MASIH MEMILIKI MASALAH ❌"
        )


    garis()



    return gagal == 0

# ==========================================================
# MAIN
# ==========================================================


if __name__ == "__main__":

    verify_project()