from pathlib import Path
import json
import sys
from src.core.productos import ordenar_por_numero_inicial

ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config.json"


DEFAULT_CONFIG = {
    "env": "DEV",
    "categoria": "1-muebles_europeos_importados",
    "paper": "carta",
    "draw_guides": False,
    "debug": True,
}


def pausar():
    input("\nPresiona ENTER para continuar...")


def leer_opcion(mensaje="\nSelecciona opción: "):
    return input(mensaje).strip()


def cargar_config():
    if not CONFIG_FILE.exists():
        guardar_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        print("⚠ No se pudo leer config.json. Se usará configuración base.")
        config = DEFAULT_CONFIG.copy()

    for key, value in DEFAULT_CONFIG.items():
        config.setdefault(key, value)

    return config


def guardar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("\n✔ config.json actualizado.")


def mostrar_configuracion():
    config = cargar_config()

    print("\n--- CONFIGURACIÓN ACTUAL ---")
    print(f"Modo: {config.get('env')}")
    print(f"Categoría: {config.get('categoria')}")
    print(f"Papel: {config.get('paper')}")
    print(f"Guías de corte: {config.get('draw_guides')}")
    print(f"Debug: {config.get('debug')}")
    print(f"Archivo: {CONFIG_FILE}")


def listar_categorias():
    carpeta_categorias = ROOT / "data" / "categorias"

    if not carpeta_categorias.exists():
        return []

    categorias = [
        p.name
        for p in carpeta_categorias.iterdir()
        if p.is_dir()
    ]

    return ordenar_por_numero_inicial(categorias)


def cambiar_modo():
    config = cargar_config()

    while True:
        print("\n--- CAMBIAR MODO ---")
        print("1. DEV")
        print("2. PROD")
        print("0. Volver")

        opcion = leer_opcion()

        if opcion == "1":
            config["env"] = "DEV"
            guardar_config(config)
            return

        if opcion == "2":
            config["env"] = "PROD"
            guardar_config(config)
            return

        if opcion == "0":
            return

        print("Opción inválida.")


def cambiar_categoria():
    config = cargar_config()
    categorias = listar_categorias()

    if not categorias:
        print("No encontré carpetas dentro de categorias/.")
        return

    while True:
        print("\n--- CAMBIAR CATEGORÍA ---")

        for i, categoria in enumerate(categorias, start=1):
            actual = "  ← actual" if categoria == config.get("categoria") else ""
            print(f"{i}. {categoria}{actual}")

        print("0. Volver")

        opcion = leer_opcion()

        if opcion == "0":
            return

        try:
            indice = int(opcion)
        except ValueError:
            print("Opción inválida.")
            continue

        if indice < 1 or indice > len(categorias):
            print("Opción fuera de rango.")
            continue

        config["categoria"] = categorias[indice - 1]
        guardar_config(config)
        return


def cambiar_papel():
    config = cargar_config()

    while True:
        print("\n--- CAMBIAR PAPEL ---")
        print("1. carta")
        print("2. a4")
        print("0. Volver")

        opcion = leer_opcion()

        if opcion == "1":
            config["paper"] = "carta"
            guardar_config(config)
            return

        if opcion == "2":
            config["paper"] = "a4"
            guardar_config(config)
            return

        if opcion == "0":
            return

        print("Opción inválida.")


def alternar_guias():
    config = cargar_config()

    actual = bool(config.get("draw_guides", False))
    config["draw_guides"] = not actual

    guardar_config(config)

    print(f"Guías de corte ahora: {config['draw_guides']}")


def alternar_debug():
    config = cargar_config()

    actual = bool(config.get("debug", True))
    config["debug"] = not actual

    guardar_config(config)

    print(f"Debug ahora: {config['debug']}")


def ejecutar_texto(args=None):
    from src.texto.procesador import main as texto_main

    args = args or []

    argv_original = sys.argv[:]

    try:
        sys.argv = ["procesador.py"] + args
        texto_main()
    finally:
        sys.argv = argv_original


def menu_configuracion():
    while True:
        print("\n--- CONFIGURACIÓN ---")
        print("1. Ver configuración actual")
        print("2. Cambiar modo DEV/PROD")
        print("3. Cambiar categoría activa")
        print("4. Cambiar papel de impresión")
        print("5. Activar/desactivar guías")
        print("6. Activar/desactivar debug")
        print("0. Volver al menú principal")

        opcion = leer_opcion()

        if opcion == "1":
            mostrar_configuracion()
            pausar()

        elif opcion == "2":
            cambiar_modo()
            pausar()

        elif opcion == "3":
            cambiar_categoria()
            pausar()

        elif opcion == "4":
            cambiar_papel()
            pausar()

        elif opcion == "5":
            alternar_guias()
            pausar()

        elif opcion == "6":
            alternar_debug()
            pausar()

        elif opcion == "0":
            return

        else:
            print("Opción inválida.")
            pausar()


def procesar_txt_json():
    while True:
        print("\n--- PROCESAR TXT A JSON ---")
        print("1. Actualizar todo")
        print("2. Actualizar un ID")
        print("3. Actualizar varios IDs")
        print("0. Volver al menú principal")

        opcion = leer_opcion()

        if opcion == "1":
            ejecutar_texto()
            pausar()

        elif opcion == "2":
            id_unico = input("ID a actualizar: ").strip()

            if not id_unico:
                print("No escribiste ID.")
                pausar()
                continue

            ejecutar_texto(["--id", id_unico])
            pausar()

        elif opcion == "3":
            ids = input("IDs separados por coma: ").strip()

            if not ids:
                print("No escribiste IDs.")
                pausar()
                continue

            ejecutar_texto(["--ids", ids])
            pausar()

        elif opcion == "0":
            return

        else:
            print("Opción inválida.")
            pausar()


def generar_etiquetas():
    from src.etiquetas.generar import procesar_todo as etiquetas_main

    etiquetas_main()


def preparar_impresion():
    from src.etiquetas.impresion import main as impresion_main

    impresion_main()


def validar_proyecto():
    from src.core.validacion import main as validar_proyecto_main

    validar_proyecto_main()


def generar_catalogo():
    from src.catalogo.menu import main as catalogo_main

    catalogo_main()


def validar_catalogo():
    from src.catalogo.validacion import main as validar_catalogo_main

    validar_catalogo_main()


def mostrar_menu():
    config = cargar_config()

    print(
        f"Modo: {config.get('env')} | "
        f"Categoría: {config.get('categoria')}"
    )
    print("\n=== SISTEMA DE ETIQUETAS TECI ===")

    print("1. Procesar TXT a JSON")
    print("2. Generar etiquetas")
    print("3. Preparar PDF de impresión")
    print("4. Generar catálogo / exportar PDF")
    print("5. Validar proyecto")
    print("6. Validar catálogo")
    print("7. Configuración")
    print("0. Salir")


def main():
    while True:
        mostrar_menu()
        opcion = leer_opcion()

        if opcion == "1":
            procesar_txt_json()

        elif opcion == "2":
            generar_etiquetas()
            pausar()

        elif opcion == "3":
            preparar_impresion()
            pausar()

        elif opcion == "4":
            generar_catalogo()
            pausar()

        elif opcion == "5":
            validar_proyecto()
            pausar()

        elif opcion == "6":
            validar_catalogo()
            pausar()
        elif opcion == "7":
            menu_configuracion()

        elif opcion == "0":
            print("Saliendo...")
            break

        else:
            print("Opción inválida.")
            pausar()


if __name__ == "__main__":
    main()
