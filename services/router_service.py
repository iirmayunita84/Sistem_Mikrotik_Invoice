# services/router_service.py
import uuid
import time
import sqlite3
from core.db import db_connection
from datetime import datetime

def get_user_routers(user_id):
    with db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM routers WHERE user_id=?",
            (user_id,)
        )
        return [dict(r) for r in c.fetchall()]

def get_router_status(user_id):

    with db_connection() as conn:

        c = conn.cursor()

        c.execute("""
            SELECT *
            FROM routers
            WHERE user_id=?
        """, (user_id,))

        routers = [dict(r) for r in c.fetchall()]

    # Gunakan status terakhir dari database.
    # Jangan konek MikroTik dari dashboard.
    for r in routers:

        r["online"] = bool(
            r.get("online", 0)
        )

        r["status"] = (
            "online"
            if r["online"]
            else "offline"
        )

    return routers

def get_router(router_id):
    with db_connection() as conn:
        c = conn.cursor()

        c.execute(
            "SELECT * FROM routers WHERE id=?",
            (router_id,)
        )

        row = c.fetchone()

    return dict(row) if row else None

def add_router(user_id, data):

    print("MASUK ADD_ROUTER =", data)

    with db_connection() as conn:
        c = conn.cursor()

        rid = uuid.uuid4().hex[:8]

        c.execute("""
        INSERT INTO routers
        (
            id,
            user_id,
            name,
            host,
            username,
            password,
            port
        )
        VALUES (?,?,?,?,?,?,?)
        """, (
            rid,
            user_id,
            data.get("name"),
            data["host"],
            data["username"],
            data["password"],
            data.get("port", 8728)
        ))

        conn.commit()

        return rid

def delete_router(router_id):
    with db_connection() as conn:
        c = conn.cursor()

        c.execute(
            "DELETE FROM routers WHERE id=?",
            (router_id,)
        )

        conn.commit()

def update_router(user_id, rid, data):
    from core.db import db_connection

    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
        UPDATE routers
        SET
            name=?,
            host=?,
            username=?,
            password=?,
            port=?
        WHERE id=?
        AND user_id=?
        """, (
            data["name"],
            data["host"],
            data["username"],
            data["password"],
            int(data.get("port", 8728)),
            rid,
            user_id
        ))

        conn.commit()

def update_router_status(router_id, online):

    status = "online" if online else "offline"

    for attempt in range(3):

        try:

            with db_connection() as conn:

                cur = conn.cursor()

                cur.execute("""
                    UPDATE routers
                    SET
                        online=?,
                        status=?,
                        last_check=?
                    WHERE id=?
                """, (
                    1 if online else 0,
                    status,
                    datetime.now().isoformat(),
                    router_id
                ))

                conn.commit()

                return True

        except sqlite3.OperationalError as e:

            if "locked" not in str(e).lower():
                raise

            print(
                f"⚠️ Database locked "
                f"(percobaan {attempt + 1}/3)"
            )

            time.sleep(0.5)

    print(
        f"❌ Gagal update status router "
        f"{router_id}: database tetap locked"
    )

    return False