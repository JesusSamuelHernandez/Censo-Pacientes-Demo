#!/bin/bash
# Script de arranque del backend.

set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
	echo "Aplicando migraciones de base de datos..."
	alembic upgrade head
fi

if [ "${CREATE_ADMIN_ON_STARTUP:-false}" = "true" ]; then
	echo "Creando usuario administrador inicial..."
	python create_admin.py
fi

echo "Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"