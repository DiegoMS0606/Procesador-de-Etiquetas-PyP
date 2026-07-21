from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORIAS_ROOT = PROJECT_ROOT / "data" / "categorias"

EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".webp"}

CARPETAS_REQUERIDAS = [
    "img",
    "processed",
    "etiquetas",
    "impresion",
]

PATRON_ACT = re.compile(r"^ACT-\d{4}$", re.IGNORECASE)
PATRON_GALERIA = re.compile(r"^\d+$")


def es_imagen(path):
    return path.is_file() and path.suffix.lower() in EXTENSIONES_IMAGEN


def revisar_categoria(categoria_path):
    errores = []
    advertencias = []

    # 1. Carpetas base requeridas
    for carpeta in CARPETAS_REQUERIDAS:
        ruta = categoria_path / carpeta

        if not ruta.exists():
            errores.append(f"Falta carpeta: {carpeta}/")
        elif not ruta.is_dir():
            errores.append(f"No es carpeta: {carpeta}/")

    img_root = categoria_path / "img"

    carpetas_act = []
    imagenes_sueltas = []
    carpetas_mal_nombradas = []
    carpetas_sin_principal = []
    carpetas_vacias = []
    archivos_raros_en_act = []

    if img_root.exists() and img_root.is_dir():
        for item in sorted(img_root.iterdir()):
            if item.is_file():
                if es_imagen(item):
                    imagenes_sueltas.append(item.name)
                else:
                    advertencias.append(f"Archivo no imagen en img/: {item.name}")

            elif item.is_dir():
                if PATRON_ACT.match(item.name):
                    carpetas_act.append(item)
                else:
                    carpetas_mal_nombradas.append(item.name)

        # 2. Revisar cada carpeta ACT
        for act_dir in carpetas_act:
            archivos = [p for p in act_dir.iterdir() if p.is_file()]

            if not archivos:
                carpetas_vacias.append(act_dir.name)
                continue

            principales = [
                act_dir / "principal.png",
                act_dir / "principal.jpg",
                act_dir / "principal.jpeg",
                act_dir / "principal.webp",
            ]

            if not any(p.exists() for p in principales):
                carpetas_sin_principal.append(act_dir.name)

            for archivo in archivos:
                if not es_imagen(archivo):
                    archivos_raros_en_act.append(f"{act_dir.name}/{archivo.name}")
                    continue

                stem = archivo.stem.lower()

                if stem == "principal":
                    continue

                if not PATRON_GALERIA.match(stem):
                    archivos_raros_en_act.append(f"{act_dir.name}/{archivo.name}")

    else:
        errores.append("Falta carpeta img/ o no es carpeta")

    return {
        "categoria": categoria_path.name,
        "errores": errores,
        "advertencias": advertencias,
        "carpetas_act": carpetas_act,
        "imagenes_sueltas": imagenes_sueltas,
        "carpetas_mal_nombradas": carpetas_mal_nombradas,
        "carpetas_sin_principal": carpetas_sin_principal,
        "carpetas_vacias": carpetas_vacias,
        "archivos_raros_en_act": archivos_raros_en_act,
    }


def imprimir_lista(titulo, items, limite=20):
    if not items:
        return

    print(f"\n  {titulo}: {len(items)}")

    for item in items[:limite]:
        print(f"    - {item}")

    if len(items) > limite:
        print(f"    ... y {len(items) - limite} más")


def main():
    if not CATEGORIAS_ROOT.exists():
        print(f"No existe la carpeta de categorías: {CATEGORIAS_ROOT}")
        return

    categorias = sorted(p for p in CATEGORIAS_ROOT.iterdir() if p.is_dir())

    print("\n=== DIAGNÓSTICO DE ESTRUCTURA DE CATEGORÍAS ===")
    print(f"Raíz: {CATEGORIAS_ROOT}")
    print(f"Categorías encontradas: {len(categorias)}")

    total_errores = 0
    total_advertencias = 0

    for categoria in categorias:
        resultado = revisar_categoria(categoria)

        errores = resultado["errores"]
        advertencias = resultado["advertencias"]

        total_errores += len(errores)
        total_advertencias += len(advertencias)

        total_act = len(resultado["carpetas_act"])
        total_sueltas = len(resultado["imagenes_sueltas"])
        total_mal = len(resultado["carpetas_mal_nombradas"])
        total_sin_principal = len(resultado["carpetas_sin_principal"])
        total_vacias = len(resultado["carpetas_vacias"])
        total_raros = len(resultado["archivos_raros_en_act"])

        estado = "OK"

        if errores:
            estado = "ERROR"
        elif (
            total_sueltas
            or total_mal
            or total_sin_principal
            or total_vacias
            or total_raros
            or advertencias
        ):
            estado = "ADVERTENCIA"

        print("\n" + "=" * 70)
        print(f"{resultado['categoria']}  [{estado}]")
        print("-" * 70)
        print(f"Carpetas ACT: {total_act}")
        print(f"Imágenes sueltas en img/: {total_sueltas}")
        print(f"Carpetas mal nombradas: {total_mal}")
        print(f"Carpetas ACT sin principal: {total_sin_principal}")
        print(f"Carpetas ACT vacías: {total_vacias}")
        print(f"Archivos raros dentro de ACT: {total_raros}")

        imprimir_lista("ERRORES", errores)
        imprimir_lista("ADVERTENCIAS", advertencias)
        imprimir_lista("Imágenes sueltas", resultado["imagenes_sueltas"])
        imprimir_lista("Carpetas mal nombradas", resultado["carpetas_mal_nombradas"])
        imprimir_lista(
            "Carpetas ACT sin principal", resultado["carpetas_sin_principal"]
        )
        imprimir_lista("Carpetas ACT vacías", resultado["carpetas_vacias"])
        imprimir_lista(
            "Archivos raros dentro de ACT", resultado["archivos_raros_en_act"]
        )

    print("\n" + "=" * 70)
    print("RESUMEN GENERAL")
    print("=" * 70)
    print(f"Categorías revisadas: {len(categorias)}")
    print(f"Errores de estructura base: {total_errores}")
    print(f"Advertencias generales: {total_advertencias}")
    print("\nNo se movió ningún archivo.")


if __name__ == "__main__":

    main()
