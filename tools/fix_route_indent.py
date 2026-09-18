from pathlib import Path
import textwrap


ROUTES = Path("../routes")


for file in ROUTES.glob("*_routes.py"):

    print("Fix:", file.name)

    text = file.read_text(
        encoding="utf-8"
    )

    text = textwrap.dedent(text)

    lines = []

    for line in text.splitlines():

        if line.startswith("    import "):
            line = line.strip()

        if line.startswith("    from "):
            line = line.strip()

        lines.append(line)


    file.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


print("SELESAI")