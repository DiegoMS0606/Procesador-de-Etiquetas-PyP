from pathlib import Path
import re
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import get_config
from src.core.productos import resolver_json_productos

EXTENSIONES = {".png", ".jpg", ".jpeg", ".webp"}


def cargar_productos(config):
    try:
        json_path = resolver_json_productos(config)
    except FileNotFoundError as e:
        print(f"\n⚠ {e}")
        return []

    print(f"JSON usado: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def imagenes_sueltas(carpeta_img):
    if not carpeta_img.exists():
        return []

    return sorted(
        p
        for p in carpeta_img.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSIONES
    )


def analizar_nombre(path):
    stem = path.stem.lower()

    match = re.fullmatch(r"(\d+)(h?)", stem)

    if not match:
        return None

    numero = int(match.group(1))
    horizontal = bool(match.group(2))

    return {
        "numero": numero,
        "horizontal": horizontal,
        "archivo": path.name,
    }


def main():
    config = get_config()
    productos = cargar_productos(config)
    sueltas = imagenes_sueltas(config.img)

    if not productos:
        print("\n=== DIAGNÓSTICO DE IMÁGENES SUELTAS ===")
        print(f"Modo: {config.modo}")
        print(f"Categoría: {config.categoria}")
        print(f"Carpeta imágenes: {config.img}")
        print(f"Imágenes sueltas: {len(sueltas)}")

        if sueltas:
            print("\n--- IMÁGENES SUELTAS DETECTADAS ---")
            for img in sueltas:
                print(f"- {img.name}")

        print("\nNo se puede proponer asignación porque falta el JSON de productos.")
        print("No se movió ningún archivo.")
        return

    productos_por_id = {
        int(p["id"]): p for p in productos if str(p.get("id", "")).isdigit()
    }


    print("\n=== DIAGNÓSTICO DE IMÁGENES SUELTAS ===")
    print(f"Modo: {config.modo}")
    print(f"Categoría: {config.categoria}")
    print(f"Carpeta imágenes: {config.img}")
    print(f"Imágenes sueltas: {len(sueltas)}")

    print("\n--- POSIBLES ASIGNACIONES DIRECTAS ---")

    ambiguas = []
    desconocidas = []

    for img in sueltas:
        info = analizar_nombre(img)

        if not info:
            desconocidas.append(img.name)
            continue

        numero = info["numero"]

        if numero in productos_por_id:
            producto = productos_por_id[numero]
            id_catalogo = producto.get("id_catalogo", f"ACT-{numero:04d}")

            print(f"{img.name}  →  {id_catalogo}/principal{img.suffix.lower()}")
        else:
            ambiguas.append(img.name)

    if ambiguas:
        print("\n--- ARCHIVOS NUMÉRICOS SIN PRODUCTO DIRECTO ---")
        for item in ambiguas:
            print(f"- {item}")

    if desconocidas:
        print("\n--- ARCHIVOS CON NOMBRE NO RECONOCIDO ---")
        for item in desconocidas:
            print(f"- {item}")

    print("\nNo se movió ningún archivo.")


if __name__ == "__main__":
    main()
