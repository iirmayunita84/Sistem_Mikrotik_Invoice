from pathlib import Path

file = Path("pelanggan_routes.py")

lines = file.read_text(encoding="utf-8").splitlines()

hasil = []
sudah = set()

for line in lines:
    if line.startswith("import ") or line.startswith("from "):
        if line not in sudah:
            hasil.append(line)
            sudah.add(line)
    else:
        hasil.append(line)

file.write_text("\n".join(hasil), encoding="utf-8")

print("Selesai")