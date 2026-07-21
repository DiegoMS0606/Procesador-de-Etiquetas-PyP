import json
from pathlib import Path

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.paths import get_config
from src.core.productos import crear_id_catalogo
from src.core.productos import resolver_json_productos

from src.catalogo.menu import (
    DISTRIBUCIONES_CATALOGO,
    resolver_template_catalogo,
    distribuir_descripcion_en_cajas,
)


def obtener_id_catalogo(producto):
    id_catalogo = str(producto.get("id_catalogo", "")).strip()

    if id_catalogo:
        return id_catalogo

    return crear_id_catalogo(producto.get("id", ""))


def cargar_productos(config):
    json_path = resolver_json_productos(config)

    if not json_path.exists():
        raise FileNotFoundError(f"No existe JSON: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        productos = json.load(f)

    if not isinstance(productos, list):
        raise ValueError("El JSON debe contener una lista de productos")

    return productos, json_path


def obtener_parrafos(descripcion):
    descripcion = str(descripcion or "")
    descripcion = descripcion.replace("\r\n", "\n").replace("\r", "\n").strip()

    if not descripcion:
        return []

    return [
        p.strip()
        for p in descripcion.split("\n")
        if p.strip()
    ]


def recomendar_distribuciones_por_capacidad(chars):
    recomendaciones = []

    for nombre, data in DISTRIBUCIONES_CATALOGO.items():
        capacidad_total = sum(data.get("capacidades", {}).values())
        paginas = data.get("paginas", 1)

        if chars <= capacidad_total:
            recomendaciones.append({
                "nombre": nombre,
                "capacidad": capacidad_total,
                "paginas": paginas,
                "sobrante": capacidad_total - chars,
            })

    recomendaciones.sort(
        key=lambda item: (
            item["paginas"],
            item["capacidad"],
        )
    )

    return recomendaciones


def analizar_producto(producto):
    id_catalogo = obtener_id_catalogo(producto)
    nombre = str(producto.get("nombre", "")).strip()
    descripcion = str(producto.get("descripcion", "")).strip()

    distribucion = resolver_template_catalogo(producto)
    data_distribucion = DISTRIBUCIONES_CATALOGO[distribucion]

    capacidades = data_distribucion["capacidades"]
    capacidad_total = sum(capacidades.values())

    parrafos = obtener_parrafos(descripcion)
    chars_total = len(descripcion)

    descripcion_cajas, overflow = distribuir_descripcion_en_cajas(
        descripcion,
        capacidades=capacidades,
    )

    recomendaciones = recomendar_distribuciones_por_capacidad(chars_total)

    return {
        "id_catalogo": id_catalogo,
        "nombre": nombre,
        "distribucion": distribucion,
        "catalogo_template": str(producto.get("catalogo_template", "")).strip(),
        "chars_total": chars_total,
        "capacidad_total": capacidad_total,
        "parrafos": parrafos,
        "descripcion_cajas": descripcion_cajas,
        "overflow": overflow,
        "recomendaciones": recomendaciones,
    }


def imprimir_reporte_producto(info):
    print("\n" + "=" * 90)
    print(f"{info['id_catalogo']} | {info['nombre']}")
    print("-" * 90)

    if info["catalogo_template"]:
        print(f"Distribución asignada manualmente: {info['distribucion']}")
    else:
        print(f"Distribución automática: {info['distribucion']}")

    print(
        f"Caracteres totales: {info['chars_total']} | "
        f"Capacidad distribución: {info['capacidad_total']}"
    )

    print("\n--- PÁRRAFOS ---")

    if not info["parrafos"]:
        print("Sin descripción.")
    else:
        for i, parrafo in enumerate(info["parrafos"], start=1):
            print(f"Párrafo {i}: {len(parrafo)} caracteres")
            print(f"  {parrafo[:180]}{'...' if len(parrafo) > 180 else ''}")

    print("\n--- REPARTO EN CAJAS ---")

    for caja, texto in info["descripcion_cajas"].items():
        chars = len(texto)
        print(f"{caja}: {chars} caracteres")

        if texto:
            print(f"  {texto[:180]}{'...' if len(texto) > 180 else ''}")
        else:
            print("  [vacía]")

    print("\n--- PÉRDIDA / OVERFLOW ---")

    if info["overflow"]:
        print(f"⚠ Se perderían {len(info['overflow'])} caracteres:")
        print(info["overflow"])
    else:
        print("✔ No se pierde información con esta distribución.")

    print("\n--- RECOMENDACIÓN ---")

    if not info["overflow"]:
        print(f"✔ La distribución actual puede funcionar: {info['distribucion']}")
        return

    recomendaciones = info["recomendaciones"]

    if not recomendaciones:
        print("❌ Ninguna distribución actual soporta toda la descripción.")
        print("Recomendación: resumir descripción o crear una plantilla con más capacidad.")
        return

    mejor = recomendaciones[0]

    print(
        f"Usar {mejor['nombre']} "
        f"({mejor['paginas']} pág., "
        f"{mejor['capacidad']} caracteres, "
        f"sobran {mejor['sobrante']} caracteres)."
    )

    print("Opciones posibles:")

    for rec in recomendaciones:
        print(
            f"  - {rec['nombre']}: "
            f"{rec['paginas']} pág. | "
            f"{rec['capacidad']} chars | "
            f"sobran {rec['sobrante']}"
        )


def main():
    config = get_config()
    productos, json_path = cargar_productos(config)

    print("\n=== ANÁLISIS DE DESCRIPCIONES PARA CATÁLOGO ===")
    print(f"Modo: {config.modo}")
    print(f"Categoría: {config.categoria}")
    print(f"JSON: {json_path}")
    print(f"Productos: {len(productos)}")

    entrada = input(
        "\nIDs a analizar, ejemplo 1,6,9 "
        "o ENTER para todos: "
    ).strip()

    if entrada:
        ids_pedidos = {
            item.strip().upper()
            for item in entrada.split(",")
            if item.strip()
        }

        productos_filtrados = []

        for producto in productos:
            id_catalogo = obtener_id_catalogo(producto)
            id_num = id_catalogo.replace("ACT-", "").lstrip("0")

            if (
                id_catalogo.upper() in ids_pedidos
                or id_num in ids_pedidos
            ):
                productos_filtrados.append(producto)
    else:
        productos_filtrados = productos

    if not productos_filtrados:
        print("No encontré productos para analizar.")
        return

    for producto in productos_filtrados:
        info = analizar_producto(producto)
        imprimir_reporte_producto(info)


if __name__ == "__main__":
    main()
