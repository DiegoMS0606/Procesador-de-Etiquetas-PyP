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
        } catch (e) {}
    }

    var archivoPSD = new File(rutaPSD);

    if (!archivoPSD.exists) {
        throw new Error("No existe PSD: " + rutaPSD);
    }

    return app.open(archivoPSD);
}


function limpiarNombreArchivo(nombre) {
    return String(nombre)
        .replace(/[\\\/\:\*\?\"\<\>\|]/g, "_")
        .replace(/\s+/g, "_");
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
    opciones.transparency = false;
    opciones.interlaced = false;
    opciones.includeProfile = false;

    app.activeDocument.exportDocument(
        archivoSalida,
        ExportType.SAVEFORWEB,
        opciones
    );
}


function ocultarTodasLasMesas(doc) {
    for (var i = 0; i < doc.layers.length; i++) {
        doc.layers[i].visible = false;
    }
}


function obtenerMesasProducto(doc, tipoMesa, templateMesa) {
    var mesas = [];

    tipoMesa = String(tipoMesa).toUpperCase();
    templateMesa = String(templateMesa).toUpperCase();

    for (var i = 0; i < doc.layers.length; i++) {
        var capa = doc.layers[i];

        if (capa.typename !== "LayerSet") {
            continue;
        }

        var nombre = String(capa.name).toUpperCase();

        // Ignorar template
        if (nombre === templateMesa || nombre.indexOf("TEMPLATE") !== -1) {
            continue;
        }

        // Solo productos
        if (nombre.indexOf(tipoMesa) === -1) {
            continue;
        }

        var b = capa.bounds;
        var x1 = b[0].value;
        var y1 = b[1].value;

        mesas.push({
            capa: capa,
            nombre: capa.name,
            x1: x1,
            y1: y1
        });
    }

    // Orden visual izquierda → derecha
    mesas.sort(function(a, b) {
        var toleranciaY = 30;

        if (Math.abs(a.y1 - b.y1) > toleranciaY) {
            return a.y1 - b.y1;
        }

        return a.x1 - b.x1;
    });

    return mesas;
}


function exportarMesa(doc, mesa, rutaSalida) {
    ocultarTodasLasMesas(doc);

    mesa.visible = true;

    exportarPNG(rutaSalida);
}


function main() {
    if (arguments.length === 0) {
        throw new Error("Falta ruta config JSON");
    }

    var config = leerJSON(arguments[0]);

    var doc = obtenerODocumentoAbierto(config.template_path);
    app.activeDocument = doc;

    var outputDir = config.output_dir;
    var outputFile = config.output_file || "000_PORTADA.png";
    var tipoMesa = config.tipo_mesa || "PRODUCTO_SIMPLE";
    var templateMesa = config.template_mesa || "TEMPLATE_PRODUCTO_SIMPLE";
    var exportMode = config.export_mode || "productos";

    var logs = [];

    // =========================
    // MODO 1: EXPORTAR PORTADA ÚNICA
    // =========================
    if (exportMode === "portada_unica") {
        var rutaPortada = outputDir + "/" + outputFile;

        exportarPNG(rutaPortada);
        logs.push("PORTADA_EXPORTADA: " + rutaPortada);

        return logs.join(" | ");
    }

    // =========================
    // MODO 2: EXPORTAR PRODUCTOS
    // =========================

    var mesas = obtenerMesasProducto(doc, tipoMesa, templateMesa);

    logs.push("MESAS_PRODUCTO_A_EXPORTAR: " + mesas.length);

    for (var i = 0; i < mesas.length; i++) {
        var item = mesas[i];

        var numero = i + 1;
        var nombreLimpio = limpiarNombreArchivo(item.nombre);

        var rutaSalida =
            outputDir +
            "/" +
            ("000" + numero).slice(-3) +
            "_" +
            nombreLimpio +
            ".png";

        exportarMesa(doc, item.capa, rutaSalida);

        logs.push("PRODUCTO_EXPORTADO: " + rutaSalida);
    }

    // estado final
    ocultarTodasLasMesas(doc);

    for (var j = 0; j < mesas.length; j++) {
        mesas[j].capa.visible = true;
    }

    try {
        doc.layers.getByName(templateMesa).visible = false;
    } catch (e) {}

    return logs.join(" | ");
}


main.apply(this, arguments);