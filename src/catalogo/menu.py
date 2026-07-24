import json
import re
from pathlib import Path
from datetime import datetime

from src.core.paths import get_config
from src.core.productos import seleccionar_por_ids, crear_id_catalogo, resolver_json_productos
from src.catalogo.plantillas import cargar_distribuciones_catalogo
from src.catalogo.texto import (
    distribuir_descripcion_en_cajas,
    formatear_medidas_catalogo,
)
from src.catalogo.imagenes import (
    buscar_carpeta_imagenes_catalogo,
    seleccionar_imagenes_catalogo_general,
)
from src.catalogo.exportacion import exportar_catalogo_pdf
from src.catalogo.photoshop import ejecutar_photoshop_catalogo

DISTRIBUCIONES_CATALOGO = cargar_distribuciones_catalogo()


def cargar_productos_catalogo(config):
    """
    Por ahora en DEV usamos el JSON de pruebas.
    """
    json_path = resolver_json_productos(config)

    if not json_path.exists():
        raise FileNotFoundError(f"No existe el JSON: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("El JSON debe contener una lista de productos")

    return data


def guardar_productos_catalogo(config, productos):
    """
    Guarda cambios en el JSON de la categoría activa.
    """

    json_path = resolver_json_productos(config)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=4)

    print(f"\n✔ JSON actualizado: {json_path}")


def marcar_catalogo_generado(producto, nombre_distribucion):
    """
    Marca en el JSON que el producto ya fue generado para catálogo.
    """

    producto["catalogo_generado"] = True
    producto["fecha_catalogo"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    producto["catalogo_distribucion"] = nombre_distribucion

    return producto


def mostrar_pendientes_catalogo():
    config = get_config()
    productos = cargar_productos_catalogo(config)

    pendientes = [
        producto
        for producto in productos
        if producto.get("catalogo_generado") is not True
    ]

    generados = [
        producto for producto in productos if producto.get("catalogo_generado") is True
    ]

    print(f"\n--- PENDIENTES DE CATÁLOGO / {config.modo} ---")
    print(f"Categoría: {config.categoria}")
    print(f"Total productos: {len(productos)}")
    print(f"Generados: {len(generados)}")
    print(f"Pendientes: {len(pendientes)}")

    if not pendientes:
        print("\n✔ No hay productos pendientes de catálogo.")
        return

    print("\n--- LISTA DE PENDIENTES ---")

    for producto in pendientes:
        id_catalogo = obtener_id_catalogo(producto)
        nombre = producto.get("nombre", "")
        descripcion = str(producto.get("descripcion", "")).strip()
        chars = len(descripcion)
        template_manual = str(producto.get("catalogo_template", "")).strip()

        if template_manual:
            distribucion = template_manual
        else:
            distribucion = resolver_template_catalogo(producto)

        print(f"{id_catalogo} | " f"{chars} chars | " f"{distribucion} | " f"{nombre}")


def generar_pendientes_catalogo():
    config = get_config()
    productos = cargar_productos_catalogo(config)

    pendientes = [
        producto
        for producto in productos
        if producto.get("catalogo_generado") is not True
    ]

    print(f"\n--- GENERAR PENDIENTES DE CATÁLOGO / {config.modo} ---")
    print(f"Categoría: {config.categoria}")
    print(f"Total productos: {len(productos)}")
    print(f"Pendientes: {len(pendientes)}")

    if not pendientes:
        print("\n✔ No hay productos pendientes de catálogo.")
        return

    print("\nSe generarán estos productos:")

    for producto in pendientes:
        id_catalogo = obtener_id_catalogo(producto)
        nombre = producto.get("nombre", "")
        descripcion = str(producto.get("descripcion", "")).strip()
        chars = len(descripcion)

        if producto.get("catalogo_template"):
            distribucion = producto.get("catalogo_template")
        else:
            distribucion = resolver_template_catalogo(producto)

        print(f"{id_catalogo} | " f"{chars} chars | " f"{distribucion} | " f"{nombre}")

    confirmar = input(
        "\n¿Generar todos los pendientes? Escribe SI para continuar: "
    ).strip()

    exportar_al_final = preguntar_exportar_catalogo_al_final()
    ids_generados = []
    if confirmar.upper() != "SI":
        print("Operación cancelada.")
        return

    generados = 0
    saltados = 0

    for producto in pendientes:
        ok = procesar_producto_catalogo(config, producto)

        if ok:
            generados += 1
            ids_generados.append(producto["id_catalogo"])
        else:
            saltados += 1

    if generados > 0:
        guardar_productos_catalogo(config, productos)

    print("\n--- RESUMEN PENDIENTES ---")
    print(f"Generados: {generados}")
    print(f"Saltados/error: {saltados}")
    exportar_si_corresponde(exportar_al_final, ids_generados)


def marcar_producto_pendiente_catalogo():
    config = get_config()
    productos = cargar_productos_catalogo(config)

    print(f"\n--- MARCAR PRODUCTO COMO PENDIENTE / {config.modo} ---")
    print(f"Categoría: {config.categoria}")

    id_input = input("\nID del producto, ejemplo ACT-0021 o 21: ").strip()

    seleccion = seleccionar_por_ids(productos, [id_input])

    if not seleccion:
        print("No encontré ese producto en el JSON.")
        return

    producto = seleccion[0]
    id_catalogo = obtener_id_catalogo(producto)

    print(f"\nProducto: {id_catalogo}")
    print(f"Nombre: {producto.get('nombre', '')}")
    print(f"Catálogo generado: {producto.get('catalogo_generado', False)}")
    print(f"Fecha catálogo: {producto.get('fecha_catalogo', '')}")
    print(f"Distribución usada: {producto.get('catalogo_distribucion', '')}")

    confirmar = input(
        "\n¿Marcar este producto como pendiente? Escribe SI para continuar: "
    ).strip()

    if confirmar.upper() != "SI":
        print("Operación cancelada.")
        return

    producto["catalogo_generado"] = False
    producto["fecha_catalogo"] = ""
    producto["catalogo_distribucion"] = ""

    guardar_productos_catalogo(config, productos)

    print(f"\n✔ {id_catalogo} marcado como pendiente de catálogo.")


def normalizar_distribucion_catalogo(valor):
    """
    Acepta:
    - 1
    - distribucion_1
    - distribucion_2
    - distribucion_4

    Devuelve:
    - distribucion_1
    - distribucion_2
    etc.
    """

    valor = str(valor or "").strip().lower()

    if not valor:
        return ""

    if valor.isdigit():
        return f"distribucion_{valor}"

    if valor.startswith("distribucion_"):
        return valor

    return valor


def mostrar_distribuciones_disponibles():
    print("\n--- DISTRIBUCIONES DISPONIBLES ---")

    for nombre, data in DISTRIBUCIONES_CATALOGO.items():
        capacidades = data.get("capacidades", {})
        total = sum(capacidades.values())
        paginas = data.get("paginas", 1)

        cajas = ", ".join(f"{caja}:{chars}" for caja, chars in capacidades.items())

        print(f"{nombre} | " f"{paginas} pág. | " f"{total} chars | " f"{cajas}")


def asignar_distribucion_producto():
    """
    Permite cambiar catalogo_template en el JSON.
    """

    config = get_config()
    productos = cargar_productos_catalogo(config)

    print(f"\n--- ASIGNAR DISTRIBUCIÓN / {config.modo} ---")
    print(f"Categoría: {config.categoria}")
    print(f"JSON: {resolver_json_productos(config)}")

    mostrar_distribuciones_disponibles()

    id_input = input("\nID del producto, ejemplo ACT-0006 o 6: ").strip()

    seleccion = seleccionar_por_ids(productos, [id_input])

    if not seleccion:
        print("No encontré ese producto en el JSON.")
        return

    producto = seleccion[0]
    id_catalogo = obtener_id_catalogo(producto)

    actual = str(producto.get("catalogo_template", "")).strip()
    descripcion = str(producto.get("descripcion", "")).strip()

    print(f"\nProducto: {id_catalogo}")
    print(f"Nombre: {producto.get('nombre', '')}")
    print(f"Caracteres descripción: {len(descripcion)}")
    print(f"Distribución actual: {actual if actual else '[automática]'}")

    nueva = input(
        "\nNueva distribución, ejemplo 2, 4, distribucion_2 "
        "o ENTER para automático: "
    ).strip()

    nueva = normalizar_distribucion_catalogo(nueva)

    if nueva and nueva not in DISTRIBUCIONES_CATALOGO:
        print(f"❌ Distribución inválida: {nueva}")
        return

    if nueva:
        producto["catalogo_template"] = nueva
        print(f"✔ {id_catalogo} asignado a {nueva}")
    else:
        if "catalogo_template" in producto:
            del producto["catalogo_template"]

        print(f"✔ {id_catalogo} quedó en modo automático")

    guardar_productos_catalogo(config, productos)


def obtener_id_catalogo(producto):
    """
    Usa id_catalogo si existe.
    Si no, convierte id numérico a ACT-0000.
    """
    id_catalogo = str(producto.get("id_catalogo", "")).strip()

    if id_catalogo:
        return id_catalogo

    return crear_id_catalogo(producto.get("id", ""))


def obtener_total_capacidad(distribucion):
    return sum(distribucion["capacidades"].values())


def resolver_template_catalogo(producto):
    """
    Decide qué distribución usar.

    Reglas:
    1. Si el producto tiene catalogo_template, se respeta.
    2. Si no tiene, solo se usan distribuciones con auto=true.
    3. Elige la distribución automática más pequeña donde quepa la descripción.
    """

    template_manual = str(producto.get("catalogo_template", "")).strip().lower()

    if template_manual:
        if template_manual in DISTRIBUCIONES_CATALOGO:
            return template_manual

        print(f"⚠ catalogo_template no válido: {template_manual}. Se usará automático.")

    descripcion = str(producto.get("descripcion", "")).strip()
    chars = len(descripcion)

    candidatas = []

    for nombre, distribucion in DISTRIBUCIONES_CATALOGO.items():
        if not distribucion.get("auto", False):
            continue

        if distribucion.get("paginas", 1) != 1:
            continue

        capacidad_total = sum(distribucion.get("capacidades", {}).values())

        candidatas.append(
            {
                "nombre": nombre,
                "capacidad": capacidad_total,
            }
        )

    candidatas.sort(key=lambda item: item["capacidad"])

    for item in candidatas:
        if chars <= item["capacidad"]:
            return item["nombre"]

    if candidatas:
        return candidatas[-1]["nombre"]

    raise ValueError(
        "No hay distribuciones automáticas disponibles. "
        "Marca al menos una distribución de una página con auto=true."
    )


def obtener_numero_categoria(config):
    categoria = str(config.categoria or "").strip()

    try:
        return int(categoria.split("-")[0])
    except Exception:
        return 0


def obtener_numero_distribucion(nombre_distribucion):
    try:
        return int(str(nombre_distribucion).split("_")[-1])
    except Exception:
        return 0


def crear_nombre_mesa_catalogo(
    config,
    id_catalogo,
    nombre_distribucion,
    pagina_num,
):
    categoria_num = obtener_numero_categoria(config)
    distribucion_num = obtener_numero_distribucion(nombre_distribucion)

    return (
        f"CAT{categoria_num:02d}_"
        f"{id_catalogo}_"
        f"D{distribucion_num:02d}_"
        f"P{pagina_num:02d}"
    )


def crear_configs_catalogo(config, producto, imagenes, nombre_distribucion):
    """
    Crea una o varias configs para Photoshop según la distribución.
    """

    id_catalogo = obtener_id_catalogo(producto)

    if not id_catalogo:
        raise ValueError("No se pudo obtener id_catalogo")

    distribucion = DISTRIBUCIONES_CATALOGO[nombre_distribucion]

    descripcion_original = str(producto.get("descripcion", ""))

    descripcion_cajas, descripcion_overflow = distribuir_descripcion_en_cajas(
        descripcion_original,
        capacidades=distribucion["capacidades"],
        margen_config=distribucion.get("margen", {}),
    )

    print(
        f"Descripción {id_catalogo} | {nombre_distribucion}: "
        f"original {len(descripcion_original)} | "
        + " | ".join(
            f"{caja}: {len(texto)}/{distribucion['capacidades'][caja]}"
            for caja, texto in descripcion_cajas.items()
        )
    )

    if descripcion_overflow:
        print(
            f"⚠ Descripción excede {nombre_distribucion} en {id_catalogo}: "
            f"sobran {len(descripcion_overflow)} caracteres."
        )

    configs = []

    for index in range(distribucion["paginas"]):
        pagina_num = index + 1
        pagina_key = f"pagina_{pagina_num}"

        template_mesa = distribucion["template_mesas"][index]

        categoria_num = obtener_numero_categoria(config)
        tipo_mesa = f"CAT{categoria_num:02d}"

        datos_texto = {
            "NAME_PRODUCT": str(producto.get("nombre", "")),
            "MEDIDAS": formatear_medidas_catalogo(producto.get("medidas", "")),
            "PRECIO": str(producto.get("precio", "")),
            "NOTAS": str(producto.get("notas", "")),
        }

        # Agregar textos de descripción repartidos por caja.
        for caja, texto in descripcion_cajas.items():
            datos_texto[caja] = texto

        imagenes_pagina = {}

        for capa_img in distribucion["imagenes"].get(pagina_key, []):
            imagenes_pagina[capa_img] = imagenes.get(capa_img, "")

        textos_pagina = distribucion.get("textos", {}).get(pagina_key, [])
        areas_pagina = distribucion.get("areas", {}).get(pagina_key, [])

        nombre_nueva_mesa = crear_nombre_mesa_catalogo(
            config=config,
            id_catalogo=id_catalogo,
            nombre_distribucion=nombre_distribucion,
            pagina_num=pagina_num,
        )

        config_data = {
            "template_path": str(distribucion["psd"]).replace("\\", "/"),
            "origen_mesa": "BUSCAR_ULTIMA",
            "template_mesa": template_mesa,
            "tipo_mesa": tipo_mesa,
            "separacion_mesas": 80,
            "nombre_nueva_mesa": nombre_nueva_mesa,
            "datos_texto": datos_texto,
            "imagenes": imagenes_pagina,
            "areas": areas_pagina,
            "textos": textos_pagina,
        }

        # Si la distribución tiene varias páginas, la página 2 debe colocarse
        # justo después de la página anterior del mismo producto.
        if pagina_num > 1:
            config_data["referencia_mesa"] = crear_nombre_mesa_catalogo(
                config=config,
                id_catalogo=id_catalogo,
                nombre_distribucion=nombre_distribucion,
                pagina_num=pagina_num - 1,
            )

        configs.append(config_data)

    return configs


def procesar_producto_catalogo(config, producto):
    """
    Genera catálogo para un producto usando la distribución asignada o automática.
    """

    id_catalogo = obtener_id_catalogo(producto)
    nombre_distribucion = resolver_template_catalogo(producto)

    print(f"\n>> Procesando {id_catalogo}")
    print("Nombre:", producto.get("nombre", ""))
    print("Distribución:", nombre_distribucion)

    carpeta_producto = buscar_carpeta_imagenes_catalogo(config, id_catalogo)

    if not carpeta_producto:
        print(f"⚠ No encontré carpeta de imágenes para {id_catalogo}")
        print("Busqué en:")
        print(config.img / id_catalogo)
        return False

    try:
        imagenes = seleccionar_imagenes_catalogo_general(
            carpeta_producto,
            id_catalogo,
        )

        print("Imágenes disponibles:")
        for capa, ruta in imagenes.items():
            print(f"  {capa}: {ruta if ruta else '[vacía]'}")

        configs = crear_configs_catalogo(
            config=config,
            producto=producto,
            imagenes=imagenes,
            nombre_distribucion=nombre_distribucion,
        )
        for i, config_data in enumerate(configs, start=1):
            print(f"Enviando página {i}/{len(configs)} a Photoshop...")
            resultado = ejecutar_photoshop_catalogo(config_data)

            for parte in str(resultado).split(" | "):
                print("  " + parte)

        marcar_catalogo_generado(producto, nombre_distribucion)

        return True

    except Exception as e:
        print(f"❌ Error generando catálogo para {id_catalogo}: {e}")
        return False


def preguntar_exportar_catalogo_al_final():
    """
    Pregunta antes de generar si se debe exportar al terminar.
    La exportación automática será sin portada y solo con esos IDs.
    """

    print()
    opcion = input(
        "¿Quieres exportar a PDF al terminar la generación? "
        "(solo estos productos, sin portada) [S/N]: "
    ).strip().lower()

    return opcion in ["s", "si", "sí", "y", "yes"]


def exportar_si_corresponde(exportar_al_final, ids_generados):
    """
    Exporta solo los productos generados en esta operación.
    """

    if not exportar_al_final:
        return

    if not ids_generados:
        print()
        print("No se exportó porque no se generó ningún producto.")
        return

    print()
    print("Exportando a PDF solo los productos generados, sin portada...")

    exportar_catalogo_pdf(
        ids_catalogo=ids_generados,
        preguntar_portada=False,
    )


def exportar_catalogo_manual():
    """
    Exportación manual desde la opción 4.
    Permite exportar todo o IDs específicos.
    """

    print("\n--- EXPORTAR CATÁLOGO A PDF ---")
    print("1. Exportar todo el catálogo generado")
    print("2. Exportar IDs específicos")
    print("0. Volver")

    opcion = input("\nSelecciona opción: ").strip()

    if opcion == "1":
        exportar_catalogo_pdf()
        return

    if opcion == "2":
        entrada = input("IDs a exportar, ejemplo 2,5,8 o ACT-0002, ACT-0005: ").strip()

        ids = [
            item.strip() for item in entrada.replace(",", " ").split() if item.strip()
        ]

        if not ids:
            print("❌ No escribiste IDs válidos.")
            return

        exportar_catalogo_pdf(ids_catalogo=ids)
        return

    if opcion == "0":
        return

    print("Opción inválida.")


def procesar_catalogo_uno():
    config = get_config()
    productos = cargar_productos_catalogo(config)

    print(f"\n--- GENERADOR DE CATÁLOGO TECI / {config.modo} ---")
    print("Distribuciones:", config.templates_catalogo_distribuciones)
    print("Imágenes:", config.img)

    id_input = input("\nID del producto, ejemplo ACT-0002 o 2: ").strip()

    exportar_al_final = preguntar_exportar_catalogo_al_final()

    seleccion = seleccionar_por_ids(productos, [id_input])
    ids_generados = []
    if not seleccion:
        print("No encontré ese producto en el JSON.")
        return

    generados = 0
    ok = procesar_producto_catalogo(config, seleccion[0])

    if ok:
        guardar_productos_catalogo(config, productos)
        generados = 1
        ids_generados.append(seleccion[0]["id_catalogo"])

    print("\n✔ Proceso terminado.")
    exportar_si_corresponde(exportar_al_final, ids_generados)


def procesar_catalogo_lote():
    config = get_config()
    productos = cargar_productos_catalogo(config)

    print(f"\n--- GENERADOR DE CATÁLOGO POR LOTE / {config.modo} ---")
    print("Base:", config.base)
    print("Imágenes:", config.img)

    inicio = input("ID inicial, ejemplo 2: ").strip()
    fin = input("ID final, ejemplo 8: ").strip()

    exportar_al_final = preguntar_exportar_catalogo_al_final()
    ids_generados = []

    try:
        inicio_num = int(inicio)
        fin_num = int(fin)
    except ValueError:
        print("❌ Los IDs deben ser números.")
        return

    if inicio_num > fin_num:
        print("❌ El ID inicial no puede ser mayor que el final.")
        return

    ids = [str(i) for i in range(inicio_num, fin_num + 1)]

    seleccion = seleccionar_por_ids(productos, ids)

    if not seleccion:
        print("No encontré productos para ese rango.")
        return

    print(f"\nProductos encontrados: {len(seleccion)}")
    print("Iniciando generación de catálogo...")

    generados = 0
    saltados = 0

    for producto in seleccion:
        ok = procesar_producto_catalogo(config, producto)

        if ok:
            generados += 1
            ids_generados.append(producto["id_catalogo"])
        else:
            saltados += 1

    if generados > 0:
        guardar_productos_catalogo(config, productos)

    print("\n--- RESUMEN ---")
    print(f"Generados: {generados}")
    print(f"Saltados/error: {saltados}")
    exportar_si_corresponde(exportar_al_final, ids_generados)


def procesar_catalogo_ids_especificos():
    config = get_config()
    productos = cargar_productos_catalogo(config)

    print(f"\n--- GENERADOR DE CATÁLOGO POR IDS / {config.modo} ---")
    print("Base:", config.base)
    print("Imágenes:", config.img)

    entrada = input("IDs a generar, ejemplo 2,5,8,12: ").strip()

    ids = [item.strip() for item in entrada.split(",") if item.strip()]

    exportar_al_final = preguntar_exportar_catalogo_al_final()
    ids_generados = []

    if not ids:
        print("❌ No escribiste IDs válidos.")
        return

    seleccion = seleccionar_por_ids(productos, ids)

    if not seleccion:
        print("No encontré productos para esos IDs.")
        return

    print(f"\nProductos encontrados: {len(seleccion)}")
    print("Iniciando generación de catálogo...")

    generados = 0
    saltados = 0

    for producto in seleccion:
        ok = procesar_producto_catalogo(config, producto)

        if ok:
            generados += 1
            ids_generados.append(producto["id_catalogo"])
        else:
            saltados += 1

    if generados > 0:
        guardar_productos_catalogo(config, productos)

    print("\n--- RESUMEN ---")
    print(f"Generados: {generados}")
    print(f"Saltados/error: {saltados}")
    exportar_si_corresponde(exportar_al_final, ids_generados)


def pausar():
    input("\nPresiona ENTER para continuar...")


def mostrar_menu_catalogo(config):
    print(f"\n--- CATÁLOGO TECI / {config.modo} ---")
    print(f"Base: {config.base}")
    print(f"JSON: {resolver_json_productos(config)}")
    print(f"Imágenes: {config.img}")
    print(f"Distribuciones PSD: {config.templates_catalogo_distribuciones}")
    print(f"Portadas PSD: {config.templates_catalogo_portadas}")
    print(f"Exportación: {config.catalogo_exportacion}")

    print("\n1 - Generar UN producto")
    print("2 - Generar LOTE consecutivo")
    print("3 - Generar IDs específicos")
    print("4 - Exportar catálogo a PDF")
    print("5 - Asignar distribución a producto")
    print("6 - Ver pendientes de catálogo")
    print("7 - Generar pendientes de catálogo")
    print("0 - Volver al menú anterior")


def main():
    config = get_config()

    while True:
        mostrar_menu_catalogo(config)

        opcion = input("\nSelecciona opción: ").strip()

        if opcion == "1":
            procesar_catalogo_uno()
            pausar()

        elif opcion == "2":
            procesar_catalogo_lote()
            pausar()

        elif opcion == "3":
            procesar_catalogo_ids_especificos()
            pausar()

        elif opcion == "4":
            exportar_catalogo_manual()
            pausar()

        elif opcion == "5":
            asignar_distribucion_producto()
            pausar()
        elif opcion == "6":
            mostrar_pendientes_catalogo()
            pausar()
            
        elif opcion == "7":
            generar_pendientes_catalogo()
            pausar()

        elif opcion == "0":
            return

        else:
            print("Opción inválida.")
            pausar()


if __name__ == "__main__":
    main()
