# core/premium.py

from core.db import get_db, release_db
from datetime import datetime, timedelta

# ================= TRIAL CHECK =================
def check_trial(user_id):
    """
    Return:
        (True, sisa_hari)
        (False, 0)
    """

    conn = get_db()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT demo_start
            FROM app_config
            WHERE user_id=?
        """, (user_id,))

        row = cur.fetchone()

    finally:
        release_db(conn)

    if not row or not row["demo_start"]:
        return False, 0

    try:
        start = datetime.fromisoformat(row["demo_start"])
        expired = start + timedelta(days=7)

        if datetime.now() >= expired:
            return False, 0

        sisa = (expired - datetime.now()).days

        return True, max(sisa, 0)

    except Exception as e:
        print("check_trial:", e)
        return False, 0

def is_premium(user_id):

    conn = get_db()

    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT demo_status
            FROM app_config
            WHERE user_id=?
        """, (user_id,))

        row = cur.fetchone()

    finally:
        release_db(conn)

    return bool(row and row["demo_status"] == "PREMIUM")