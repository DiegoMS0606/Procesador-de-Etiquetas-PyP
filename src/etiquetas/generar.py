# motor/procesar_etiquetas.py

import json
from datetime import datetime
from pathlib import Path
from PIL import Image

from src.core.paths import get_config
from src.core.productos import (
    crear_id_catalogo,
    buscar_imagen_producto,
    seleccionar_por_ids,
)
from src.etiquetas.photoshop import renderizar_front_back
from src.etiquetas.plantillas import resolver_plantilla_producto


def mostrar_configuracion_actual(config, json_data):
    print("\n--- CONFIGURACIÓN ACTUAL ETIQUETAS ---")
    print(f"Modo: {config.modo}")
    print(f"Categoría: {config.categoria}")
    print(f"Base: {config.base}")
    print(f"JSON: {json_data}")
    print(f"Imágenes: {config.img}")
    print(f"Salida: {config.output}")


# =========================
# UTILIDADES
# =========================

def es_horizontal_real(ruta):
    if not ruta:
        return False

    try:
        with Image.open(ruta) as img:
            width, height = img.size
            return width >= height
    except Exception:
        return False


def determinar_size(layout, descripcion):
    """
    Regla temporal.

    Después podemos reemplazar esto por:
    - plantilla definida en JSON
    - regla por categoría
    - muebles => vertical/a5
    """

    descripcion = descripcion or ""
    longitud = len(descripcion)

    if layout == "vertical":
        if longitud <= 440:
            return "small"
        elif longitud <= 1120:
            return "large"
        else:
            raise ValueError("Descripción demasiado larga para vertical")

    elif layout == "horizontal":
        if longitud <= 440:
            return "small"
        elif longitud <= 820:
            return "large"
        else:
            raise ValueError("Descripción demasiado larga para horizontal")

    else:
        raise ValueError("Layout desconocido")


def determinar_plantilla(item):
    layout, size, origen = resolver_plantilla_producto(item)
    return layout, size, origen

MAX_TEXTO_BACK_NORMAL = 915
MAX_TEXTO_BACK_LARGO = 1530


def contar_caracteres_descripcion(texto):
    if not texto:
        return 0

    texto = str(texto).replace("\r\n", "\n").replace("\r", "\n")
    texto = texto.strip()

    return len(texto)


def resolver_back_psd_por_texto(config, layout, size, descripcion):
    """
    Decide qué PSD de reverso usar según longitud de descripción.

    Para vertical/a5:
    - back.psd acepta hasta 915 caracteres aprox.
    - back-texto-largo.psd acepta hasta 1530 caracteres aprox.
    """

    chars = contar_caracteres_descripcion(descripcion)

    carpeta_template = config.templates_base / layout / size

    if layout == "vertical" and size == "a5":
        if chars <= MAX_TEXTO_BACK_NORMAL:
            return carpeta_template / "back.psd", "normal", chars

        if chars <= MAX_TEXTO_BACK_LARGO:
            return carpeta_template / "back-texto-largo.psd", "texto_largo", chars

        raise ValueError(
            f"Descripción demasiado larga para etiqueta: "
            f"{chars} caracteres. Máximo permitido: {MAX_TEXTO_BACK_LARGO}."
        )

    # Para otras plantillas se usa back.psd normal por ahora.
    return carpeta_template / "back.psd", "normal", chars


def cargar_productos_json(json_data):
    if not json_data.exists():
        raise FileNotFoundError(f"No existe el JSON: {json_data}")

    with open(json_data, "r", encoding="utf-8") as f:
        productos = json.load(f)

    return productos


def seleccionar_productos(productos):
    print("--- GENERADOR DE ETIQUETAS TECI ---")
    print("Modo de ejecución:")
    print("1 - Generar UNA etiqueta por ID")
    print("2 - Generar LOTE consecutivo")
    print("3 - Generar IDs específicos (ej: 5,8,12)")

    modo = input("Selecciona opción: ").strip()

    if modo == "1":
        id_unico = input("ID del artículo: ").strip()
        seleccion = seleccionar_por_ids(productos, [id_unico])

    elif modo == "2":
        try:
            id_inicio = int(input("¿Desde qué ID empezar?: "))
            how_many = int(input("¿Cuántos artículos?: "))
        except ValueError:
            print("Valores inválidos")
            return []

        start_index = id_inicio - 1

        if start_index < 0:
            start_index = 0

        seleccion = productos[start_index:start_index + how_many]

    elif modo == "3":
        ids_input = input("Escribe los IDs separados por coma: ")
        lista_ids = [x.strip() for x in ids_input.split(",")]
        seleccion = seleccionar_por_ids(productos, lista_ids)

    else:
        print("Modo inválido")
        return []

    return seleccion

def asegurar_estado(item):
    estado = item.setdefault("estado", {})

    estado.setdefault("etiqueta_generada", False)
    estado.setdefault("impresa", False)
    estado.setdefault("fecha_generacion", None)
    estado.setdefault("fecha_impresion", None)

    return estado


def marcar_etiqueta_generada(
    item,
    id_catalogo,
    layout,
    size,
    ruta_img,
    back_variant="normal",
    chars_descripcion=0,
):
    estado = asegurar_estado(item)

    estado["etiqueta_generada"] = True
    estado["fecha_generacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    item["id_catalogo"] = id_catalogo
    item["imagen_principal"] = str(ruta_img).replace("\\", "/")

    item["plantilla"] = {
    "layout": layout,
    "size": size,
    "back_variant": back_variant,
    "descripcion_caracteres": chars_descripcion,
}


def guardar_productos_json(productos, ruta_json):
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)


def debe_regenerar_etiqueta(item):
    estado = item.get("estado", {})

    if not estado.get("etiqueta_generada", False):
        return True

    print("\nEste producto ya tiene etiqueta generada.")
    print(f"Fecha generación: {estado.get('fecha_generacion', 'sin fecha')}")
    print("1. Sí, regenerar")
    print("2. No, saltar")

    opcion = input("Elige una opción: ").strip()

    return opcion == "1"

def decidir_modo_regeneracion_lote(seleccion, force=False):
    """
    Decide cómo manejar productos que ya tienen etiqueta generada.

    Retorna:
    - "regenerar_todas"
    - "saltar_generadas"
    - "preguntar_una_por_una"
    """

    if force:
        return "regenerar_todas"

    ya_generadas = []

    for item in seleccion:
        estado = item.get("estado", {})

        if estado.get("etiqueta_generada", False):
            ya_generadas.append(item)

    if not ya_generadas:
        return "regenerar_todas"

    print("\nAlgunos productos seleccionados ya tienen etiqueta generada.")
    print(f"Productos seleccionados: {len(seleccion)}")
    print(f"Ya generados: {len(ya_generadas)}")

    ids_generados = [
        crear_id_catalogo(item.get("id"))
        for item in ya_generadas
    ]

    print("IDs ya generados:")
    print(", ".join(ids_generados))

    print("\n¿Qué quieres hacer?")
    print("1 - Regenerar TODOS sin volver a preguntar")
    print("2 - Saltar los que ya están generados")
    print("3 - Preguntar uno por uno")

    opcion = input("Elige una opción: ").strip()

    if opcion == "1":
        return "regenerar_todas"

    if opcion == "2":
        return "saltar_generadas"

    return "preguntar_una_por_una"


# =========================
# PROCESO PRINCIPAL
# =========================


def procesar_todo():
    config = get_config()
    json_data = config.processed / "1.json"

    mostrar_configuracion_actual(config, json_data)
    try:
        productos = cargar_productos_json(json_data)
    except Exception as e:
        print(f"Error cargando productos: {e}")
        return

    seleccion = seleccionar_productos(productos)

    if not seleccion:
        print("No se encontraron productos.")
        return

    print(f"\nIniciando lote de {len(seleccion)} productos...")

    modo_regeneracion = decidir_modo_regeneracion_lote(seleccion)

    hubo_cambios_json = False

    for item in seleccion:
        id_prod = item.get("id")
        id_catalogo = crear_id_catalogo(id_prod)

        print(f"\n>> Procesando Producto {id_prod} ({id_catalogo})...")

        estado = item.get("estado", {})
        ya_generada = estado.get("etiqueta_generada", False)

        if ya_generada:
            if modo_regeneracion == "saltar_generadas":
                print("Saltado: la etiqueta ya estaba generada.")
                continue

            if modo_regeneracion == "preguntar_una_por_una":
                if not debe_regenerar_etiqueta(item):
                    print("Saltado: la etiqueta ya estaba generada.")
                    continue

            if modo_regeneracion == "regenerar_todas":
                print("Etiqueta ya generada. Regenerando por decisión de lote.")

        ruta_img = buscar_imagen_producto(config, id_prod)

        if ruta_img:
            ruta_img = str(ruta_img).replace("\\", "/")

        print("Ruta encontrada:", ruta_img)

        if not ruta_img:
            print(f"No hay imagen para ID: {id_prod}")
            continue

        try:
            layout, size, origen_plantilla = determinar_plantilla(item)

            print(f"Tipo objeto: {item.get('tipo_objeto', 'otros')}")
            print(f"Subtipo: {item.get('subtipo', 'sin_subtipo')}")
            print(f"Plantilla seleccionada: {layout}/{size} ({origen_plantilla})")
        except ValueError as e:
            print(f"Error determinando plantilla para ID {id_prod}: {e}")
            continue

        print(f"Plantilla seleccionada: {layout}/{size}")

        try:

            try:
                back_psd, back_variant, chars_descripcion = resolver_back_psd_por_texto(
                    config=config,
                    layout=layout,
                    size=size,
                    descripcion=item.get("descripcion", ""),
                )

                print(f"Descripción: {chars_descripcion} caracteres")
                print(f"Plantilla reverso: {back_variant} ({back_psd.name})")

            except ValueError as e:
                print(f"Error en descripción para ID {id_prod}: {e}")
                continue

            resultado = renderizar_front_back(
                config=config,
                layout=layout,
                size=size,
                id_catalogo=id_catalogo,
                item=item,
                ruta_img=ruta_img,
                back_psd=back_psd,
            )

            print("   Front:", resultado["log_front"])
            print("   Back:", resultado["log_back"])
            print("   Exportado:", resultado["front"])
            print("   Exportado:", resultado["back"])

            front_ok = Path(resultado["front"]).exists()
            back_ok = Path(resultado["back"]).exists()

            if front_ok and back_ok:
                marcar_etiqueta_generada(
                    item=item,
                    id_catalogo=id_catalogo,
                    layout=layout,
                    size=size,
                    ruta_img=ruta_img,
                    back_variant=back_variant,
                    chars_descripcion=chars_descripcion,
                )

                hubo_cambios_json = True
                print("Estado JSON: etiqueta_generada = true")
            else:
                print("Estado JSON: no se actualizó porque faltó front o back")

        except Exception as e:
            print(f"   Error crítico en ID {id_prod}: {e}")

        if hubo_cambios_json:
            guardar_productos_json(productos, json_data)
            print("✔ JSON actualizado con estado de etiquetas.")

    print("\n✔ ¡Lote completado!")


if __name__ == "__main__":
    procesar_todo()
