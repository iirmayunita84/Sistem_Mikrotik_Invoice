from pathlib import Path

path = Path("core/core_pelanggan.py")

text = path.read_text(encoding="utf-8")

old = '''        # ==========================================
        # NORMALISASI JATUH TEMPO
        # ==========================================

        jatuh_tempo = (
            data.get("jatuh_tempo") or ""
        ).strip()

        if jatuh_tempo:

            # Kalau YYYY-MM-DD
            try:
                jatuh_tempo = datetime.strptime(
                    jatuh_tempo,
                    "%d/%m/%Y"
                ).strftime("%d/%m/%Y")

            except ValueError:

                # Kalau sudah DD/MM/YYYY
                try:
                    jatuh_tempo = datetime.strptime(
                        jatuh_tempo,
                        "%d/%m/%Y"
                    ).strftime("%d/%m/%Y")

                except ValueError:
                    pass
'''

new = '''        # ==========================================
        # NORMALISASI JATUH TEMPO
        # FORMAT INTERNAL: DD/MM/YYYY
        # ==========================================

        jatuh_tempo = (
            data.get("jatuh_tempo") or ""
        ).strip()

        if jatuh_tempo:

            # Format aplikasi: DD/MM/YYYY
            try:
                jatuh_tempo = datetime.strptime(
                    jatuh_tempo,
                    "%d/%m/%Y"
                ).strftime("%d/%m/%Y")

            except ValueError:

                # Kompatibel dengan input HTML YYYY-MM-DD
                try:
                    jatuh_tempo = datetime.strptime(
                        jatuh_tempo,
                        "%Y-%m-%d"
                    ).strftime("%d/%m/%Y")

                except ValueError:
                    jatuh_tempo = ""

        # Jika tanggal baru kosong/invalid,
        # pertahankan tanggal yang sudah ada di database.
        if not jatuh_tempo:

            cur.execute(
                "SELECT jatuh_tempo FROM pelanggan WHERE id=?",
                (pid,)
            )

            old_due = cur.fetchone()

            if old_due and old_due["jatuh_tempo"]:
                jatuh_tempo = old_due["jatuh_tempo"]
'''

if old not in text:
    print("ERROR: blok lama tidak ditemukan.")
    raise SystemExit(1)

text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

print("OK: blok normalisasi update_pelanggan() berhasil diperbaiki.")