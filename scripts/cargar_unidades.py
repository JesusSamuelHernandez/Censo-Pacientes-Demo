"""
scripts/cargar_unidades.py — Carga masiva de unidades médicas desde Excel.

Uso:
    python scripts/cargar_unidades.py
    python scripts/cargar_unidades.py --archivo ruta/a/mi_archivo.xlsx

Columnas requeridas en el Excel:
    clues                 : Clave CLUES (ej. BCSSA004266) — PK, debe ser única.
    nombre_de_la_unidad   : Nombre completo de la unidad médica.
    id_entidad            : Identificador del estado (ej. BAJA_CALIFORNIA).

Columnas opcionales:
    categoria_gerencial   : Categoría (ej. HG, HE, CS).

Comportamiento:
    - Registros con CLUES ya existente en la BD se OMITEN (no se sobreescriben).
    - Al final imprime un resumen: insertados / omitidos / errores.
"""
import argparse
import os
import sys

# Asegurar que Python encuentre el paquete 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal, engine
from app.models import Base, UnidadMedica

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ARCHIVO_DEFAULT = os.path.join(os.path.dirname(__file__), "data", "unidades.xlsx")
COLUMNAS_REQUERIDAS = {"clues", "nombre_de_la_unidad", "id_entidad"}


def cargar_unidades(archivo: str) -> None:
    print(f"\n{'='*60}")
    print(f"  CARGA MASIVA — UNIDADES MÉDICAS")
    print(f"{'='*60}")
    print(f"Archivo : {archivo}")

    # 1. Leer Excel
    try:
        df = pd.read_excel(archivo, dtype=str)
    except FileNotFoundError:
        print(f"\n[ERROR] No se encontró el archivo: {archivo}")
        print("  Genera la plantilla ejecutando: python scripts/crear_plantillas_excel.py")
        sys.exit(1)

    # Normalizar nombres de columna: minúsculas y sin espacios
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # 2. Validar columnas requeridas
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        print(f"\n[ERROR] El Excel no tiene las columnas requeridas: {faltantes}")
        print(f"  Columnas encontradas: {list(df.columns)}")
        sys.exit(1)

    # Asegurar que existan las tablas
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    insertados = 0
    omitidos = 0
    errores = 0

    print(f"\nProcesando {len(df)} filas...\n")

    for idx, row in df.iterrows():
        fila_num = idx + 2  # +2 porque fila 1 es encabezado, idx es base-0

        # Limpiar y validar campos requeridos
        clues = str(row.get("clues", "")).strip().upper()
        nombre = str(row.get("nombre_de_la_unidad", "")).strip()
        id_entidad = str(row.get("id_entidad", "")).strip()
        categoria = str(row.get("categoria_gerencial", "")).strip() or None

        # Saltar filas vacías
        if not clues or clues == "NAN":
            print(f"  [OMITIDA] Fila {fila_num}: CLUES vacía.")
            omitidos += 1
            continue

        if not nombre or nombre == "NAN":
            print(f"  [ERROR]   Fila {fila_num} ({clues}): nombre_de_la_unidad vacío.")
            errores += 1
            continue

        if not id_entidad or id_entidad == "NAN":
            print(f"  [ERROR]   Fila {fila_num} ({clues}): id_entidad vacío.")
            errores += 1
            continue

        try:
            # Verificar si ya existe
            existe = db.query(UnidadMedica).filter(UnidadMedica.clues == clues).first()
            if existe:
                print(f"  [OMITIDA] Fila {fila_num}: CLUES '{clues}' ya existe.")
                omitidos += 1
                continue

            nueva = UnidadMedica(
                clues=clues,
                nombre_de_la_unidad=nombre,
                id_entidad=id_entidad,
                categoria_gerencial=categoria if categoria != "NAN" else None,
            )
            db.add(nueva)
            db.commit()
            print(f"  [OK]      Fila {fila_num}: '{clues}' — {nombre[:50]}")
            insertados += 1

        except Exception as e:
            db.rollback()
            print(f"  [ERROR]   Fila {fila_num} ({clues}): {e}")
            errores += 1

    db.close()

    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    print(f"  Insertados : {insertados}")
    print(f"  Omitidos   : {omitidos}  (ya existían o fila vacía)")
    print(f"  Errores    : {errores}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga masiva de unidades médicas desde Excel.")
    parser.add_argument(
        "--archivo",
        default=ARCHIVO_DEFAULT,
        help=f"Ruta al archivo Excel (default: {ARCHIVO_DEFAULT})",
    )
    args = parser.parse_args()
    cargar_unidades(args.archivo)
