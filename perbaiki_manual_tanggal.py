from pathlib import Path

path = Path(r"templates\pelanggan_manual_edit.html")
text = path.read_text(encoding="utf-8")


# =========================================================
# 1. PERBAIKI REGEX NORMALISASI
# =========================================================

old = r"/^\\d{4}-\\d{2}-\\d{2}$/.test(tanggalAwal)"
new = r"/^\d{4}-\d{2}-\d{2}$/.test(tanggalAwal)"

print("Regex normalisasi ditemukan:", text.count(old))

if text.count(old) == 1:
    text = text.replace(old, new, 1)
elif text.count(new) == 1:
    print("Regex normalisasi sudah benar.")
else:
    raise SystemExit("ERROR: regex normalisasi tidak ditemukan.")


# =========================================================
# 2. PERBAIKI VALIDASI DD/MM/YYYY
# =========================================================

old = """                tanggalText.value =
                    month +
                    "/" +
                    day +
                    "/" +
                    year;"""

new = """                tanggalText.value =
                    day +
                    "/" +
                    month +
                    "/" +
                    year;"""
print("Blok validasi ditemukan:", text.count(old))

if text.count(old) == 1:
    text = text.replace(old, new, 1)
elif new in text:
    print("Validasi DD/MM/YYYY sudah benar.")
else:
    raise SystemExit("ERROR: blok validasi tidak ditemukan.")


# =========================================================
# 3. PERBAIKI KONVERSI:
# DD/MM/YYYY -> YYYY-MM-DD
# =========================================================

old = """                    kalender.value =
                        parts[2] +
                        "-" +
                        parts[0] +
                        "-" +
                        parts[1];"""

new = """                    kalender.value =
                        parts[2] +
                        "-" +
                        parts[1] +
                        "-" +
                        parts[0];"""

print("Konversi kalender masuk ditemukan:", text.count(old))

if text.count(old) == 1:
    text = text.replace(old, new, 1)
elif new in text:
    print("Konversi kalender masuk sudah benar.")
else:
    raise SystemExit("ERROR: konversi kalender masuk tidak ditemukan.")


# =========================================================
# 4. PERBAIKI KONVERSI:
# YYYY-MM-DD -> DD/MM/YYYY
# =========================================================

old = """                 tanggalText.value =
                     month +
                     "/" +
                     day +
                     "/" +
                     year;"""

new = """                 tanggalText.value =
                     day +
                     "/" +
                     month +
                     "/" +
                     year;"""

print("Konversi kalender keluar ditemukan:", text.count(old))

if text.count(old) == 1:
    text = text.replace(old, new, 1)
elif new in text:
    print("Konversi kalender keluar sudah benar.")
else:
    raise SystemExit("ERROR: konversi kalender keluar tidak ditemukan.")


# =========================================================
# SIMPAN
# =========================================================

path.write_text(text, encoding="utf-8")

print()
print("OK: seluruh logika tanggal manual sudah DD/MM/YYYY.")