from pathlib import Path
import sys
import json
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import get_config
from src.core.productos import resolver_json_productos


def obtener_rango(chars):
    if chars < 500:
        return "menos_500"

    if 500 <= chars <= 699:
        return "500_699"

    if 700 <= chars <= 799:
        return "700_799"

    if 800 <= chars <= 899:
        return "800_899"

    return "mas_900"


def main():
    config = get_config()
    json_path = resolver_json_productos(config)

    if not json_path.exists():
        print(f"No existe JSON: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        productos = json.load(f)

    conteo = Counter()
    detalle = []

    for producto in productos:
        id_catalogo = producto.get("id_catalogo", "")
        nombre = producto.get("nombre", "")
        descripcion = str(producto.get("descripcion", "")).strip()

        chars = len(descripcion)
        rango = obtener_rango(chars)

        conteo[rango] += 1

        detalle.append(
            {
                "id_catalogo": id_catalogo,
                "nombre": nombre,
                "chars": chars,
                "rango": rango,
            }
        )

    print("\n=== REPORTE DE DESCRIPCIONES ===")
    print(f"Modo: {config.modo}")
    print(f"Categoría: {config.categoria}")
    print(f"JSON: {json_path}")
    print(f"Productos revisados: {len(productos)}")

    print("\n--- RESUMEN POR RANGO ---")
    print(f"Menos de 500: {conteo['menos_500']}")
    print(f"500 a 699:   {conteo['500_699']}")
    print(f"700 a 799:   {conteo['700_799']}")
    print(f"800 a 899:   {conteo['800_899']}")
    print(f"Más de 900:  {conteo['mas_900']}")

    print("\n--- DETALLE ---")

    for item in sorted(detalle, key=lambda x: x["chars"]):
        print(
            f"{item['id_catalogo']} | "
            f"{item['chars']:>4} chars | "
            f"{item['rango']:<10} | "
            f"{item['nombre']}"
        )


if __name__ == "__main__":
    main()
