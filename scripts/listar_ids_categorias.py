from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORIAS_ROOT = PROJECT_ROOT / "data" / "categorias"

PATRON_ACT = re.compile(r"^ACT-(\d{4})$", re.IGNORECASE)
EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".webp"}


def es_imagen(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in EXTENSIONES_IMAGEN


def existe_principal(carpeta_act: Path) -> bool:
    for ext in EXTENSIONES_IMAGEN:
        if (carpeta_act / f"principal{ext}").exists():
            return True
    return False


def contar_imagenes(carpeta_act: Path) -> int:
    if not carpeta_act.exists():
        return 0

    return len([p for p in carpeta_act.iterdir() if es_imagen(p)])


def formatear_ids(numeros):
    if not numeros:
        return "Ninguno"

    return ", ".join(f"ACT-{n:04d}" for n in sorted(numeros))


def obtener_categorias():
    if not CATEGORIAS_ROOT.exists():
        return []

    return sorted([p for p in CATEGORIAS_ROOT.iterdir() if p.is_dir()])


def analizar_categoria(categoria_path: Path):
    img_dir = categoria_path / "img"

    resultado = {
        "categoria": categoria_path.name,
        "errores": [],
        "existentes": [],
        "listos": [],
        "incompletos": [],
        "libres": [],
        "proximo": "ACT-0001",
    }

    if not img_dir.exists() or not img_dir.is_dir():
        resultado["errores"].append("No existe carpeta img/")
        return resultado

    usados = set()

    for item in sorted(img_dir.iterdir()):
        if not item.is_dir():
            continue

        match = PATRON_ACT.match(item.name)

        if not match:
            continue

        numero = int(match.group(1))
        usados.add(numero)

        total_imgs = contar_imagenes(item)
        principal = existe_principal(item)

        resultado["existentes"].append(numero)

        if total_imgs > 0 and principal:
            resultado["listos"].append(numero)
        else:
            detalle = []

            if total_imgs == 0:
                detalle.append("vacío")

            if not principal:
                detalle.append("sin principal")

            resultado["incompletos"].append(
                {
                    "numero": numero,
                    "id_catalogo": f"ACT-{numero:04d}",
                    "estado": ", ".join(detalle) if detalle else "incompleto",
                    "imagenes": total_imgs,
                }
            )

    if usados:
        mayor = max(usados)

        resultado["libres"] = [n for n in range(1, mayor + 1) if n not in usados]

        siguiente = 1
        while siguiente in usados:
            siguiente += 1

        resultado["proximo"] = f"ACT-{siguiente:04d}"

    return resultado


def imprimir_resultado(resultado, vista="todo"):
    print("\n" + "=" * 78)
    print(resultado["categoria"])
    print("=" * 78)

    if resultado["errores"]:
        print("Estado: ERROR")
        for err in resultado["errores"]:
            print(f"  - {err}")
        return

    print("Estado: OK")

    if vista in ["todo", "existentes"]:
        print("\n--- IDs existentes ---")
        print(formatear_ids(resultado["existentes"]))

    if vista in ["todo", "listos"]:
        print("\n--- IDs listos ---")
        print(formatear_ids(resultado["listos"]))

    if vista in ["todo", "incompletos"]:
        print("\n--- IDs incompletos ---")
        if not resultado["incompletos"]:
            print("Ninguno")
        else:
            for item in sorted(resultado["incompletos"], key=lambda x: x["numero"]):
                print(
                    f"{item['id_catalogo']} | "
                    f"{item['estado']} | "
                    f"{item['imagenes']} imagen(es)"
                )

    if vista in ["todo", "libres"]:
        print("\n--- IDs libres ---")
        print(formatear_ids(resultado["libres"]))

    if vista in ["todo", "proximo"]:
        print("\n--- Próximo ID sugerido ---")
        print(resultado["proximo"])


def mostrar_categorias(categorias):
    print("\n--- CATEGORÍAS DISPONIBLES ---")

    for i, categoria in enumerate(categorias, start=1):
        print(f"{i}. {categoria.name}")

    print("0. Volver")


def pedir_indices(categorias):
    entrada = input("\nSelecciona número(s), ejemplo 1 o 1,3,5: ").strip()

    if entrada == "0":
        return []

    partes = entrada.replace(",", " ").split()
    indices = []

    for parte in partes:
        if not parte.isdigit():
            print(f"Valor inválido: {parte}")
            continue

        numero = int(parte)

        if numero < 1 or numero > len(categorias):
            print(f"Número fuera de rango: {numero}")
            continue

        indices.append(numero - 1)

    return indices


def pedir_vista():
    while True:
        print("\n--- QUÉ QUIERES VER ---")
        print("1. Todo")
        print("2. Solo IDs existentes")
        print("3. Solo IDs listos")
        print("4. Solo IDs incompletos")
        print("5. Solo IDs libres")
        print("6. Solo próximo ID")
        print("0. Volver")

        opcion = input("\nSelecciona opción: ").strip()

        if opcion == "1":
            return "todo"
        if opcion == "2":
            return "existentes"
        if opcion == "3":
            return "listos"
        if opcion == "4":
            return "incompletos"
        if opcion == "5":
            return "libres"
        if opcion == "6":
            return "proximo"
        if opcion == "0":
            return None

        print("Opción inválida.")


def ver_una_categoria(categorias):
    mostrar_categorias(categorias)
    indices = pedir_indices(categorias)

    if not indices:
        return

    vista = pedir_vista()

    if not vista:
        return

    categoria = categorias[indices[0]]
    resultado = analizar_categoria(categoria)
    imprimir_resultado(resultado, vista=vista)


def ver_varias_categorias(categorias):
    mostrar_categorias(categorias)
    indices = pedir_indices(categorias)

    if not indices:
        return

    vista = pedir_vista()

    if not vista:
        return

    for indice in indices:
        categoria = categorias[indice]
        resultado = analizar_categoria(categoria)
        imprimir_resultado(resultado, vista=vista)


def ver_todas_categorias(categorias):
    vista = pedir_vista()

    if not vista:
        return

    for categoria in categorias:
        resultado = analizar_categoria(categoria)
        imprimir_resultado(resultado, vista=vista)


def main():
    categorias = obtener_categorias()

    if not categorias:
        print(f"No encontré categorías en: {CATEGORIAS_ROOT}")
        return

    while True:
        print("\n=== IDS POR CATEGORÍA ===")
        print("1. Ver una categoría")
        print("2. Ver varias categorías")
        print("3. Ver todas las categorías")
        print("0. Salir")

        opcion = input("\nSelecciona opción: ").strip()

        if opcion == "1":
            ver_una_categoria(categorias)

        elif opcion == "2":
            ver_varias_categorias(categorias)

        elif opcion == "3":
            ver_todas_categorias(categorias)

        elif opcion == "0":
            print("Saliendo...")
            break

        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()
