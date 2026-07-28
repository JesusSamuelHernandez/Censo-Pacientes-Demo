# Censo de Pacientes — Medicamentos de Alto Costo

Sistema web para el registro y seguimiento de pacientes con prescripción de medicamentos de alto costo del IMSS Bienestar.

- **Backend:** FastAPI (Python 3.11) + PostgreSQL
- **Frontend:** React 19 + Vite
- **Auth:** JWT + bcrypt
- **Cifrado de datos sensibles:** Fernet (columnas de nombre/CURP)

---

## Requisitos del servidor

| Componente | Versión mínima |
|---|---|
| Python | 3.11 |
| Node.js | 18 |
| PostgreSQL | 14 |

> Para correr con Docker solo se necesita Docker Desktop 24+.

---

## Arranque local (desarrollo)

Ver guía completa: [docs/arranque_local.md](docs/arranque_local.md)

Pasos rápidos:

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env           # Luego editar .env con los valores reales

# 4. Aplicar migraciones
alembic upgrade head

# 5. Crear usuario administrador inicial
python create_admin.py

# 6. Levantar backend
uvicorn app.main:app --reload  # http://localhost:8001
```

En otra terminal:

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

---

## Variables de entorno

Copiar `.env.example` como `.env` y completar:

| Variable | Descripción |
|---|---|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Conexión a PostgreSQL (recomendado sobre `DATABASE_URL` si la contraseña tiene caracteres especiales) |
| `DATABASE_SSL_MODE` | `disable` en local; en producción al menos `require` (nunca `prefer`, permite continuar sin cifrar), idealmente `verify-full` con `DATABASE_SSL_ROOT_CERT` |
| `JWT_SECRET_KEY` | Clave secreta JWT. Mínimo 32 caracteres. Generar con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FERNET_KEY` | Clave de cifrado de datos. Generar **una sola vez** con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **No cambiar después si ya hay datos.** |
| `HASH_KEY` | Clave del HMAC-SHA256 de `curp_hash`/`cedula_hash` (búsquedas sin descifrar). Distinta de `FERNET_KEY`. Generar **una sola vez** con `python -c "import secrets; print(secrets.token_urlsafe(32))"`. **No cambiar después si ya hay datos** sin remigrar los hashes existentes. |
| `FRONTEND_URL` | Origen(es) permitidos para CORS, separados por coma. Ej: `https://mi-frontend.com` |
| `JWT_EXPIRE_HOURS` | Tiempo de vida del token (default: 8) |

El frontend necesita su propio archivo `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8001   # URL del backend
```

---

## Base de datos

La app usa **Alembic** para versionar el esquema. Una vez configurado `.env`:

```bash
alembic upgrade head
```

Esto crea o actualiza todas las tablas necesarias. Si la base ya existe con un esquema anterior (sin `alembic_version`), aplicar primero la migración de compatibilidad:

```sql
-- solo si la base tiene esquema viejo (tabla "recetas" en lugar de "registros")
psql -U usuario -d nombre_bd -f tools/migrate_legacy_schema_20260623.sql
```

Luego correr `alembic upgrade head` normalmente.

---

## Carga inicial de catálogos

Solo la primera vez que se levanta el sistema:

```bash
python scripts/cargar_unidades.py       # Unidades médicas
python scripts/cargar_medicamentos.py   # Catálogo CNIS
```

Los archivos Excel de datos deben colocarse en `scripts/data/` antes de ejecutarlos.

---

## Validar configuración antes de desplegar

```bash
python tools/validate_production_config.py --check-db
```

Verifica variables de entorno, formatos de clave y conexión real a la base. No imprime secretos.

---

## Despliegue en producción (Render / Railway)

Ver guía completa: [docs/despliegue_railway.md](docs/despliegue_railway.md)

Resumen:

1. Configurar las variables de entorno del servidor (nunca subir `.env` al repositorio).
2. Ejecutar `alembic upgrade head` contra la base de producción antes o durante el arranque.
3. Arrancar el backend con Gunicorn:
   ```bash
   gunicorn -w $WEB_CONCURRENCY -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
   ```
4. Compilar el frontend y servir la carpeta `dist/`:
   ```bash
   cd frontend && npm run build
   ```
5. Configurar `FRONTEND_URL` en el backend con la URL real del frontend.
6. Configurar `VITE_API_BASE_URL` en el frontend con la URL real del backend.

> `render.yaml` contiene la configuración completa para Render. Para Railway, importar el repositorio y configurar variables manualmente.

---

## Pruebas

```bash
pytest tests/
```

---

## Arquitectura

- [Arquitectura del backend](docs/arquitectura_backend.md)
- [Arquitectura del frontend](docs/arquitectura_frontend.md)
- [Blueprint de la aplicación](docs/blueprint_v6.md)
