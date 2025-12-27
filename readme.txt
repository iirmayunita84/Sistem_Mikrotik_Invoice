=== Sistem Mikrotik Invoice ===

Aplikasi ini digunakan untuk membuat, preview, dan mencetak struk pembayaran pelanggan Mikrotik 
dengan dukungan logo, QRIS, dan konfigurasi yang bisa diubah sesuai kebutuhan.

-----------------------------------
📌 Fitur
-----------------------------------
1. Preview struk (menampilkan contoh struk di aplikasi)
2. Cetak struk ke printer thermal (80mm)
3. Simpan logo dan QRIS sesuai config.json
4. Edit konfigurasi (logo, QRIS, nama toko, footer) via GUI
5. Simpan PDF/riwayat invoice otomatis

-----------------------------------
📦 Instalasi
-----------------------------------
1. Pastikan Python 3.10+ sudah terinstal
2. Install requirements:
   pip install -r requirements.txt

3. Simpan file berikut dalam satu folder:
   - main.py
   - config.json
   - folder assets/ (isi: logo.bmp, qris.png)

4. Jalankan aplikasi:
   python main.py

-----------------------------------
⚙️ Konfigurasi
-----------------------------------
Config berada di file `config.json`. Contoh:

{
  "app": {
    "logo_file": "assets/logo.bmp",
    "qris_file": "assets/qris.png",
    "store_name": "Warung Internet Jaya",
    "store_address": "Jl. Raya No. 123, Jakarta",
    "footer_message": "Terima kasih telah membayar tepat waktu.",
    "store_contact": "082116090241",
    "riwayat_dir": "riwayat_invoice"
  }
}

-----------------------------------
💻 Build EXE
-----------------------------------
Gunakan pyinstaller:
   pyinstaller --onefile --noconsole main.py

File exe akan ada di folder `dist/`.

-----------------------------------
✉️ Kontak
-----------------------------------
Dibuat untuk sistem billing Mikrotik
