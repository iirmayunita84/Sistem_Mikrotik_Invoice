import sqlite3
import os
import shutil
import re
import sys
from datetime import datetime

DB = r"C:\Users\yunit\AppData\Roaming\MikrotikInvoice\database.db"
BACKUP = r"C:\Users\yunit\AppData\Roaming\MikrotikInvoice\database_sebelum_perbaikan_otomatis.db"


def konversi_tanggal_lama(tanggal):
    if not tanggal:
        return tanggal, False

    tanggal = str(tanggal).strip()

    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", tanggal)
    if not m:
        return tanggal, False

    a = int(m.group(1))
    b = int(m.group(2))
    tahun = m.group(3)

    # Sudah DD/MM/YYYY
    if a > 12 and b <= 12:
        return tanggal, False

    # Jelas MM/DD/YYYY
    if b > 12 and a <= 12:
        return "%02d/%02d/%s" % (b, a, tahun), True

    # Data legacy yang sudah kita identifikasi:
    # 10/06/2026 = 06/10/2026
    if a == 10 and b == 6 and tahun == "2026":
        return "%02d/%02d/%s" % (b, a, tahun), True

    return tanggal, False


def hitung_status(tanggal):
    if not tanggal:
        return "Belum Bayar"

    try:
        jatuh_tempo = datetime.strptime(
            tanggal, "%d/%m/%Y"
        ).date()
    except ValueError:
        return "Belum Bayar"

    hari_ini = datetime.now().date()

    if hari_ini >= jatuh_tempo:
        return "ISOLIR"

    return "Belum Bayar"


def tampilkan_data(cur):
    print()
    print("=" * 70)
    print("DATA PELANGGAN SETELAH PERBAIKAN")
    print("=" * 70)

    rows = cur.execute(
        """
        SELECT nama, jatuh_tempo, status
        FROM pelanggan
        ORDER BY nama
        """
    ).fetchall()

    for row in rows:
        print(
            "%-25s | %-10s | %s"
            % (
                row[0],
                row[1] or "",
                row[2] or ""
            )
        )


print("=" * 70)
print("PERBAIKAN OTOMATIS TANGGAL DATA PELANGGAN LAMA")
print("=" * 70)
print("Database :", DB)
print("Backup   :", BACKUP)
print()

if not os.path.exists(DB):
    print("ERROR: database tidak ditemukan.")
    sys.exit(1)

# ------------------------------------------------------------
# BACKUP
# ------------------------------------------------------------

if not os.path.exists(BACKUP):
    shutil.copy2(DB, BACKUP)
    print("Backup tambahan berhasil dibuat.")
else:
    print("Backup tambahan sudah tersedia.")

print()

conn = sqlite3.connect(DB)
cur = conn.cursor()

# ------------------------------------------------------------
# BACA DATA DHCP
# ------------------------------------------------------------

dhcp_changes = []

rows = cur.execute(
    "SELECT id, nama, due FROM dhcp_clients ORDER BY nama"
).fetchall()

for row in rows:
    lama = row[2]
    baru, berubah = konversi_tanggal_lama(lama)

    if berubah:
        dhcp_changes.append(
            (row[0], row[1], lama, baru)
        )

# ------------------------------------------------------------
# BACA DATA PELANGGAN
# ------------------------------------------------------------

pelanggan_changes = []

rows = cur.execute(
    """
    SELECT id, nama, jatuh_tempo, status
    FROM pelanggan
    ORDER BY nama
    """
).fetchall()

for row in rows:
    lama = row[2]
    baru, berubah = konversi_tanggal_lama(lama)

    if berubah:
        status_lama = row[3]
        status_baru = hitung_status(baru)

        pelanggan_changes.append(
            (
                row[0],
                row[1],
                lama,
                baru,
                status_lama,
                status_baru
            )
        )

# ------------------------------------------------------------
# TAMPILKAN PREVIEW
# ------------------------------------------------------------

print("-" * 70)
print("PERUBAHAN DHCP")
print("-" * 70)

if dhcp_changes:
    for row in dhcp_changes:
        print(
            "[DHCP] %-25s : %s -> %s"
            % (row[1], row[2], row[3])
        )
else:
    print("Tidak ada perubahan DHCP.")

print()

print("-" * 70)
print("PERUBAHAN PELANGGAN")
print("-" * 70)

if pelanggan_changes:
    for row in pelanggan_changes:
        print(
            "[PELANGGAN] %-25s : %s -> %s | %s -> %s"
            % (
                row[1],
                row[2],
                row[3],
                row[4],
                row[5]
            )
        )
else:
    print("Tidak ada perubahan pelanggan.")

print()
print("=" * 70)
print("RINGKASAN")
print("=" * 70)
print("DHCP       :", len(dhcp_changes))
print("Pelanggan  :", len(pelanggan_changes))
print()

# ------------------------------------------------------------
# MODE PREVIEW
# ------------------------------------------------------------

if "--fix" not in sys.argv:
    print("MODE: PREVIEW")
    print()
    print("BELUM ADA DATA YANG DIUBAH.")
    print()
    print("Jika hasil di atas benar, jalankan:")
    print()
    print("python perbaiki_tanggal_lama.py --fix")
    print()

    conn.close()
    input("Tekan ENTER untuk keluar...")
    sys.exit(0)

# ------------------------------------------------------------
# MODE FIX
# ------------------------------------------------------------

print("=" * 70)
print("MODE: PERBAIKAN OTOMATIS")
print("=" * 70)
print()

try:
    # 1. Perbaiki dhcp_clients
    for row in dhcp_changes:
        cur.execute(
            """
            UPDATE dhcp_clients
            SET due = ?
            WHERE id = ?
            """,
            (row[3], row[0])
        )

    # 2. Perbaiki pelanggan + status
    for row in pelanggan_changes:
        cur.execute(
            """
            UPDATE pelanggan
            SET jatuh_tempo = ?, status = ?
            WHERE id = ?
            """,
            (row[3], row[5], row[0])
        )

    conn.commit()

    print("PERBAIKAN BERHASIL DISIMPAN.")
    print()
    print("DHCP diperbaiki      :", len(dhcp_changes))
    print("Pelanggan diperbaiki :", len(pelanggan_changes))

except Exception as e:
    conn.rollback()
    print()
    print("ERROR SAAT PERBAIKAN:")
    print(str(e))
    conn.close()
    sys.exit(1)

# ------------------------------------------------------------
# VERIFIKASI
# ------------------------------------------------------------

print()
print("=" * 70)
print("VERIFIKASI DATABASE")
print("=" * 70)

# Cek DHCP
print()
print("[DHCP CLIENTS]")

rows = cur.execute(
    """
    SELECT nama, due
    FROM dhcp_clients
    ORDER BY nama
    """
).fetchall()

for row in rows:
    print(
        "%-25s | %s"
        % (row[0], row[1] or "")
    )

# Cek pelanggan
tampilkan_data(cur)

conn.close()

print()
print("=" * 70)
print("SELESAI")
print("=" * 70)
print()
print("Backup tersedia:")
print(BACKUP)
print()
input("Tekan ENTER untuk keluar...")