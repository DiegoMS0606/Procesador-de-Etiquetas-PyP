from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORIAS_ROOT = PROJECT_ROOT / "data" / "categorias"



def numero_categoria(path):
    match = re.match(r"^(\d+)", path.name)

    if match:
        return int(match.group(1))

    return 999999


CARPETAS_REQUERIDAS = [
    "img",
    "processed",
    "etiquetas",
    "impresion",
]


def main():
    if not CATEGORIAS_ROOT.exists():
        print(f"No existe: {CATEGORIAS_ROOT}")
        return

    categorias = sorted(
        [p for p in CATEGORIAS_ROOT.iterdir() if p.is_dir()],
        key=lambda p: (numero_categoria(p), p.name.lower()),
    )

    print("\n=== CREAR ESTRUCTURA BASE DE CATEGORÍAS ===")
    print(f"Raíz: {CATEGORIAS_ROOT}")
    print(f"Categorías encontradas: {len(categorias)}")

    creadas = 0
    existentes = 0

    for categoria in categorias:
        print(f"\n{categoria.name}")

        for nombre_carpeta in CARPETAS_REQUERIDAS:
            ruta = categoria / nombre_carpeta

            if ruta.exists():
                print(f"  OK     {nombre_carpeta}/")
                existentes += 1
            else:
                ruta.mkdir(parents=True, exist_ok=True)
                print(f"  CREADA {nombre_carpeta}/")
                creadas += 1

    print("\n=== RESUMEN ===")
    print(f"Carpetas creadas: {creadas}")
    print(f"Carpetas existentes: {existentes}")


if __name__ == "__main__":
    main()
