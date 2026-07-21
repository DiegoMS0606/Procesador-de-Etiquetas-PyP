import json
import tempfile
import re
from pathlib import Path

import win32com.client
from PIL import Image, ImageDraw, ImageFont

from src.core.paths import get_config
from src.catalogo.plantillas import cargar_distribuciones_catalogo

ROOT = Path(__file__).resolve().parents[2]
JSX_EXPORT = ROOT / "src" / "catalogo" / "exportar_catalogo.jsx"

PORTADAS_CATALOGO = ROOT / "templates" / "catalogo" / "portadas"

PORTADAS_DISPONIBLES = {
    "1": PORTADAS_CATALOGO / "portada_1.psd",
    "2": PORTADAS_CATALOGO / "portada_2.psd",
    "3": PORTADAS_CATALOGO / "portada_3.psd",
}

DISTRIBUCIONES_CATALOGO = cargar_distribuciones_catalogo()


def normalizar_ruta(path):
    if not path:
        return ""

    return str(Path(path).resolve()).replace("\\", "/")


def obtener_numero_categoria(config):
    categoria = str(config.categoria or "").strip()

    try:
        return int(categoria.split("-")[0])
    except Exception:
        return 0


def crear_pdf_catalogo_desde_paginas(carpeta_paginas, ruta_pdf):
    """
    Une portada + páginas exportadas en un PDF final.
    Todas las páginas se convierten a RGB.
    """

    carpeta_paginas = Path(carpeta_paginas)
    ruta_pdf = Path(ruta_pdf)

    imagenes = sorted(carpeta_paginas.glob("*.png"))

    if not imagenes:
        raise FileNotFoundError(f"No hay páginas PNG en: {carpeta_paginas}")

    paginas = []

    for img_path in imagenes:
        img = Image.open(img_path).convert("RGB")
        paginas.append(img)

    ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    primera = paginas[0]
    resto = paginas[1:]

    primera.save(
        ruta_pdf,
        save_all=True,
        append_images=resto,
        resolution=300.0
    )

    print(f"\nPDF generado: {ruta_pdf}")


def exportar_portada_psd(ruta_portada_psd, carpeta_salida):
    if not ruta_portada_psd.exists():
        raise FileNotFoundError(f"No existe portada PSD: {ruta_portada_psd}")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        json.dump({
            "template_path": normalizar_ruta(ruta_portada_psd),
            "output_dir": normalizar_ruta(carpeta_salida),
            "output_file": "000_PORTADA.png",
            "export_mode": "portada_unica",
        }, tmp, ensure_ascii=False, indent=2)

        ruta_config = tmp.name

    ps = win32com.client.Dispatch("Photoshop.Application")
    ps.Visible = True

    resultado = ps.DoJavaScriptFile(
        str(JSX_EXPORT),
        [normalizar_ruta(ruta_config)]
    )

    print("\nResultado exportación portada:")
    print(resultado)


def exportar_distribucion_psd(nombre_distribucion, carpeta_salida):
    data = DISTRIBUCIONES_CATALOGO[nombre_distribucion]
    ruta_psd = data["psd"]

    if not ruta_psd.exists():
        raise FileNotFoundError(f"No existe PSD de distribución: {ruta_psd}")

    config = get_config()

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        json.dump({
            "template_path": normalizar_ruta(ruta_psd),
            "output_dir": normalizar_ruta(carpeta_salida),
            "template_mesa": data["template_mesas"][0],
            "tipo_mesa": f"CAT{obtener_numero_categoria(config):02d}",
            "export_mode": "productos",
        }, tmp, ensure_ascii=False, indent=2)

        ruta_config = tmp.name

    ps = win32com.client.Dispatch("Photoshop.Application")
    ps.Visible = True

    resultado = ps.DoJavaScriptFile(
        str(JSX_EXPORT),
        [normalizar_ruta(ruta_config)]
    )

    print(f"\nResultado exportación {nombre_distribucion}:")
    print(resultado)


PATRON_PAGINA_CATALOGO = re.compile(
    r"CAT(?P<cat>\d+)_ACT-(?P<id>\d+)_D(?P<dist>\d+)_P(?P<pag>\d+)",
    re.IGNORECASE,
)


def extraer_info_pagina_catalogo(ruta):
    """
    Extrae datos desde nombres como:
    CAT01_ACT-0006_D06_P01.png
    001_CAT01_ACT-0006_D06_P01.png
    """

    nombre = Path(ruta).stem
    match = PATRON_PAGINA_CATALOGO.search(nombre)

    if not match:
        return {
            "cat": 999,
            "id": 999999,
            "dist": 999,
            "pag": 999,
            "key_producto": ("SIN_FORMATO", nombre),
        }

    cat = int(match.group("cat"))
    id_producto = int(match.group("id"))
    dist = int(match.group("dist"))
    pag = int(match.group("pag"))

    return {
        "cat": cat,
        "id": id_producto,
        "dist": dist,
        "pag": pag,
        "key_producto": (cat, id_producto),
    }


def ordenar_paginas_catalogo(rutas_png):
    """
    Ordena páginas exportadas.

    Reglas:
    - Agrupa por producto.
    - Las páginas de un mismo producto siempre quedan juntas.
    - Ordena por categoría e ID.
    - Patrón: doble + sencilla + sencilla.
    """

    productos = {}

    for ruta in rutas_png:
        info = extraer_info_pagina_catalogo(ruta)
        key = info["key_producto"]

        if key not in productos:
            productos[key] = []

        productos[key].append((ruta, info))

    grupos = []

    for key, paginas in productos.items():
        paginas_ordenadas = sorted(
            paginas,
            key=lambda item: item[1]["pag"],
        )

        primera_info = paginas_ordenadas[0][1]

        grupos.append({
            "key": key,
            "cat": primera_info["cat"],
            "id": primera_info["id"],
            "paginas": [item[0] for item in paginas_ordenadas],
            "total_paginas": len(paginas_ordenadas),
        })

    grupos.sort(key=lambda g: (g["cat"], g["id"]))

    if not grupos:
        return []

    dobles = [g for g in grupos if g["total_paginas"] == 2]
    sencillos = [g for g in grupos if g["total_paginas"] == 1]
    otros = [g for g in grupos if g["total_paginas"] not in [1, 2]]

    ordenadas = []

    idx_doble = 0
    idx_sencillo = 0

    while idx_doble < len(dobles) or idx_sencillo < len(sencillos):
        if idx_doble < len(dobles):
            ordenadas.extend(dobles[idx_doble]["paginas"])
            idx_doble += 1

        for _ in range(2):
            if idx_sencillo < len(sencillos):
                ordenadas.extend(sencillos[idx_sencillo]["paginas"])
                idx_sencillo += 1

    for grupo in otros:
        ordenadas.extend(grupo["paginas"])

    return ordenadas


def agregar_numero_pagina(img, numero_pagina):
    """
    Agrega número visual de página en la esquina inferior derecha.
    """

    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    texto = str(numero_pagina)

    try:
        fuente = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        fuente = ImageFont.load_default()

    margen_x = 60
    margen_y = 45

    bbox = draw.textbbox((0, 0), texto, font=fuente)
    ancho_texto = bbox[2] - bbox[0]
    alto_texto = bbox[3] - bbox[1]

    x = img.width - ancho_texto - margen_x
    y = img.height - alto_texto - margen_y

    padding_x = 18
    padding_y = 10

    rect = [
        x - padding_x,
        y - padding_y,
        x + ancho_texto + padding_x,
        y + alto_texto + padding_y,
    ]

    draw.rounded_rectangle(rect, radius=10, fill=(255, 255, 255))
    draw.text((x, y), texto, font=fuente, fill=(0, 0, 0))

    return img


def exportar_catalogo_pdf():
    config = get_config()

    carpeta_paginas = config.catalogo_paginas
    ruta_pdf = config.catalogo_final_pdf

    carpeta_paginas.mkdir(parents=True, exist_ok=True)

    # Limpiar páginas finales anteriores.
    for archivo in carpeta_paginas.glob("*.png"):
        archivo.unlink()

    tmp_dir = carpeta_paginas / "_tmp"

    if tmp_dir.exists():
        for p in tmp_dir.rglob("*.png"):
            p.unlink()

    tmp_dir.mkdir(parents=True, exist_ok=True)

    # =========================
    # 1. Elegir portada
    # =========================
    print("\n--- PORTADAS DISPONIBLES ---")
    print("0 - Sin portada")
    print("1 - portada_1")
    print("2 - portada_2")
    print("3 - portada_3")

    opcion_portada = input("Selecciona portada: ").strip()

    archivos_ordenados = []
    archivos_productos = []

    if opcion_portada in PORTADAS_DISPONIBLES:
        carpeta_portada = tmp_dir / "portada"
        carpeta_portada.mkdir(parents=True, exist_ok=True)

        exportar_portada_psd(
            PORTADAS_DISPONIBLES[opcion_portada],
            carpeta_portada,
        )

        portada_png = carpeta_portada / "000_PORTADA.png"

        if portada_png.exists():
            archivos_ordenados.append(portada_png)

    # =========================
    # 2. Exportar distribuciones
    # =========================
    for nombre_distribucion in DISTRIBUCIONES_CATALOGO.keys():
        carpeta_dist = tmp_dir / nombre_distribucion
        carpeta_dist.mkdir(parents=True, exist_ok=True)

        exportar_distribucion_psd(nombre_distribucion, carpeta_dist)

        pngs = list(carpeta_dist.glob("*.png"))
        archivos_productos.extend(pngs)

    archivos_productos_ordenados = ordenar_paginas_catalogo(archivos_productos)
    archivos_ordenados.extend(archivos_productos_ordenados)

    if not archivos_ordenados:
        print("❌ No se exportó ninguna página.")
        return

    # =========================
    # 3. Renombrar en carpeta final
    # =========================
    for i, ruta_src in enumerate(archivos_ordenados):
        nombre_final = f"{i:03d}_{ruta_src.stem}.png"
        destino = carpeta_paginas / nombre_final

        with Image.open(ruta_src) as img:
            img_final = agregar_numero_pagina(img, i)
            img_final.save(destino)

    # =========================
    # 4. Crear PDF
    # =========================
    crear_pdf_catalogo_desde_paginas(carpeta_paginas, ruta_pdf)
