from pdf2image import convert_from_path
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POPPLER = os.path.join(BASE_DIR, "poppler", "bin")

print("POPPLER:", POPPLER)

images = convert_from_path("test.pdf", poppler_path=POPPLER)
print("Berhasil:", len(images))
