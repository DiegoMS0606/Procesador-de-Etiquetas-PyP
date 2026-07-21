import re
import unicodedata


CATEGORIAS_CATALOGO = {
    "1": "muebles_europeos_importados",
    "2": "arte_decorativo_exclusivo",
    "3": "ebanisteria_de_elite",
    "4": "estilo_en_las_alturas",
    "5": "cristaleria_decorativa",
    "6": "historias_en_movimiento",
    "7": "lladro_capturando_esencias",
    "8": "iluminacion_clasica",
    "9": "alabastro_esculturas",
    "10": "un_toque_de_refinamiento",
    "11": "fragmentos_del_pasado",
    "12": "arte_en_bronce",
}


TIPOS_OBJETO = {
    "mueble": {
        "keywords": [
            "comoda", "gabinete", "aparador", "bonnetier", "escritorio",
            "mesa", "vitrina", "armario", "consola", "secreter",
            "bargueno", "bargueño", "sillon", "silla", "ropero",
            "ebanisteria", "madera", "roble", "caoba", "palo de rosa"
        ],
        "subtipos": {
            "comoda": ["comoda", "bombe", "bombé", "tumbeau", "tombeau"],
            "gabinete": ["gabinete"],
            "aparador": ["aparador"],
            "vitrina": ["vitrina"],
            "bonnetier": ["bonnetier"],
            "mesa": ["mesa"],
            "escritorio": ["escritorio", "secreter"],
            "sillon": ["sillon", "silla"],
        }
    },

    "porcelana": {
        "keywords": [
            "porcelana", "limoges", "sevres", "sèvres", "royal vienna",
            "viejo paris", "viejo parís", "karl ens", "meissen",
            "mayolica", "majolica", "tibor", "jarron", "jarrón",
            "guarnicion", "guarnición"
        ],
        "subtipos": {
            "jarron": ["jarron", "jarrón"],
            "tibor": ["tibor"],
            "figura": ["figura", "escultura", "grupo escultorico"],
            "guarnicion": ["guarnicion", "guarnición"],
            "plato": ["plato", "bandeja"],
            "candelabro": ["candelabro", "candelabros"],
        }
    },

    "lladro": {
        "keywords": [
            "lladro", "lladró", "nao", "porcelana lladro", "porcelana lladró"
        ],
        "subtipos": {
            "figura": ["figura", "escultura"],
            "grupo": ["grupo"],
        }
    },

    "cristal": {
        "keywords": [
            "cristal", "murano", "bohemia", "vidrio", "bacarat", "baccarat"
        ],
        "subtipos": {
            "jarron": ["jarron", "jarrón"],
            "copa": ["copa", "copas"],
            "centro": ["centro de mesa", "centro"],
            "florero": ["florero"],
        }
    },

    "bronce": {
        "keywords": [
            "bronce", "bronze", "patinado", "ormolu", "bronce dorado"
        ],
        "subtipos": {
            "escultura": ["escultura", "figura"],
            "candelabro": ["candelabro", "candelabros"],
            "reloj": ["reloj"],
        }
    },

    "iluminacion": {
        "keywords": [
            "candil", "chandelier", "lampara", "lámpara",
            "aplique", "luminaria", "plafon", "plafón"
        ],
        "subtipos": {
            "candil": ["candil", "chandelier"],
            "lampara": ["lampara", "lámpara"],
            "aplique": ["aplique"],
        }
    },

    "reloj": {
        "keywords": [
            "reloj", "maquinaria", "movimiento", "pendulo", "péndulo"
        ],
        "subtipos": {
            "reloj_mesa": ["reloj de mesa"],
            "reloj_pared": ["reloj de pared"],
            "reloj": ["reloj"],
        }
    },

    "alabastro": {
        "keywords": [
            "alabastro"
        ],
        "subtipos": {
            "escultura": ["escultura", "figura"],
            "lampara": ["lampara", "lámpara"],
        }
    },

    "pintura": {
        "keywords": [
            "pintura", "oleo", "óleo", "lienzo", "cuadro", "acuarela"
        ],
        "subtipos": {
            "oleo": ["oleo", "óleo"],
            "cuadro": ["cuadro", "pintura"],
        }
    },

    "plateria": {
        "keywords": [
            "plata",  "silver", "plateria", "platería"
        ],
        "subtipos": {
            "centro": ["centro"],
            "bandeja": ["bandeja"],
            "candelabro": ["candelabro"],
        }
    },
}
PESOS_CAMPO = {
    "nombre": 4,
    "descripcion": 2,
    "medidas": 1,
    "notas": 2,
}


CATALOGO_HINTS = {
    "1": {"mueble": 4},
    "2": {"porcelana": 2},
    "3": {"mueble": 4},
    "4": {},
    "5": {"cristal": 3},
    "6": {"reloj": 5},
    "7": {"lladro": 6},
    "8": {"iluminacion": 5},
    "9": {"alabastro": 6},
    "10": {"porcelana": 3},
    "11": {"porcelana": 3},
    "12": {"bronce": 6},
}


PRIORIDAD_TIPO = [
    "mueble",
    "iluminacion",
    "reloj",
    "lladro",
    "porcelana",
    "cristal",
    "bronce",
    "alabastro",
    "pintura",
    "plateria",
    "otros",
]

REGLAS_FUERTES_NOMBRE = {
    "reloj": ["reloj"],
    "iluminacion": ["lampara", "lámpara", "candil", "chandelier", "aplique", "plafon", "plafón", "luminaria"],
}


def detectar_regla_fuerte(textos_por_campo):
    nombre = normalizar_texto(textos_por_campo.get("nombre", ""))

    for tipo, palabras in REGLAS_FUERTES_NOMBRE.items():
        for palabra in palabras:
            if keyword_en_texto(nombre, palabra):
                return tipo, palabra

    return None, ""


def normalizar_texto(texto):
    texto = texto or ""
    texto = texto.lower()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")

    texto = re.sub(r"[^a-z0-9ñ\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def obtener_numero_catalogo(archivo_origen):
    archivo_origen = archivo_origen or ""

    match = re.match(r"^(\d+)", archivo_origen.strip())

    if not match:
        return ""

    return match.group(1)


def detectar_categoria_catalogo(archivo_origen):
    numero = obtener_numero_catalogo(archivo_origen)

    return CATEGORIAS_CATALOGO.get(numero, "sin_categoria_catalogo")


def contar_coincidencias(texto, palabras):
    total = 0
    encontrada = ""

    for palabra in palabras:
        palabra_norm = normalizar_texto(palabra)

        if palabra_norm and palabra_norm in texto:
            total += 1

            if not encontrada:
                encontrada = palabra

    return total, encontrada


def detectar_tipo_objeto(textos_por_campo, archivo_origen):
    scores = {}
    keywords_detectadas = {}

    for tipo, config in TIPOS_OBJETO.items():
        score, keyword = puntuar_keywords(
            textos_por_campo,
            config["keywords"]
        )

        scores[tipo] = score
        keywords_detectadas[tipo] = keyword

    # Si no hay ninguna palabra real, no aplicar pista de catálogo
    mejor_score_real = max(scores.values()) if scores else 0

    if mejor_score_real == 0:
        return "otros", 0, ""

    # Agregar pista por categoría del catálogo
    numero_catalogo = obtener_numero_catalogo(archivo_origen)
    hints = CATALOGO_HINTS.get(numero_catalogo, {})
    
    tipo_fuerte, keyword_fuerte = detectar_regla_fuerte(textos_por_campo)

    if tipo_fuerte:
        scores[tipo_fuerte] = scores.get(tipo_fuerte, 0) + 10
        keywords_detectadas[tipo_fuerte] = keyword_fuerte

    for tipo, extra in hints.items():
        if tipo in scores:
            scores[tipo] += extra

            if not keywords_detectadas[tipo]:
                keywords_detectadas[tipo] = "categoria_catalogo"

    mejor_tipo = "otros"
    mejor_score = 0

    for tipo, score in scores.items():
        if score > mejor_score:
            mejor_tipo = tipo
            mejor_score = score

        elif score == mejor_score and score > 0:
            if prioridad_tipo(tipo) < prioridad_tipo(mejor_tipo):
                mejor_tipo = tipo
                mejor_score = score

    return mejor_tipo, mejor_score, keywords_detectadas.get(mejor_tipo, "")


def detectar_subtipo(textos_por_campo, tipo_objeto):
    if tipo_objeto not in TIPOS_OBJETO:
        return "sin_subtipo"

    subtipos = TIPOS_OBJETO[tipo_objeto].get("subtipos", {})

    mejor_subtipo = "sin_subtipo"
    mejor_score = 0

    for subtipo, palabras in subtipos.items():
        score, _ = puntuar_keywords(textos_por_campo, palabras)

        if score > mejor_score:
            mejor_score = score
            mejor_subtipo = subtipo

    return mejor_subtipo


def clasificar_producto(nombre, descripcion, archivo_origen, medidas="", notas=""):
    textos_por_campo = {
        "nombre": nombre or "",
        "descripcion": descripcion or "",
        "medidas": medidas or "",
        "notas": notas or "",
    }

    categoria_catalogo = detectar_categoria_catalogo(archivo_origen)

    tipo_objeto, score, keyword = detectar_tipo_objeto(
        textos_por_campo,
        archivo_origen
    )

    subtipo = detectar_subtipo(textos_por_campo, tipo_objeto)

    return {
        "categoria_catalogo": categoria_catalogo,
        "tipo_objeto": tipo_objeto,
        "subtipo": subtipo,
        "clasificacion_score": score,
        "clasificacion_keyword": keyword,
    }
    
def prioridad_tipo(tipo):
    try:
        return PRIORIDAD_TIPO.index(tipo)
    except ValueError:
        return len(PRIORIDAD_TIPO)


def keyword_en_texto(texto_normalizado, keyword):
    keyword_norm = normalizar_texto(keyword)

    if not keyword_norm:
        return False

    # Para frases completas
    if " " in keyword_norm:
        patron = r"(?<![a-z0-9ñ])" + re.escape(keyword_norm) + r"(?![a-z0-9ñ])"
    else:
        # Permite plural simple: comoda / comodas, lampara / lamparas
        patron = r"(?<![a-z0-9ñ])" + re.escape(keyword_norm) + r"s?(?![a-z0-9ñ])"

    return bool(re.search(patron, texto_normalizado))


def puntuar_keywords(textos_por_campo, palabras):
    total = 0
    primera_keyword = ""

    vistas = set()

    for palabra in palabras:
        palabra_norm = normalizar_texto(palabra)

        # Evita contar doble marmol/mármol, sevres/sèvres, etc.
        if palabra_norm in vistas:
            continue

        vistas.add(palabra_norm)

        for campo, texto in textos_por_campo.items():
            texto_norm = normalizar_texto(texto)

            if keyword_en_texto(texto_norm, palabra):
                total += PESOS_CAMPO.get(campo, 1)

                if not primera_keyword:
                    primera_keyword = palabra

    return total, primera_keyword