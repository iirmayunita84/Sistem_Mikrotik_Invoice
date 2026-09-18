import sqlite3
import os

print("Mencari semua file database...\n")

for root, dirs, files in os.walk("."):
    for f in files:
        if f.endswith(".db"):
            path = os.path.abspath(os.path.join(root, f))

            print("=" * 60)
            print("DATABASE :", path)

            try:
                conn = sqlite3.connect(path)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                cur.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    ORDER BY name
                """)

                tables = [r["name"] for r in cur.fetchall()]

                print("\nTABLE:")
                for t in tables:
                    print(" -", t)

                # =========================
                # Struktur routers
                # =========================
                if "routers" in tables:
                    print("\nSTRUKTUR ROUTERS")
                    cur.execute("PRAGMA table_info(routers)")
                    for col in cur.fetchall():
                        print(dict(col))

                    print("\nDATA ROUTERS")
                    cur.execute("SELECT * FROM routers")
                    for r in cur.fetchall():
                        print(dict(r))

                # =========================
                # Struktur pelanggan
                # =========================
                if "pelanggan" in tables:
                    print("\nSTRUKTUR PELANGGAN")
                    cur.execute("PRAGMA table_info(pelanggan)")
                    for col in cur.fetchall():
                        print(dict(col))

                conn.close()

            except Exception as e:
                print("ERROR:", e)