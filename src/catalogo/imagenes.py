import re
from pathlib import Path


EXT_IMAGENES = {".png", ".jpg", ".jpeg", ".webp"}



def clave_imagen_numerica(path):
    """
    Ordena imágenes secundarias como 1, 2, 3, 10
    en vez de 1, 10, 2.
    """
    match = re.match(r"^(\d+)", path.stem)

    if match:
        return int(match.group(1)), path.name.lower()

    return 999999, path.name.lower()

def normalizar_ruta(path):
    if not path:
        return ""

    return str(Path(path).resolve()).replace("\\", "/")


def buscar_carpeta_imagenes_catalogo(config, id_catalogo):
    """
    Busca la carpeta oficial de imágenes del producto.

    PROD:
    categorias/<categoria>/img/ACT-0002/
    """

    carpeta_producto = config.producto_img_dir(id_catalogo)

    if carpeta_producto.exists() and carpeta_producto.is_dir():
        return carpeta_producto

    return None


def buscar_principal(carpeta_producto):
    """
    Busca imagen principal del producto.
    """

    for nombre in ["principal", "main", "portada", "foto_principal"]:
        for ext in EXT_IMAGENES:
            ruta = carpeta_producto / f"{nombre}{ext}"

            if ruta.exists():
                return ruta

    return None


def listar_secundarias(carpeta_producto, principal):
    """
    Devuelve todas las imágenes menos principal.
    """

    secundarias = []

    principal_resuelta = principal.resolve() if principal else None

    for archivo in carpeta_producto.iterdir():
        if not archivo.is_file():
            continue

        if archivo.suffix.lower() not in EXT_IMAGENES:
            continue

        if principal_resuelta and archivo.resolve() == principal_resuelta:
            continue

        secundarias.append(archivo)

    secundarias.sort(key=clave_imagen_numerica)

    return secundarias


def seleccionar_imagenes_catalogo_general(carpeta_producto, id_catalogo):
    """
    Devuelve todas las imágenes posibles.
    Cada distribución usará solo las capas que necesite.
    """

    principal = buscar_principal(carpeta_producto)

    if not principal:
        raise FileNotFoundError(
            f"No encontré principal.png en: {carpeta_producto}"
        )

    secundarias = listar_secundarias(carpeta_producto, principal)

    imagenes = {
        "IMG_PRINCIPAL": normalizar_ruta(principal),

        # Compatibilidad vieja
        "IMG_SECOND": "",
        "IMG_THIRD": "",

        # Estándar actual
        "IMG_2": "",
        "IMG_3": "",
        "IMG_4": "",
        "IMG_5": "",
        "IMG_6": "",
    }

    if len(secundarias) >= 1:
        imagenes["IMG_SECOND"] = normalizar_ruta(secundarias[0])
        imagenes["IMG_2"] = normalizar_ruta(secundarias[0])

    if len(secundarias) >= 2:
        imagenes["IMG_THIRD"] = normalizar_ruta(secundarias[1])
        imagenes["IMG_3"] = normalizar_ruta(secundarias[1])

    if len(secundarias) >= 3:
        imagenes["IMG_4"] = normalizar_ruta(secundarias[2])

    if len(secundarias) >= 4:
        imagenes["IMG_5"] = normalizar_ruta(secundarias[3])

    if len(secundarias) >= 5:
        imagenes["IMG_6"] = normalizar_ruta(secundarias[4])

    return imagenes