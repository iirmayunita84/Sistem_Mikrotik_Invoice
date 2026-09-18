from pathlib import Path

path = Path(r"templates\pelanggan_manual_edit.html")
text = path.read_text(encoding="utf-8")

old = """tanggalText.value =
                     month +
                     "/" +
                     day +
                     "/" +
                     year;"""

new = """tanggalText.value =
                     day +
                     "/" +
                     month +
                     "/" +
                     year;"""

if old in text:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("OK: konversi kalender keluar sudah diperbaiki.")
else:
    # Cari berdasarkan baris agar tidak tergantung jumlah spasi
    lines = text.splitlines(True)

    ditemukan = False

    for i in range(len(lines) - 6):
        gabungan = "".join(lines[i:i+6])

        if (
            "tanggalText.value" in gabungan
            and "month +" in gabungan
            and "day +" in gabungan
            and "year;" in gabungan
        ):
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]

            lines[i:i+6] = [
                indent + "tanggalText.value =\n",
                indent + "    day +\n",
                indent + '    "/" +\n',
                indent + "    month +\n",
                indent + '    "/" +\n',
                indent + "    year;\n"
            ]

            ditemukan = True
            break

    if not ditemukan:
        raise SystemExit(
            "ERROR: blok tanggalText.value tidak ditemukan."
        )

    path.write_text("".join(lines), encoding="utf-8")
    print("OK: konversi kalender keluar diperbaiki berdasarkan struktur kode.")