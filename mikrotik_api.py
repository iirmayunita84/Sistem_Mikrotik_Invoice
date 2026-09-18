import os, sys, json
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageWin
import win32print
import win32ui
from tkinter import simpledialog
import win32con
import ipaddress
from datetime import datetime

# Optional RouterOS API
try:
    from routeros_api import RouterOsApiPool
except ImportError:
    RouterOsApiPool = None

# Optional ESC/POS USB driver
try:
    from escpos.printer import Usb
except Exception:
    Usb = None
import qrcode

# ===== Config dasar =====
POS_WIDTH_MM = 80
DPI = 203  # thermal printer rata-rata 203 dpi
POS_WIDTH_PX = int((POS_WIDTH_MM / 25.4) * DPI)

# ===== Load Font (pakai monospace bold biar jelas) =====
FONT_BOLD  = ImageFont.truetype("consolab.ttf", 32)   # Judul & highlight
FONT_BODY  = ImageFont.truetype("consolab.ttf", 28)   # Detail pelanggan
FONT_SMALL = ImageFont.truetype("consolab.ttf", 24)   # Footer kecil

# === Helper ===
def resource_path(relative_path):
    """Dapatkan path absolut (support kalau dibundle jadi exe PyInstaller)"""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config(config_file="config.json"):
    """Membaca config.json"""
    try:
        with open(resource_path(config_file), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Gagal load {config_file}: {e}")
        return {}
def get_pelanggan():
    # contoh dummy data
    return [
        {"nama_pelanggan": "Andi", "paket": "10Mbps", "harga": 100000,
         "no_hp": "08123456789", "jatuh_tempo": "2025-10-10", "usage": "2GB"},
        {"nama_pelanggan": "Budi", "paket": "20Mbps", "harga": 200000,
         "no_hp": "082233445566", "jatuh_tempo": "2025-10-12", "usage": "5GB"}
    ]
def get_account(cfg, router_id):
    """Ambil data router sesuai id"""
    routers = cfg.get("routers", [])
    for r in routers:
        if r["id"] == router_id:
            return r
    raise ValueError(f"[ERROR] Router '{router_id}' tidak ditemukan di config.json!")


# === Load config ===
cfg = load_config()
default_router = cfg["app"]["default_account"]
acc = get_account(cfg, default_router)

# Path aset
logo_path = resource_path(cfg["app"]["logo_file"])
qris_path = resource_path(cfg["app"]["qris_file"])

# Folder riwayat invoice
RIWAYAT_DIR = resource_path(cfg["app"]["riwayat_dir"])
os.makedirs(RIWAYAT_DIR, exist_ok=True)

# Debug info
print("✅ Config loaded")
print(f"Logo: {logo_path}")
print(f"QRIS: {qris_path}")
print(f"POS width: {cfg['app']['pos_width_mm']} mm")
print(
    f"Akun {acc.get('id','?')} "
    f"({acc.get('label', acc.get('id','?'))}) → "
    f"{acc.get('host','-')}:{acc.get('port','8728')}"
)

# Cek file logo/qris
if not os.path.exists(logo_path):
    print(f"⚠️ Peringatan: Logo tidak ditemukan di {logo_path}")
if not os.path.exists(qris_path):
    print(f"⚠️ Peringatan: QRIS tidak ditemukan di {qris_path}")


# ===== Helper Parsing Comment =====
def parse_comment(comment):
    data = {}
    key_map = {
        'nama': 'nama_pelanggan',
        'paket': 'paket',
        'harga': 'harga',
        'due': 'jatuh_tempo',
        'jatuh_tempo': 'jatuh_tempo',
        'no_hp': 'no_hp',
    }
    try:
        parts = [p for p in comment.split(';') if ':' in p]
        for part in parts:
            k, v = part.split(':', 1)
            k_clean = k.strip().lower()
            v_clean = v.strip()
            if k_clean in key_map:
                data[key_map[k_clean]] = v_clean
    except Exception as e:
        print(f"[ERROR] Gagal parse comment: {comment} -> {e}")
    return data

def validate_comment(comment):
    return bool(str(comment or "").strip())

def ip_in_target(ip_addr, target_str):
    try:
        if '/' not in target_str:
            return ip_addr == target_str
        return ipaddress.ip_address(ip_addr) in ipaddress.ip_network(target_str, strict=False)
    except:
        return False

# ===== Mikrotik Client =====
class MikrotikClient:
    def __init__(self, host, username, password, port=8728):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.api = None
        self.connection = None

    def connect(self):
        try:
            self.connection = RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                plaintext_login=True,
                use_ssl=False
            )
            self.api = self.connection.get_api()
            return True
        except Exception as e:
            print(f"[ERROR] Gagal konek ke {self.host}: {e}")
            return False

    def disconnect(self):
        try:
            if self.connection:
                self.connection.disconnect()
        except:
            pass

    def get_leases_with_comment(self):
        if not self.api:
            return []
        try:
            leases = self.api.get_resource('/ip/dhcp-server/lease').get()
            filtered = [l for l in leases if validate_comment(l.get('comment', ''))]
            for l in filtered:
                l['parsed'] = parse_comment(l.get('comment', ''))
            return filtered
        except Exception as e:
            print(f"[ERROR] Gagal ambil leases: {e}")
            return []

    def get_monthly_usage_gb(self, ip_addr):
        """Hitung total usage per IP dari queue simple (upload+download)"""
        if not self.api or not ip_addr:
            return 0.0
        try:
            queues = self.api.get_resource('/queue/simple').call('print', {'stats': ''})
            for q in queues:
                target = q.get('target', '') or q.get('dst', '')
                if ip_in_target(ip_addr, target):
                    tb = q.get('bytes')
                    if tb:
                        parts = tb.split('/')
                        total_bytes = sum(int(p) for p in parts if p.isdigit())
                        return round(total_bytes / (1024**3), 2)
        except:
            pass
        return 0.0

    def get_interface_usage_gb(self, interface_name=None):
        """Hitung usage per interface (upload+download)"""
        if not self.api:
            return {} if interface_name is None else 0.0
        usage = {}
        try:
            interfaces = self.api.get_resource('/interface').get()
            for intf in interfaces:
                name = intf.get('name')
                if interface_name and name != interface_name:
                    continue
                rx = int(intf.get('rx-byte', 0))
                tx = int(intf.get('tx-byte', 0))
                usage_gb = round((rx + tx) / (1024**3), 2)
                usage[name] = usage_gb
            if interface_name:
                return usage.get(interface_name, 0.0)
            return usage
        except:
            return {} if interface_name is None else 0.0


def load_pelanggan_dari_mikrotik_per_interface(client: MikrotikClient):
    if not client.connect():
        return []
    leases = client.get_leases_with_comment()
    pelanggan_list = []

    for lease in leases:
        data = lease.get('parsed', {})
        ip_addr = lease.get('address', '')

        usage_total_gb = client.get_monthly_usage_gb(ip_addr)
        usage_per_interface = {}
        if usage_total_gb == 0.0:
            usage_per_interface = client.get_interface_usage_gb()
            usage_total_gb = sum(usage_per_interface.values())
        if not usage_per_interface and usage_total_gb > 0:
            usage_per_interface = {'QueueSimple': usage_total_gb}

        usage_str = f"{usage_total_gb:.2f} GB" if usage_total_gb >= 1 else f"{usage_total_gb*1024:.2f} MB"

        pelanggan_list.append({
            "nama_pelanggan": data.get('nama_pelanggan', 'Unknown'),
            "paket": data.get('paket', '-'),
            "harga": int(data.get('harga', 0)),  # pastikan angka
            "no_hp": data.get('no_hp', '-'),
            "jatuh_tempo": data.get('jatuh_tempo', '-'),
            "ip": ip_addr,
            "usage_total": usage_str,
            "usage_per_interface": usage_per_interface
        })

    client.disconnect()
    return pelanggan_list
    
def update_usage_comment_per_interface(client: MikrotikClient):
    if not client.connect():
        return
    leases = client.get_leases_with_comment()

    for lease in leases:
        ip_addr = lease.get('address', '')

        usage_total_gb = client.get_monthly_usage_gb(ip_addr)
        usage_per_interface = {}
        if usage_total_gb == 0.0:
            usage_per_interface = client.get_interface_usage_gb()
            usage_total_gb = sum(usage_per_interface.values())
        if not usage_per_interface and usage_total_gb > 0:
            usage_per_interface = {'QueueSimple': usage_total_gb}

        usage_total_str = f"{usage_total_gb:.2f} GB" if usage_total_gb >= 1 else f"{usage_total_gb*1024:.2f} MB"
        usage_interface_strs = []
        for iface, gb in usage_per_interface.items():
            s = f"{gb:.2f} GB" if gb >= 1 else f"{gb*1024:.2f} MB"
            usage_interface_strs.append(f"{iface}: {s}")
        usage_full_str = f"Total: {usage_total_str}; " + '; '.join(usage_interface_strs)

        old_comment = lease.get('comment', '')
        comment_parts = [p.strip() for p in old_comment.split(';') if p.strip() and not p.strip().startswith('Usage:')]
        comment_parts.append(f"Usage: {usage_full_str}")
        new_comment = '; '.join(comment_parts)

        try:
            client.api.get_resource('/ip/dhcp-server/lease').call('set', {
                '.id': lease.get('.id'),
                'comment': new_comment
            })
        except:
            pass

    client.disconnect()
    
def generate_mikrotik_rsc(pelanggan_list, output_file="queue_pelanggan.rsc"):
    """
    Generate file .rsc untuk membuat simple queue di MikroTik per pelanggan.
    pelanggan_list: list of dict [{'nama_pelanggan': 'Ilyas', 'ip': '192.168.22.254'}, ...]
    """
    try:
        with open(output_file, "w") as f:
            f.write("# Auto-generated Mikrotik Simple Queue\n")
            f.write("# Import ke MikroTik dengan: /import queue_pelanggan.rsc\n")
            f.write("\n/queue simple\n")
            for p in pelanggan_list:
                nama = p['nama_pelanggan'].replace(" ", "_")
                ip = p.get('ip', '')
                if ip:
                    f.write(f'add name="{nama}" target={ip}/32 max-limit=20M/20M\n')
        print(f"[INFO] File {output_file} berhasil dibuat.")
    except Exception as e:
        print(f"[ERROR] Gagal membuat file RSC: {e}")
        
# ===== Variabel Global =====
last_selected_data = None   # data pelanggan yang dipilih dari tabel
latest_pdf_path = None      # path PDF terakhir yang dibuat

# ===== Fungsi Format Rupiah =====
def format_rupiah(angka):
    try:
        if angka is None or str(angka).strip() == "":
            return "Rp 0"
        angka = int(str(angka).replace('.', '').replace(',', '').split()[0])
        return f"Rp {angka:,}".replace(",", ".")
    except Exception:
        return f"Rp {angka}"

# ===== Buat Invoice PDF (Thermal 80mm) =====
def buat_invoice_pdf(data):
    global latest_pdf_path

    # Ukuran thermal printer 80mm
    POS_WIDTH = 80 * mm
    MARGIN = 10 * mm
    LINE_HEIGHT = 14

    # Estimasi tinggi halaman
    total_lines = 30
    POS_HEIGHT = (total_lines * LINE_HEIGHT) + 120

    # Output path
    filename = f"invoice_{data['nama_pelanggan'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_folder = cfg.get("pdf_output_folder") or os.path.join(os.getcwd(), "invoices")
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)

    # Buat PDF
    c = canvas.Canvas(output_path, pagesize=(POS_WIDTH, POS_HEIGHT))
    width, height = POS_WIDTH, POS_HEIGHT
    y = height - 20

    # Logo
    if os.path.exists(cfg["app"]["logo_file"]):
        logo_width = 40 * mm
        logo_height = 20 * mm
        x_center = (width - logo_width) / 2
        c.drawImage(cfg["app"]["logo_file"], x_center, y - logo_height,
                    width=logo_width, height=logo_height, mask='auto')
        y -= logo_height + 10

    # Judul
    c.setFont("Courier-Bold", 12)
    c.drawCentredString(width/2, y, "===== STRUK PEMBAYARAN =====")
    y -= LINE_HEIGHT * 2

    # Detail pelanggan (pakai monospace agar rapi)
    c.setFont("Courier", 10)
    details = [
        ("Nama", data['nama_pelanggan']),
        ("IP MikroTik", data.get('ip_mikrotik', '-')),
        ("Paket", data.get('paket', '-')),
        ("Tagihan", format_rupiah(data.get('harga', '0'))),
        ("Usage", data.get('usage', '0MB/0MB')),
        ("No. HP", data.get('no_hp', '-')),
        ("Jatuh Tempo", data.get('jatuh_tempo', '-')),
        ("Tanggal", datetime.now().strftime('%d/%m/%Y')),
        ("Metode Bayar", data.get('metode', 'Tunai')),
    ]

    for label, value in details:
        c.setFont("Courier-Bold", 10)
        c.drawString(MARGIN, y, f"{label:12}:")
        c.setFont("Courier", 10)
        c.drawString(MARGIN + 80, y, str(value))
        y -= LINE_HEIGHT

    # Garis
    y -= 5
    c.setFont("Courier-Bold", 9)
    c.drawCentredString(width/2, y, "-" * 32)
    y -= LINE_HEIGHT * 2

    # Footer
    c.setFont("Courier", 8)
    c.drawCentredString(width/2, y, "Terima kasih telah membayar tepat waktu.")
    y -= LINE_HEIGHT
    c.drawCentredString(width/2, y, "Jika ada kendala hubungi wa/tlp 082116090241")
    y -= LINE_HEIGHT * 2

    # QRIS
    if os.path.exists(cfg["app"]["qris_file"]):
        qris_size = 35 * mm
        x_center = (width - qris_size) / 2
        c.drawImage(cfg["app"]["qris_file"], x_center, y - qris_size,
                    width=qris_size, height=qris_size, mask='auto')
        y -= qris_size + 10
        c.setFont("Courier", 7)
        c.drawCentredString(width/2, y, "Scan QRIS untuk pembayaran digital")

    c.save()
    latest_pdf_path = output_path
    return latest_pdf_path
def preview_invoice_pdf(pdf_path, parent):
    try:
        images = convert_from_path(pdf_path, dpi=150)  # render PDF jadi gambar
        if not images:
            messagebox.showerror("Error", "Gagal membuka PDF.")
            return

        img = images[0]  # ambil halaman pertama
        img_tk = ImageTk.PhotoImage(img)

        # Buat window baru
        top = tk.Toplevel(parent)
        top.title("Preview Struk POS")

        lbl = tk.Label(top, image=img_tk)
        lbl.image = img_tk  # simpan referensi biar ga ke-GC
        lbl.pack()

        # Tombol cetak langsung
        btn = ttk.Button(top, text="🖨️ Cetak Struk", command=lambda: cetak_pdf(pdf_path))
        btn.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error Preview", str(e))
        

# ===== Render Struk (Preview & Print) =====
POS_WIDTH_PX = 576  # lebar thermal printer 80mm (default 203 dpi)

def format_rupiah(angka):
    """Format angka ke format Rupiah: Rp 1.234.567"""
    try:
        angka = int(str(angka).replace(".", "").replace(",", ""))
        return "Rp {:,}".format(angka).replace(",", ".")
    except:
        return str(angka)

# ====== Render Struk ke Gambar (untuk Preview) ======
POS_WIDTH_PX = 576  # lebar printer thermal 80mm

def render_struk(data):
    img = Image.new("L", (POS_WIDTH_PX, 2000), 255)  # putih
    draw = ImageDraw.Draw(img)
    y = 20

    # --- Logo ---
    logo_path = cfg.get("logo_file", "assets/logo.bmp")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("L")
        logo = logo.resize((500, 180))  # agak besar biar jelas
        x = (POS_WIDTH_PX - logo.width) // 2
        img.paste(logo, (x, y))
        y += logo.height + 25

    # --- Judul ---
    title = "===== STRUK PEMBAYARAN ====="
    bbox = draw.textbbox((0,0), title, font=FONT_BOLD)
    draw.text(((POS_WIDTH_PX-bbox[2])//2, y), title, font=FONT_BOLD, fill=0)
    y += 60

    # --- Detail (pakai monospace supaya titik dua rata) ---
    fields = [
        ("Nama", data.get("nama","-")),
        ("IP MikroTik", data.get("ip_mikrotik","-")),
        ("Paket", data.get("paket","-")),
        ("Tagihan", format_rupiah(data.get("tagihan","0"))),
        ("Usage", data.get("usage","-")),
        ("No. HP", data.get("no_hp","-")),
        ("Jatuh Tempo", data.get("jatuh_tempo","-")),
        ("Tanggal", datetime.now().strftime("%d/%m/%Y")),
        ("Metode Bayar", data.get("metode_bayar","Tunai")),
    ]
    for k,v in fields:
        line = f"{k:<12}: {v}"   # pakai fixed width (12 karakter) → rata
        draw.text((20, y), line, font=FONT_BODY, fill=0)
        y += 45   # jarak antar baris

    y += 10
    draw.line((20, y, POS_WIDTH_PX-20, y), fill=0, width=2)
    y += 25

    # --- Footer ---
    footer = [
        "Terima kasih telah membayar tepat waktu.",
        "Jika ada kendala hubungi 082116090241",
        "Scan QRIS untuk melakukan pembayaran "
    ]
    for msg in footer:
        bbox = draw.textbbox((0,0), msg, font=FONT_SMALL)
        draw.text(((POS_WIDTH_PX-bbox[2])//2, y), msg, font=FONT_SMALL, fill=0)
        y += 35

    y += 20

    # --- QRIS ---
    qris_path = cfg.get("qris_file", "assets/qris.png")
    if os.path.exists(qris_path):
        qr = Image.open(qris_path).convert("L")
        qr = qr.resize((300,300))  # agak besar
        x = (POS_WIDTH_PX - qr.width)//2
        img.paste(qr, (x,y))
        y += qr.height + 25

    return img.crop((0,0,POS_WIDTH_PX,y))

# ===== Preview Invoice (Tkinter) =====
def preview_invoice_only(path_pdf):
    try:
        POS_WIDTH_MM = 80
        PX_PER_MM = 3.78   # konversi mm → px (untuk monitor 96 DPI)
        canvas_w = int(POS_WIDTH_MM * PX_PER_MM)  # lebar canvas = 80mm

        # Buka PDF dan konversi jadi image (1 halaman)
        images = convert_from_path(path_pdf, poppler_path=cfg["poppler_path"], dpi=96)
        if not images:
            messagebox.showerror("Error", "Gagal mengubah PDF ke gambar.")
            return

        preview_win = tk.Toplevel()
        preview_win.title("Preview Invoice PDF (80mm Thermal)")

        # Ambil halaman pertama PDF
        img = images[0]
        ratio = canvas_w / img.width
        new_h = int(img.height * ratio)
        img = img.resize((canvas_w, new_h), Image.LANCZOS)

        # Convert ke Tkinter Image
        tk_img = ImageTk.PhotoImage(img)

        # Canvas preview
        canvas = tk.Canvas(preview_win, width=canvas_w, height=new_h, bg="white")
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        canvas.image = tk_img

        # Tombol cetak
        btn = ttk.Button(preview_win, text="🖨️ Cetak Sekarang", 
                         command=lambda: cetak_pdf(path_pdf))
        btn.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error Preview", str(e))


# ===== Cetak PDF via Windows =====
def cetak_pdf(path_pdf):
    try:
        import win32api
        printer_name = win32print.GetDefaultPrinter()
        win32api.ShellExecute(
            0,
            "print",
            path_pdf,
            f'"{printer_name}"',
            ".",
            0
        )
    except Exception as e:
        messagebox.showerror("Error Cetak", str(e))

# ====== Preview di Tkinter ======
def preview_struk(data):
    try:
        img = render_struk(data)

        # --- Scale down untuk preview ---
        max_width = 300
        scale = max_width / img.width
        new_size = (int(img.width * scale), int(img.height * scale))
        img_preview = img.resize(new_size, Image.LANCZOS)

        # convert ke format Tkinter
        img_tk = ImageTk.PhotoImage(img_preview)

        # bikin window baru
        top = tk.Toplevel()
        top.title("Preview Struk")

        label = tk.Label(top, image=img_tk)
        label.image = img_tk
        label.pack()

        # tombol cetak manual
        btn_cetak = ttk.Button(top, text="🖨️ Cetak Struk Sekarang",
                               command=lambda: [cetak_struk_win32print(data), top.destroy()])
        btn_cetak.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error", f"Gagal membuat preview struk:\n{e}")

# ===== Cetak ke Printer (Win32) =====
def cetak_struk_win32print(data, printer_name=None):
    img = render_struk(data)

    # konversi ke biner hitam-putih supaya tajam
    img_bw = img.convert("1")

    if not printer_name:
        printers = [p[2] for p in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )]

        def pilih_printer():
            nonlocal printer_name
            printer_name = combo.get()
            win.destroy()

        win = tk.Toplevel()
        win.title("Pilih Printer")
        win.geometry("350x120")
        tk.Label(win, text="Pilih printer untuk mencetak struk:", font=("Arial", 10)).pack(pady=5)

        combo = ttk.Combobox(win, values=printers, state="readonly", width=40)
        combo.pack(pady=5)
        if printers:
            combo.current(0)

        btn_ok = ttk.Button(win, text="OK", command=pilih_printer)
        btn_ok.pack(pady=5)

        win.wait_window()

        if not printer_name:
            print("[INFO] Cetak dibatalkan (tidak ada printer dipilih).")
            return

    try:
        hprinter = win32print.OpenPrinter(printer_name)
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)

        hdc.StartDoc("Struk Pembayaran")
        hdc.StartPage()

        dib = ImageWin.Dib(img_bw)   # sudah biner
        dib.draw(hdc.GetHandleOutput(), (0, 0, img_bw.width, img_bw.height))

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
        win32print.ClosePrinter(hprinter)

        messagebox.showinfo("Berhasil", f"✅ Struk berhasil dicetak ke {printer_name}")
        print(f"[INFO] Struk berhasil dicetak ke {printer_name}")

    except Exception as e:
        messagebox.showerror("Error", f"Gagal mencetak ke printer {printer_name}:\n{e}")
        print(f"[ERROR] Gagal mencetak ke printer {printer_name}: {e}")

# ===== GUI Handlers =====
mikrotik_clients = []
for r in cfg.get("routers", []):
    print(
        f"Router {r.get('id','?')} "
        f"({r.get('label', r.get('id','?'))}) → "
        f"{r.get('host','-')}:{r.get('port','8728')}"
    )
    mikrotik_clients.append(
        MikrotikClient(
            r.get("host","127.0.0.1"),
            r.get("username","admin"),
            r.get("password",""),
            r.get("port", 8728),
        )
    )



def update_table(ip):
    for i in tree.get_children():
        tree.delete(i)

    data_all = []
    if ip is None or ip == "Semua MikroTik":
        for client in mikrotik_clients:
            data_all.extend(load_pelanggan_dari_mikrotik_per_interface(client))
    else:
        client = next((c for c in mikrotik_clients if c.host == ip), None)
        if client:
            data_all = load_pelanggan_dari_mikrotik_per_interface(client)

    for row in data_all:
        tree.insert('', 'end', values=(
            row['nama_pelanggan'],
            row.get('paket', '-'),
            row.get('harga', 0),
            row.get('no_hp', '-'),
            row.get('jatuh_tempo', '-'),
            row.get('usage_total', '0MB/0MB')
        ))

    # Buat file RSC otomatis setiap refresh tabel
    generate_mikrotik_rsc(data_all)

def on_ip_selected(event):
    ip = combo_ip.get()
    update_table(ip)

def on_tree_select(event):
    global last_selected_data
    selected = tree.focus()
    if selected:
        values = tree.item(selected)['values']
        last_selected_data = {
            "nama_pelanggan": values[0],
            "paket": values[1],
            "harga": values[2],
            "no_hp": values[3],
            "jatuh_tempo": values[4],
            "usage": values[5],
        }
    else:
        last_selected_data = None

def on_buat_invoice_pdf():
    global latest_pdf_path, last_selected_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return
    
    data = {
        "nama_pelanggan": last_selected_data['nama_pelanggan'],
        "paket": last_selected_data['paket'],
        "harga": last_selected_data['harga'],
        "no_hp": last_selected_data['no_hp'],
        "jatuh_tempo": last_selected_data['jatuh_tempo'],
        "usage": last_selected_data['usage'],
        "ip_mikrotik": combo_ip.get(),  
        "metode": combo_metode.get() if combo_metode.get() else "Tunai",
    }

    latest_pdf_path = buat_invoice_pdf(data)
    messagebox.showinfo("Sukses", f"Invoice PDF berhasil dibuat di:\n{latest_pdf_path}")
    preview_invoice_only(latest_pdf_path)


def on_lihat_struk():
    global last_selected_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return
    data = {
        "nama": last_selected_data['nama_pelanggan'],
        "ip_mikrotik": combo_ip.get(),
        "paket": last_selected_data['paket'],
        "tagihan": last_selected_data['harga'],
        "usage": last_selected_data['usage'],
        "no_hp": last_selected_data['no_hp'],
        "jatuh_tempo": last_selected_data['jatuh_tempo'],
        "tanggal": datetime.now().strftime('%d/%m/%Y'),
        "metode": combo_metode.get() if combo_metode.get() else "Tunai",
    }
    preview_struk(data)

def on_cetak_struk():
    global last_selected_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return
    data = {
        "nama": last_selected_data['nama_pelanggan'],
        "ip_mikrotik": combo_ip.get(),
        "paket": last_selected_data['paket'],
        "tagihan": last_selected_data['harga'],
        "usage": last_selected_data['usage'],
        "no_hp": last_selected_data['no_hp'],
        "jatuh_tempo": last_selected_data['jatuh_tempo'],
        "tanggal": datetime.now().strftime('%d/%m/%Y'),
        "metode": combo_metode.get() if combo_metode.get() else "Tunai",
    }
    cetak_struk_win32print(data)

# ===== GUI Setup =====
root = tk.Tk()
root.title("Invoice WiFi - YUNITA NET")
root.geometry("800x500")

frame_top = ttk.Frame(root)
frame_top.pack(pady=10)

ttk.Label(frame_top, text="Pilih IP MikroTik:").pack(side="left", padx=5)

ip_list = ["Semua MikroTik"] + [c.host for c in mikrotik_clients]
combo_ip = ttk.Combobox(frame_top, values=ip_list, state="readonly", width=30)
combo_ip.pack(side="left")
combo_ip.bind("<<ComboboxSelected>>", on_ip_selected)

frame_kanan = ttk.Frame(root)
frame_kanan.pack(pady=10)

ttk.Label(frame_kanan, text="Metode Bayar:").pack(side="left", padx=5)
combo_metode = ttk.Combobox(frame_kanan, values=["Tunai","QRIS","Transfer","Belum Bayar"], state="readonly")
combo_metode.set("Belum Bayar")
combo_metode.pack(side="left")

columns = ('nama_pelanggan','paket','harga','no_hp','jatuh_tempo','usage')
tree = ttk.Treeview(root, columns=columns, show='headings')
for col in columns:
    tree.heading(col, text=col.replace('_',' ').title())
    tree.column(col, width=120)
tree.pack(fill=tk.BOTH, expand=True, padx=10)

combo_ip.current(0)
update_table(None)

tree.bind("<<TreeviewSelect>>", on_tree_select)

frame_btn = ttk.Frame(root)
frame_btn.pack(pady=10)

btn_buat_pdf = ttk.Button(frame_btn, text="🖨️ Buat & Preview Invoice (PDF)", command=on_buat_invoice_pdf)
btn_buat_pdf.pack(side="left", padx=5)

btn_lihat_pdf = ttk.Button(frame_btn, text="👁️ Lihat Invoice (PDF)", command=lambda: preview_invoice_only(latest_pdf_path) if latest_pdf_path else messagebox.showwarning("Belum Ada PDF", "Buat invoice dulu!"))
btn_lihat_pdf.pack(side="left", padx=5)

btn_lihat_struk = ttk.Button(frame_btn, text="👁️ Lihat Struk", command=on_lihat_struk)
btn_lihat_struk.pack(side="left", padx=5)

btn_cetak_struk = ttk.Button(frame_btn, text="🧾 Cetak Struk", command=on_cetak_struk)
btn_cetak_struk.pack(side="left", padx=5)

root.mainloop()

