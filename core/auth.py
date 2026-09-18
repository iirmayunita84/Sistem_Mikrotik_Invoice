from core.db import db_connection
import uuid
from datetime import datetime
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


def verify_login(username, password):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        user = cur.fetchone()

        if not user:
            return None

        if not check_password_hash(
            user["password"],
            password
        ):
            return None

        return user


def get_user_by_username(username):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        return cur.fetchone()


def total_user():
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]


def create_admin(username, password):
    with db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM users WHERE username=?",
            (username,)
        )

        if cur.fetchone():
            return False

        cur.execute("""
            INSERT INTO users(
                id,
                username,
                password,
                is_admin,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            uuid.uuid4().hex,
            username,
            generate_password_hash(password),
            1,
            datetime.now().isoformat()
        ))

        conn.commit()
        return True