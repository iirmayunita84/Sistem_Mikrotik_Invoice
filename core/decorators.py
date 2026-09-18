from functools import wraps
from flask import session, redirect

from core.logic import boleh_masuk
from core.license_core import get_license_info
from flask import (
    session,
    redirect,
    flash,
    url_for,
)

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("⚠️ Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return wrapper


def app_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("⚠️ Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def premium_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        info = get_license_info()
        if info.get("mode") in ("PREMIUM", "TRIAL"):
            return f(*args, **kwargs)

        flash("🔒 Fitur ini hanya tersedia untuk lisensi Premium.", "danger")
        return redirect(url_for("auth.aktivasi"))
    return wrapper