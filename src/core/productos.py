from pathlib import Path


EXT_IMAGENES_PROCESADAS = [".png"]
EXT_IMAGENES_FALLBACK = [".jpg", ".jpeg", ".webp"]


def normalizar_numero_id(valor):
    """
    Convierte entradas como:
    4
    "4"
    "ATC-0004"
    "ACT-0004"
    "ATC 0004"
    "atc-4"

    a:
    "4"
    """

    texto = str(valor).strip().upper()

    # Caso simple: "4"
    if texto.isdigit():
        return str(int(texto))

    # Extraer solo números
    numeros = "".join(c for c in texto if c.isdigit())

    if not numeros:
        return ""

    return str(int(numeros))


def crear_id_catalogo(valor, prefijo="ACT"):
    """
    Convierte:
    4 → ATC-0004
    """

    numero = normalizar_numero_id(valor)

    if not numero:
        return ""

    return f"{prefijo}-{int(numero):04d}"


def candidatos_principal():
    """
    Nombres aceptados para la imagen principal en estructura nueva.
    """

    nombres = []

    for base in ["principal", "main", "portada", "foto_principal"]:
        for ext in EXT_IMAGENES_PROCESADAS + EXT_IMAGENES_FALLBACK:
            nombres.append(base + ext)

    return nombres


def candidatos_legacy(numero_id, incluir_fallback=True):
    """
    Nombres aceptados para la estructura vieja.

    Para ID 4 busca:
    4.png
    4.jpg
    4.jpeg
    4-1.png
    4h.jpg
    etc.
    """

    bases = [
        f"{numero_id}",
        f"{numero_id}-1",
        f"{numero_id}-2",
        f"{numero_id}h",
    ]

    nombres = []

    for base in bases:
        for ext in EXT_IMAGENES_PROCESADAS:
            nombres.append(base + ext)
    if incluir_fallback:
        for base in bases:
            for ext in EXT_IMAGENES_FALLBACK:
                nombres.append(base + ext)

    return nombres


def buscar_archivo_por_nombre(carpeta, nombres):
    """
    Busca archivos por nombre sin importar mayúsculas/minúsculas.
    """

    carpeta = Path(carpeta)

    if not carpeta.exists():
        return None

    disponibles = {}

    for archivo in carpeta.iterdir():
        if archivo.is_file():
            disponibles[archivo.name.lower()] = archivo

    for nombre in nombres:
        encontrado = disponibles.get(nombre.lower())
        if encontrado:
            return encontrado

    return None


def buscar_imagen_producto(config, id_usuario):
    """
    Busca la imagen principal del producto usando este orden:

    1. Estructura nueva oficial:
       img/ACT-0004/principal.png

    2. Estructura vieja dentro de img:
       img/4.png
       img/4.jpg
       img/4.jpeg
       img/4-1.png
       img/4h.jpg

    3. Estructura vieja alternativa en la raíz:
       4.png
       4.jpg
       4.jpeg
    """

    numero_id = normalizar_numero_id(id_usuario)
    id_catalogo = crear_id_catalogo(id_usuario)

    if not numero_id:
        return None

    # 1. Estructura nueva oficial:
    # img/ACT-0004/principal.png
    encontrada = config.principal_image(id_catalogo)

    if encontrada:
        return encontrada

    # 2. Por si hay imagen principal con otro nombre aceptado
    carpeta_producto = config.producto_img_dir(id_catalogo)

    encontrada = buscar_archivo_por_nombre(
        carpeta_producto,
        candidatos_principal()
    )

    if encontrada:
        return encontrada

    # 3. Estructura vieja dentro de img/
    encontrada = buscar_archivo_por_nombre(
        config.img,
        candidatos_legacy(numero_id)
    )

    if encontrada:
        return encontrada

    # 4. Estructura vieja alternativa en raíz de categoría/base
    encontrada = buscar_archivo_por_nombre(
        config.base,
        candidatos_legacy(numero_id)
    )

    if encontrada:
        return encontrada

    return None

def seleccionar_por_ids(productos, ids_usuario):
    """
    Permite que el usuario escriba solo números.

    Si escribe:
    4

    Busca coincidencias con:
    id = 4
    id_anterior = 4
    id_catalogo = ACT-0004
    """

    ids_normalizados = set()

    for valor in ids_usuario:
        numero = normalizar_numero_id(valor)

        if not numero:
            continue

        ids_normalizados.add(numero)
        ids_normalizados.add(crear_id_catalogo(numero).lower())

    seleccion = []

    for producto in productos:
        id_producto = normalizar_numero_id(producto.get("id", ""))
        id_anterior = normalizar_numero_id(producto.get("id_anterior", ""))
        id_catalogo = str(producto.get("id_catalogo", "")).strip().lower()

        claves_producto = {
            id_producto,
            id_anterior,
            id_catalogo,
        }

        if claves_producto & ids_normalizados:
            seleccion.append(producto)

    return seleccion


def resolver_json_productos(config):
    """
    Resuelve el JSON principal de productos para la categoría/modo actual.

    Prioridad:
    1. processed/1.json
    2. Si solo existe un .json en processed/, usar ese.
    3. Si hay varios .json y no existe 1.json, pedir decisión manual.
    """

    json_default = config.processed / "1.json"

    if json_default.exists():
        return json_default

    if not config.processed.exists():
        raise FileNotFoundError(
            f"No existe la carpeta de JSON procesados: {config.processed}"
        )

    jsons = sorted(config.processed.glob("*.json"))

    if len(jsons) == 1:
        return jsons[0]

    if len(jsons) == 0:
        raise FileNotFoundError(
            "No hay ningún JSON de productos para esta categoría.\n"
            f"Carpeta revisada: {config.processed}"
        )

    disponibles = "\n".join(f"  - {p.name}" for p in jsons)

    raise FileNotFoundError(
        "No existe processed/1.json y hay varios JSON disponibles.\n"
        "No puedo decidir automáticamente cuál usar.\n\n"
        f"Carpeta: {config.processed}\n"
        f"JSON disponibles:\n{disponibles}\n\n"
        "Solución rápida: renombra o copia el JSON correcto como 1.json."
    )
