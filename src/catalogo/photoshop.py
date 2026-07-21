import json
import tempfile
from pathlib import Path

import win32com.client


ROOT = Path(__file__).resolve().parents[2]
JSX_CATALOGO = ROOT / "src" / "catalogo" / "render_catalogo.jsx"


def normalizar_ruta(path):
    if not path:
        return ""

    return str(Path(path).resolve()).replace("\\", "/")


def ejecutar_photoshop_catalogo(config_data):
    """
    Envía una config JSON temporal a Photoshop para renderizar una página del catálogo.
    """

    template_path = Path(config_data.get("template_path", ""))

    if not template_path.exists():
        raise FileNotFoundError(f"No existe el PSD de catálogo: {template_path}")

    if not JSX_CATALOGO.exists():
        raise FileNotFoundError(f"No existe el JSX del catálogo: {JSX_CATALOGO}")

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
        str(JSX_CATALOGO),
        [normalizar_ruta(ruta_config)]
    )

    return resultado
