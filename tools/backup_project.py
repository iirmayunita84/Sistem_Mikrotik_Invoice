import os
import shutil
import zipfile
from datetime import datetime

# ==========================================================
# Backup Project Mikrotik Invoice
# Tidak mengubah file project
# Hanya membuat folder backup dan file ZIP
# ==========================================================

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BACKUP_ROOT = os.path.join(PROJECT_DIR, "backup")


EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "backup",
    "build",
    "dist",
    "logs"
}

EXCLUDE_EXT = {
    ".pyc",
    ".pyo",
    ".log",
}


def should_skip(path):
    name = os.path.basename(path)

    if name in EXCLUDE_DIRS:
        return True

    ext = os.path.splitext(name)[1].lower()

    if ext in EXCLUDE_EXT:
        return True

    return False


def copy_project(dst):

    for root, dirs, files in os.walk(PROJECT_DIR):

        dirs[:] = [d for d in dirs if not should_skip(d)]

        rel = os.path.relpath(root, PROJECT_DIR)

        target = os.path.join(dst, rel)

        os.makedirs(target, exist_ok=True)

        for file in files:

            if should_skip(file):
                continue

            src_file = os.path.join(root, file)
            dst_file = os.path.join(target, file)

            shutil.copy2(src_file, dst_file)


def make_zip(folder, zip_name):

    with zipfile.ZipFile(zip_name,
                         "w",
                         zipfile.ZIP_DEFLATED) as z:

        for root, dirs, files in os.walk(folder):

            for file in files:

                full = os.path.join(root, file)

                arc = os.path.relpath(full, folder)

                z.write(full, arc)


def main():

    os.makedirs(BACKUP_ROOT, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_folder = os.path.join(
        BACKUP_ROOT,
        "project_" + stamp
    )

    print("=" * 50)
    print("Backup Project")
    print("=" * 50)
    print()

    print("Project :")
    print(PROJECT_DIR)
    print()

    print("Membuat folder backup...")

    os.makedirs(backup_folder)

    copy_project(backup_folder)

    print("OK")

    zip_name = backup_folder + ".zip"

    print("Membuat ZIP...")

    make_zip(
        backup_folder,
        zip_name
    )

    print("OK")

    print()

    print("=" * 50)
    print("SELESAI")
    print("=" * 50)
    print()

    print("Folder Backup :")
    print(backup_folder)
    print()

    print("ZIP Backup :")
    print(zip_name)
    print()

    print("Project aman.")
    print("Silakan lanjut refactor.")

if __name__ == "__main__":
    main()