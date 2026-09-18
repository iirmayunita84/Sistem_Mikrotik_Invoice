from pathlib import Path
import re


ROUTES = Path("../routes")


BLUEPRINTS = {
    "auth_routes.py": ("auth_bp", "auth"),
    "invoice_routes.py": ("invoice_bp", "invoice"),
    "misc_routes.py": ("misc_bp", "misc"),
    "pelanggan_routes.py": ("pelanggan_bp", "pelanggan"),
    "router_routes.py": ("router_bp", "router"),
    "setting_routes.py": ("setting_bp", "setting"),
    "transaksi_routes.py": ("transaksi_bp", "transaksi"),
}


for filename, (bp_name, bp_value) in BLUEPRINTS.items():

    file = ROUTES / filename

    if not file.exists():
        print("SKIP:", filename)
        continue


    print("Fix:", filename)


    text = file.read_text(
        encoding="utf-8"
    )


    # hapus semua deklarasi Blueprint lama
    text = re.sub(
        rf'{bp_name}\s*=\s*Blueprint\s*\([^)]*\)',
        '',
        text,
        flags=re.S
    )


    text = re.sub(
        r'bp\s*=\s*Blueprint\s*\([^)]*\)',
        '',
        text,
        flags=re.S
    )


    # tambahkan Blueprint satu kali setelah import
    header = f'''

{bp_name} = Blueprint(
    "{bp_value}",
    __name__
)

'''


    # cari posisi setelah import terakhir
    lines = text.splitlines()

    pos = 0

    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            pos = i + 1


    lines.insert(
        pos,
        header
    )


    text = "\n".join(lines)


    file.write_text(
        text,
        encoding="utf-8"
    )


    print("OK", filename)


print("=" * 50)
print("FIX BLUEPRINT SELESAI")
print("=" * 50)