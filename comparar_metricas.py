import os
import re
from pathlib import Path
import argparse

# --- Configuración ---
PATRON_FECHA = re.compile(r"(\d{8}_\d{6})\.txt$")


def extraer_urls(path_txt):
    """Lee un archivo txt y devuelve un conjunto de URLs."""
    urls = set()
    with open(path_txt, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('-'):
                # Quitar el prefijo '-\t' o '- ' y obtener solo la URL
                url = line.lstrip('-\t ').strip()
                urls.add(url)
    return urls


def listar_archivos(directorio):
    """Obtiene todos los archivos .txt válidos ordenados por fecha."""
    archivos = []
    for entry in os.listdir(directorio):
        if PATRON_FECHA.match(entry):
            archivos.append(entry)
    # Orden cronológico
    archivos.sort()
    return [Path(directorio) / a for a in archivos]


def comparar_archivos(archivos):
    """Compara los conjuntos de URLs entre archivos consecutivos."""
    datasets = [(archivo.name, extraer_urls(archivo)) for archivo in archivos]

    for i in range(1, len(datasets)):
        nombre_anterior, urls_prev = datasets[i - 1]
        nombre_actual, urls_curr = datasets[i]

        nuevas = urls_curr - urls_prev
        eliminadas = urls_prev - urls_curr
        interseccion = urls_curr & urls_prev

        print(f"\nComparando {nombre_anterior}  ➜  {nombre_actual}")
        print(f"  URLs totales: {len(urls_prev)} ➜ {len(urls_curr)}")
        print(f"  Sin cambios: {len(interseccion)}")
        print(f"  Nuevas: {len(nuevas)}")
        for u in sorted(nuevas):
            print(f"    + {u}")
        print(f"  Eliminadas: {len(eliminadas)}")
        for u in sorted(eliminadas):
            print(f"    - {u}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compara archivos de métricas generados por el crawler"
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Directorio que contiene los archivos .txt de métricas a comparar",
    )

    args = parser.parse_args()

    directorio = args.dir

    if not os.path.isdir(directorio):
        print(f"Error: El directorio '{directorio}' no existe o no es válido.")
        exit(1)

    archivos_txt = listar_archivos(directorio)

    if len(archivos_txt) < 2:
        print("Se necesitan al menos dos archivos para comparar.")
    else:
        comparar_archivos(archivos_txt)
