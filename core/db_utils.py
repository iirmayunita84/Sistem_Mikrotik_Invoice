from core.db import get_db, release_db
from datetime import datetime
import uuid


def simpan_dhcp_ke_db(router_id, dhcp_list):

    conn = get_db()

    try:

        cur = conn.cursor()

        for lease in dhcp_list:

            cur.execute("""
                INSERT OR REPLACE INTO dhcp(
                    id,
                    router_id,
                    ip,
                    mac,
                    client,
                    status,
                    updated_at
                )
                VALUES(?,?,?,?,?,?,?)
            """,(

                lease.get("id") or uuid.uuid4().hex[:8],

                router_id,

                lease.get("address"),

                lease.get("mac-address"),

                lease.get("host-name"),

                lease.get("status"),

                datetime.now().isoformat()

            ))

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        release_db(conn)