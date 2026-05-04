"""
scripts/cargar_medicamentos.py — Carga masiva de medicamentos desde Excel.

Uso:
    python scripts/cargar_medicamentos.py
    python scripts/cargar_medicamentos.py --archivo ruta/a/mi_archivo.xlsx
    python scripts/cargar_medicamentos.py --actualizar

Columnas requeridas en el Excel:
    clave_cnis    : Clave CNIS del medicamento (ej. 010.000.4155.00) — PK única.
    descripcion   : Nombre/descripción del medicamento.

Columnas opcionales:
    grupo         : Grupo terapéutico (ej. BIOLOGICOS, ONCOLOGICOS).
    tipo_clave    : Tipo de clave (ej. CUADRO BASICO, GASTOS CATASTROFICOS).

Comportamiento:
    - Sin --actualizar : registros con clave_cnis ya existente se OMITEN (solo inserta nuevos).
    - Con --actualizar : registros existentes se ACTUALIZAN (descripcion, grupo, tipo_clave).
    - Al final imprime un resumen: insertados / actualizados / omitidos / errores.
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal, engine
from app.models import Base, CatMedicamento

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ARCHIVO_DEFAULT = os.path.join(os.path.dirname(__file__), "data", "medicamentos.xlsx")
COLUMNAS_REQUERIDAS = {"clave_cnis", "descripcion"}


def cargar_medicamentos(archivo: str, actualizar: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"  CARGA MASIVA — CATÁLOGO DE MEDICAMENTOS")
    print(f"{'='*60}")
    print(f"Archivo   : {archivo}")
    print(f"Modo      : {'INSERTAR + ACTUALIZAR existentes' if actualizar else 'SOLO INSERTAR nuevos'}")

    # 1. Leer Excel
    try:
        df = pd.read_excel(archivo, dtype=str)
    except FileNotFoundError:
        print(f"\n[ERROR] No se encontró el archivo: {archivo}")
        print("  Genera la plantilla ejecutando: python scripts/crear_plantillas_excel.py")
        sys.exit(1)

    # Normalizar nombres de columna
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # 2. Validar columnas requeridas
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        print(f"\n[ERROR] El Excel no tiene las columnas requeridas: {faltantes}")
        print(f"  Columnas encontradas: {list(df.columns)}")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    insertados = 0
    actualizados = 0
    omitidos = 0
    errores = 0

    print(f"\nProcesando {len(df)} filas...\n")

    for idx, row in df.iterrows():
        fila_num = idx + 2

        clave = str(row.get("clave_cnis", "")).strip()
        descripcion = str(row.get("descripcion", "")).strip()
        grupo = str(row.get("grupo", "")).strip() or None
        tipo_clave = str(row.get("tipo_clave", "")).strip() or None

        # Saltar filas vacías
        if not clave or clave == "NAN":
            print(f"  [OMITIDA] Fila {fila_num}: clave_cnis vacía.")
            omitidos += 1
            continue

        if not descripcion or descripcion == "NAN":
            print(f"  [ERROR]   Fila {fila_num} ({clave}): descripción vacía.")
            errores += 1
            continue

        try:
            existe = db.query(CatMedicamento).filter(
                CatMedicamento.clave_cnis == clave
            ).first()

            if existe:
                if actualizar:
                    existe.descripcion = descripcion
                    existe.grupo = grupo if grupo != "NAN" else None
                    existe.tipo_clave = tipo_clave if tipo_clave != "NAN" else None
                    db.commit()
                    print(f"  [ACTUALIZ] Fila {fila_num}: '{clave}' — {descripcion[:50]}")
                    actualizados += 1
                else:
                    print(f"  [OMITIDA] Fila {fila_num}: clave '{clave}' ya existe.")
                    omitidos += 1
                continue

            nuevo = CatMedicamento(
                clave_cnis=clave,
                descripcion=descripcion,
                grupo=grupo if grupo != "NAN" else None,
                tipo_clave=tipo_clave if tipo_clave != "NAN" else None,
                es_activo=True,
            )
            db.add(nuevo)
            db.commit()
            print(f"  [OK]      Fila {fila_num}: '{clave}' — {descripcion[:50]}")
            insertados += 1

        except Exception as e:
            db.rollback()
            print(f"  [ERROR]   Fila {fila_num} ({clave}): {e}")
            errores += 1

    db.close()

    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    print(f"  Insertados  : {insertados}")
    print(f"  Actualizados: {actualizados}")
    print(f"  Omitidos    : {omitidos}  (ya existían o fila vacía)")
    print(f"  Errores     : {errores}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga masiva de medicamentos desde Excel.")
    parser.add_argument(
        "--archivo",
        default=ARCHIVO_DEFAULT,
        help=f"Ruta al archivo Excel (default: {ARCHIVO_DEFAULT})",
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Actualiza descripcion, grupo y tipo_clave de claves que ya existen en la BD.",
    )
    args = parser.parse_args()
    cargar_medicamentos(args.archivo, actualizar=args.actualizar)
