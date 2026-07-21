from pathlib import Path
import re

FILES = [
    Path("src/catalogo/menu.py"),
    Path("src/catalogo/validacion.py"),
    Path("src/core/validacion.py"),
    Path("src/etiquetas/generar.py"),
    Path("scripts/analizar_descripciones_catalogo.py"),
    Path("scripts/reporte_descripciones.py"),
    Path("scripts/diagnosticar_imagenes.py"),
]


def ensure_resolver_import(text):
    if re.search(r"from src\.core\.productos import .*resolver_json_productos", text):
        return text

    pattern = r"from src\.core\.productos import ([^\n]+)"

    match = re.search(pattern, text)

    if match:
        imports = match.group(1).strip()

        if imports.startswith("("):
            # Import multiline; no lo tocamos automáticamente.
            return text

        nombres = [item.strip() for item in imports.split(",")]

        if "resolver_json_productos" not in nombres:
            nombres.append("resolver_json_productos")

        nueva_linea = "from src.core.productos import " + ", ".join(nombres)

        return re.sub(pattern, nueva_linea, text, count=1)

    if "from src.core.paths import get_config" in text:
        return text.replace(
            "from src.core.paths import get_config",
            "from src.core.paths import get_config\nfrom src.core.productos import resolver_json_productos",
            1,
        )

    return "from src.core.productos import resolver_json_productos\n" + text


for path in FILES:
    if not path.exists():
        print(f"NO EXISTE: {path}")
        continue

    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace('config.processed / "1.json"', 'resolver_json_productos(config)')
    text = text.replace("config.processed / '1.json'", "resolver_json_productos(config)")

    if "resolver_json_productos(config)" in text:
        text = ensure_resolver_import(text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"MODIFICADO: {path}")
    else:
        print(f"SIN CAMBIOS: {path}")
