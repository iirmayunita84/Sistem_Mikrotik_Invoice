# core/config_core.py
import os
from core.db import db_connection 
import sqlite3
# ================= STORAGE =================

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "MikrotikInvoice")
os.makedirs(APP_FOLDER, exist_ok=True)

BASE_DIR = os.path.join(APP_FOLDER, "shared")
os.makedirs(BASE_DIR, exist_ok=True)

# ================= APP CONFIG (DB BASED) =================
def get_app_config(user_id):
    """Ambil konfigurasi aplikasi dari database, aman untuk DB lama."""
    defaults = {
        "store_name": "",
        "store_address": "",
        "footer_message": "",
        "default_account": "",
        "logo_file": "",
        "qris_file": ""
    }

    with db_connection() as conn:
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT store_name, store_address, footer_message,
                       default_account, logo_file, qris_file
                FROM app_config
                WHERE user_id = ?
            """, (user_id,))

            row = cur.fetchone()

            if row:
                try:
                    row = dict(row)
                except Exception:
                    row = {}

                for k in defaults:
                    defaults[k] = row.get(k, "")

        except sqlite3.OperationalError:
            # DB lama / kolom belum ada → aman saja
            pass

    return defaults

def save_app_config(user_id, data):
    """Simpan / update konfigurasi aplikasi ke database."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO app_config (
                user_id, store_name, store_address,
                footer_message, default_account,
                logo_file, qris_file
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                store_name=excluded.store_name,
                store_address=excluded.store_address,
                footer_message=excluded.footer_message,
                default_account=excluded.default_account,
                logo_file=excluded.logo_file,
                qris_file=excluded.qris_file
        """, (
            user_id,
            data.get("store_name", ""),
            data.get("store_address", ""),
            data.get("footer_message", ""),
            data.get("default_account", ""),
            data.get("logo_file", ""),
            data.get("qris_file", ""),
        ))
        conn.commit()
