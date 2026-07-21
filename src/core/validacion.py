import json
import re
from pathlib import Path

from src.core.paths import get_config
from src.core.productos import crear_id_catalogo, normalizar_numero_id, resolver_json_productos


EXTENSIONES_IMG = [".png", ".jpg", ".jpeg", ".webp"]


def cargar_json_productos(config):
    ruta_json = resolver_json_productos(config)

    if not ruta_json.exists():
        return None, ruta_json

    with open(ruta_json, "r", encoding="utf-8") as f:
        return json.load(f), ruta_json


def existe_imagen_principal(config, id_catalogo):
    carpeta = config.img / id_catalogo

    if not carpeta.exists():
        return False

    for ext in EXTENSIONES_IMG:
        if (carpeta / f"principal{ext}").exists():
            return True

    return False


def obtener_carpetas_act(config):
    if not config.img.exists():
        return []

    return [
        carpeta
        for carpeta in config.img.iterdir()
        if carpeta.is_dir() and carpeta.name.upper().startswith("ACT-")
    ]


def obtener_imagenes_sueltas(config):
    if not config.img.exists():
        return []

    return [
        archivo
        for archivo in config.img.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_IMG
    ]

def indexar_productos_por_act(productos):
    productos_por_act = {}

    for producto in productos:
        id_prod = producto.get("id")
        id_catalogo = producto.get("id_catalogo") or crear_id_catalogo(id_prod)

        if id_catalogo:
            productos_por_act[str(id_catalogo).upper()] = producto

    return productos_por_act

def buscar_imagen_suelta_probable(config, id_prod):
    """
    Busca imágenes sueltas tipo:
    1.jpeg
    25.jpeg
    25-1.png
    23h.jpeg
    """

    numero = normalizar_numero_id(id_prod)

    if not numero or not config.img.exists():
        return []

    patrones = [
        f"{numero}",
        f"{numero}-",
        f"{numero}h",
    ]

    encontradas = []

    for archivo in config.img.iterdir():
        if not archivo.is_file():
            continue

        if archivo.suffix.lower() not in EXTENSIONES_IMG:
            continue

        stem = archivo.stem.lower()

        for patron in patrones:
            if stem == patron.lower() or stem.startswith(patron.lower()):
                encontradas.append(archivo.name)
                break

    return encontradas

def validar_carpeta_act(config, carpeta_act, productos_por_act):
    errores = []
    advertencias = []

    id_catalogo = carpeta_act.name.upper()
    producto = productos_por_act.get(id_catalogo)

    if not validar_nombre_act(id_catalogo):
        errores.append("carpeta ACT mal nombrada")

    if producto is None:
        errores.append("carpeta ACT no existe en JSON")
        return {
            "id_catalogo": id_catalogo,
            "id": None,
            "errores": errores,
            "advertencias": advertencias,
        }

    id_prod = producto.get("id")

    if not existe_imagen_principal(config, id_catalogo):
        errores.append("sin principal.png/jpg")

    if campo_vacio(producto.get("nombre")):
        errores.append("sin nombre")

    if campo_vacio(producto.get("descripcion")):
        advertencias.append("sin descripción")

    if campo_vacio(producto.get("precio")):
        advertencias.append("sin precio")
    elif not validar_precio(producto.get("precio")):
        advertencias.append(f"precio con formato sospechoso: {producto.get('precio')}")

    if campo_vacio(producto.get("medidas")):
        advertencias.append("sin medidas")

    if nota_tiene_comillas(producto.get("notas")):
        advertencias.append("notas con comillas")

    if descripcion_tiene_puntuacion_sucia(producto.get("descripcion", "")):
        advertencias.append("descripción con puntuación sospechosa")

    front = config.output / f"{id_catalogo}_front.png"
    back = config.output / f"{id_catalogo}_back.png"

    estado = producto.get("estado", {})
    etiqueta_generada = estado.get("etiqueta_generada", False)

    if etiqueta_generada:
        if not front.exists():
            advertencias.append("estado dice generada, pero falta front")
        if not back.exists():
            advertencias.append("estado dice generada, pero falta back")

    return {
        "id": id_prod,
        "id_catalogo": id_catalogo,
        "errores": errores,
        "advertencias": advertencias,
    }

def validar_nombre_act(nombre):
    return re.fullmatch(r"ACT-\d{4}", nombre.upper()) is not None


def campo_vacio(valor):
    if valor is None:
        return True

    if isinstance(valor, str) and not valor.strip():
        return True

    if isinstance(valor, list) and not valor:
        return True

    return False


def descripcion_tiene_puntuacion_sucia(texto):
    if not texto:
        return False

    patrones = [
        r"\s+[,.;:!?]",     # espacio antes de coma/punto
        r",{2,}",           # coma doble
        r"\.{2,}",          # punto doble
        r"\. [a-záéíóúñ]",  # después de punto inicia minúscula
    ]

    return any(re.search(p, texto) for p in patrones)


def nota_tiene_comillas(texto):
    if not texto:
        return False

    texto = str(texto).strip()

    return (
        texto.startswith('"')
        or texto.endswith('"')
        or texto.startswith("'")
        or texto.endswith("'")
        or "“" in texto
        or "”" in texto
    )


def validar_precio(precio):
    if not precio:
        return False

    precio = str(precio).strip()

    return re.fullmatch(r"\$\d{1,3}(,\d{3})*(\.\d{2})", precio) is not None


def validar_producto(config, producto):
    errores = []
    advertencias = []

    id_prod = producto.get("id")
    id_catalogo = producto.get("id_catalogo") or crear_id_catalogo(id_prod)

    if campo_vacio(id_prod):
        errores.append("sin id")

    if campo_vacio(id_catalogo):
        errores.append("sin id_catalogo")

    if campo_vacio(producto.get("nombre")):
        errores.append("sin nombre")

    if campo_vacio(producto.get("descripcion")):
        advertencias.append("sin descripción")

    if campo_vacio(producto.get("precio")):
        advertencias.append("sin precio")
    elif not validar_precio(producto.get("precio")):
        advertencias.append(f"precio con formato sospechoso: {producto.get('precio')}")

    if campo_vacio(producto.get("medidas")):
        advertencias.append("sin medidas")

    if nota_tiene_comillas(producto.get("notas")):
        advertencias.append("notas con comillas")

    if descripcion_tiene_puntuacion_sucia(producto.get("descripcion", "")):
        advertencias.append("descripción con puntuación sospechosa")

    carpeta_img = config.img / id_catalogo

    if not carpeta_img.exists():
        errores.append(f"sin carpeta de imágenes: img/{id_catalogo}")
    else:
        if not existe_imagen_principal(config, id_catalogo):
            errores.append(f"sin principal.png/jpg: img/{id_catalogo}/principal")

    front = config.output / f"{id_catalogo}_front.png"
    back = config.output / f"{id_catalogo}_back.png"

    estado = producto.get("estado", {})
    etiqueta_generada = estado.get("etiqueta_generada", False)

    if etiqueta_generada:
        if not front.exists():
            advertencias.append("estado dice generada, pero falta front")
        if not back.exists():
            advertencias.append("estado dice generada, pero falta back")

    return {
        "id": id_prod,
        "id_catalogo": id_catalogo,
        "errores": errores,
        "advertencias": advertencias,
    }


def imprimir_lista(titulo, elementos, max_items=40):
    print(f"\n{titulo}")

    if not elementos:
        print("  OK")
        return

    for item in elementos[:max_items]:
        print(f"  - {item}")

    if len(elementos) > max_items:
        print(f"  ... y {len(elementos) - max_items} más")

def tiene_etiqueta_front_back(config, id_catalogo):
    front = config.output / f"{id_catalogo}_front.png"
    back = config.output / f"{id_catalogo}_back.png"

    return front.exists(), back.exists()


def obtener_estado_etiquetas(config, productos_por_act):
    generadas = []
    incompletas = []
    pendientes = []

    for id_catalogo in sorted(productos_por_act.keys()):
        producto = productos_por_act[id_catalogo]
        id_prod = producto.get("id")
        estado = producto.get("estado", {})

        front_ok, back_ok = tiene_etiqueta_front_back(config, id_catalogo)

        etiqueta_generada_json = estado.get("etiqueta_generada", False)

        item = {
            "id": id_prod,
            "id_catalogo": id_catalogo,
            "front_ok": front_ok,
            "back_ok": back_ok,
            "json_generada": etiqueta_generada_json,
            "fecha_generacion": estado.get("fecha_generacion"),
        }

        if front_ok and back_ok:
            generadas.append(item)
        elif front_ok or back_ok:
            incompletas.append(item)
        else:
            pendientes.append(item)

    return generadas, incompletas, pendientes


def validar_proyecto():
    config = get_config()

    print("\n=== VALIDACIÓN DEL PROYECTO ===")
    print(f"Modo: {config.modo}")
    print(f"Categoría: {config.categoria}")
    print(f"Base: {config.base}")
    print(f"JSON: {resolver_json_productos(config)}")
    print(f"Imágenes: {config.img}")
    print(f"Etiquetas: {config.output}")

    productos, ruta_json = cargar_json_productos(config)

    if productos is None:
        print(f"\n❌ No existe JSON: {ruta_json}")
        return

    print(f"\nProductos en JSON: {len(productos)}")

    errores_productos = []
    advertencias_productos = []

    productos_por_act = indexar_productos_por_act(productos)
    ids_json = set(productos_por_act.keys())

    etiquetas_generadas, etiquetas_incompletas, etiquetas_pendientes = obtener_estado_etiquetas(
        config,
        productos_por_act,
    )

    carpetas_act = obtener_carpetas_act(config)

    for carpeta_act in carpetas_act:
        resultado = validar_carpeta_act(
            config=config,
            carpeta_act=carpeta_act,
            productos_por_act=productos_por_act,
        )

        if resultado["errores"]:
            errores_productos.append(resultado)

        if resultado["advertencias"]:
            advertencias_productos.append(resultado)

    carpetas_act_nombres = {c.name.upper() for c in carpetas_act}

    carpetas_mal_nombradas = [
        c.name for c in carpetas_act if not validar_nombre_act(c.name)
    ]

    carpetas_sin_json = sorted([
        nombre
        for nombre in carpetas_act_nombres
        if nombre not in ids_json
    ])

    json_sin_carpeta = sorted([
        nombre
        for nombre in ids_json
        if nombre not in carpetas_act_nombres
    ])

    pendientes_migracion = []

    for id_catalogo in json_sin_carpeta:
        producto = productos_por_act.get(id_catalogo, {})
        id_prod = producto.get("id")

        imagenes_probables = buscar_imagen_suelta_probable(config, id_prod)

        pendientes_migracion.append({
            "id_catalogo": id_catalogo,
            "id": id_prod,
            "imagenes_probables": imagenes_probables,
        })

    imagenes_sueltas = obtener_imagenes_sueltas(config)

    print("\n--- RESUMEN ---")
    print(f"Carpetas ACT con errores: {len(errores_productos)}")
    print(f"Carpetas ACT con advertencias: {len(advertencias_productos)}")
    print(f"Carpetas ACT: {len(carpetas_act)}")
    print(f"Carpetas ACT mal nombradas: {len(carpetas_mal_nombradas)}")
    print(f"Carpetas ACT sin producto en JSON: {len(carpetas_sin_json)}")
    print(f"Productos pendientes de migrar a carpeta ACT: {len(json_sin_carpeta)}")
    print(f"Imágenes sueltas en img/: {len(imagenes_sueltas)}")

    print(f"Etiquetas generadas front/back: {len(etiquetas_generadas)}")
    print(f"Etiquetas incompletas: {len(etiquetas_incompletas)}")
    print(f"Etiquetas pendientes: {len(etiquetas_pendientes)}")

    print("\n--- ERRORES POR PRODUCTO ---")
    if not errores_productos:
        print("OK")
    else:
        for item in errores_productos:
            print(f"\n{item['id_catalogo']} / ID {item['id']}")
            for err in item["errores"]:
                print(f"  ❌ {err}")

    print("\n--- ADVERTENCIAS POR PRODUCTO ---")
    if not advertencias_productos:
        print("OK")
    else:
        for item in advertencias_productos:
            print(f"\n{item['id_catalogo']} / ID {item['id']}")
            for adv in item["advertencias"]:
                print(f"  ⚠ {adv}")

    imprimir_lista(
        "--- CARPETAS ACT MAL NOMBRADAS ---",
        carpetas_mal_nombradas,
    )

    imprimir_lista(
        "--- CARPETAS ACT SIN PRODUCTO EN JSON ---",
        carpetas_sin_json,
    )

    print("\n--- PRODUCTOS PENDIENTES DE MIGRAR A CARPETA ACT ---")

    if not pendientes_migracion:
        print("  OK")
    else:
        for item in pendientes_migracion:
            imgs = item["imagenes_probables"]

            if imgs:
                print(
                    f"  - {item['id_catalogo']} / ID {item['id']} "
                    f"→ posibles imágenes: {', '.join(imgs)}"
                )
            else:
                print(
                    f"  - {item['id_catalogo']} / ID {item['id']} "
                    f"→ sin imagen suelta probable"
                )

    imprimir_lista(
        "--- IMÁGENES SUELTAS EN img/ ---",
        [img.name for img in imagenes_sueltas],
    )

    print("\n=== VALIDACIÓN TERMINADA ===")

    if errores_productos:
        print("Resultado: ❌ hay errores en carpetas ACT existentes.")
    elif advertencias_productos:
        print("Resultado: ⚠ las carpetas ACT existentes no tienen errores críticos, pero sí advertencias.")
    else:
        print("Resultado: ✅ carpetas ACT existentes listas.")

    if pendientes_migracion:
        print(
            f"Pendiente: hay {len(pendientes_migracion)} productos del JSON "
            "sin carpeta ACT. No bloquean el trabajo actual, pero conviene migrarlos."
        )
    print("\n--- ETIQUETAS GENERADAS ---")

    if not etiquetas_generadas:
        print("  Ninguna")
    else:
        for item in etiquetas_generadas:
            fecha = item["fecha_generacion"] or "sin fecha"
            print(f"  - {item['id_catalogo']} / ID {item['id']} / {fecha}")

    print("\n--- ETIQUETAS INCOMPLETAS ---")

    if not etiquetas_incompletas:
        print("  OK")
    else:
        for item in etiquetas_incompletas:
            partes = []

            if item["front_ok"]:
                partes.append("front OK")
            else:
                partes.append("front falta")

            if item["back_ok"]:
                partes.append("back OK")
            else:
                partes.append("back falta")

            print(
                f"  - {item['id_catalogo']} / ID {item['id']} "
                f"→ {', '.join(partes)}"
            )

    print("\n--- ETIQUETAS PENDIENTES ---")

    if not etiquetas_pendientes:
        print("  OK")
    else:
        for item in etiquetas_pendientes:
            print(f"  - {item['id_catalogo']} / ID {item['id']}")


def main():
    validar_proyecto()


if __name__ == "__main__":
    main()
