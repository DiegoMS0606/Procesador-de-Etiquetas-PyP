import re
from PIL import Image, ImageDraw, ImageFont

from src.core.paths import get_config
from src.core.productos import crear_id_catalogo


DPI = 300

TAMANOS_PAPEL = {
    # Carta horizontal: 11 x 8.5 pulgadas a 300 dpi
    "carta": (3300, 2550),

    # A4 horizontal: 11.69 x 8.27 pulgadas a 300 dpi
    "a4": (3508, 2480),
}

ETIQUETAS_POR_HOJA = 2


def cm_a_px(cm, dpi=DPI):
    return int(round((cm / 2.54) * dpi))


# Tamaño final de etiqueta: 15 x 10 cm
ANCHO_ETIQUETA = cm_a_px(10)
ALTO_ETIQUETA = cm_a_px(16)

# Margen interior entre contenido y contorno
MARGEN_INTERNO = 20
COLOR_ID_CORTE = (0, 0, 0, 255)
TAMANO_TEXTO_ID_CORTE = 32
MARGEN_ID_CORTE = 14
# Estilo del contorno de corte
COLOR_CONTORNO = (0, 0, 0, 255)
GROSOR_CONTORNO = 3

def cargar_fuente_id_corte():
    """
    Carga una fuente para el ID de corte.
    Usa Arial en Windows si está disponible.
    Si falla, usa fuente default.
    """

    posibles = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]

    for ruta in posibles:
        try:
            return ImageFont.truetype(ruta, TAMANO_TEXTO_ID_CORTE)
        except Exception:
            continue

    return ImageFont.load_default()


def dividir_ids(texto):
    partes = re.split(r"[\s,;]+", texto.strip())
    return [p for p in partes if p]


def buscar_etiquetas_generadas(config, id_usuario):
    id_catalogo = crear_id_catalogo(id_usuario)

    front = config.output / f"{id_catalogo}_front.png"
    back = config.output / f"{id_catalogo}_back.png"

    if not front.exists() or not back.exists():
        return None

    return {
        "id_catalogo": id_catalogo,
        "front": front,
        "back": back,
    }

def listar_categorias_disponibles(config):
    carpeta_categorias = config.data_categorias

    if not carpeta_categorias.exists():
        return []

    return sorted([
        p.name
        for p in carpeta_categorias.iterdir()
        if p.is_dir()
    ])


def obtener_rutas_categoria(config, nombre_categoria):
    base = config.data_categorias / nombre_categoria

    return {
        "categoria": nombre_categoria,
        "base": base,
        "etiquetas": base / "etiquetas",
        "impresion": base / "impresion" / config.paper,
    }


def buscar_etiquetas_generadas_en_categoria(config, nombre_categoria, id_usuario):
    id_catalogo = crear_id_catalogo(id_usuario)
    rutas = obtener_rutas_categoria(config, nombre_categoria)

    front = rutas["etiquetas"] / f"{id_catalogo}_front.png"
    back = rutas["etiquetas"] / f"{id_catalogo}_back.png"

    if not front.exists() or not back.exists():
        return None

    return {
        "categoria": nombre_categoria,
        "id_catalogo": id_catalogo,
        "front": front,
        "back": back,
    }


def seleccionar_categoria(config, mensaje="Selecciona categoría"):
    categorias = listar_categorias_disponibles(config)

    if not categorias:
        print("No encontré categorías disponibles.")
        return None

    print("\n--- CATEGORÍAS DISPONIBLES ---")

    for i, categoria in enumerate(categorias, start=1):
        actual = " ← activa" if categoria == config.categoria else ""
        print(f"{i}. {categoria}{actual}")

    opcion = input(f"\n{mensaje}: ").strip()

    try:
        indice = int(opcion)
    except ValueError:
        print("Opción inválida.")
        return None

    if indice < 1 or indice > len(categorias):
        print("Opción fuera de rango.")
        return None

    return categorias[indice - 1]


def capturar_etiquetas_varias_categorias(config):
    """
    Permite capturar IDs por categoría.

    Ejemplo:
    Categoría 1: 1,2,3
    Categoría 2: 8,9
    """

    etiquetas = []

    print("\n--- IMPRESIÓN DESDE VARIAS CATEGORÍAS ---")
    print("Selecciona una categoría y después escribe sus IDs.")
    print("Deja los IDs vacíos para terminar.")

    while True:
        categoria = seleccionar_categoria(
            config,
            mensaje="Categoría para agregar"
        )

        if not categoria:
            return etiquetas

        print(f"\nCategoría seleccionada: {categoria}")
        texto_ids = input("IDs para esta categoría, o ENTER para terminar: ").strip()

        if not texto_ids:
            break

        ids = dividir_ids(texto_ids)

        for id_usuario in ids:
            encontrada = buscar_etiquetas_generadas_en_categoria(
                config,
                categoria,
                id_usuario,
            )

            if not encontrada:
                print(f"❌ No encontré {crear_id_catalogo(id_usuario)} en {categoria}")
                continue

            etiquetas.append(encontrada)

        continuar = input("\n¿Agregar otra categoría? [s/N]: ").strip().lower()

        if continuar != "s":
            break

    return etiquetas


def capturar_etiquetas_todas_categorias(config):
    """
    Busca IDs específicos en todas las categorías.
    Solo agrega coincidencias encontradas.
    """

    categorias = listar_categorias_disponibles(config)

    print("\n--- IMPRESIÓN DESDE TODAS LAS CATEGORÍAS ---")
    texto_ids = input("IDs a buscar en todas las categorías: ").strip()
    ids = dividir_ids(texto_ids)

    etiquetas = []

    for categoria in categorias:
        for id_usuario in ids:
            encontrada = buscar_etiquetas_generadas_en_categoria(
                config,
                categoria,
                id_usuario,
            )

            if encontrada:
                etiquetas.append(encontrada)

    return etiquetas

def crear_slots_2up_horizontal(tamano_papel):
    page_w, page_h = tamano_papel
    mitad = page_w // 2

    # Centrar etiqueta en cada mitad de la hoja
    y1 = (page_h - ALTO_ETIQUETA) // 2
    y2 = y1 + ALTO_ETIQUETA

    x1_left = (mitad - ANCHO_ETIQUETA) // 2
    x2_left = x1_left + ANCHO_ETIQUETA

    x1_right = mitad + (mitad - ANCHO_ETIQUETA) // 2
    x2_right = x1_right + ANCHO_ETIQUETA

    return [
        (x1_left, y1, x2_left, y2),
        (x1_right, y1, x2_right, y2),
    ]


def ajustar_imagen_a_slot(ruta_imagen, slot_w, slot_h):
    img = Image.open(ruta_imagen).convert("RGBA")

    max_w = slot_w - (MARGEN_INTERNO * 2)
    max_h = slot_h - (MARGEN_INTERNO * 2)

    w, h = img.size
    scale = min(max_w / w, max_h / h)

    nuevo_w = int(w * scale)
    nuevo_h = int(h * scale)

    return img.resize((nuevo_w, nuevo_h), Image.LANCZOS)


def pegar_en_slot(hoja, ruta_imagen, slot):
    x1, y1, x2, y2 = slot

    slot_w = x2 - x1
    slot_h = y2 - y1

    etiqueta = ajustar_imagen_a_slot(ruta_imagen, slot_w, slot_h)

    pos_x = x1 + (slot_w - etiqueta.width) // 2
    pos_y = y1 + (slot_h - etiqueta.height) // 2

    hoja.alpha_composite(etiqueta, (pos_x, pos_y))


def dibujar_contornos(hoja, slots):
    draw = ImageDraw.Draw(hoja)

    for x1, y1, x2, y2 in slots:
        draw.rectangle(
            (x1, y1, x2, y2),
            outline=COLOR_CONTORNO,
            width=GROSOR_CONTORNO,
        )

def obtener_codigo_categoria(nombre_categoria):
    """
    Convierte:
    1-muebles_europeos_importados -> 1
    3-ebaniesteria-de-elite -> 3
    """

    if not nombre_categoria:
        return "X"

    texto = str(nombre_categoria).strip()

    if "-" in texto:
        return texto.split("-")[0]

    return texto


def crear_label_etiqueta(etiqueta):
    categoria = etiqueta.get("categoria", "")
    id_catalogo = etiqueta.get("id_catalogo", "")

    codigo_categoria = obtener_codigo_categoria(categoria)

    return f"{codigo_categoria}-{id_catalogo}"


def dibujar_ids_corte(hoja, slots, etiquetas):
    """
    Dibuja el identificador arriba del marco de corte.
    Ejemplo:
    1-ACT-0048
    """

    draw = ImageDraw.Draw(hoja)
    fuente = cargar_fuente_id_corte()

    for slot, etiqueta in zip(slots, etiquetas):
        if etiqueta is None:
            continue

        x1, y1, x2, y2 = slot
        label = crear_label_etiqueta(etiqueta)

        pos_x = x1 + MARGEN_ID_CORTE
        pos_y = max(5, y1 - TAMANO_TEXTO_ID_CORTE - MARGEN_ID_CORTE)

        draw.text(
            (pos_x, pos_y),
            label,
            fill=COLOR_ID_CORTE,
            font=fuente,
        )

def dibujar_guias(hoja, draw_guides=False):
    if not draw_guides:
        return

    draw = ImageDraw.Draw(hoja)
    page_w, page_h = hoja.size
    mitad = page_w // 2

    # Línea central entre las 2 etiquetas
    draw.line(
        (mitad, 0, mitad, page_h),
        fill=(180, 180, 180, 255),
        width=2,
    )

    # Borde exterior de la hoja
    draw.rectangle(
        (5, 5, page_w - 5, page_h - 5),
        outline=(200, 200, 200, 255),
        width=2,
    )


def crear_hoja(
    rutas_imagenes,
    tamano_papel,
    draw_guides=False,
    draw_cut_outline=True,
    etiquetas_info=None,
    draw_ids_corte=False,
):
    hoja = Image.new("RGBA", tamano_papel, (255, 255, 255, 255))
    slots = crear_slots_2up_horizontal(tamano_papel)

    for ruta_imagen, slot in zip(rutas_imagenes, slots):
        if ruta_imagen is None:
            continue

        pegar_en_slot(hoja, ruta_imagen, slot)

    # Contorno real de corte
    if draw_cut_outline:
        dibujar_contornos(hoja, slots)

    # ID arriba del marco de corte
    if draw_ids_corte and etiquetas_info:
        dibujar_ids_corte(hoja, slots, etiquetas_info)

    # Guías extra opcionales desde config.json
    dibujar_guias(hoja, draw_guides=draw_guides)

    return hoja


def crear_nombre_pdf_impresion(etiquetas, prefijo="tags"):
    ids = [e["id_catalogo"] for e in etiquetas]

    if len(ids) <= 8:
        ids_txt = "_".join(ids)
    else:
        ids_txt = f"{ids[0]}_a_{ids[-1]}_{len(ids)}ids"

    return f"{prefijo}_{ids_txt}.pdf"


def guardar_pdf_multipagina(hojas, ruta_pdf):
    if not hojas:
        raise ValueError("No hay hojas para guardar en PDF.")

    paginas_rgb = [hoja.convert("RGB") for hoja in hojas]

    primera = paginas_rgb[0]
    restantes = paginas_rgb[1:]

    primera.save(
        ruta_pdf,
        "PDF",
        resolution=DPI,
        save_all=True,
        append_images=restantes,
    )

    return ruta_pdf


def agrupar(lista, cantidad):
    for i in range(0, len(lista), cantidad):
        yield lista[i:i + cantidad]

def crear_paginas_frente_reverso(grupo):
    """
    Crea la distribución correcta para impresión dúplex horizontal
    con volteo por borde corto.

    Caso par:
        front: [1, 2]
        back:  [2, 1]

    Caso impar:
        front: [1, vacío]
        back:  [vacío, 1]
    """

    if len(grupo) == 1:
        etiqueta = grupo[0]

        fronts = [
            etiqueta["front"],
            None,
        ]

        backs = [
            None,
            etiqueta["back"],
        ]

        etiquetas_front = [
            etiqueta,
            None,
        ]

        etiquetas_back = [
            None,
            etiqueta,
        ]

        return fronts, backs, etiquetas_front, etiquetas_back

    fronts = [
        grupo[0]["front"],
        grupo[1]["front"],
    ]

    backs = [
        grupo[1]["back"],
        grupo[0]["back"],
    ]

    etiquetas_front = [
        grupo[0],
        grupo[1],
    ]

    etiquetas_back = [
        grupo[1],
        grupo[0],
    ]

    return fronts, backs, etiquetas_front, etiquetas_back

def preparar_pdf_desde_etiquetas(config, etiquetas, salida, prefijo="tags"):
    paper = config.paper or "carta"

    if paper not in TAMANOS_PAPEL:
        print(f"❌ Papel no soportado: {paper}")
        print(f"Opciones disponibles: {', '.join(TAMANOS_PAPEL.keys())}")
        return

    tamano_papel = TAMANOS_PAPEL[paper]

    salida.mkdir(parents=True, exist_ok=True)

    if not etiquetas:
        print("No hay etiquetas válidas para preparar.")
        return

    paginas_pdf = []
    resumen_hojas = []

    for num_hoja, grupo in enumerate(
        agrupar(etiquetas, ETIQUETAS_POR_HOJA),
        start=1,
    ):
        fronts, backs, etiquetas_front, etiquetas_back = crear_paginas_frente_reverso(grupo)

        hoja_front = crear_hoja(
            fronts,
            tamano_papel,
            draw_guides=config.draw_guides,
            draw_cut_outline=True,
            etiquetas_info=etiquetas_front,
            draw_ids_corte=True,
        )

        hoja_back = crear_hoja(
            backs,
            tamano_papel,
            draw_guides=False,
            draw_cut_outline=False,
            etiquetas_info=etiquetas_back,
            draw_ids_corte=False,
        )

        paginas_pdf.append(hoja_front)
        paginas_pdf.append(hoja_back)

        ids_hoja = ", ".join(e["id_catalogo"] for e in grupo)
        resumen_hojas.append((num_hoja, ids_hoja))

    nombre_pdf = crear_nombre_pdf_impresion(etiquetas, prefijo=prefijo)
    ruta_pdf = salida / nombre_pdf

    guardar_pdf_multipagina(paginas_pdf, ruta_pdf)

    print("\n✔ PDF de impresión creado")
    print(f"Archivo: {ruta_pdf}")

    print("\nOrden de páginas:")
    for num_hoja, ids_hoja in resumen_hojas:
        pagina_front = (num_hoja - 1) * 2 + 1
        pagina_back = pagina_front + 1

        print(f"   Hoja {num_hoja:03d}: {ids_hoja}")
        print(f"      Página {pagina_front}: frente")
        print(f"      Página {pagina_back}: reverso")

    print("\nConfiguración recomendada de impresión:")
    print("   Doble cara: activado")
    print("   Orientación: horizontal")
    print("   Voltear por borde corto")
    print("   Escala: 100% / tamaño real")

    print("\nTamaño de etiqueta:")
    print("   10 x 16 cm")
    print("   Con contorno de corte solo al frente")

def preparar_hojas_impresion_categoria_activa(config, ids):
    etiquetas = []

    for id_usuario in ids:
        encontrada = buscar_etiquetas_generadas(config, id_usuario)

        if not encontrada:
            print(f"❌ No encontré front/back generado para: {id_usuario}")
            continue

        encontrada["categoria"] = config.categoria
        etiquetas.append(encontrada)

    salida = config.base / "impresion" / config.paper

    preparar_pdf_desde_etiquetas(
        config=config,
        etiquetas=etiquetas,
        salida=salida,
        prefijo="tags",
    )

def main():
    config = get_config()

    while True:
        print("\n=== Preparar hojas para imprimir etiquetas ===")
        print(f"Modo: {config.modo}")
        print(f"Categoría activa: {config.categoria}")
        print(f"Base: {config.base}")
        print(f"Papel: {config.paper}")
        print(f"Guías extra: {config.draw_guides}")
        print("Formato actual: 2 etiquetas por hoja")
        print("Tamaño etiqueta: 10 x 16 cm")

        print("\n--- PREPARAR IMPRESIÓN ---")
        print("1. Imprimir desde categoría activa")
        print("2. Imprimir desde varias categorías")
        print("3. Imprimir desde todas las categorías")
        print("0. Volver al menú anterior")

        opcion = input("\nSelecciona opción: ").strip()

        if opcion == "1":
            print("\nEscribe los IDs separados por espacio o coma.")
            print("Ejemplo: 1 4 6")
            print("Ejemplo: ACT-0001, ACT-0004, ACT-0006")

            texto_ids = input("\nIDs: ").strip()
            ids = dividir_ids(texto_ids)

            if not ids:
                print("No escribiste IDs.")
                continue

            preparar_hojas_impresion_categoria_activa(config, ids)
            input("\nPresiona ENTER para continuar...")

        elif opcion == "2":
            etiquetas = capturar_etiquetas_varias_categorias(config)

            if not etiquetas:
                print("No agregaste etiquetas válidas.")
                input("\nPresiona ENTER para continuar...")
                continue

            salida = config.root / "impresion" / "multi_categoria" / config.paper

            preparar_pdf_desde_etiquetas(
                config=config,
                etiquetas=etiquetas,
                salida=salida,
                prefijo="tags_multi",
            )

            input("\nPresiona ENTER para continuar...")

        elif opcion == "3":
            etiquetas = capturar_etiquetas_todas_categorias(config)

            if not etiquetas:
                print("No encontré etiquetas válidas.")
                input("\nPresiona ENTER para continuar...")
                continue

            salida = config.root / "impresion" / "todas_categorias" / config.paper

            preparar_pdf_desde_etiquetas(
                config=config,
                etiquetas=etiquetas,
                salida=salida,
                prefijo="tags_all",
            )

            input("\nPresiona ENTER para continuar...")

        elif opcion == "0":
            return

        else:
            print("Opción inválida.")
            input("\nPresiona ENTER para continuar...")

if __name__ == "__main__":
    main()
