#!/bin/bash
# Script para inicializar la base de datos en el primer despliegue

echo "Esperando a que PostgreSQL esté lista..."
sleep 10

echo "Creando usuario administrador..."
python create_admin.py 2>/dev/null || true

echo "Iniciando servidor..."
# Usar PORT si existe, sino usar 8000
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"