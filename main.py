# main.py - Sistem Mikrotik Invoice (rapi + fitur comment edit)
import os
import sys
import json
import ipaddress
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageWin
import win32print
import win32ui
from settings_window import open_settings_window
from ttkbootstrap import Style
import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
import ttkbootstrap as tb

# Optional libs (jika ada)

try:
    from routeros_api import RouterOsApiPool
except ImportError:
    RouterOsApiPool = None

# ========== Utility: resource path & config ==========
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config(config_file="config.json"):
    try:
        with open(resource_path(config_file), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Gagal load config.json: {e} - pakai config default minimal")
        return {
            "app": {
                "logo_file": "assets/logo.bmp",
                "qris_file": "assets/qris.png",
                "riwayat_dir": "riwayat",
                "pdf_output_folder": "invoices",
                # "poppler_path": "poppler/Library/bin"
            },
            "routers": []
        }

cfg = load_config()

# Ensure riwayat dir exists
RIWAYAT_DIR = resource_path(cfg["app"].get("riwayat_dir", "riwayat"))
os.makedirs(RIWAYAT_DIR, exist_ok=True)

# ========== Font loading safe ==========
def load_font(path, size):
    try:
        return ImageFont.truetype(resource_path(path), size)
    except Exception:
        return ImageFont.load_default()

FONT_BOLD = load_font("consolab.ttf", 32)
FONT_BODY = load_font("consolab.ttf", 28)
FONT_SMALL = load_font("consolab.ttf", 24)

# ========== Helpers ==========
def format_rupiah(angka):
    try:
        if angka is None or str(angka).strip() == "":
            return "Rp 0"
        angka_int = int(str(angka).replace('.', '').replace(',', '').split()[0])
        return f"Rp {angka_int:,}".replace(",", ".")
    except Exception:
        return f"Rp {angka}"

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

def build_comment_from_dict(d):
    """
    Build stable ordered comment string from dict
    """
    if not d: return ""
    parts = []
    for k in ('nama_pelanggan','paket','harga','jatuh_tempo','no_hp','iface','usage'):
        if k in d and d[k] is not None and str(d[k]).strip() != "":
            keyname = k
            if k == 'nama_pelanggan': keyname = 'nama'
            if k == 'jatuh_tempo': keyname = 'due'
            if k == 'no_hp': keyname = 'no_hp'
            if k == 'usage': keyname = 'Usage'
            parts.append(f"{keyname}:{d[k]}")
    for k,v in d.items():
        if k not in ('nama_pelanggan','paket','harga','jatuh_tempo','no_hp','iface','usage'):
            parts.append(f"{k}:{v}")
    return '; '.join(parts)

# ========== Mikrotik client (jika routeros_api ada) ==========
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

    # ---- New: set comment helpers ----
    def set_lease_comment_by_id(self, lease_id, comment):
        if not self.api or not lease_id:
            return False
        try:
            self.api.get_resource('/ip/dhcp-server/lease').call('set', {'.id': lease_id, 'comment': comment})
            return True
        except Exception as e:
            print(f"[ERROR] Gagal set comment (.id={lease_id}): {e}")
            return False

    def set_lease_comment_by_address(self, address, comment):
        if not self.api or not address:
            return False
        try:
            res = self.api.get_resource('/ip/dhcp-server/lease')
            leases = res.get()
            target = next((l for l in leases if l.get('address') == address), None)
            if not target:
                print(f"[WARN] Lease untuk address {address} tidak ditemukan.")
                return False
            lease_id = target.get('.id')
            return self.set_lease_comment_by_id(lease_id, comment)
        except Exception as e:
            print(f"[ERROR] Gagal set comment (address={address}): {e}")
            return False

# build mikrotik_clients list from config
mikrotik_clients = []
for r in cfg.get("routers", []):
    mikrotik_clients.append(MikrotikClient(r.get("host","127.0.0.1"),
                                           r.get("username","admin"),
                                           r.get("password",""),
                                           r.get("port",8728)))

# ========== Local manual customers store ==========
CUSTOMERS_FILE = resource_path("customers.json")

def load_manual_customers():
    try:
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print("[WARN] Gagal load customers.json:", e)
    return []

def save_manual_customers(lst):
    try:
        with open(CUSTOMERS_FILE, "w", encoding="utf-8") as f:
            json.dump(lst, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[ERROR] Gagal simpan customers.json:", e)

manual_customers = load_manual_customers()

# ========== Generate RSC ==========
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

# ========== Invoice PDF ==========
def buat_invoice_pdf(data, target_path=None):
    POS_WIDTH = 80 * mm
    MARGIN = 10 * mm
    LINE_HEIGHT = 14
    total_lines = 30
    POS_HEIGHT = (total_lines * LINE_HEIGHT) + 120

    if target_path:
        output_path = target_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    else:
        filename = f"invoice_{data.get('nama_pelanggan','unknown').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_folder = cfg["app"].get("pdf_output_folder") or os.path.join(os.getcwd(), "invoices")
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, filename)

    c = canvas.Canvas(output_path, pagesize=(POS_WIDTH, POS_HEIGHT))
    width, height = POS_WIDTH, POS_HEIGHT
    y = height - 20

    logo_cfg_path = resource_path(cfg["app"].get("logo_file","assets/logo.bmp"))
    if os.path.exists(logo_cfg_path):
        try:
            logo_width = 40 * mm
            logo_height = 20 * mm
            x_center = (width - logo_width) / 2
            c.drawImage(logo_cfg_path, x_center, y - logo_height, width=logo_width, height=logo_height, mask='auto')
            y -= logo_height + 10
        except Exception as e:
            print("[WARN] Gagal draw logo:", e)

    c.setFont("Courier-Bold", 12)
    c.drawCentredString(width/2, y, "===== STRUK PEMBAYARAN =====")
    y -= LINE_HEIGHT * 2

    c.setFont("Courier", 10)
    details = [
        ("Nama", data.get('nama_pelanggan') or data.get('nama') or "-"),
        ("IP MikroTik", data.get('ip_mikrotik', '-')),
        ("Paket", data.get('paket', '-')),
        ("Tagihan", format_rupiah(data.get('harga', data.get('tagihan', 0)))),
        ("Usage", data.get('usage', '-')),
        ("No. HP", data.get('no_hp', '-')),
        ("Jatuh Tempo", data.get('jatuh_tempo', '-')),
        ("Tanggal", data.get('tanggal', datetime.now().strftime('%d/%m/%Y'))),
        ("Metode Bayar", data.get('metode_bayar', data.get('metode', 'Tunai'))),
    ]

    for label, value in details:
        c.setFont("Courier-Bold", 10)
        c.drawString(MARGIN, y, f"{label:12}:")
        c.setFont("Courier", 10)
        c.drawString(MARGIN + 80, y, str(value))
        y -= LINE_HEIGHT

    y -= 5
    c.setFont("Courier-Bold", 9)
    c.drawCentredString(width/2, y, "-" * 32)
    y -= LINE_HEIGHT * 2

    c.setFont("Courier", 8)
    c.drawCentredString(width/2, y, "Terima kasih telah membayar tepat waktu.")
    y -= LINE_HEIGHT
    c.drawCentredString(width/2, y, "Jika ada kendala hubungi wa/tlp 082116090241")
    y -= LINE_HEIGHT * 2

    qris_cfg = resource_path(cfg["app"].get("qris_file","assets/qris.png"))
    if os.path.exists(qris_cfg):
        try:
            qris_size = 35 * mm
            x_center = (width - qris_size) / 2
            c.drawImage(qris_cfg, x_center, y - qris_size, width=qris_size, height=qris_size, mask='auto')
            y -= qris_size + 10
            c.setFont("Courier", 7)
            c.drawCentredString(width/2, y, "Scan QRIS untuk pembayaran digital")
        except Exception as e:
            print("[WARN] Gagal draw QRIS:", e)

    c.save()
    return output_path

# ========== Render struk ke gambar (untuk preview & print) ==========
POS_WIDTH_PX = 576

def render_struk(data):
    img = Image.new("L", (POS_WIDTH_PX, 2000), 255)
    draw = ImageDraw.Draw(img)
    y = 20

    logo_path = resource_path(cfg["app"].get("logo_file","assets/logo.bmp"))
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("L")
            logo = logo.resize((500, 180))
            x = (POS_WIDTH_PX - logo.width) // 2
            img.paste(logo, (x, y))
            y += logo.height + 25
        except Exception:
            pass

    title = "===== STRUK PEMBAYARAN ====="
    bbox = draw.textbbox((0,0), title, font=FONT_BOLD)
    draw.text(((POS_WIDTH_PX-bbox[2])//2, y), title, font=FONT_BOLD, fill=0)
    y += 60

    fields = [
        ("Nama", data.get("nama_pelanggan") or data.get("nama","-")),
        ("IP MikroTik", data.get("ip_mikrotik","-")),
        ("Paket", data.get("paket","-")),
        ("Tagihan", format_rupiah(data.get("harga", data.get("tagihan", 0)))),
        ("Usage", data.get("usage","-")),
        ("No. HP", data.get("no_hp","-")),
        ("Jatuh Tempo", data.get("jatuh_tempo","-")),
        ("Tanggal", data.get("tanggal", datetime.now().strftime("%d/%m/%Y"))),
        ("Metode Bayar", data.get("metode_bayar", data.get("metode","Tunai"))),
    ]
    for k,v in fields:
        line = f"{k:<12}: {v}"
        draw.text((20, y), line, font=FONT_BODY, fill=0)
        y += 35

    y += 10
    draw.line((20, y, POS_WIDTH_PX-20, y), fill=0, width=2)
    y += 25

    footer = [
        "Terima kasih telah membayar tepat waktu.",
        "Jika ada kendala hubungi 082116090241",
        "Scan QRIS untuk melakukan pembayaran "
    ]
    for msg in footer:
        bbox = draw.textbbox((0,0), msg, font=FONT_SMALL)
        draw.text(((POS_WIDTH_PX-bbox[2])//2, y), msg, font=FONT_SMALL, fill=0)
        y += 30

    y += 20
    qris_path = resource_path(cfg["app"].get("qris_file","assets/qris.png"))
    if os.path.exists(qris_path):
        try:
            qr = Image.open(qris_path).convert("L")
            qr = qr.resize((200,200))
            x = (POS_WIDTH_PX - qr.width)//2
            img.paste(qr, (x,y))
            y += qr.height + 25
        except Exception:
            pass

    return img.crop((0,0,POS_WIDTH_PX,y))

# ========== Preview PDF helper (poppler optional) ==========
def preview_invoice_only(path_pdf, parent=None):
    try:
        poppler_path = cfg["app"].get("poppler_path")
        if poppler_path:
            images = convert_from_path(path_pdf, poppler_path=resource_path(poppler_path), dpi=96)
        else:
            images = convert_from_path(path_pdf, dpi=96)

        if not images:
            messagebox.showerror("Error", "Gagal mengubah PDF ke gambar.")
            return

        img = images[0]
        preview_win = tk.Toplevel(parent or root)
        preview_win.title("Preview Invoice PDF (80mm Thermal)")
        POS_WIDTH_MM = 80
        PX_PER_MM = 3.78
        canvas_w = int(POS_WIDTH_MM * PX_PER_MM)

        ratio = canvas_w / img.width
        new_h = int(img.height * ratio)
        img = img.resize((canvas_w, new_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)

        canvas = tk.Canvas(preview_win, width=canvas_w, height=new_h, bg="white")
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        canvas.image = tk_img

        btn = ttk.Button(preview_win, text="🖨️ Cetak Sekarang", command=lambda: cetak_pdf(path_pdf))
        btn.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Error Preview", str(e))

# ========== Cetak PDF via Windows ==========
def cetak_pdf(path_pdf):
    try:
        import win32api
        printer_name = win32print.GetDefaultPrinter()
        win32api.ShellExecute(0, "print", path_pdf, f'"{printer_name}"', ".", 0)
    except Exception as e:
        messagebox.showerror("Error Cetak", str(e))

# ========== Cetak struk ke printer (win32) ==========
def cetak_struk_win32print(data, printer_name=None):
    img = render_struk(data)
    img_bw = img.convert("1")

    if not printer_name:
        printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
        win = tk.Toplevel()
        win.title("Pilih Printer")
        tk.Label(win, text="Pilih printer untuk mencetak struk:", font=("Arial", 10)).pack(pady=5)
        combo = ttk.Combobox(win, values=printers, state="readonly", width=50)
        combo.pack(pady=5)
        if printers:
            combo.current(0)
        def pilih():
            nonlocal printer_name
            printer_name = combo.get()
            win.destroy()
        ttk.Button(win, text="OK", command=pilih).pack(pady=5)
        win.wait_window()
        if not printer_name:
            messagebox.showinfo("Info", "Cetak dibatalkan (tidak ada printer dipilih).")
            return

    try:
        hprinter = win32print.OpenPrinter(printer_name)
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        hdc.StartDoc("Struk Pembayaran")
        hdc.StartPage()
        dib = ImageWin.Dib(img_bw)
        dib.draw(hdc.GetHandleOutput(), (0, 0, img_bw.width, img_bw.height))
        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
        win32print.ClosePrinter(hprinter)
        messagebox.showinfo("Berhasil", f"✅ Struk berhasil dicetak ke {printer_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mencetak: {e}")

def ip_in_target(ip_addr, target_str):
    try:
        if '/' not in target_str:
            return ip_addr == target_str
        return ipaddress.ip_address(ip_addr) in ipaddress.ip_network(target_str, strict=False)
    except:
        return False

# ========== Load pelanggan from Mikrotik and manual ==========
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

def collect_all_pelanggan(selected_ip=None):
    data_all = []
    for c in manual_customers:
        data_all.append({
            "nama_pelanggan": c.get("nama_pelanggan"),
            "paket": c.get("paket","-"),
            "harga": int(c.get("harga",0)),
            "no_hp": c.get("no_hp","-"),
            "jatuh_tempo": c.get("jatuh_tempo","-"),
            "ip": c.get("ip",""),
            "usage_total": c.get("usage_total","-")
        })
    if selected_ip is None or selected_ip == "Semua MikroTik":
        for client in mikrotik_clients:
            data_all.extend(load_pelanggan_dari_mikrotik_per_interface(client))
    else:
        client = next((c for c in mikrotik_clients if c.host == selected_ip), None)
        if client:
            data_all.extend(load_pelanggan_dari_mikrotik_per_interface(client))
    return data_all

# ========== GUI & Handlers ==========
root = tb.Window(themename="cyborg") 
root.title("💻 Sistem Mikrotik Invoice")
root.geometry("1000x650")

last_selected_data = None
latest_pdf_path = None

# ===================== GLASS BLUE THEME ======================
style = Style(theme="flatly")  # jangan buat style = ttk.Style()

GLASS_BG = "#e6f2ff"
GLASS_BORDER = "#b3d9ff"
GLASS_ACTIVE = "#99ccff"

root.configure(bg=GLASS_BG)

style.configure("GlassBlue.TButton",
    font=("Segoe UI", 10, "bold"),
    foreground="#003366",
    background=GLASS_BG,
    bordercolor=GLASS_BORDER,
    relief="flat",
    padding=8
)
style.map("GlassBlue.TButton",
    background=[
        ("active", GLASS_ACTIVE),
        ("!disabled", GLASS_BG),
    ],
    foreground=[
        ("active", "#00264d"),
    ]
)

style.configure("GlassPrimary.TButton",
    font=("Segoe UI", 10, "bold"),
    foreground="white",
    background="#3399ff",
    bordercolor="#1a75ff",
    relief="flat",
    padding=10
)
style.map("GlassPrimary.TButton",
    background=[
        ("active", "#4da6ff"),
        ("pressed", "#1a8cff"),
    ]
)

style.configure("GlassDanger.TButton",
    font=("Segoe UI", 10, "bold"),
    foreground="white",
    background="#ff4d4d",
    bordercolor="#e60000",
    relief="flat",
    padding=10
)
style.map("GlassDanger.TButton",
    background=[
        ("active", "#ff6666"),
        ("pressed", "#ff1a1a"),
    ]
)
# ================================================================

# Top buttons frame
frame_top = tk.Frame(root)
frame_top.pack(pady=10)
ttk.Button(frame_top, text="⚙️ App Setting", style="GlassBlue.TButton", width=18,
           command=lambda: open_settings_window(root)).pack(side="left", padx=5)

ttk.Button(frame_top, text="🌐 Router Setting", style="GlassBlue.TButton", width=18,
           command=lambda: messagebox.showinfo("Router", "Buka router setting")).pack(side="left", padx=5)
           
ttk.Button(frame_top, text="Daftar Pelanggan", style="GlassBlue.TButton", width=18,
           command=lambda: show_daftar_pelanggan()).pack(side="left", padx=5)
ttk.Button(frame_top, text="❌ Keluar", style="GlassBlue.TButton", width=12, command=root.quit).pack(side="left", padx=10)

# IP combo
frame_ip = tk.Frame(root); frame_ip.pack(pady=8)
tk.Label(frame_ip, text="Pilih IP MikroTik:", font=("Arial",10,"bold")).pack(side="left", padx=5)
ip_list = ["Semua MikroTik"] + [r.get("host","127.0.0.1") for r in cfg.get("routers", [])]
combo_ip = ttk.Combobox(frame_ip, values=ip_list, state="readonly", width=30)
combo_ip.pack(side="left"); combo_ip.current(0)

# Metode bayar combo
frame_bayar = tk.Frame(root); frame_bayar.pack(pady=8)
tk.Label(frame_bayar, text="Metode Bayar:", font=("Arial",10,"bold")).pack(side="left", padx=5)
combo_metode = ttk.Combobox(frame_bayar, values=["Tunai","QRIS","Transfer","Belum Bayar"], state="readonly", width=20)
combo_metode.set("Belum Bayar"); combo_metode.pack(side="left")

# Treeview table (include hidden ip column at end)
columns = ('nama_pelanggan', 'paket', 'harga', 'no_hp', 'jatuh_tempo', 'usage_total', 'ip')
tree = ttk.Treeview(root, columns=columns, show='headings', height=18)
for col in columns:
    heading = col.replace('_',' ').title() if col != 'ip' else 'IP'
    tree.heading(col, text=heading)
    if col == 'ip':
        tree.column(col, width=0, stretch=False)  # hidden
    else:
        tree.column(col, width=140)
tree.pack(fill="both", expand=True, padx=10, pady=5)

def on_tree_select(event):
    global last_selected_data
    sel = tree.focus()
    if not sel:
        last_selected_data = None
        return
    vals = tree.item(sel)['values']
    # map with ip at index 6
    last_selected_data = {
        "nama_pelanggan": vals[0] if len(vals) > 0 else None,
        "paket": vals[1] if len(vals) > 1 else None,
        "harga": vals[2] if len(vals) > 2 else None,
        "no_hp": vals[3] if len(vals) > 3 else None,
        "jatuh_tempo": vals[4] if len(vals) > 4 else None,
        "usage": vals[5] if len(vals) > 5 else None,
        "ip": vals[6] if len(vals) > 6 else None
    }

tree.bind("<<TreeviewSelect>>", on_tree_select)

# Buttons frame
frame_btn = tk.Frame(root); frame_btn.pack(pady=12)
ttk.Button(frame_btn, text="🖨️ Buat & Preview Invoice", style="GlassPrimary.TButton", width=22,
           command=lambda: on_buat_invoice_pdf()).pack(side="left", padx=6)
ttk.Button(frame_btn, text="✏️ Edit Comment", style="GlassBlue.TButton", width=14,
           command=lambda: on_edit_comment()).pack(side="left", padx=6)
ttk.Button(frame_btn, text="🧾 Cetak Struk", style="GlassPrimary.TButton", width=18,
           command=lambda: on_cetak_struk()).pack(side="left", padx=6)
ttk.Button(frame_btn, text="👁️ Lihat Struk", style="GlassPrimary.TButton", width=18,
           command=lambda: on_lihat_struk()).pack(side="left", padx=6)
ttk.Button(frame_btn, text="🔄 Refresh", style="GlassPrimary.TButton", width=12,
           command=lambda: update_table(combo_ip.get())).pack(side="left", padx=6)

# ========== Handlers for invoice / print / preview ==========
from functools import partial

def on_buat_invoice_pdf():
    global latest_pdf_path, last_selected_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return
    data = {
        "nama_pelanggan": last_selected_data.get('nama_pelanggan'),
        "paket": last_selected_data.get('paket'),
        "harga": last_selected_data.get('harga'),
        "no_hp": last_selected_data.get('no_hp'),
        "jatuh_tempo": last_selected_data.get('jatuh_tempo'),
        "usage": last_selected_data.get('usage'),
        "ip_mikrotik": last_selected_data.get('ip') or combo_ip.get(),
        "metode_bayar": combo_metode.get() or "Belum Bayar",
        "tanggal": datetime.now().strftime('%d/%m/%Y')
    }

    save_path = filedialog.asksaveasfilename(
        title="Simpan Invoice PDF",
        defaultextension=".pdf",
        filetypes=[("PDF Files", "*.pdf")],
        initialfile=f"Invoice_{data['nama_pelanggan']}.pdf"
    )
    if not save_path:
        return

    latest_pdf_path = buat_invoice_pdf(data, save_path)
    messagebox.showinfo("Sukses", f"Invoice PDF berhasil dibuat:\n{latest_pdf_path}")
    preview_invoice_only(latest_pdf_path, parent=root)

def preview_struk_window(img):
    """Tampilkan Image (PIL) di window preview"""
    try:
        max_width = 420
        scale = max_width / img.width if img.width > max_width else 1.0
        new_size = (int(img.width * scale), int(img.height * scale))
        img_preview = img.resize(new_size, Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_preview)
        win = tk.Toplevel(root)
        win.title("Preview Struk")
        label = tk.Label(win, image=tk_img)
        label.image = tk_img
        label.pack()
        ttk.Button(win, text="🖨️ Cetak Struk", command=lambda: cetak_struk_win32print(current_preview_data, None)).pack(pady=8)
    except Exception as e:
        messagebox.showerror("Preview Error", str(e))

# Keep current preview data for printing from preview window
current_preview_data = {}

def on_lihat_struk():
    global last_selected_data, current_preview_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return
    data = {
        "nama_pelanggan": last_selected_data.get('nama_pelanggan'),
        "ip_mikrotik": last_selected_data.get('ip') or combo_ip.get(),
        "paket": last_selected_data.get('paket'),
        "harga": last_selected_data.get('harga'),
        "usage": last_selected_data.get('usage'),
        "no_hp": last_selected_data.get('no_hp'),
        "jatuh_tempo": last_selected_data.get('jatuh_tempo'),
        "tanggal": datetime.now().strftime('%d/%m/%Y'),
        "metode_bayar": combo_metode.get() or "Belum Bayar",
    }
    current_preview_data = data
    img = render_struk(data)
    preview_struk_window(img)

def on_cetak_struk():
    global last_selected_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return
    data = {
        "nama_pelanggan": last_selected_data.get('nama_pelanggan'),
        "ip_mikrotik": last_selected_data.get('ip') or combo_ip.get(),
        "paket": last_selected_data.get('paket'),
        "harga": last_selected_data.get('harga'),
        "usage": last_selected_data.get('usage'),
        "no_hp": last_selected_data.get('no_hp'),
        "jatuh_tempo": last_selected_data.get('jatuh_tempo'),
        "tanggal": datetime.now().strftime('%d/%m/%Y'),
        "metode_bayar": combo_metode.get() or "Belum Bayar",
    }
    cetak_struk_win32print(data)

# ========== Edit Comment handler ==========
def on_edit_comment():
    global last_selected_data
    if not last_selected_data:
        messagebox.showwarning("Pilih Pelanggan", "Silakan pilih pelanggan terlebih dahulu.")
        return

    selected_ip = last_selected_data.get('ip') or combo_ip.get()

    old_comment = ""
    # cek manual customers
    for c in manual_customers:
        if c.get('nama_pelanggan') == last_selected_data.get('nama_pelanggan') and (not selected_ip or c.get('ip') == selected_ip):
            old_comment = build_comment_from_dict(c)
            break

    # coba ambil dari Mikrotik jika tersedia
    mk_client = None
    if RouterOsApiPool is not None:
        mk_client = next((mc for mc in mikrotik_clients if mc.host == combo_ip.get()), None)
        if mk_client and mk_client.connect():
            addr = last_selected_data.get('ip') or selected_ip
            try:
                leases = mk_client.get_leases_with_comment()
                target = next((l for l in leases if l.get('address') == addr or l.get('ip') == addr), None)
                if target:
                    old_comment = target.get('comment') or old_comment
            except Exception:
                pass
            mk_client.disconnect()

    parsed = parse_comment_to_dict(old_comment)

    edit_win = tk.Toplevel(root)
    edit_win.title(f"Edit Comment - {last_selected_data.get('nama_pelanggan')}")
    edit_win.geometry("460x380")
    fields = [
        ('Nama', 'nama_pelanggan', parsed.get('nama_pelanggan','')),
        ('Paket', 'paket', parsed.get('paket','')),
        ('Harga', 'harga', parsed.get('harga','')),
        ('Due (dd/mm/yyyy)', 'jatuh_tempo', parsed.get('jatuh_tempo','')),
        ('No. HP', 'no_hp', parsed.get('no_hp','')),
        ('Interface', 'iface', parsed.get('iface','')),
        ('Usage', 'usage', parsed.get('usage',''))
    ]
    entries = {}
    for i,(label,key,val) in enumerate(fields):
        tk.Label(edit_win, text=label).grid(row=i, column=0, sticky='w', padx=8, pady=6)
        e = tk.Entry(edit_win, width=36)
        e.grid(row=i, column=1, padx=8, pady=6)
        e.insert(0, str(val))
        entries[key] = e

    def save_comment_action():
        newd = {}
        for _,key,_ in fields:
            v = entries[key].get().strip()
            if v != "":
                if key == 'harga':
                    try:
                        newd[key] = int(''.join(ch for ch in v if ch.isdigit()))
                    except:
                        newd[key] = v
                else:
                    newd[key] = v
        new_comment = build_comment_from_dict(newd)

        saved_local = False
        for c in manual_customers:
            if c.get('nama_pelanggan') == last_selected_data.get('nama_pelanggan') and (not selected_ip or c.get('ip') == selected_ip):
                c.update(newd)
                save_manual_customers(manual_customers)
                saved_local = True
                break

        updated_mk = False
        if RouterOsApiPool is not None:
            mk_client = next((mc for mc in mikrotik_clients if mc.host == combo_ip.get()), None)
            if mk_client and mk_client.connect():
                addr = last_selected_data.get('ip') or selected_ip
                try:
                    updated_mk = mk_client.set_lease_comment_by_address(addr, new_comment)
                except Exception:
                    updated_mk = False
                mk_client.disconnect()

        msg = []
        if saved_local: msg.append("Disimpan ke data manual.")
        if updated_mk: msg.append("Comment berhasil diupdate ke Mikrotik.")
        if not saved_local and not updated_mk:
            msg.append("Tidak ada perubahan tersimpan (cek koneksi Mikrotik atau simpan manual).")

        messagebox.showinfo("Selesai", "\n".join(msg), parent=edit_win)
        edit_win.destroy()
        update_table(combo_ip.get())

    ttk.Button(edit_win, text="Simpan", command=save_comment_action).grid(row=len(fields), column=0, pady=12, padx=8)
    ttk.Button(edit_win, text="Batal", command=edit_win.destroy).grid(row=len(fields), column=1, pady=12, padx=8)

# ========== Table update ==========
def update_table(ip):
    for i in tree.get_children():
        tree.delete(i)
    data_all = collect_all_pelanggan(ip)
    for row in data_all:
        tree.insert('', 'end', values=(
            row.get('nama_pelanggan'),
            row.get('paket','-'),
            row.get('harga',0),
            row.get('no_hp','-'),
            row.get('jatuh_tempo','-'),
            row.get('usage_total','-'),
            row.get('ip','')  # hidden column
        ))
    try:
        generate_mikrotik_rsc(data_all)
    except Exception as e:
        print("[WARN] generate rsc failed:", e)

combo_ip.bind("<<ComboboxSelected>>", lambda e: update_table(combo_ip.get()))

# ========== Daftar Pelanggan popup (add/edit/delete) ==========
def show_daftar_pelanggan():
    win = tk.Toplevel(root)
    win.title("Daftar Pelanggan")
    win.geometry("900x520")

    tree2 = ttk.Treeview(win, columns=('nama','paket','harga','no_hp','jatuh','ip','usage'), show='headings')
    for c in ('nama','paket','harga','no_hp','jatuh','ip','usage'):
        tree2.heading(c, text=c.title())
        tree2.column(c, width=120)
    tree2.pack(fill="both", expand=True, padx=10, pady=8)

    def refresh_local_view():
        for i in tree2.get_children():
            tree2.delete(i)
        for c in manual_customers:
            tree2.insert('', 'end', values=(
                c.get('nama_pelanggan'),
                c.get('paket','-'),
                c.get('harga',0),
                c.get('no_hp','-'),
                c.get('jatuh_tempo','-'),
                c.get('ip','-'),
                c.get('usage_total','-'),
            ))

    def add_customer():
        d = {}
        d['nama_pelanggan'] = simpledialog.askstring("Nama", "Nama pelanggan:", parent=win)
        if not d['nama_pelanggan']:
            return
        d['paket'] = simpledialog.askstring("Paket", "Paket:", parent=win) or "-"
        try:
            d['harga'] = int(simpledialog.askstring("Harga", "Harga (angka):", parent=win) or "0")
        except:
            d['harga'] = 0
        d['no_hp'] = simpledialog.askstring("No HP", "No HP:", parent=win) or "-"
        d['jatuh_tempo'] = simpledialog.askstring("Jatuh Tempo", "YYYY-MM-DD:", parent=win) or "-"
        d['ip'] = simpledialog.askstring("IP", "IP:", parent=win) or "-"
        d['usage_total'] = simpledialog.askstring("Usage", "Usage text:", parent=win) or "-"
        manual_customers.append(d)
        save_manual_customers(manual_customers)
        refresh_local_view()
        update_table(combo_ip.get())

    def edit_customer():
        sel = tree2.focus()
        if not sel:
            messagebox.showwarning("Pilih", "Pilih baris untuk diedit", parent=win)
            return
        vals = tree2.item(sel)['values']
        for c in manual_customers:
            if c.get('nama_pelanggan') == vals[0] and c.get('ip','-') == vals[5]:
                c['paket'] = simpledialog.askstring("Paket", "Paket:", initialvalue=c.get('paket','-'), parent=win) or c.get('paket','-')
                try:
                    c['harga'] = int(simpledialog.askstring("Harga", "Harga (angka):", initialvalue=str(c.get('harga',0)), parent=win) or c.get('harga',0))
                except:
                    pass
                c['no_hp'] = simpledialog.askstring("No HP", "No HP:", initialvalue=c.get('no_hp','-'), parent=win) or c.get('no_hp','-')
                c['jatuh_tempo'] = simpledialog.askstring("Jatuh Tempo", "YYYY-MM-DD:", initialvalue=c.get('jatuh_tempo','-'), parent=win) or c.get('jatuh_tempo','-')
                save_manual_customers(manual_customers)
                refresh_local_view()
                update_table(combo_ip.get())
                return
        messagebox.showwarning("Tidak ditemukan", "Pelanggan manual tidak ditemukan.", parent=win)

    def delete_customer():
        sel = tree2.focus()
        if not sel:
            messagebox.showwarning("Pilih", "Pilih baris untuk dihapus", parent=win)
            return
        vals = tree2.item(sel)['values']
        for idx, c in enumerate(manual_customers):
            if c.get('nama_pelanggan') == vals[0] and c.get('ip','-') == vals[5]:
                if messagebox.askyesno("Konfirmasi", f"Hapus pelanggan {c.get('nama_pelanggan')}?", parent=win):
                    manual_customers.pop(idx)
                    save_manual_customers(manual_customers)
                    refresh_local_view()
                    update_table(combo_ip.get())
                return
        messagebox.showwarning("Tidak ditemukan", "Pelanggan manual tidak ditemukan.", parent=win)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=6)
    ttk.Button(btn_frame, text="Tambah", command=add_customer).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Edit", command=edit_customer).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Hapus", command=delete_customer).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Refresh", command=refresh_local_view).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Tutup", command=win.destroy).pack(side="left", padx=6)

    refresh_local_view()

# ========== Start app ==========
update_table(combo_ip.get())
root.mainloop()
