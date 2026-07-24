import json
import re
import sys
from pathlib import Path
import spacy
import argparse
from spacy.tokens import Doc

from src.core.paths import get_config
from src.texto.clasificador import clasificar_producto
from src.core.productos import crear_id_catalogo, normalizar_numero_id

# --------------------------------------------------
# CONFIGURACIÓN Y CARGA DE MODELO
# --------------------------------------------------
try:
    # Cargamos el modelo desactivando componentes innecesarios para ganar velocidad
    nlp = spacy.load("es_core_news_lg", disable=["lemmatizer", "attribute_ruler"])
except OSError:
    print("\n❌ ERROR: No se encontró el modelo 'es_core_news_lg'.")
    print("Ejecuta: python -m spacy download es_core_news_lg\n")
    sys.exit(1)


def leer_argumentos():
    parser = argparse.ArgumentParser(
        description="Procesador de TXT a JSON para etiquetas TECI"
    )

    parser.add_argument(
        "--id",
        dest="id_unico",
        help="Actualiza solo un ID. Ejemplo: --id 44"
    )

    parser.add_argument(
        "--ids",
        dest="ids_multiples",
        help="Actualiza varios IDs separados por coma. Ejemplo: --ids 43,44,45"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Actualiza todos los productos. Es el comportamiento normal."
    )

    return parser.parse_args()

import re

SINONIMOS_ESTILO = [
    "con inspiración en",
    "con influencia de",
    "a manera de",
    "evocando",
    "siguiendo la línea de",
    "en diálogo con",
    "en la línea de",
    "con aire de",
]


def limpiar_referencia_estilo(referencia):
    referencia = str(referencia or "").strip()

    # Quitar comillas exteriores si ya venía con comillas
    referencia = referencia.strip("\"'“”‘’")

    # Limpiar espacios
    referencia = re.sub(r"\s+", " ", referencia).strip()

    # Mejorar iniciales tipo "a. Foullet" -> "A. Foullet"
    referencia = re.sub(
        r"\b([a-záéíóúñ])\.",
        lambda m: m.group(1).upper() + ".",
        referencia,
        flags=re.IGNORECASE,
    )

    return referencia


def reformular_estilo_en_nombre(nombre, indice=0):
    """
    Convierte:
    'Gabinete Francés Estilo Simón Philippe'
    en:
    'Gabinete Francés con inspiración en “Simón Philippe”'

    La selección del sinónimo es estable según el ID/índice.
    """

    nombre = str(nombre or "").strip()

    if not nombre:
        return ""

    patron = re.compile(r"\b[Ee]stilo\s+(.+)$")
    match = patron.search(nombre)

    if not match:
        return nombre

    referencia = limpiar_referencia_estilo(match.group(1))
    base = patron.sub("", nombre).strip()

    # Quitar separadores sobrantes antes del reemplazo
    base = base.rstrip(" ,-/")

    if not base or not referencia:
        return nombre

    sinonimo = SINONIMOS_ESTILO[indice % len(SINONIMOS_ESTILO)]

    return f"{base} {sinonimo} “{referencia}”"


def obtener_ids_objetivo(args):
    if args.id_unico:
        return {str(args.id_unico).strip()}

    if args.ids_multiples:
        return {
            x.strip()
            for x in args.ids_multiples.split(",")
            if x.strip()
        }

    return None

def filtrar_productos_por_ids(productos, ids_objetivo):
    if not ids_objetivo:
        return productos

    ids_objetivo = {str(x).strip() for x in ids_objetivo}

    filtrados = []

    for producto in productos:
        id_prod = str(producto.get("id", "")).strip()
        id_catalogo = str(producto.get("id_catalogo", "")).strip()

        if id_prod in ids_objetivo or id_catalogo in ids_objetivo:
            filtrados.append(producto)

    return filtrados

# --------------------------------------------------
# UTILIDADES DE ARCHIVO Y PARSEO
# --------------------------------------------------
def obtener_claves_producto(producto):
    """
    Genera claves equivalentes para comparar productos viejos y nuevos.

    Ejemplo:
    id = 6
    id_catalogo = ACT-0006

    Devuelve claves como:
    6
    ACT-0006
    """

    claves = set()

    for campo in ["id", "id_anterior", "id_catalogo"]:
        valor = producto.get(campo)

        if not valor:
            continue

        valor_txt = str(valor).strip()

        if valor_txt:
            claves.add(valor_txt.upper())

        numero = normalizar_numero_id(valor_txt)

        if numero:
            claves.add(numero)
            claves.add(crear_id_catalogo(numero).upper())

    return claves

def conservar_campos_producto_anterior(producto_nuevo, producto_anterior):
    campos_top_level_a_conservar = [
        "imagen_principal",
        "plantilla",
        "ruta_front",
        "ruta_back",
        "catalogo_generado",
        "fecha_catalogo",
        "impreso",
        "fecha_impresion",
        "observaciones",
        "catalogo_template",
    ]

    if "estado" in producto_anterior:
        producto_nuevo["estado"] = producto_anterior["estado"]

    for campo in campos_top_level_a_conservar:
        if campo in producto_anterior:
            producto_nuevo[campo] = producto_anterior[campo]

    return producto_nuevo


def guardar_json_parcial(productos_actualizados, archivo_txt, carpeta_salida):
    """
    Actualiza solo algunos productos dentro del JSON existente.

    Conserva los demás productos tal como estaban.
    También conserva campos de estado del producto anterior.
    """

    nombre_json = archivo_txt.stem.replace("-copy", "")
    ruta_json = carpeta_salida / f"{nombre_json}.json"

    if not ruta_json.exists():
        print(f"❌ No existe JSON base para actualización parcial: {ruta_json}")
        print("Primero genera el JSON completo una vez.")
        return

    with open(ruta_json, "r", encoding="utf-8") as f:
        productos_anteriores = json.load(f)

    anteriores_por_clave = {}

    for producto_anterior in productos_anteriores:
        claves = obtener_claves_producto(producto_anterior)

        for clave in claves:
            anteriores_por_clave[clave] = producto_anterior

    actualizados_por_clave = {}

    for producto_nuevo in productos_actualizados:
        if producto_nuevo.get("id"):
            producto_nuevo["id_catalogo"] = crear_id_catalogo(producto_nuevo.get("id"))

        claves = obtener_claves_producto(producto_nuevo)

        producto_anterior = None

        for clave in claves:
            if clave in anteriores_por_clave:
                producto_anterior = anteriores_por_clave[clave]
                break

        if producto_anterior:
            producto_nuevo = conservar_campos_producto_anterior(
                producto_nuevo,
                producto_anterior,
            )

        for clave in claves:
            actualizados_por_clave[clave] = producto_nuevo

    productos_finales = []
    reemplazados = 0

    for producto_anterior in productos_anteriores:
        claves = obtener_claves_producto(producto_anterior)

        reemplazo = None

        for clave in claves:
            if clave in actualizados_por_clave:
                reemplazo = actualizados_por_clave[clave]
                break

        if reemplazo:
            productos_finales.append(reemplazo)
            reemplazados += 1
        else:
            productos_finales.append(producto_anterior)

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(productos_finales, f, ensure_ascii=False, indent=4)

    print(f"✔ JSON actualizado parcialmente: {ruta_json.name}")
    print(f"Productos reemplazados: {reemplazados}")


def guardar_json(productos, archivo_txt, carpeta_salida):
    nombre_json = archivo_txt.stem.replace("-copy", "")
    ruta_json = carpeta_salida / f"{nombre_json}.json"

    # Campos de avance que NO deben perderse al regenerar desde TXT
    campos_top_level_a_conservar = [
        "id_catalogo",
        "imagen_principal",
        "plantilla",
        "ruta_front",
        "ruta_back",
        "catalogo_generado",
        "fecha_catalogo",
        "impreso",
        "fecha_impresion",
        "observaciones",
        "catalogo_template",
    ]

    productos_anteriores_por_clave = {}

    # Leer JSON anterior si existe
    if ruta_json.exists():
        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                data_anterior = json.load(f)

            for producto_anterior in data_anterior:
                claves = obtener_claves_producto(producto_anterior)

                for clave in claves:
                    productos_anteriores_por_clave[clave] = producto_anterior

        except Exception as e:
            print(f"⚠ No se pudo leer JSON anterior {ruta_json.name}: {e}")

    # Conservar estados del JSON anterior
    for producto in productos:
        id_prod = producto.get("id")

        # A partir de ahora todos los productos tendrán id_catalogo
        if id_prod:
            producto["id_catalogo"] = crear_id_catalogo(id_prod)

        claves = obtener_claves_producto(producto)

        anterior = None

        for clave in claves:
            if clave in productos_anteriores_por_clave:
                anterior = productos_anteriores_por_clave[clave]
                break

        if not anterior:
            continue

        # Conservar estado anidado:
        # "estado": {"etiqueta_generada": true, ...}
        if "estado" in anterior:
            producto["estado"] = anterior["estado"]

        # Conservar otros campos de avance
        for campo in campos_top_level_a_conservar:
            if campo in anterior:
                producto[campo] = anterior[campo]

    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=4)

    print(f"✔ Guardado: {ruta_json.name}")


def numero_archivo(path):
    m = re.match(r"(\d+)\.txt$", path.name)
    return int(m.group(1)) if m else None

patron_producto = re.compile(
    r"\*+\s*\n(\d+)\s*\n\*+\s*\n(.*?)(?=\n\*+\s*\n\d+\s*\n\*+|\Z)",
    re.DOTALL
)

# --------------------------------------------------
# CLASIFICADORES Y TÍTULOS
# --------------------------------------------------
STOP_WORDS = {"de", "del", "la", "las", "el", "los", "un", "una", "y", "en", "con", "por", "para", "al", "a", "du", "des", "et", "sur", "avec", "dans"}

ROMANO_RE = re.compile(r"^(?=[IVXLCDM]+$)M{0,4}(CM|CD|D?C{0,3})"
                       r"(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")

def es_romano(palabra):
    return bool(ROMANO_RE.match(palabra))

def smart_title_nombre(texto):
    palabras = texto.split()
    resultado = []
    for i, p in enumerate(palabras):
        limpia = re.sub(r"[^\wáéíóúñÁÉÍÓÚÑ]", "", p)
        low = limpia.lower()
        if es_romano(limpia):
            resultado.append(limpia)
        elif i > 0 and low in STOP_WORDS:
            resultado.append(p.lower())
        elif limpia.isupper() and len(limpia) > 1:
            resultado.append(limpia.capitalize())
        else:
            resultado.append(p)
    return " ".join(resultado)

def es_precio(l): return bool(re.search(r"(MXN|\$)", l))

def normalizar_precio(texto):
    """
    Normaliza precios a formato:
    $220,000.00

    Soporta:
    $55,000.00
    $220,000
    220000
    220.000
    55.000,00
    55,000.00
    """

    if not texto:
        return ""

    texto = str(texto).replace("\xa0", " ").strip()

    # Extraer número con posibles separadores
    m = re.search(r"(\d[\d.,]*)", texto)

    if not m:
        return ""

    numero = m.group(1).strip()

    # Quitar espacios internos
    numero = re.sub(r"\s+", "", numero)

    tiene_coma = "," in numero
    tiene_punto = "." in numero

    if tiene_coma and tiene_punto:
        # Si el último separador es punto: formato americano
        # 55,000.00 -> 55000.00
        if numero.rfind(".") > numero.rfind(","):
            numero = numero.replace(",", "")

        # Si el último separador es coma: formato europeo
        # 55.000,00 -> 55000.00
        else:
            numero = numero.replace(".", "").replace(",", ".")

    elif tiene_coma and not tiene_punto:
        partes = numero.split(",")

        # $220,000 -> miles
        # $1,250,000 -> miles
        if all(len(p) == 3 for p in partes[1:]):
            numero = "".join(partes)

        # 220,50 -> decimal
        elif len(partes[-1]) == 2:
            numero = numero.replace(",", ".")

        # Fallback: tratar como miles
        else:
            numero = "".join(partes)

    elif tiene_punto and not tiene_coma:
        partes = numero.split(".")

        # 220.000 -> miles
        # 1.250.000 -> miles
        if all(len(p) == 3 for p in partes[1:]):
            numero = "".join(partes)

        # 220.50 -> decimal
        elif len(partes[-1]) == 2:
            numero = numero

        # Fallback: tratar como miles
        else:
            numero = "".join(partes)

    try:
        valor = float(numero)
        return f"${valor:,.2f}"
    except ValueError:
        return ""

def balancear_comillas(texto):
    # Contar comillas dobles
    total = texto.count('"')

    # Si es impar, agregamos una comilla al final
    if total % 2 != 0:
        texto = texto.rstrip() + '"'

    return texto


PALABRAS_MEDIDA = (
    "longitud|logitud|largo|alto|altura|fondo|ancho|" "diámetro|diametro|base"
)

PREFIJOS_NO_COMPONENTE = {
    "medida",
    "medidas",
    "dimension",
    "dimensión",
    "dimensiones",
    "altura",
    "alto",
    "longitud",
    "logitud",
    "largo",
    "fondo",
    "ancho",
    "diametro",
    "diámetro",
}


def es_medida(l):
    l = str(l or "").lower()

    patrones = [
        r"\b\d+(?:[.,]\d+)?\s*cm\b",
        r"\b\d+(?:[.,]\d+)?\s*m\b",
        rf"\b({PALABRAS_MEDIDA})\b\s*:?\s*\d+",
        rf"\b\d+(?:[.,]\d+)?\s*(cm|m)?\s*(de\s+)?\b({PALABRAS_MEDIDA})\b",
        r"\b\d+(?:[.,]\d+)?\s*(cm|m)?\s*x\s*\d+(?:[.,]\d+)?\s*(cm|m)?\b",
        # Caso conjunto:
        # Mesa: 88cm longitud x 64cm fondo
        # Sillas: 95cm altura
        rf"^[a-záéíóúüñ\s]+:\s*.*(\d+(?:[.,]\d+)?\s*(cm|m)|\b({PALABRAS_MEDIDA})\b)",
    ]

    return any(re.search(p, l) for p in patrones)


def normalizar_cuerpo_medida(texto):
    texto = str(texto or "").strip()
    texto = re.sub(r"\s+", " ", texto)

    texto = re.sub(
        r"(\d+(?:[.,]\d+)?)\s*cm\b",
        r"\1 cm",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(
        r"(\d+(?:[.,]\d+)?)\s*m\b",
        r"\1 m",
        texto,
        flags=re.IGNORECASE,
    )

    texto = re.sub(r"\s+x\s+", " × ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s*:\s*", ": ", texto)

    return texto.strip()


def extraer_prefijo_componente_medida(texto):
    """
    Detecta casos como:
    Mesa: 88cm longitud x 64cm fondo
    Sillas: 95cm altura

    Devuelve:
    ("Mesa", "88cm longitud x 64cm fondo")
    """

    texto = str(texto or "").strip()

    match = re.match(
        r"^([a-záéíóúüñ][a-záéíóúüñ\s]{1,40})\s*:\s*(.+)$",
        texto,
        flags=re.IGNORECASE,
    )

    if not match:
        return "", texto

    prefijo = re.sub(r"\s+", " ", match.group(1)).strip()
    cuerpo = match.group(2).strip()

    prefijo_lower = prefijo.lower()

    if prefijo_lower in PREFIJOS_NO_COMPONENTE:
        return "", texto

    if not re.search(r"\d", cuerpo):
        return "", texto

    return prefijo.capitalize(), cuerpo


def formatear_medida(linea):
    texto = limpiar_ruido_ocr(linea)
    texto = normalizar_cuerpo_medida(texto)

    prefijo, cuerpo = extraer_prefijo_componente_medida(texto)

    if prefijo:
        cuerpo = normalizar_cuerpo_medida(cuerpo)
        return f"{prefijo}: {cuerpo}"

    equivalencias = {
        "longitud": "Longitud",
        "logitud": "Longitud",
        "largo": "Longitud",
        "alto": "Altura",
        "altura": "Altura",
        "fondo": "Fondo",
        "ancho": "Ancho",
        "diametro": "Diámetro",
        "diámetro": "Diámetro",
        "base": "Base",
    }

    # Caso especial: 55 cm × 55 cm base
    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(cm|m)?\s*×\s*" r"(\d+(?:[.,]\d+)?)\s*(cm|m)?\s*base",
        texto,
        flags=re.IGNORECASE,
    )

    if m:
        n1 = m.group(1)
        u1 = m.group(2) or "cm"
        n2 = m.group(3)
        u2 = m.group(4) or u1
        return f"Base: {n1} {u1} × {n2} {u2}"

    # Caso: LONGITUD: 125 cm / Altura 75 cm
    m = re.search(
        rf"\b({PALABRAS_MEDIDA})\b\s*:?\s*(\d+(?:[.,]\d+)?)\s*(cm|m)?",
        texto,
        flags=re.IGNORECASE,
    )

    if m:
        tipo = equivalencias.get(m.group(1).lower(), m.group(1).capitalize())
        numero = m.group(2)
        unidad = m.group(3) or "cm"
        return f"{tipo}: {numero} {unidad}"

    # Caso: 86 cm longitud / 40 cm fondo / 75 cm altura
    m = re.search(
        rf"(\d+(?:[.,]\d+)?)\s*(cm|m)?\s*(?:de\s+)?\b({PALABRAS_MEDIDA})\b",
        texto,
        flags=re.IGNORECASE,
    )

    if m:
        numero = m.group(1)
        unidad = m.group(2) or "cm"
        tipo = equivalencias.get(m.group(3).lower(), m.group(3).capitalize())
        return f"{tipo}: {numero} {unidad}"

    return texto


def extraer_medidas_de_linea(linea):
    """
    Extrae una o varias medidas desde una línea.

    Casos:
    Mesa: 88cm longitud x 64cm fondo
    -> ['Mesa: 88 cm longitud × 64 cm fondo']

    Sillas: 95cm altura
    -> ['Sillas: 95 cm altura']

    90cm alto y 60cm fondo
    -> ['Altura: 90 cm', 'Fondo: 60 cm']
    """

    texto = limpiar_ruido_ocr(linea)
    texto = normalizar_puntuacion(texto)

    prefijo, cuerpo = extraer_prefijo_componente_medida(texto)

    if prefijo:
        return [formatear_medida(texto)]

    patron = re.compile(
        rf"(\d+(?:[.,]\d+)?)\s*(cm|m)?\s*(?:de\s+)?({PALABRAS_MEDIDA})",
        flags=re.IGNORECASE,
    )

    coincidencias = list(patron.finditer(texto))

    if len(coincidencias) >= 2:
        return [formatear_medida(m.group(0)) for m in coincidencias]

    return [formatear_medida(texto)]


def es_nota(l):
    claves = ["importado", "tesoro", "colección", "precio por cada", "precio individual", "artículo europeo"]
    return any(k in l.lower() for k in claves)
def es_ruido(l):
    claves = ["apartado", "tarjeta", "pago", "disponible", "tienda", "crédito", "débito"]
    return any(k in l.lower() for k in claves)

# --------------------------------------------------
# NUEVA LÓGICA DE LIMPIEZA Y RESTAURACIÓN
# --------------------------------------------------

def limpiar_ruido_ocr(texto):
    texto = re.sub(r"[❗️❤️‼️]", "", texto)
    texto = texto.replace("\xa0", " ").replace("“", "\"").replace("”", "\"")

    # Preservar saltos de línea.
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    # Limpiar espacios y tabs, pero no eliminar saltos.
    texto = re.sub(r"[ \t]+", " ", texto)

    # Limpiar espacios alrededor de saltos.
    texto = re.sub(r" *\n *", "\n", texto)

    # Evitar más de 2 saltos seguidos.
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()

def proteger_patrones_puntuacion(texto):
    """
    Protege patrones que usan punto pero no deben alterarse:
    - decimales: 1.10
    - siglos: S. XIX
    """

    protegidos = {}

    def guardar(valor):
        key = f"__PUNT_{len(protegidos)}__"
        protegidos[key] = valor
        return key

    # Proteger decimales: 1.10, 2.5, etc.
    texto = re.sub(
        r"\b\d+\.\d+\b",
        lambda m: guardar(m.group(0)),
        texto,
    )

    # Proteger siglos: S. XIX, S.XVIII
    texto = re.sub(
        r"\bS\.\s*([IVXLCDM]+)\b",
        lambda m: guardar(m.group(0)),
        texto,
        flags=re.IGNORECASE,
    )

    return texto, protegidos


def restaurar_patrones_puntuacion(texto, protegidos):
    for key, valor in protegidos.items():
        texto = texto.replace(key, valor)

    return texto


def normalizar_comillas_y_diagonales(texto):
    """
    Corrige detalles de formato:
    - "Gran aparador " -> "Gran aparador"
    - " Gran aparador" -> "Gran aparador"
    - aparador/ gabinete -> aparador / gabinete
    - vitrina/aparador -> vitrina / aparador
    """

    if not texto:
        return ""

    texto = str(texto)

    # Quitar espacio justo después de comilla de apertura:
    # " Gran aparador" -> "Gran aparador"
    texto = re.sub(r'(^|[\s([{¿¡])"\s+', r'\1"', texto)

    # Quitar espacio antes de comilla de cierre:
    # "Gran aparador " -> "Gran aparador"
    texto = re.sub(r'(?<=\S)\s+"(?=($|[\s,.;:!?)]))', '"', texto)

    # Espacios alrededor de diagonales entre palabras:
    # aparador/ gabinete -> aparador / gabinete
    # vitrina/aparador -> vitrina / aparador
    letras = r"A-Za-zÁÉÍÓÚÜÑáéíóúüñ"

    texto = re.sub(
        rf"(?<=[{letras}])\s*/\s*(?=[{letras}])",
        " / ",
        texto,
    )

    # Evitar espacios duplicados por los reemplazos.
    texto = re.sub(r"[ \t]{2,}", " ", texto)

    return texto.strip()


def normalizar_puntuacion(texto):
    """
    Limpia puntuación común:
    - elimina espacios antes de coma, punto, punto y coma, dos puntos
    - agrega espacio después de puntuación cuando falta
    - limpia comas/puntos duplicados
    - conserva saltos de línea
    """

    if not texto:
        return ""

    texto = str(texto)

    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    texto, protegidos = proteger_patrones_puntuacion(texto)

    # Normalizar comillas curvas
    texto = texto.replace("“", "\"").replace("”", "\"")
    texto = texto.replace("‘", "'").replace("’", "'")

    # Quitar espacios antes de signos
    texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)

    # Comas/puntos repetidos
    texto = re.sub(r",{2,}", ",", texto)
    texto = re.sub(r"\.{2,}", ".", texto)

    # Espacio después de coma, punto y coma, dos puntos, signos
    # No afecta saltos de línea.
    texto = re.sub(r"([,;:!?])([^\s\n])", r"\1 \2", texto)

    # Espacio después de punto cuando después viene letra.
    texto = re.sub(r"\.([A-Za-zÁÉÍÓÚÜÑáéíóúüñ])", r". \1", texto)

    # Limpiar espacios repetidos sin destruir saltos de línea.
    texto = re.sub(r"[ \t]+", " ", texto)

    # Limpiar espacios alrededor de saltos.
    texto = re.sub(r" *\n *", "\n", texto)

    # Máximo dos saltos seguidos.
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    texto = restaurar_patrones_puntuacion(texto, protegidos)
    
    texto = normalizar_comillas_y_diagonales(texto)

    return texto.strip()

def capitalizar_oraciones(texto):
    """
    Capitaliza el inicio de cada oración y de cada párrafo.
    No convierte todo a formato título; solo corrige inicios.
    """

    if not texto:
        return ""

    resultado = []
    capitalizar_siguiente = True

    for char in texto:
        if capitalizar_siguiente and re.match(
            r"[a-záéíóúüñ]",
            char,
            flags=re.IGNORECASE,
        ):
            resultado.append(char.upper())
            capitalizar_siguiente = False
        else:
            resultado.append(char)

        if char in ".!?":
            capitalizar_siguiente = True

        if char == "\n":
            capitalizar_siguiente = True

    return "".join(resultado)

def normalizar_notas(texto):
    """
    Limpia notas para que no salgan con comillas ni puntuación sobrante.
    """

    if not texto:
        return ""

    texto = str(texto).strip()

    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    # Quitar viñetas o símbolos decorativos.
    texto = re.sub(r"[⚜️❗️❤️‼️]", "", texto)

    # Normalizar separadores.
    texto = texto.replace("\n", " | ")

    # Quitar comillas externas e internas sueltas.
    texto = texto.strip()
    texto = texto.strip("\"'“”‘’")
    texto = texto.replace("\"", "")
    texto = texto.replace("“", "").replace("”", "")
    texto = texto.replace("‘", "").replace("’", "")

    texto = normalizar_puntuacion(texto)

    # Quitar punto final en notas cortas tipo etiqueta.
    texto = texto.rstrip(".")

    # Normalizar espacios alrededor de separadores.
    texto = re.sub(r"\s*\|\s*", " | ", texto)

    # Normalizar espacios.
    texto = re.sub(r"\s+", " ", texto).strip()

    # Para notas tipo "artículo europeo importado", queda mejor en mayúsculas.
    if len(texto) <= 120:
        texto = texto.upper()

    return texto

def normalizar_titulo(texto):
    """
    Limpia títulos/nombres de producto sin alterar demasiado el estilo.
    """

    if not texto:
        return ""

    texto = str(texto).strip()

    texto = re.sub(r"[⚜️❗️❤️‼️]", "", texto)
    texto = texto.strip("\"'“”‘’")

    texto = normalizar_puntuacion(texto)

    # Evitar punto final en título.
    texto = texto.rstrip(".")

    texto = capitalizar_oraciones(texto)

    return texto.strip()

def proteger_romanos_y_siglos(texto):
    protegidos = {}
    i = 0

    def guardar(valor):
        nonlocal i
        key = f"§ROM{i}§"
        protegidos[key] = valor
        i += 1
        return f"{key} "
    
    ROMANO = r"(?:X{1,4}(?:IX|IV|V?I{2,3}))"  

    # 2️⃣ Siglos simples: Siglo XIX / S. XX
    texto = re.sub(
        rf"\b(?:siglo|s\.)\s*({ROMANO})\s*[-–]\s*({ROMANO})\b",
        lambda m: guardar(f"S. {m.group(1).upper()}–S. {m.group(2).upper()}"),
        texto,
        flags=re.IGNORECASE
    )
    # 1️⃣ Rangos bien formados: Siglo XIX–XX
    texto = re.sub(
        rf"\b(?:siglo|s\.)\s*({ROMANO})\b",
        lambda m: guardar(f"S. {m.group(1).upper()}"),
        texto,
        flags=re.IGNORECASE
    )



    return texto, protegidos

def procesar_con_spacy(texto):
    doc = nlp(texto)
    resultado = []

    for sent in doc.sents:
        for token in sent:
            if token.text.startswith("§ROM"):
                resultado.append(token.text)
            elif token.ent_type_ in {"PER", "LOC", "ORG", "MISC"}:
                resultado.append(token.text.capitalize())
            elif token.is_sent_start:
                resultado.append(token.text.capitalize())
            else:
                resultado.append(token.text)

            resultado.append(token.whitespace_)

    return "".join(resultado).strip()


def restaurar_final(texto, protegidos):
    for k, v in protegidos.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"\s{2,}", " ", texto)
    return texto.strip()


def normalizar_ortografia(texto):
    texto = re.sub(r"\s+([,.;:])", r"\1", texto)
    texto = re.sub(r"([,.;:])([^\s])", r"\1 \2", texto)
    return texto.strip()

def normalizar_romanos_sueltos(texto):
    def repl(m):
        return m.group(0).upper()

    return re.sub(
        r"\b[IVXLCDM]{2,}\b",
        repl,
        texto,
        flags=re.IGNORECASE
    )

def estructurar_parrafos_descripcion(texto, oraciones_por_parrafo=2):
    """
    Estructura la descripción en párrafos.

    - Si el TXT ya traía saltos de línea, los respeta.
    - Si viene todo corrido, agrupa cada 2 oraciones.
    - Protege siglos tipo S. XIX y números decimales tipo 1.10.
    """

    if not texto:
        return ""

    texto = str(texto).strip()
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")

    # Si ya hay saltos de línea reales, respetarlos como párrafos.
    lineas = [linea.strip() for linea in texto.split("\n") if linea.strip()]

    if len(lineas) > 1:
        return "\n".join(lineas)

    protecciones = {}

    def proteger(valor):
        key = f"__PROT_{len(protecciones)}__"
        protecciones[key] = valor
        return key

    # Proteger siglos: S. XIX, S. XVIII, etc.
    texto = re.sub(
        r"\bS\.\s*([IVXLCDM]+)\b",
        lambda m: proteger(m.group(0)),
        texto,
        flags=re.IGNORECASE,
    )

    # Proteger números decimales: 1.10, 2.5, etc.
    texto = re.sub(
        r"\b\d+\.\d+\b",
        lambda m: proteger(m.group(0)),
        texto,
    )

    # Separar en oraciones.
    partes = re.split(r"(?<=[.!?])\s+", texto)

    parrafos = []
    actual = []

    for parte in partes:
        parte = parte.strip()

        if not parte:
            continue

        actual.append(parte)

        if len(actual) >= oraciones_por_parrafo:
            parrafos.append(" ".join(actual))
            actual = []

    if actual:
        parrafos.append(" ".join(actual))

    resultado = "\n\n".join(parrafos)

    # Restaurar protecciones.
    for key, valor in protecciones.items():
        resultado = resultado.replace(key, valor)

    return resultado.strip()

def descripcion_a_oraciones(lineas):
    """
    Limpia y estructura la descripción.

    Importante:
    - Conserva los saltos de línea del TXT.
    - Si el texto viene corrido, crea párrafos automáticamente.
    - Corrige puntuación sucia: " ," / " ." / ",,"
    - Capitaliza inicios de oración y párrafo.
    """

    texto = "\n".join(lineas)

    texto = limpiar_ruido_ocr(texto)
    texto = texto.lower()

    texto = procesar_con_spacy(texto)
    texto = normalizar_romanos_sueltos(texto)

    texto, protegidos = proteger_romanos_y_siglos(texto)
    texto = restaurar_final(texto, protegidos)

    texto = normalizar_ortografia(texto)
    texto = normalizar_puntuacion(texto)

    if texto and not texto.endswith("."):
        texto += "."

    texto = re.sub(r"\.{2,}$", ".", texto)
    texto = balancear_comillas(texto)

    texto = normalizar_puntuacion(texto)

    texto = estructurar_parrafos_descripcion(
        texto,
        oraciones_por_parrafo=2,
    )

    texto = capitalizar_oraciones(texto)
    texto = normalizar_puntuacion(texto)

    return texto

def preparar_bloque_producto(bloque):
    """
    Prepara el bloque completo antes de dividirlo en líneas.

    El símbolo ⚜️ en los TXT funciona como separador visual.
    Si solo se elimina, las frases se pegan:
    'mármol⚜️base' -> 'mármolbase'

    Por eso primero lo convertimos en salto de línea.
    """

    if not bloque:
        return ""

    bloque = bloque.replace("\r\n", "\n").replace("\r", "\n")

    # Separadores decorativos usados como cortes de frase.
    bloque = re.sub(r"⚜️+", "\n", bloque)

    # Signos decorativos de nota. No los queremos como texto.
    bloque = re.sub(r"[❗️❤️‼️]", "", bloque)

    # Limpiar saltos excesivos.
    bloque = re.sub(r"\n{3,}", "\n\n", bloque)

    return bloque.strip()

def parece_nombre_producto(linea, nombre_actual):
    if nombre_actual:
        return False

    if not linea:
        return False

    l = linea.strip()

    if es_precio(l) or es_medida(l) or es_nota(l) or es_ruido(l):
        return False

    # Primera línea normalmente es nombre.
    if len(l) <= 80:
        return True

    return False
# --------------------------------------------------
# PROCESAMIENTO PRINCIPAL
# --------------------------------------------------

SEPARADORES_DECORATIVOS_RE = re.compile(r"(?:⚜️|⚜|❗️|❗|❤️|❤|‼️|‼)+")


def dividir_por_separadores_decorativos(texto):
    partes = SEPARADORES_DECORATIVOS_RE.split(str(texto or ""))

    resultado = []

    for parte in partes:
        parte = limpiar_ruido_ocr(parte)
        parte = parte.strip()

        if parte:
            resultado.append(parte)

    return resultado


def extraer_encabezado_antes_de_precio(bloque):
    """
    Extrae nombre, precio y notas ubicadas antes del precio.

    Corrige casos como:
    'CÓMODA FRANCESA ⚜️FRANCOIS⚜️'
    para que 'FRANCOIS' no se vaya a descripción.
    """

    lineas_raw = [
        linea.strip()
        for linea in str(bloque or "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .splitlines()
        if linea.strip() and "*" not in linea
    ]

    partes_nombre = []
    notas = []
    precio = ""

    for linea in lineas_raw:
        # Si encontramos el precio, termina el encabezado.
        if es_precio(linea):
            precio = linea
            break

        partes = dividir_por_separadores_decorativos(linea)

        for parte in partes:
            if not parte:
                continue

            if es_precio(parte):
                precio = parte
                break

            if es_ruido(parte):
                continue

            if es_medida(parte):
                continue

            if es_nota(parte):
                notas.append(parte)
                continue

            # Todo lo válido antes del precio se considera parte del nombre.
            if len(parte) <= 120:
                partes_nombre.append(parte)

        if precio:
            break

    nombre_raw = " ".join(partes_nombre)
    nombre_raw = re.sub(r"\s+", " ", nombre_raw).strip()

    if nombre_raw:
        nombre = normalizar_titulo(smart_title_nombre(nombre_raw))
    else:
        nombre = ""

    return nombre, precio, notas


def procesar_archivos(path_txt):
    with open(path_txt, "r", encoding="utf-8") as f:
        texto = f.read()

    productos = []
    for match in patron_producto.finditer(texto):
        id_prod = match.group(1)
        bloque_original = match.group(2)

        nombre_extraido, precio_extraido, notas_extraidas = extraer_encabezado_antes_de_precio(
            bloque_original
        )

        bloque = preparar_bloque_producto(bloque_original)

        # Usamos limpiar_ruido_ocr aquí también para los campos individuales
        lineas = [
            limpiar_ruido_ocr(l)
            for l in bloque.splitlines()
            if l.strip() and "*" not in l
        ]

        nombre = nombre_extraido
        precio = precio_extraido
        medidas = []
        notas = notas_extraidas[:]
        descripcion_raw = []

        procesar_despues_precio = False if precio_extraido else True

        for l in lineas:
            if es_precio(l):
                if not precio:
                    precio = l

                procesar_despues_precio = True
                continue

            # Si ya detectamos encabezado antes del precio,
            # ignoramos todo lo anterior al precio para evitar duplicados
            # y evitar que fragmentos del nombre se vayan a descripción.
            if not procesar_despues_precio:
                continue

            if es_medida(l):
                medidas.extend(extraer_medidas_de_linea(l))

            elif es_nota(l):
                notas.append(l)

            elif es_ruido(l):
                continue

            elif parece_nombre_producto(l, nombre):
                nombre = normalizar_titulo(smart_title_nombre(l))

            else:
                descripcion_raw.append(l)

        descripcion = descripcion_a_oraciones(descripcion_raw)

        medidas_items = [
            normalizar_puntuacion(m)
            for m in medidas
        ]

        medidas_txt = "\n".join(medidas_items)

        notas_limpias = []

        for n in notas:
            nota_limpia = normalizar_notas(n)

            if nota_limpia:
                notas_limpias.append(nota_limpia)

        notas_txt = " | ".join(notas_limpias)

        clasificacion = clasificar_producto(
            nombre=nombre,
            descripcion=descripcion,
            archivo_origen=path_txt.name,
            medidas=medidas_txt,
            notas=notas_txt
        )
        
        nombre_limpio = normalizar_titulo(nombre)
        nombre_limpio = reformular_estilo_en_nombre(
            nombre_limpio,
            indice=int(id_prod),
        )

        productos.append({
            "id": id_prod,
            "id_catalogo": crear_id_catalogo(id_prod),
            "nombre": nombre_limpio,
            "precio": normalizar_precio(precio) if precio else "",
            "descripcion": descripcion,
            "medidas": normalizar_puntuacion(medidas_txt),
            "medidas_items": medidas_items,
            "notas": normalizar_notas(notas_txt),
            "archivo_origen": path_txt.name,

            "categoria_catalogo": clasificacion["categoria_catalogo"],
            "tipo_objeto": clasificacion["tipo_objeto"],
            "subtipo": clasificacion["subtipo"],
            "clasificacion_score": clasificacion["clasificacion_score"],
            "clasificacion_keyword": clasificacion["clasificacion_keyword"],
        })
    return productos

def mostrar_configuracion_actual(config, carpeta_txt, carpeta_salida):
    print("\n--- CONFIGURACIÓN ACTUAL TEXTO ---")
    print(f"Modo: {config.modo}")
    print(f"Categoría: {config.categoria}")
    print(f"Base: {config.base}")
    print(f"Carpeta TXT: {carpeta_txt}")
    print(f"Carpeta JSON: {carpeta_salida}")

# --------------------------------------------------
# EJECUCIÓN
# --------------------------------------------------


def main():
    config = get_config()

    carpeta_txt = config.raw_txt
    carpeta_salida = config.processed
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    archivos_txt = sorted(
        [p for p in carpeta_txt.glob("*.txt") if numero_archivo(p)], key=numero_archivo
    )

    args = leer_argumentos()
    ids_objetivo = obtener_ids_objetivo(args)

    mostrar_configuracion_actual(
        config=config,
        carpeta_txt=carpeta_txt,
        carpeta_salida=carpeta_salida,
    )

    if ids_objetivo:
        print(
            f"\nModo actualización parcial. IDs objetivo: {', '.join(sorted(ids_objetivo))}"
        )
    else:
        print("\nModo actualización completa.")

    if not carpeta_txt.exists():
        print(f"❌ No existe la carpeta de TXT: {carpeta_txt}")
        return

    if not archivos_txt:
        print(f"⚠ No encontré archivos .txt válidos en: {carpeta_txt}")
        return

    total_productos = 0
    total_actualizados = 0

    for archivo in archivos_txt:
        productos = procesar_archivos(archivo)

        if not productos:
            continue

        total_productos += len(productos)

        productos_filtrados = filtrar_productos_por_ids(
            productos,
            ids_objetivo,
        )

        if ids_objetivo and not productos_filtrados:
            continue

        if ids_objetivo:
            guardar_json_parcial(
                productos_filtrados,
                archivo,
                carpeta_salida,
            )
            total_actualizados += len(productos_filtrados)
        else:
            guardar_json(
                productos,
                archivo,
                carpeta_salida,
            )
            total_actualizados += len(productos)

    print("\nProceso terminado.")
    print(f"Productos procesados desde TXT: {total_productos}")
    print(f"Productos actualizados en JSON: {total_actualizados}")

    if ids_objetivo and total_actualizados == 0:
        print("⚠ No encontré ningún producto con esos IDs.")


if __name__ == "__main__":
    main()
