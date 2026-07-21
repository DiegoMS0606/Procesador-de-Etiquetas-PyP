#target photoshop

app.displayDialogs = DialogModes.NO;


function leerJSON(ruta) {
    var archivo = new File(ruta);

    if (!archivo.exists) {
        throw new Error("No existe config JSON: " + ruta);
    }

    archivo.open("r");
    archivo.encoding = "UTF-8";
    var contenido = archivo.read();
    archivo.close();

    contenido = contenido.replace(/^\uFEFF/, "");

    return eval("(" + contenido + ")");
}


function normalizarRuta(ruta) {
    return String(ruta).replace(/\\/g, "/").toLowerCase();
}


function obtenerODocumentoAbierto(rutaPSD) {
    var rutaNorm = normalizarRuta(rutaPSD);

    for (var i = 0; i < app.documents.length; i++) {
        var doc = app.documents[i];

        try {
            var fullName = normalizarRuta(doc.fullName.fsName);

            if (fullName === rutaNorm) {
                return doc;
            }
        } catch (e) { }
    }

    var archivoPSD = new File(rutaPSD);

    if (!archivoPSD.exists) {
        throw new Error("No existe plantilla PSD: " + rutaPSD);
    }

    return app.open(archivoPSD);
}


function limpiarNombre(nombre) {
    return String(nombre)
        .toUpperCase()
        .replace(/\s+/g, "")
        .replace(/-/g, "_");
}


function esCapaRender(nombre) {
    nombre = String(nombre).toUpperCase();

    return (
        nombre.indexOf("_RENDER") !== -1 ||
        nombre.indexOf(" RENDER") !== -1 ||
        nombre.indexOf("RENDER COPIA") !== -1
    );
}


function buscarCapaFlexible(contenedor, nombreBuscado) {
    var objetivo = limpiarNombre(nombreBuscado);
    var esBusquedaArea = objetivo.indexOf("AREA_") === 0;

    // =========================
    // 1. Buscar coincidencia EXACTA primero
    // =========================
    for (var i = 0; i < contenedor.layers.length; i++) {
        var capa = contenedor.layers[i];
        var nombreOriginal = String(capa.name);

        if (esCapaRender(nombreOriginal)) {
            continue;
        }

        var nombreCapa = limpiarNombre(nombreOriginal);

        if (nombreCapa === objetivo) {
            return capa;
        }

        if (capa.typename === "LayerSet") {
            var encontradaExacta = buscarCapaFlexible(capa, nombreBuscado);

            if (encontradaExacta) {
                return encontradaExacta;
            }
        }
    }

    // =========================
    // 2. Buscar coincidencia parcial
    //    pero evitando confundir AREA_MEDIDAS con MEDIDAS
    // =========================
    for (var j = 0; j < contenedor.layers.length; j++) {
        var capa2 = contenedor.layers[j];
        var nombreOriginal2 = String(capa2.name);

        if (esCapaRender(nombreOriginal2)) {
            continue;
        }

        var nombreCapa2 = limpiarNombre(nombreOriginal2);

        // Si estoy buscando una capa normal, NO aceptar capas AREA_.
        if (!esBusquedaArea && nombreCapa2.indexOf("AREA_") === 0) {
            continue;
        }

        if (nombreCapa2.indexOf(objetivo) !== -1) {
            return capa2;
        }

        if (capa2.typename === "LayerSet") {
            var encontradaParcial = buscarCapaFlexible(capa2, nombreBuscado);

            if (encontradaParcial) {
                return encontradaParcial;
            }
        }
    }

    return null;
}


function listarCapas(contenedor, prefijo, salida) {
    prefijo = prefijo || "";
    salida = salida || [];

    for (var i = 0; i < contenedor.layers.length; i++) {
        var capa = contenedor.layers[i];

        salida.push(prefijo + capa.name + " [" + capa.typename + "]");

        if (capa.typename === "LayerSet") {
            listarCapas(capa, prefijo + "  > ", salida);
        }
    }

    return salida;
}


function buscarUltimaMesa(doc, tipoMesa, templateMesa) {
    var ultima = null;
    var maxX = -999999;

    tipoMesa = String(tipoMesa).toUpperCase();
    templateMesa = String(templateMesa).toUpperCase();

    for (var i = 0; i < doc.layers.length; i++) {
        var capa = doc.layers[i];

        if (capa.typename !== "LayerSet") {
            continue;
        }

        var nombre = String(capa.name).toUpperCase();

        // Ignorar plantilla
        if (nombre === templateMesa || nombre.indexOf("TEMPLATE") !== -1) {
            continue;
        }

        // Solo buscar mesas del tipo PRODUCTO_SIMPLE
        if (nombre.indexOf(tipoMesa) === -1) {
            continue;
        }

        try {
            var b = capa.bounds;
            var x2 = b[2].value;

            if (x2 > maxX) {
                maxX = x2;
                ultima = capa;
            }
        } catch (e) { }
    }

    return ultima;
}

function buscarMesaPorNombre(doc, nombreBuscado) {
    nombreBuscado = String(nombreBuscado || "").toUpperCase();

    if (!nombreBuscado) {
        return null;
    }

    for (var i = 0; i < doc.layers.length; i++) {
        var capa = doc.layers[i];

        if (capa.typename !== "LayerSet") {
            continue;
        }

        var nombre = String(capa.name).toUpperCase();

        if (nombre === nombreBuscado) {
            return capa;
        }
    }

    return null;
}
function ocultarTemplates(doc) {
    for (var i = 0; i < doc.layers.length; i++) {
        var capa = doc.layers[i];

        if (capa.typename !== "LayerSet") {
            continue;
        }

        var nombre = String(capa.name).toUpperCase();

        if (nombre.indexOf("TEMPLATE") !== -1) {
            capa.visible = false;
        }
    }
}


function moverDespuesDeMesa(copia, mesaReferencia, separacion) {
    separacion = separacion || 40;

    var bRef = mesaReferencia.bounds;
    var bCop = copia.bounds;

    var refX2 = bRef[2].value;
    var copX1 = bCop[0].value;

    var moverX = (refX2 + separacion) - copX1;

    copia.translate(moverX, 0);
}

function limpiarRendersDentroDeMesa(contenedor) {
    /*
    Borra capas renderizadas dentro de una mesa.
    Sirve como protección si el template o la mesa duplicada ya venía contaminada.
    */

    for (var i = contenedor.layers.length - 1; i >= 0; i--) {
        var capa = contenedor.layers[i];

        if (capa.typename === "LayerSet") {
            limpiarRendersDentroDeMesa(capa);
            continue;
        }

        if (esCapaRender(capa.name)) {
            capa.remove();
        }
    }
}

function obtenerMesaParaRender(doc, config) {
    var template = null;
    var referencia = null;

    var nombreDestino = config.nombre_nueva_mesa;
    var templateMesa = config.template_mesa || "TEMPLATE_PRODUCTO_SIMPLE";
    var tipoMesa = config.tipo_mesa || "PRODUCTO_SIMPLE";
    var separacion = config.separacion_mesas || 80;

    // 1. Si la mesa ya existe, reutilizarla.
    var existente = buscarMesaPorNombre(doc, nombreDestino);

    if (existente) {
        existente.visible = true;
        limpiarRendersDentroDeMesa(existente);
        ocultarTemplates(doc);
        return existente;
    }

    // 2. Si no existe, buscar template limpio.
    try {
        template = doc.layers.getByName(templateMesa);
    } catch (e) {
        throw new Error("No encontré la mesa plantilla: " + templateMesa);
    }

    // 3. Si Python manda referencia exacta, colocar después de esa mesa.
    if (config.referencia_mesa) {
        referencia = buscarMesaPorNombre(doc, config.referencia_mesa);

        if (!referencia) {
            throw new Error(
                "No encontré la mesa referencia: " + config.referencia_mesa
            );
        }
    }

    // 4. Si no hay referencia exacta, buscar última mesa del mismo tipo.
    if (!referencia) {
        referencia = buscarUltimaMesa(doc, tipoMesa, templateMesa);
    }

    // 5. Si no hay ninguna generada, usar template como referencia.
    if (!referencia) {
        referencia = template;
    }

    // 6. Crear nueva mesa desde template.
    var copia = template.duplicate();
    copia.name = nombreDestino;
    copia.visible = true;

    moverDespuesDeMesa(copia, referencia, separacion);
    limpiarRendersDentroDeMesa(copia);
    ocultarTemplates(doc);

    return copia;
}

function actualizarTextosDesdeConfig(contenedor, config) {
    var logs = [];
    var textos = config.textos || [];
    var datos = config.datos_texto || {};

    var mapaEspecial = {
        "TXT_PRECIO_FRONT": "PRECIO",
        "TXT_PRECIO_BACK": "PRECIO"
    };

    for (var i = 0; i < textos.length; i++) {
        var nombreCapa = textos[i];
        var campoDato = mapaEspecial[nombreCapa] || nombreCapa;
        var valor = datos[campoDato] || "";

        logs.push(actualizarTexto(contenedor, nombreCapa, valor));
    }

    return logs;
}

function colocarImagenesDesdeConfig(contenedor, config) {
    var logs = [];
    var imagenes = config.imagenes || {};

    for (var nombreCapa in imagenes) {
        if (!imagenes.hasOwnProperty(nombreCapa)) {
            continue;
        }

        logs.push(colocarImagen(
            contenedor,
            nombreCapa,
            imagenes[nombreCapa]
        ));
    }

    return logs;
}

function actualizarTexto(contenedor, nombreCapa, valor) {
    var capa = buscarCapaFlexible(contenedor, nombreCapa);

    if (!capa) {
        return nombreCapa + ": NO_EXISTE";
    }

    if (capa.kind !== LayerKind.TEXT) {
        return nombreCapa + ": NO_ES_TEXTO (" + capa.typename + ")";
    }

    valor = valor || "";
    valor = String(valor).replace(/\n/g, "\r");

    capa.textItem.contents = valor;

    return nombreCapa + ": OK";
}

function obtenerBoundsNumericos(capa) {
    var b = capa.bounds;

    return {
        x1: b[0].value,
        y1: b[1].value,
        x2: b[2].value,
        y2: b[3].value,
        ancho: b[2].value - b[0].value,
        alto: b[3].value - b[1].value
    };
}


function centrarCapaEnArea(contenedor, nombreTexto, nombreArea, modo) {
    var capaTexto = buscarCapaFlexible(contenedor, nombreTexto);
    var capaArea = buscarCapaFlexible(contenedor, nombreArea);

    if (!capaTexto) {
        return nombreTexto + " -> " + nombreArea + ": TEXTO_NO_EXISTE";
    }

    if (!capaArea) {
        return nombreTexto + " -> " + nombreArea + ": AREA_NO_EXISTE";
    }

    try {
        var bTexto = obtenerBoundsNumericos(capaTexto);
        var bArea = obtenerBoundsNumericos(capaArea);

        var centroTextoX = bTexto.x1 + bTexto.ancho / 2;
        var centroTextoY = bTexto.y1 + bTexto.alto / 2;

        var centroAreaX = bArea.x1 + bArea.ancho / 2;
        var centroAreaY = bArea.y1 + bArea.alto / 2;

        var moverX = 0;
        var moverY = 0;

        if (modo === "horizontal" || modo === "ambos") {
            moverX = centroAreaX - centroTextoX;
        }

        if (modo === "vertical" || modo === "ambos") {
            moverY = centroAreaY - centroTextoY;
        }

        capaTexto.translate(moverX, moverY);

        return nombreTexto + " -> " + nombreArea + ": CENTRADO_" + modo.toUpperCase();
    } catch (e) {
        return nombreTexto + " -> " + nombreArea + ": ERROR_CENTRADO " + e;
    }
}


function contieneValor(lista, valor) {
    if (!lista) {
        return false;
    }

    valor = String(valor).toUpperCase();

    for (var i = 0; i < lista.length; i++) {
        if (String(lista[i]).toUpperCase() === valor) {
            return true;
        }
    }

    return false;
}


function aplicarCentradoPorAreas(contenedor, config) {
    var logs = [];
    var areas = config.areas || [];

    if (contieneValor(areas, "AREA_NAME")) {
        logs.push(centrarCapaEnArea(
            contenedor,
            "NAME_PRODUCT",
            "AREA_NAME",
            "vertical"
        ));
    }

    if (contieneValor(areas, "AREA_DESC")) {
        logs.push(centrarCapaEnArea(
            contenedor,
            "DESCRIPCION_1",
            "AREA_DESC",
            "vertical"
        ));
    }

    if (contieneValor(areas, "AREA_DESC_2")) {
        logs.push(centrarCapaEnArea(
            contenedor,
            "DESCRIPCION_2",
            "AREA_DESC_2",
            "vertical"
        ));
    }

    if (contieneValor(areas, "AREA_DESC_3")) {
        logs.push(centrarCapaEnArea(
            contenedor,
            "DESCRIPCION_3",
            "AREA_DESC_3",
            "vertical"
        ));
    }

    if (contieneValor(areas, "AREA_MEDIDAS")) {
        logs.push(centrarCapaEnArea(
            contenedor,
            "MEDIDAS",
            "AREA_MEDIDAS",
            "vertical"
        ));
    }

    // Solo notas, no precio.
    if (contieneValor(areas, "AREA_P_N")) {
        logs.push(centrarCapaEnArea(
            contenedor,
            "NOTAS",
            "AREA_P_N",
            "horizontal"
        ));
    }

    return logs;
}

function ocultarAreasUsadas(contenedor, config) {
    var logs = [];
    var areas = config.areas || [];

    for (var i = 0; i < areas.length; i++) {
        var nombreArea = String(areas[i] || "").toUpperCase();

        // No ocultar AREA_NAME
        if (nombreArea === "AREA_NAME") {
            continue;
        }

        var capaArea = buscarCapaFlexible(contenedor, nombreArea);

        if (!capaArea) {
            logs.push(nombreArea + ": AREA_NO_EXISTE_AL_OCULTAR");
            continue;
        }

        try {
            capaArea.visible = false;
            logs.push(nombreArea + ": OCULTA");
        } catch (e) {
            logs.push(nombreArea + ": ERROR_OCULTAR " + e);
        }
    }

    return logs;
}
function colocarImagen(contenedor, nombreCapa, rutaImagen) {
    var doc = app.activeDocument;

    var capaDestino = buscarCapaFlexible(contenedor, nombreCapa);

    if (!capaDestino) {
        return nombreCapa + ": NO_EXISTE";
    }

    if (!rutaImagen || rutaImagen === "") {
        capaDestino.visible = false;
        return nombreCapa + ": SIN_IMAGEN_OCULTA";
    }

    var archivoImagen = new File(rutaImagen);

    if (!archivoImagen.exists) {
        capaDestino.visible = false;
        return nombreCapa + ": IMAGEN_NO_EXISTE";
    }

    var boundsDestino = capaDestino.bounds;

    var x1 = boundsDestino[0].value;
    var y1 = boundsDestino[1].value;
    var x2 = boundsDestino[2].value;
    var y2 = boundsDestino[3].value;

    var anchoDestino = x2 - x1;
    var altoDestino = y2 - y1;

    doc.activeLayer = capaDestino;

    var idPlc = charIDToTypeID("Plc ");
    var desc = new ActionDescriptor();

    desc.putPath(charIDToTypeID("null"), archivoImagen);
    desc.putEnumerated(
        charIDToTypeID("FTcs"),
        charIDToTypeID("QCSt"),
        charIDToTypeID("Qcsa")
    );

    executeAction(idPlc, desc, DialogModes.NO);

    var capaImagen = doc.activeLayer;
    capaImagen.name = nombreCapa + "_RENDER";

    try {
        capaImagen.move(capaDestino, ElementPlacement.PLACEBEFORE);
    } catch (e) { }

    var boundsImg = capaImagen.bounds;

    var imgX1 = boundsImg[0].value;
    var imgY1 = boundsImg[1].value;
    var imgX2 = boundsImg[2].value;
    var imgY2 = boundsImg[3].value;

    var anchoImg = imgX2 - imgX1;
    var altoImg = imgY2 - imgY1;

    if (anchoImg <= 0 || altoImg <= 0 || anchoDestino <= 0 || altoDestino <= 0) {
        return nombreCapa + ": ERROR_BOUNDS";
    }

    var escala = Math.min(
        anchoDestino / anchoImg,
        altoDestino / altoImg
    ) * 100;

    capaImagen.resize(escala, escala, AnchorPosition.MIDDLECENTER);

    boundsImg = capaImagen.bounds;

    imgX1 = boundsImg[0].value;
    imgY1 = boundsImg[1].value;
    imgX2 = boundsImg[2].value;
    imgY2 = boundsImg[3].value;

    var centroDestinoX = x1 + anchoDestino / 2;
    var centroDestinoY = y1 + altoDestino / 2;

    var centroImgX = imgX1 + (imgX2 - imgX1) / 2;
    var centroImgY = imgY1 + (imgY2 - imgY1) / 2;

    capaImagen.translate(
        centroDestinoX - centroImgX,
        centroDestinoY - centroImgY
    );

    capaDestino.visible = false;

    return nombreCapa + ": OK";
}


function main() {
    if (arguments.length === 0) {
        throw new Error("Falta la ruta del config JSON");
    }

    var config = leerJSON(arguments[0]);

    var logs = [];

    var doc = obtenerODocumentoAbierto(config.template_path);
    app.activeDocument = doc;

    logs.push("PSD_ABIERTO: OK");

    var nuevaMesa = obtenerMesaParaRender(doc, config);

    logs.push("MESA_RENDER: " + config.nombre_nueva_mesa);

    if (config.debug === true) {
        logs.push("CAPAS_EN_MESA: " + listarCapas(nuevaMesa, "", []).join(" / "));
    }

    var logsTextos = actualizarTextosDesdeConfig(nuevaMesa, config);

    for (var t = 0; t < logsTextos.length; t++) {
        logs.push(logsTextos[t]);
    }
    var logsCentrado = aplicarCentradoPorAreas(nuevaMesa, config);

    for (var c = 0; c < logsCentrado.length; c++) {
        logs.push(logsCentrado[c]);
    }

    var logsAreas = ocultarAreasUsadas(nuevaMesa, config);

    for (var a = 0; a < logsAreas.length; a++) {
        logs.push(logsAreas[a]);
    }

    var logsImagenes = colocarImagenesDesdeConfig(nuevaMesa, config);

    for (var im = 0; im < logsImagenes.length; im++) {
        logs.push(logsImagenes[im]);
    }

    return logs.join(" | ");
}


main.apply(this, arguments);