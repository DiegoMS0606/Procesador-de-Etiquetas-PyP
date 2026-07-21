#target photoshop

app.displayDialogs = DialogModes.NO;


function leerJSON(ruta) {
    var archivo = new File(ruta);

    if (!archivo.exists) {
        throw new Error("No existe config JSON: " + ruta);
    }

    archivo.open("r");
    var contenido = archivo.read();
    archivo.close();

    // Quitar BOM si existe
    contenido = contenido.replace(/^\uFEFF/, "");

    // Photoshop ExtendScript no siempre soporta JSON.parse()
    // Como este archivo lo genera Python, podemos evaluarlo como objeto JS.
    return eval("(" + contenido + ")");
}


function buscarCapaPorNombre(contenedor, nombreBuscado) {
    for (var i = 0; i < contenedor.layers.length; i++) {
        var capa = contenedor.layers[i];

        if (capa.name === nombreBuscado) {
            return capa;
        }

        if (capa.typename === "LayerSet") {
            var encontrada = buscarCapaPorNombre(capa, nombreBuscado);

            if (encontrada) {
                return encontrada;
            }
        }
    }

    return null;
}

function centrarCapaVerticalEnArea(nombreTexto, nombreArea) {
    var doc = app.activeDocument;

    var capaTexto = buscarCapaPorNombre(doc, nombreTexto);
    var capaArea = buscarCapaPorNombre(doc, nombreArea);

    if (!capaTexto) {
        return nombreTexto + ": NO_EXISTE";
    }

    if (!capaArea) {
        return nombreArea + ": NO_EXISTE";
    }

    try {
        app.refresh();

        // Hacer visible el área temporalmente para leer bien sus bounds
        capaArea.visible = true;

        var boundsArea = capaArea.bounds;
        var boundsTexto = capaTexto.bounds;

        var areaY1 = boundsArea[1].value;
        var areaY2 = boundsArea[3].value;

        var textoY1 = boundsTexto[1].value;
        var textoY2 = boundsTexto[3].value;

        var altoArea = areaY2 - areaY1;
        var altoTexto = textoY2 - textoY1;

        var centroAreaY = areaY1 + altoArea / 2;
        var centroTextoY = textoY1 + altoTexto / 2;

        var moverY = centroAreaY - centroTextoY;

        // Si el texto es más alto que el área, no lo centramos
        if (altoTexto > altoArea) {
            capaArea.visible = false;
            return nombreTexto + ": TEXTO_MAS_ALTO_QUE_AREA";
        }

        capaTexto.translate(0, moverY);

        // Ocultar para que no salga exportada
        capaArea.visible = false;

        return nombreTexto + ": CENTRADO_VERTICAL_OK";

    } catch (e) {
        try {
            capaArea.visible = false;
        } catch (err) {}

        return nombreTexto + ": ERROR_CENTRADO " + e.message;
    }
}


function actualizarTexto(nombreCapa, valor) {
    var doc = app.activeDocument;
    var capa = buscarCapaPorNombre(doc, nombreCapa);

    if (!capa) {
        return nombreCapa + ": NO_EXISTE";
    }

    if (capa.kind !== LayerKind.TEXT) {
        return nombreCapa + ": NO_ES_TEXTO";
    }

    valor = valor || "";
    valor = String(valor).replace(/\n/g, "\r");

    capa.textItem.contents = valor || "";

    return nombreCapa + ": OK";
}


function colocarImagenEnCapa(nombreCapa, rutaImagen) {
    if (!rutaImagen || rutaImagen === "") {
        return nombreCapa + ": SIN_IMAGEN";
    }

    var doc = app.activeDocument;
    var capaDestino = buscarCapaPorNombre(doc, nombreCapa);

    if (!capaDestino) {
        return nombreCapa + ": NO_EXISTE";
    }

    var archivoImagen = new File(rutaImagen);

    if (!archivoImagen.exists) {
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

    var boundsImg = capaImagen.bounds;

    var imgX1 = boundsImg[0].value;
    var imgY1 = boundsImg[1].value;
    var imgX2 = boundsImg[2].value;
    var imgY2 = boundsImg[3].value;

    var anchoImg = imgX2 - imgX1;
    var altoImg = imgY2 - imgY1;

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


function exportarPNG(rutaSalida) {
    var archivoSalida = new File(rutaSalida);
    var carpetaSalida = archivoSalida.parent;

    if (!carpetaSalida.exists) {
        carpetaSalida.create();
    }

    var opciones = new ExportOptionsSaveForWeb();
    opciones.format = SaveDocumentType.PNG;
    opciones.PNG8 = false;
    opciones.transparency = true;
    opciones.interlaced = false;
    opciones.includeProfile = false;

    app.activeDocument.exportDocument(
        archivoSalida,
        ExportType.SAVEFORWEB,
        opciones
    );
}


function main() {
    var rutaConfig = arguments[0];
    var config = leerJSON(rutaConfig);

    var logs = [];

    var archivoPSD = new File(config.template_path);

    if (!archivoPSD.exists) {
        throw new Error("No existe plantilla PSD: " + config.template_path);
    }

    app.open(archivoPSD);

    logs.push("PSD_ABIERTO: OK");

    if (config.side === "front") {
        logs.push(colocarImagenEnCapa("IMG_PRINCIPAL", config.ruta_imagen));
        logs.push(actualizarTexto("TXT_NOMBRE", config.nombre));
    }
    
    if (config.side === "back") {
        logs.push(actualizarTexto("TXT_DESCRIPCION", config.descripcion));
        logs.push(centrarCapaVerticalEnArea("TXT_DESCRIPCION", "AREA_DESCRIPCION"));
        logs.push(actualizarTexto("TXT_MEDIDAS", config.medidas));
        logs.push(actualizarTexto("TXT_PRECIO_FRONT", config.precio));
        logs.push(actualizarTexto("TXT_PRECIO_BACK", config.precio));
        logs.push(actualizarTexto("TXT_NOTAS", config.notas));
    }

    exportarPNG(config.output_path);

    logs.push("EXPORT: OK");

    app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);

    return logs.join(" | ");
}


main.apply(this, arguments);