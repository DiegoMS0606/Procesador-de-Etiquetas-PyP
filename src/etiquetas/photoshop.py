import json
import tempfile
from pathlib import Path

import win32com.client


ROOT = Path(__file__).resolve().parents[2]
JSX_RENDER = ROOT / "src" / "etiquetas" / "render_template.jsx"


def normalizar_ruta(path):
    return str(Path(path).resolve()).replace("\\", "/")


def renderizar_template_photoshop(config_data):
    if not JSX_RENDER.exists():
        raise FileNotFoundError(f"No existe JSX: {JSX_RENDER}")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        json.dump(config_data, tmp, ensure_ascii=False, indent=2)
        ruta_config = tmp.name

    ps = win32com.client.Dispatch("Photoshop.Application")
    ps.Visible = True

    resultado = ps.DoJavaScriptFile(
        str(JSX_RENDER),
        [normalizar_ruta(ruta_config)]
    )

    return resultado


def renderizar_front_back(
    config,
    layout,
    size,
    id_catalogo,
    item,
    ruta_img,
    back_psd=None,
):
    template_front = config.template_file(layout, size, "front")
    template_back = back_psd
    if template_back is None:
        template_back = config.template_file(layout, size, "back")

    output_front = config.output / f"{id_catalogo}_front.png"
    output_back = config.output / f"{id_catalogo}_back.png"

    datos_base = {
        "id_catalogo": id_catalogo,
        "precio": str(item.get("precio", "")),
        "nombre": str(item.get("nombre", "")),
        "descripcion": str(item.get("descripcion", "")),
        "medidas": str(item.get("medidas", "")),
        "notas": str(item.get("notas", "")),
        "ruta_imagen": normalizar_ruta(ruta_img) if ruta_img else "",
    }

    config_front = {
        **datos_base,
        "side": "front",
        "template_path": normalizar_ruta(template_front),
        "output_path": normalizar_ruta(output_front),
    }

    config_back = {
        **datos_base,
        "side": "back",
        "template_path": normalizar_ruta(template_back),
        "output_path": normalizar_ruta(output_back),
    }

    log_front = renderizar_template_photoshop(config_front)
    log_back = renderizar_template_photoshop(config_back)

    return {
        "front": output_front,
        "back": output_back,
        "log_front": log_front,
        "log_back": log_back,
    }
