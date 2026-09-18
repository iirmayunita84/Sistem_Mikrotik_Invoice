import os
import re


ROUTE_DIR = r"D:\mikrotik_invoice\routes"


HEADER = {
    "auth_routes.py": "auth",
    "invoice_routes.py": "invoice",
    "misc_routes.py": "misc",
    "pelanggan_routes.py": "pelanggan",
    "router_routes.py": "router",
    "setting_routes.py": "setting",
    "transaksi_routes.py": "transaksi",
}


COMMON_IMPORT = """
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory
)

import os
import logging
from datetime import datetime
from urllib.parse import quote

"""


def clean_file(path, name):

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()


    # hapus semua import rusak sampai blueprint
    pos = text.find("@")

    if pos == -1:
        print("SKIP", name)
        return


    routes = text[pos:]


    bpname = HEADER[name]


    new_text = COMMON_IMPORT + f"""

bp = Blueprint("{bpname}", __name__)

""" + routes


    # ganti auth_bp menjadi bp dll
    new_text = re.sub(
        rf"{bpname}_bp",
        "bp",
        new_text
    )


    with open(path,"w",encoding="utf-8") as f:
        f.write(new_text)


    print("FIX",name)



for file in HEADER:

    clean_file(
        os.path.join(ROUTE_DIR,file),
        file
    )


print("="*50)
print("IMPORT ROUTE CLEAN SELESAI")
print("="*50)