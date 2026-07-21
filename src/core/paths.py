from datetime import datetime
from pathlib import Path
import json


# =========================================================
# ROOT Y CONFIG GLOBAL
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config.json"


DEFAULT_APP_CONFIG = {
    "env": "DEV",
    "categoria": "1-muebles_europeos_importados",
    "paper": "carta",
    "draw_guides": False,
    "debug": True,
}


def load_app_config():
    """
    Lee config.json desde la raíz del proyecto.

    Si no existe config.json, usa valores por defecto.
    """

    if not CONFIG_FILE.exists():
        return DEFAULT_APP_CONFIG.copy()

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = DEFAULT_APP_CONFIG.copy()
    config.update(data)

    config["env"] = str(config.get("env", "DEV")).upper().strip()

    return config


def get_config(
    layout=None,
    size=None,
    mode_type="base",
    imposition=None,
    side=None,
    **overrides
):
    """
    Crea una Config usando config.json.

    Ejemplo básico:
        config = get_config()

    Para etiquetas:
        config = get_config(layout="horizontal", size="small")

    Para impresión:
        config = get_config(
            layout="horizontal",
            size="small",
            mode_type="print",
            imposition="4up_same_orientation"
        )
    """

    app_config = load_app_config()

    for key, value in overrides.items():
        if value is not None:
            app_config[key] = value

    return Config(
        modo=app_config.get("env", "DEV"),
        categoria=app_config.get("categoria"),
        layout=layout or app_config.get("layout"),
        size=size or app_config.get("size"),
        mode_type=mode_type or app_config.get("mode_type", "base"),
        imposition=imposition or app_config.get("imposition"),
        paper=app_config.get("paper", "carta"),
        draw_guides=app_config.get("draw_guides", False),
        debug=app_config.get("debug", True),
    )


class Config:
    def __init__(
        self,
        modo="DEV",
        categoria=None,
        layout=None,
        size=None,
        mode_type="base",
        imposition=None,
        paper="carta",
        draw_guides=False,
        debug=True,
    ):
        self.modo = str(modo).upper().strip()
        self.categoria = categoria
        self.layout = layout
        self.size = size
        self.mode_type = mode_type
        self.imposition = imposition
        self.paper = paper
        self.draw_guides = draw_guides
        self.debug = debug

        # =========================
        # VALIDACIONES
        # =========================

        self.VALID_MODES = ["DEV", "PROD"]
        self.VALID_LAYOUTS = ["horizontal", "vertical"]
        self.VALID_SIZES = ["small", "large", "a5"]
        self.VALID_MODE_TYPES = ["base", "print"]
        self.VALID_IMPOSITIONS = [
            "4up_same_orientation",
            "6up_vertical_on_horizontal",
            "a5",
        ]
        self.VALID_SIDES = ["front", "back"]
        self.VALID_PAPERS = ["carta", "a4"]

        if self.modo not in self.VALID_MODES:
            raise ValueError("Modo inválido. Usa DEV o PROD")

        if self.layout and self.layout not in self.VALID_LAYOUTS:
            raise ValueError(f"layout inválido: {self.layout}")

        if self.size and self.size not in self.VALID_SIZES:
            raise ValueError(f"size inválido: {self.size}")

        if self.mode_type not in self.VALID_MODE_TYPES:
            raise ValueError(f"mode_type inválido: {self.mode_type}")

        if self.imposition and self.imposition not in self.VALID_IMPOSITIONS:
            raise ValueError(f"imposition inválida: {self.imposition}")

        if self.paper and self.paper not in self.VALID_PAPERS:
            raise ValueError(f"paper inválido: {self.paper}")

        # =========================
        # ROOT DEL PROYECTO
        # =========================

        self.root = PROJECT_ROOT

        self.templates = self.root / "templates"
        self.templates_etiquetas = self.templates / "etiquetas"

        # LEGACY: nombre antiguo usado por código existente.
        # Apunta a la nueva ubicación para no romper módulos todavía.
        self.templates_base = self.templates_etiquetas

        self.templates_print = self.templates / "print"
        self.templates_legacy = self.templates / "base-legacy"

        self.templates_catalogo = self.templates / "catalogo"
        self.templates_catalogo_distribuciones = self.templates_catalogo / "distribuciones"
        self.templates_catalogo_portadas = self.templates_catalogo / "portadas"

        # Datos
        self.data = self.root / "data"
        self.data_categorias = self.data / "categorias"
        self.data_dev = self.data / "dev"

        # LEGACY temporal
        self.categorias_legacy = self.root / "categorias"
        self.dev_legacy = self.root / "descripcion_etiquetas"

        # Salidas globales
        self.output_root = self.root / "output"
        self.output_catalogo = self.output_root / "catalogo"
        self.output_impresion = self.output_root / "impresion"

        # =========================
        # RUTAS DE CATÁLOGO
        # =========================

        self.fecha_exportacion_catalogo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        self.catalogo_exportacion = self.output_catalogo
        self.catalogo_paginas = self.output_catalogo / "paginas"
        self.catalogo_tmp = self.output_catalogo / "tmp"
        self.catalogo_final_pdf = self.output_catalogo / f"catalogo_{self.fecha_exportacion_catalogo}.pdf"

        # LEGACY: si algún módulo viejo todavía lo usa.
        # Catálogo
        # El catálogo se construye desde plantillas por distribución y portadas.
        self.catalogo = self.templates_catalogo
        self.catalogo_distribuciones = self.templates_catalogo_distribuciones
        self.catalogo_portadas = self.templates_catalogo_portadas

        # =========================
        # MODO DESARROLLO
        # =========================

        if self.modo == "DEV":
            nueva_base = self.data_dev
            legacy_base = self.dev_legacy

            if nueva_base.exists() and any(nueva_base.iterdir()):
                self.base = nueva_base
                self.raw_txt = self.base / "raw_txt"
                self.processed = self.base / "processed"
                self.img = self.base / "img"
                self.etiquetas_output = self.base / "etiquetas"
            else:
                self.base = legacy_base
                self.raw_txt = self.base / "data" / "raw_txt"
                self.processed = self.base / "data" / "processed"
                self.img = self.base / "pruebas_img" / "img"
                self.etiquetas_output = self.base / "pruebas_img" / "exportacion"

        # =========================
        # MODO PRODUCCIÓN
        # =========================

        elif self.modo == "PROD":
            if not self.categoria:
                raise ValueError("En modo PROD debes indicar categoria")

            if not isinstance(self.categoria, str):
                raise ValueError(
                    f"categoria debe ser str, no {type(self.categoria)}"
                )

            nueva_base = self.data_categorias / self.categoria
            legacy_base = self.categorias_legacy / self.categoria

            if nueva_base.exists():
                self.base = nueva_base
            else:
                self.base = legacy_base

            self.raw_txt = self.base
            self.processed = self.base / "processed"
            self.img = self.base / "img"
            self.etiquetas_output = self.base / "etiquetas"

        # LEGACY: varios módulos viejos todavía usan config.output para etiquetas.
        # La salida global real es output_root.
        self.output = self.etiquetas_output

        # =========================
        # CREAR CARPETAS NECESARIAS
        # =========================

        for carpeta in [
            self.data,
            self.data_categorias,
            self.data_dev,
            self.processed,
            self.etiquetas_output,
            self.output_root,
            self.output_catalogo,
            self.output_impresion,
            self.catalogo_exportacion,
            self.catalogo_paginas,
            self.catalogo_tmp,
        ]:
            carpeta.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # PSD BASE: PLANTILLAS NORMALES FRONT/BACK
    # =========================================================

    def get_psd_path(self, side=None):
        """
        Para mode_type='base' busca:

        templates/base/<layout>/<size>/<side>.psd

        Ejemplo:
        templates/base/horizontal/small/front.psd
        templates/base/horizontal/small/back.psd

        Para mode_type='print' conserva la lógica de plantillas de impresión.
        """

        if self.mode_type == "base":
            if not self.layout or not self.size:
                raise ValueError("Para mode_type='base' necesitas layout y size")

            if not side:
                raise ValueError(
                    "Para mode_type='base' necesitas side='front' o side='back'"
                )

            side = side.lower().strip()

            if side not in self.VALID_SIDES:
                raise ValueError(f"side inválido: {side}")

            ruta = self.templates_base / self.layout / self.size / f"{side}.psd"

            if not ruta.exists():
                raise FileNotFoundError(f"No existe la plantilla base: {ruta}")

            return ruta

        elif self.mode_type == "print":
            return self.get_print_psd_path()

        else:
            raise ValueError("mode_type inválido")

    # =========================================================
    # ALIAS MÁS CLARO PARA PLANTILLAS BASE
    # =========================================================

    def template_file(self, layout=None, size=None, side=None):
        """
        Alias para obtener front.psd o back.psd.

        Permite usar:
            config.template_file("horizontal", "small", "front")

        o usar los valores ya guardados:
            config.template_file(side="front")
        """

        layout = layout or self.layout
        size = size or self.size

        if not layout:
            raise ValueError("Falta layout")

        if not size:
            raise ValueError("Falta size")

        if not side:
            raise ValueError("Falta side: usa 'front' o 'back'")

        side = side.lower().strip()

        if layout not in self.VALID_LAYOUTS:
            raise ValueError(f"layout inválido: {layout}")

        if size not in self.VALID_SIZES:
            raise ValueError(f"size inválido: {size}")

        if side not in self.VALID_SIDES:
            raise ValueError(f"side inválido: {side}")

        ruta = self.templates_base / layout / size / f"{side}.psd"

        if not ruta.exists():
            raise FileNotFoundError(f"No existe la plantilla: {ruta}")

        return ruta

    # =========================================================
    # PSD DE IMPRESIÓN
    # =========================================================

    def get_print_psd_path(self):
        """
        Plantillas de impresión:

        templates/print/4up_same_orientation/horizontal/small_print.psd
        templates/print/4up_same_orientation/vertical/small_print.psd

        templates/print/6up_vertical_on_horizontal/small.psd

        templates/print/a5/a5.psd
        """

        if self.imposition == "4up_same_orientation":
            if not self.layout:
                raise ValueError("4up_same_orientation necesita layout")

            if not self.size:
                raise ValueError("4up_same_orientation necesita size")

            ruta = (
                self.templates_print
                / "4up_same_orientation"
                / self.layout
                / f"{self.size}_print.psd"
            )

        elif self.imposition == "6up_vertical_on_horizontal":
            if not self.size:
                raise ValueError("6up_vertical_on_horizontal necesita size")

            ruta = (
                self.templates_print
                / "6up_vertical_on_horizontal"
                / f"{self.size}.psd"
            )

        elif self.imposition == "a5":
            ruta = self.templates_print / "a5" / "a5.psd"

        else:
            raise ValueError("imposition no válida para print")

        if not ruta.exists():
            raise FileNotFoundError(f"No existe la plantilla de impresión: {ruta}")

        return ruta

    # =========================================================
    # PSD LEGACY CON MESAS DE TRABAJO
    # =========================================================

    def get_legacy_psd_path(self):
        """
        Por si necesitas abrir las plantillas viejas con mesas de trabajo.

        Busca:
        templates/base-legacy/horizontal/small.psd
        templates/base-legacy/vertical/large.psd
        """

        if not self.layout or not self.size:
            raise ValueError("Para legacy necesitas layout y size")

        ruta = self.templates_legacy / self.layout / f"{self.size}.psd"

        if not ruta.exists():
            raise FileNotFoundError(f"No existe plantilla legacy: {ruta}")

        return ruta

    # =========================================================
    # IMÁGENES DE PRODUCTO
    # =========================================================

    def producto_img_dir(self, id_catalogo):
        """
        Devuelve la carpeta de imágenes de un producto.

        Ejemplo PROD:
        categorias/1-muebles_europeos_importados/img/ACT-0002/

        Ejemplo DEV:
        descripcion_etiquetas/pruebas_img/img/ACT-0002/
        """

        return self.img / id_catalogo

    def principal_image(self, id_catalogo):
        """
        Busca la imagen principal del producto.

        Prioridad:
        principal.png
        principal.jpg
        principal.jpeg
        """

        carpeta = self.producto_img_dir(id_catalogo)

        posibles = [
            carpeta / "principal.png",
            carpeta / "principal.jpg",
            carpeta / "principal.jpeg",
        ]

        for ruta in posibles:
            if ruta.exists():
                return ruta

        return None

    def gallery_images(self, id_catalogo):
        """
        Devuelve imágenes secundarias del producto.

        Busca:
        1.png, 2.png, 3.png...
        1.jpg, 2.jpg...
        1.jpeg, 2.jpeg...
        """

        carpeta = self.producto_img_dir(id_catalogo)

        if not carpeta.exists():
            return []

        extensiones = [".png", ".jpg", ".jpeg"]

        imagenes = []

        for archivo in carpeta.iterdir():
            if archivo.suffix.lower() in extensiones:
                if archivo.stem.lower() != "principal":
                    imagenes.append(archivo)

        def ordenar_por_numero(path):
            try:
                return int(path.stem)
            except ValueError:
                return 9999

        return sorted(imagenes, key=ordenar_por_numero)

    # =========================================================
    # RUTAS DE SALIDA
    # =========================================================

    def output_file(self, id_catalogo, side, ext="png"):
        """
        Devuelve la ruta final de una etiqueta.

        Ejemplo:
        categorias/1-muebles.../etiquetas/ACT-0006_front.png
        """

        side = side.lower().strip()

        if side not in self.VALID_SIDES:
            raise ValueError(f"side inválido: {side}")

        return self.etiquetas_output / f"{id_catalogo}_{side}.{ext}"

    # =========================================================
    # INFO RÁPIDA
    # =========================================================

    def resumen(self):
        return {
            "modo": self.modo,
            "categoria": self.categoria,
            "layout": self.layout,
            "size": self.size,
            "mode_type": self.mode_type,
            "imposition": self.imposition,
            "paper": self.paper,
            "draw_guides": self.draw_guides,
            "debug": self.debug,
            "base": str(self.base),
            "raw_txt": str(self.raw_txt),
            "img": str(self.img),
            "processed": str(self.processed),
            "output": str(self.output),
            "output_root": str(self.output_root),
            "etiquetas_output": str(self.etiquetas_output),
            "templates_base": str(self.templates_base),
            "templates_print": str(self.templates_print),
            "catalogo": str(self.catalogo),
            "catalogo_exportacion": str(self.catalogo_exportacion),
        }
