# device_popup.py
from flask import render_template
from core.license_core import get_device_id
import urllib.parse

def show_device_popup():
    device_id = get_device_id()
    return render_template(
        "aktivasi.html",
        device_id=device_id,
        device_id_encoded=urllib.parse.quote(device_id)
    )