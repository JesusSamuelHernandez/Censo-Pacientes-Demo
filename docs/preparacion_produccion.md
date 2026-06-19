# Preparacion para Produccion

Este documento describe lo que debe quedar listo en la aplicacion antes de que el equipo de infraestructura haga el despliegue final. El alcance de este repositorio es codigo, configuracion, migraciones y validaciones de conexion; no incluye provisionar servidores, DNS, TLS, firewall, backups ni monitoreo de infraestructura.

## Base de datos externa

La aplicacion espera una base PostgreSQL accesible mediante `DATABASE_URL`.

Formato base:

```env
DATABASE_URL=postgresql://usuario:password@host:5432/censo_pacientes
```

Si el servidor requiere SSL, definir tambien:

```env
DATABASE_SSL_MODE=require
```

Valores comunes de `DATABASE_SSL_MODE`: `prefer`, `require`, `verify-ca`, `verify-full`. Si infraestructura requiere certificado CA, debe montarlo fuera del repositorio y definir el mecanismo de conexion correspondiente.

## Variables requeridas

```env
DATABASE_URL=postgresql://usuario:password@host:5432/censo_pacientes
JWT_SECRET_KEY=<clave-aleatoria-minimo-32-caracteres>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
FERNET_KEY=<clave-fernet-generada-una-sola-vez>
FRONTEND_URL=https://frontend.dominio.gob.mx
VITE_API_BASE_URL=https://api.dominio.gob.mx
```

`FERNET_KEY` es critica: si se pierde o cambia, los datos cifrados existentes no podran descifrarse. Debe respaldarse en el gestor de secretos institucional, no en el repositorio.

## Variables opcionales

```env
DATABASE_SSL_MODE=prefer
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
RUN_MIGRATIONS=false
CREATE_ADMIN_ON_STARTUP=false
```

`RUN_MIGRATIONS=true` solo debe usarse si el flujo de despliegue decide que el contenedor aplique migraciones al arrancar. La opcion preferida es que infraestructura ejecute `alembic upgrade head` como paso separado y controlado.

`CREATE_ADMIN_ON_STARTUP=true` solo debe usarse en una inicializacion controlada. Para produccion, se recomienda crear usuarios administrativos mediante un procedimiento definido y auditable.

## Migraciones

Antes de iniciar la API contra una base vacia o nueva version de esquema:

```bash
alembic upgrade head
```

La configuracion de Alembic lee `DATABASE_URL` desde variables de entorno. No editar `alembic.ini` para guardar credenciales.

## Arranque backend

Comando simple compatible con el contenedor actual:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Opcion productiva si infraestructura usa Gunicorn:

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000}
```

El numero de workers debe ajustarse segun CPU/RAM disponibles y limite de conexiones de PostgreSQL.

## Build frontend

El frontend debe compilarse con `VITE_API_BASE_URL` apuntando al backend publico:

```bash
cd frontend
npm install
npm run build
```

El resultado `frontend/dist` puede servirse con Nginx u otro servidor estatico definido por infraestructura.

## Checklist de entrega

- `DATABASE_URL` valida contra el servidor PostgreSQL externo.
- `FERNET_KEY` generada, respaldada y no expuesta en el repo.
- `JWT_SECRET_KEY` generada con minimo 32 caracteres.
- `FRONTEND_URL` contiene solo dominios permitidos para CORS.
- `VITE_API_BASE_URL` apunta a la API productiva.
- `alembic upgrade head` ejecuta correctamente.
- `/health` responde `status: ok` y `database: ok`.
- Login y cambio de password temporal funcionan.
- RBAC validado para `SUPER_ADMIN`, `ADMIN_ESTATAL` y `RESPONSABLE_UNIDAD`.
- Datos sensibles se guardan cifrados en PostgreSQL.

## Fuera de alcance de la aplicacion

- Provisionamiento del servidor.
- Firewall y reglas de red.
- Certificados TLS y terminacion HTTPS.
- Backups y pruebas de restauracion de PostgreSQL.
- Monitoreo de CPU, RAM, disco y logs centralizados.
- Rotacion institucional de credenciales.
