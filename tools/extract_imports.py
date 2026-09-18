import ast
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent

WEB = BASE / "web.py"
ROUTES = BASE / "routes"


print("=" * 60)
print(" EXTRACT IMPORTS AST ")
print("=" * 60)


text = WEB.read_text(
    encoding="utf8",
    errors="ignore"
)


tree = ast.parse(text)


imports = []


for node in tree.body:

    if isinstance(node, ast.Import):

        source = ast.get_source_segment(
            text,
            node
        )

        imports.append(source)


    elif isinstance(node, ast.ImportFrom):

        source = ast.get_source_segment(
            text,
            node
        )

        if source.startswith("from routes"):
            continue

        imports.append(source)



imports = list(dict.fromkeys(imports))


print(
    "Jumlah import:",
    len(imports)
)


for file in ROUTES.glob("*.py"):

    isi = file.read_text(
        encoding="utf8",
        errors="ignore"
    )


    lines = isi.splitlines()


    # hapus import rusak lama
    while lines and (
        lines[0].startswith("import ")
        or lines[0].startswith("from ")
        or lines[0].strip()==""
    ):
        lines.pop(0)


    header = "\n".join(imports)


    hasil = (
        header
        + "\n\n"
        + "\n".join(lines)
    )


    file.write_text(
        hasil,
        encoding="utf8"
    )


    print("OK:", file.name)


print("SELESAI")