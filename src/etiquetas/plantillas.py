from src.core.productos import crear_id_catalogo


DEFAULT_RULE = {
    "layout": "vertical",
    "size_mode": "descripcion",
    "small_max_chars": 440,
}


REGLAS_POR_TIPO = {
    "mueble": {
        "layout": "vertical",
        "size": "a5",
    },

    "iluminacion": {
        "layout": "vertical",
        "size": "large",
    },

    "reloj": {
        "layout": "vertical",
        "size": "large",
    },

    "bronce": {
        "layout": "vertical",
        "size": "large",
    },

    "alabastro": {
        "layout": "vertical",
        "size": "large",
    },

    "porcelana": {
        "layout": "vertical",
        "size_mode": "descripcion",
        "small_max_chars": 440,
    },

    "lladro": {
        "layout": "vertical",
        "size_mode": "descripcion",
        "small_max_chars": 440,
    },

    "cristal": {
        "layout": "vertical",
        "size_mode": "descripcion",
        "small_max_chars": 440,
    },

    "plateria": {
        "layout": "vertical",
        "size_mode": "descripcion",
        "small_max_chars": 440,
    },

    "pintura": {
        "layout": "vertical",
        "size": "large",
    },

    "otros": {
        "layout": "vertical",
        "size_mode": "descripcion",
        "small_max_chars": 440,
    },
}


REGLAS_POR_ARTICULO = {
    # Excepciones manuales.
    # Ejemplo:
    #
    # "ATC-0006": {
    #     "layout": "horizontal",
    #     "size": "large",
    # },
}


def calcular_size_por_descripcion(descripcion, small_max_chars=440):
    descripcion = descripcion or ""

    if len(descripcion) <= small_max_chars:
        return "small"

    return "large"


def resolver_plantilla_producto(item):
    """
    Prioridad:
    1. Plantilla fija en el JSON.
    2. Regla manual por artículo.
    3. Regla por tipo_objeto.
    4. Default vertical.
    """

    # 1. Plantilla directa en JSON
    plantilla = item.get("plantilla", {})

    layout_json = plantilla.get("layout")
    size_json = plantilla.get("size")

    if layout_json and size_json:
        return layout_json, size_json, "json"

    # 2. Regla especial por artículo
    id_catalogo = item.get("id_catalogo") or crear_id_catalogo(item.get("id"))

    if id_catalogo in REGLAS_POR_ARTICULO:
        regla = REGLAS_POR_ARTICULO[id_catalogo]
        return regla["layout"], regla["size"], "articulo"

    # 3. Regla por tipo de objeto
    tipo_objeto = item.get("tipo_objeto", "otros")
    regla = REGLAS_POR_TIPO.get(tipo_objeto, DEFAULT_RULE)

    layout = regla.get("layout", DEFAULT_RULE["layout"])

    if "size" in regla:
        size = regla["size"]
    else:
        size = calcular_size_por_descripcion(
            item.get("descripcion", ""),
            regla.get("small_max_chars", DEFAULT_RULE["small_max_chars"])
        )

    return layout, size, f"tipo_objeto:{tipo_objeto}"