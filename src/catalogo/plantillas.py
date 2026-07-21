import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUTA_DISTRIBUCIONES = ROOT / "config" / "catalogo_distribuciones.json"


def normalizar_ruta_distribucion(data):
    """
    Convierte rutas relativas del JSON a rutas absolutas Path.
    """

    distribuciones = {}

    for nombre, dist in data.items():
        nueva = dict(dist)

        if "psd" not in nueva:
            raise ValueError(f"La distribución {nombre} no tiene campo 'psd'")

        nueva["psd"] = ROOT / nueva["psd"]

        distribuciones[nombre] = nueva

    return distribuciones


def cargar_distribuciones_catalogo():
    if not RUTA_DISTRIBUCIONES.exists():
        raise FileNotFoundError(
            f"No existe el archivo de distribuciones: {RUTA_DISTRIBUCIONES}"
        )

    with open(RUTA_DISTRIBUCIONES, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("catalogo_distribuciones.json debe contener un objeto JSON")

    return normalizar_ruta_distribucion(data)