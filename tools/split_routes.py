import ast
import os
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

WEB = BASE / "web.py"

ROUTES = BASE / "routes"

ROUTES.mkdir(exist_ok=True)

# ==========================================================
# Bersihkan file route lama
# ==========================================================

for py in ROUTES.glob("*_routes.py"):
    py.unlink()

FILES = {
    "auth_routes.py": [
        "/login",
        "/logout",
        "/aktivasi",
        "/setup",
    ],

    "pelanggan_routes.py": [
        "/pelanggan",
        "/bayar",
        "/tagihan",
    ],

    "invoice_routes.py": [
        "/invoice",
        "/cetak-pdf",
        "/print-thermal",
    ],

    "router_routes.py": [
        "/router",
        "/routers",
        "/mikrotik",
        "/sinkron",
        "/pppoe",
    ],

    "setting_routes.py": [
        "/setting",
    ],

    "transaksi_routes.py": [
        "/transaksi",
    ],
}
text = WEB.read_text(
    encoding="utf8",
    errors="ignore"
)

tree = ast.parse(text)

lines = text.splitlines()

route_blocks = []

for node in tree.body:

    if not isinstance(node, ast.FunctionDef):
        continue

    if not node.decorator_list:
        continue

    first = node.decorator_list[0]

    if not isinstance(first, ast.Call):
        continue

    if not hasattr(first.func, "attr"):
        continue

    if first.func.attr != "route":
        continue

    if not first.args:
        continue

    if not isinstance(first.args[0], ast.Constant):
        continue

    url = first.args[0].value

    start = min(
        d.lineno
        for d in node.decorator_list
    )

    end = node.end_lineno

    block = "\n".join(
        lines[start-1:end]
    )

    route_blocks.append(
        (
            url,
            start,
            end,
            block
        )
    )
def append_route(filename, block):

    file = ROUTES / filename

    if file.exists():

        old = file.read_text(
            encoding="utf8",
            errors="ignore"
        )

    else:

        old = ""

    if block in old:
        return

    if old.strip() == "":

        nama = file.stem.replace("_routes", "")

        old = f'''from flask import Blueprint

    bp = Blueprint("{nama}", __name__)

    '''

    old += "\n\n" + block + "\n"

    file.write_text(
        old,
        encoding="utf8"
    )

# ==========================================================
# Kelompokkan route ke file tujuan
# ==========================================================

report = []

for url, start, end, block in route_blocks:

    tujuan = "misc_routes.py"

    for filename, prefixes in FILES.items():

        cocok = False

        for prefix in prefixes:

            if url.startswith(prefix):
                tujuan = filename
                cocok = True
                break

        if cocok:
            break

    append_route(tujuan, block)

    report.append(
        f"{url:35} -> {tujuan}"
    )


# ==========================================================
# Tambahkan Blueprint jika belum ada
# ==========================================================

for py in ROUTES.glob("*_routes.py"):

    isi = py.read_text(
        encoding="utf8",
        errors="ignore"
    )

    isi = isi.replace(
        "@app.route",
        "@bp.route"
    )

    py.write_text(
        isi,
        encoding="utf8"
    )

print("=" * 60)
print("ROUTE BERHASIL DISALIN")
print("=" * 60)

for r in report:
    print(r)

print()
print("Folder :", ROUTES)