# web.py
# ================= PYTHON =================
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    session,
    send_from_directory
)

from datetime import datetime
from urllib.parse import quote
import uuid
import sys
from core.router_log import get_router_logs
from core.license_core import get_license_info
from core.config_core import get_app_config
from core.mikrotik_core import auto_blokir_router
from services.wa_service import (
    kirim_wa,
    pesan_reminder
)
from services.inject_router_status import inject_router_status
from dotenv import load_dotenv

import os
import logging
import threading
import schedule
import time

from logging.handlers import RotatingFileHandler

# semua import core/service yang memang dipakai startup

# blueprint
from routes.auth_routes import bp as auth_bp
from routes.misc_routes import bp as misc_bp
from routes.router_routes import bp as router_bp
from routes.pelanggan_routes import bp as pelanggan_bp
from routes.invoice_routes import bp as invoice_bp
from routes.setting_routes import bp as setting_bp
from routes.transaksi_routes import bp as transaksi_bp
from routes.paket_routes import bp as paket_bp
from routes.tagihan_routes import bp as tagihan_bp
from routes.pembayaran_routes import bp as pembayaran_bp
from routes.laporan_routes import bp as laporan_bp

# ================= PATH =================

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ================= USER DATA =================

APPDATA_DIR = os.getenv("APPDATA")

if not APPDATA_DIR:
    APPDATA_DIR = os.path.expanduser("~")

USER_APP_DIR = os.path.join(
APPDATA_DIR,
"MikrotikInvoice"
)

UPLOAD_FOLDER = os.path.join(
USER_APP_DIR,
"uploads"
)

LOG_DIR = os.path.join(
USER_APP_DIR,
"logs"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
LOG_DIR,
"error.log"
)

# ================= LOGGING =================

logger = logging.getLogger("app_logger")
logger.setLevel(logging.ERROR)
logger.propagate = False

file_handler = RotatingFileHandler(
LOG_FILE,
maxBytes=1_000_000,
backupCount=5,
encoding="utf-8"
)

file_handler.setFormatter(
logging.Formatter(
"%(asctime)s | %(levelname)s | %(message)s"
)
)

logger.addHandler(file_handler)

# ================= ERROR LOG =================
def log_error(source, error):
    error_id = f"ERR-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    logger.exception(
        f"\nERROR_ID : {error_id}\nSOURCE   : {source}\nERROR    : {error}\n"
    )
    return error_id

# ================= FLASK APP =================
load_dotenv()

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.secret_key = os.getenv(
    "SECRET_KEY",
    os.urandom(24)
)

app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    SECRET_KEY=os.environ.get(
        "SECRET_KEY",
        os.urandom(24)
    ),
    DEBUG=False,
)

app.config["ENV"] = (
    "development"
    if app.config["DEBUG"]
    else "production"
)

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

# ================= ERROR HANDLER GLOBAL =================
@app.errorhandler(Exception)
def handle_global_error(e):
    error_id = log_error(request.path, e)
    if app.config["DEBUG"]:
        raise e
    return (
        render_template("error.html", error_id=error_id),
        500,
    )

@app.before_request
def check_license_global():
    if request.path.startswith((
        "/aktivasi",
        "/login",
        "/static",
        "/favicon.ico",
    )):
        return

    info = get_license_info()
    if info["status"] in {
        "INVALID_OR_EXPIRED",
        "NO_LICENSE",
    }:
        return redirect(
            url_for("auth.aktivasi")
        )

@app.context_processor
def inject_license():
    return dict(license_info=get_license_info())

# ================= CONTEXT PROCESSORS =================
@app.context_processor
def inject_router_status_context():
    user_id = session.get("user_id")

    if not user_id:
        return {
            "routers_status": [],
            "router_online": False
        }

    routers = inject_router_status(user_id)

    return {
        "routers_status": routers,
        "router_online": any(
            r.get("online", False)
            for r in routers
        )
    }

@app.context_processor
def inject_config():
    user_id = session.get("user_id")

    if user_id:
        try:
            app_cfg = get_app_config(user_id)
        except Exception as e:
            log_error("inject_config", e)
            app_cfg = {}
    else:
        app_cfg = {}

    defaults = {
        "store_name": "",
        "store_address": "",
        "footer_message": "",
        "default_account": "",
        "logo_file": "",
        "qris_file": "",
    }

    defaults.update(app_cfg)

    # app_cfg adalah nama utama konfigurasi.
    # app disediakan sebagai alias agar template lama
    # yang menggunakan {{ app.store_name }} tetap kompatibel.
    return {
        "app_cfg": defaults,
        "app": defaults,
    }

@app.context_processor
def inject_now():
    return {"now": datetime.now()}

@app.template_filter("url_encode")
def url_encode_filter(value):
    return quote(str(value))

# =====================
# REGISTER BLUEPRINT
# =====================

app.register_blueprint(auth_bp)
app.register_blueprint(misc_bp)
app.register_blueprint(router_bp)
app.register_blueprint(pelanggan_bp)
app.register_blueprint(invoice_bp)
app.register_blueprint(setting_bp)
app.register_blueprint(transaksi_bp)
app.register_blueprint(paket_bp)
app.register_blueprint(tagihan_bp)
app.register_blueprint(pembayaran_bp)
app.register_blueprint(laporan_bp)

file_handler.setLevel(logging.INFO)

app.logger.addHandler(file_handler)

# =====================
# MAIN
# =====================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )