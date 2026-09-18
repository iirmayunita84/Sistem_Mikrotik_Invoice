
"""
===========================================================
 FIX BLUEPRINTS V2
 Mikrotik Invoice Refactor Tool
===========================================================

Fungsi:

1. Scan routes/
2. Membuat Blueprint otomatis
3. Convert app.route -> blueprint.route
4. Bersihkan import duplicate
5. Perbaiki url_for endpoint
6. Siapkan route untuk register_blueprints.py

===========================================================
"""


from pathlib import Path
import re



# ==========================================================
# CONFIG
# ==========================================================


BASE_DIR = Path(__file__).resolve().parent.parent

ROUTES_DIR = BASE_DIR / "routes"



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



def write_text(file, content):

    file.write_text(
        content,
        encoding="utf-8"
    )



# ==========================================================
# SCAN ROUTES
# ==========================================================


def scan_routes():

    return sorted(
        ROUTES_DIR.glob("*_routes.py")
    )



# ==========================================================
# BLUEPRINT NAME
# ==========================================================


def get_blueprint_name(file):

    name = file.stem

    name = name.replace(
        "_routes",
        ""
    )


    return f"{name}_bp"



# ==========================================================
# CLEAN FLASK IMPORT
# ==========================================================


def clean_flask_import(content):


    content = re.sub(
        r"from flask import Blueprint\s*\n",
        "",
        content
    )


    content = re.sub(
        r"from flask import \*",
        "from flask import *",
        content
    )


    if "from flask import *" in content:


        content = content.replace(
            "from flask import *",
            "from flask import *\nfrom flask import Blueprint",
            1
        )


    else:

        content = (
            "from flask import Blueprint\n"
            +
            content
        )


    return content



# ==========================================================
# ADD BLUEPRINT OBJECT
# ==========================================================


def add_blueprint_object(
        content,
        bp_name
):


    if f"{bp_name} = Blueprint" in content:

        return content



    block = f"""

{bp_name} = Blueprint(
    "{bp_name.replace('_bp','')}",
    __name__
)

"""


    return content + block



# ==========================================================
# REPLACE ROUTE
# ==========================================================


def replace_routes(
        content,
        bp_name
):


    content = re.sub(
        r"@app\.route",
        f"@{bp_name}.route",
        content
    )


    content = re.sub(
        r"@bp\.route",
        f"@{bp_name}.route",
        content
    )


    return content



# ==========================================================
# FIX URL_FOR
# ==========================================================


def fix_url_for(
        content,
        bp_name
):


    bp_prefix = bp_name.replace(
        "_bp",
        ""
    )


    def replace(match):

        endpoint = match.group(1)


        if "." in endpoint:

            return match.group(0)


        return (
            f'url_for("{bp_prefix}.{endpoint}")'
        )


    content = re.sub(
        r'url_for\("([^"]+)"\)',
        replace,
        content
    )


    return content



# ==========================================================
# PROCESS FILE
# ==========================================================


def fix_blueprint_file(file):


    print()

    print(
        "Processing:",
        file.name
    )


    content = read_text(
        file
    )


    bp_name = get_blueprint_name(
        file
    )


    # import

    content = clean_flask_import(
        content
    )


    # route decorator

    content = replace_routes(
        content,
        bp_name
    )


    # endpoint

    content = fix_url_for(
        content,
        bp_name
    )


    # blueprint object

    content = add_blueprint_object(
        content,
        bp_name
    )


    write_text(
        file,
        content
    )


    print(
        "Blueprint OK:",
        bp_name
    )



# ==========================================================
# MAIN
# ==========================================================


def fix_blueprints():


    garis()

    print(
        "FIX BLUEPRINT ROUTES V2"
    )

    garis()



    files = scan_routes()



    if not files:

        print(
            "Folder routes kosong"
        )

        return



    for file in files:

        fix_blueprint_file(
            file
        )



    garis()

    print(
        "FIX BLUEPRINT SELESAI"
    )

    garis()



if __name__ == "__main__":

    fix_blueprints()