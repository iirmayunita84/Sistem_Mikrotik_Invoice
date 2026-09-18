# services/license_storage.py
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_FILE = os.path.join(BASE_DIR, "licenses.json")


def load():
    if not os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "w") as f:
            json.dump({"licenses": []}, f, indent=2)

    with open(LICENSE_FILE, "r") as f:
        return json.load(f)


def save(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=2)