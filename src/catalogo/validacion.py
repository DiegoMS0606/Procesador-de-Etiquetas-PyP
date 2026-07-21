import json
from src.core.paths import get_config
from src.core.productos import resolver_json_productos
from src.catalogo.plantillas import cargar_distribuciones_catalogo

def cargar_productos(config):
    ruta_json = resolver_json_productos(config)

    if not ruta_json.exists():
        raise FileNotFoundError(f"No existe JSON de productos: {ruta_json}")

    with open(ruta_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("El JSON de productos debe contener una lista")

    return data


def validar_distribuciones(distribuciones):
    errores = []
    advertencias = []

    for nombre, dist in distribuciones.items():
        psd = dist.get("psd")
        paginas = dist.get("paginas")
        template_mesas = dist.get("template_mesas", [])
        capacidades = dist.get("capacidades", {})
        textos = dist.get("textos", {})
        areas = dist.get("areas", {})
        imagenes = dist.get("imagenes", {})
        auto = dist.get("auto", False)

        if not psd:
            errores.append(f"{nombre}: falta campo psd")
        elif not psd.exists():
            errores.append(f"{nombre}: no existe PSD: {psd}")

        if not isinstance(paginas, int) or paginas <= 0:
            errores.append(f"{nombre}: paginas debe ser número mayor a 0")
            
        if auto is True and paginas != 1:
            errores.append(
                f"{nombre}: tiene auto=true pero usa {paginas} páginas. "
                "Las distribuciones automáticas deben ser de una sola página."
            )

        if paginas > 1 and auto is True:
            errores.append(
                f"{nombre}: distribución de {paginas} páginas no debe usarse en automático. "
                "Cambia auto a false."
            )

        if "auto" not in dist:
            advertencias.append(
                f"{nombre}: no tiene campo auto definido. Usa auto=true para una página "
                "o auto=false para excepciones manuales."
            )

        if len(template_mesas) != paginas:
            errores.append(
                f"{nombre}: template_mesas tiene {len(template_mesas)} elementos, "
                f"pero paginas={paginas}"
            )

        if not capacidades:
            advertencias.append(f"{nombre}: no tiene capacidades definidas")

        for i in range(1, paginas + 1):
            pagina_key = f"pagina_{i}"

            if pagina_key not in textos:
                advertencias.append(f"{nombre}: falta textos.{pagina_key}")

            if pagina_key not in areas:
                advertencias.append(f"{nombre}: falta areas.{pagina_key}")

            if pagina_key not in imagenes:
                advertencias.append(f"{nombre}: falta imagenes.{pagina_key}")
                
        automaticas = [
            nombre
            for nombre, dist in distribuciones.items()
            if dist.get("auto", False) is True
        ]

        if not automaticas:
            errores.append(
                "No hay distribuciones automáticas. "
                "Debe existir al menos una distribución de una página con auto=true."
            )


    return errores, advertencias


def validar_productos(productos, distribuciones):
    errores = []
    advertencias = []

    distribuciones_validas = set(distribuciones.keys())

    for producto in productos:
        id_catalogo = producto.get("id_catalogo") or producto.get("id")
        template = str(producto.get("catalogo_template", "")).strip()

        if template and template not in distribuciones_validas:
            errores.append(
                f"{id_catalogo}: catalogo_template inválido: {template}"
            )

        if not producto.get("descripcion"):
            advertencias.append(f"{id_catalogo}: producto sin descripción")

        if not producto.get("nombre"):
            advertencias.append(f"{id_catalogo}: producto sin nombre")

        if not producto.get("precio"):
            advertencias.append(f"{id_catalogo}: producto sin precio")

        if not producto.get("medidas"):
            advertencias.append(f"{id_catalogo}: producto sin medidas")

    return errores, advertencias

def validar_catalogo(silencioso=False):
    config = get_config()

    distribuciones = cargar_distribuciones_catalogo()
    productos = cargar_productos(config)

    errores_dist, advertencias_dist = validar_distribuciones(distribuciones)
    errores_prod, advertencias_prod = validar_productos(productos, distribuciones)

    errores = errores_dist + errores_prod
    advertencias = advertencias_dist + advertencias_prod

    if not silencioso:
        print("\n--- VALIDACIÓN CATÁLOGO TECI ---")
        print(f"Modo: {config.modo}")
        print(f"Categoría: {config.categoria}")
        print(f"JSON: {resolver_json_productos(config)}")

        print("\n--- RESUMEN ---")
        print(f"Distribuciones: {len(distribuciones)}")
        print(f"Productos: {len(productos)}")
        print(f"Errores: {len(errores)}")
        print(f"Advertencias: {len(advertencias)}")

        if errores:
            print("\n--- ERRORES ---")
            for error in errores:
                print(f"❌ {error}")

        if advertencias:
            print("\n--- ADVERTENCIAS ---")
            for advertencia in advertencias:
                print(f"⚠ {advertencia}")

        if not errores:
            print("\n✔ Validación terminada sin errores críticos.")

    return len(errores) == 0

def main():
    validar_catalogo(silencioso=False)


if __name__ == "__main__":
    main()
