def calcular_capacidades_maximas(capacidades, porcentaje=0.05, minimo=15):
    """
    Calcula la capacidad máxima permitida por caja usando margen.

    Ejemplo:
    base 520 + margen 5% = 546
    """

    capacidades_maximas = {}

    for caja, base in capacidades.items():
        margen = max(minimo, round(base * porcentaje))
        capacidades_maximas[caja] = base + margen

    return capacidades_maximas


def distribuir_descripcion_en_cajas(texto, capacidades, margen_config=None):
    """
    Distribuye texto entre varias cajas respetando:
    - capacidad base de cada caja
    - margen dinámico si hace falta
    - no cortar palabras
    - conservar párrafos cuando sea posible
    - continuar texto en la siguiente caja si no cabe
    """

    cajas = {nombre: "" for nombre in capacidades}
    nombres_cajas = list(capacidades.keys())

    margen_config = margen_config or {}

    porcentaje_margen = margen_config.get("porcentaje", 0.05)
    minimo_margen = margen_config.get("minimo", 15)

    capacidades_maximas = calcular_capacidades_maximas(
        capacidades,
        porcentaje=porcentaje_margen,
        minimo=minimo_margen,
    )

    texto = str(texto or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not texto:
        return cajas, ""

    parrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    idx_caja = 0
    overflow = []

    def caja_actual():
        if idx_caja >= len(nombres_cajas):
            return None

        return nombres_cajas[idx_caja]

    def agregar_texto(nombre_caja, texto_agregar, separador=" "):
        actual = cajas[nombre_caja]

        if not actual:
            candidato = texto_agregar
        else:
            candidato = actual + separador + texto_agregar

        if len(candidato) <= capacidades[nombre_caja]:
            cajas[nombre_caja] = candidato
            return True

        if len(candidato) <= capacidades_maximas[nombre_caja]:
            cajas[nombre_caja] = candidato
            return True

        return False

    def agregar_palabras(parrafo):
        nonlocal idx_caja

        palabras = parrafo.split()
        i = 0

        while i < len(palabras):
            nombre_caja = caja_actual()

            if not nombre_caja:
                return " ".join(palabras[i:])

            actual = cajas[nombre_caja]
            palabra = palabras[i]

            if not actual:
                candidato = palabra
            else:
                candidato = actual + " " + palabra

            if len(candidato) <= capacidades[nombre_caja]:
                cajas[nombre_caja] = candidato
                i += 1
                continue

            if len(candidato) <= capacidades_maximas[nombre_caja]:
                cajas[nombre_caja] = candidato
                i += 1
                continue

            idx_caja += 1

        return ""

    for parrafo in parrafos:
        nombre_caja = caja_actual()

        if not nombre_caja:
            overflow.append(parrafo)
            continue

        separador = "\n" if cajas[nombre_caja] else ""

        if agregar_texto(nombre_caja, parrafo, separador=separador):
            continue

        if cajas[nombre_caja] and agregar_texto(nombre_caja, parrafo, separador=" "):
            continue

        resto = agregar_palabras(parrafo)

        if resto:
            overflow.append(resto)

    overflow_texto = "\n".join(overflow).strip()

    return cajas, overflow_texto


def formatear_medidas_catalogo(medidas):
    """
    Agrega encabezado visual a las medidas para catálogo.

    Entrada:
    Altura: 90 cm
    Ancho: 60 cm

    Salida:
    Dimensiones:
    Altura: 90 cm
    Ancho: 60 cm
    """

    medidas = str(medidas or "").strip()

    if not medidas:
        return ""

    if medidas.lower().startswith("dimensiones"):
        return medidas

    return "Dimensiones:\n" + medidas