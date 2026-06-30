# Preparacion para Produccion

Este documento describe lo que debe quedar listo en la aplicacion antes de que el equipo de infraestructura haga el despliegue final. El alcance de este repositorio es codigo, configuracion, migraciones y validaciones de conexion; no incluye provisionar servidores, DNS, TLS, firewall, backups ni monitoreo de infraestructura.

## Base de datos externa

La aplicacion espera una base PostgreSQL externa. La forma recomendada es usar variables separadas para evitar errores cuando la contrasena contiene caracteres especiales.

Formato recomendado:

```env
DB_HOST=host
DB_PORT=5432
DB_NAME=censo_pacientes
DB_USER=usuario
DB_PASSWORD=password
```

Alternativa si infraestructura entrega una URL ya codificada:

```env
DATABASE_URL=postgresql://usuario:password-codificado@host:5432/censo_pacientes
```

Si `DB_HOST`, `DB_NAME`, `DB_USER` o `DB_PASSWORD` estan definidas, la aplicacion usa el modo de variables separadas y no depende de `DATABASE_URL`.

Si el servidor requiere SSL, definir tambien:

```env
DATABASE_SSL_MODE=require
DATABASE_SSL_ROOT_CERT=/ruta/segura/ca.crt
DATABASE_CONNECT_TIMEOUT=10
```

Valores comunes de `DATABASE_SSL_MODE`: `prefer`, `require`, `verify-ca`, `verify-full`. Si infraestructura requiere certificado CA, debe montarlo fuera del repositorio y apuntar `DATABASE_SSL_ROOT_CERT` a esa ruta.

Si el usuario o contrasena de PostgreSQL contiene caracteres especiales como `/`, `?`, `#`, `@`, `%`, espacios o comas, usa variables separadas o codifica esos caracteres antes de formar `DATABASE_URL`.

## Variables requeridas

```env
DB_HOST=host
DB_PORT=5432
DB_NAME=censo_pacientes
DB_USER=usuario
DB_PASSWORD=password
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
DATABASE_SSL_ROOT_CERT=
DATABASE_CONNECT_TIMEOUT=10
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
WEB_CONCURRENCY=2
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

## Validacion segura de configuracion

Antes de entregar variables a infraestructura, ejecutar:

```bash
python tools/validate_production_config.py
```

Para validar tambien conectividad real a PostgreSQL:

```bash
python tools/validate_production_config.py --check-db
```

El validador no imprime credenciales ni secretos. Solo indica si las variables estan presentes, tienen formato esperado y, con `--check-db`, si `SELECT 1` responde correctamente.

## Arranque backend

Comando simple para desarrollo o validacion puntual:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Comando recomendado para produccion si infraestructura usa Gunicorn:

```bash
gunicorn -w ${WEB_CONCURRENCY:-2} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000}
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

El `frontend/Dockerfile.prod` ya genera el build con Node y lo sirve desde Nginx. Si se usa Docker, `VITE_API_BASE_URL` debe enviarse como build arg para que Vite lo incorpore al build estatico.

El cliente frontend falla de forma explicita si `VITE_API_BASE_URL` no esta definida, para evitar llamadas a un backend `undefined`.

## Empaquetado Docker

Existen `.dockerignore` en la raiz y en `frontend/` para evitar copiar secretos, entornos virtuales, `node_modules`, builds previos y caches dentro de las imagenes.

## Reportes y volumen de datos

El endpoint `/reportes/resumen-detallado` esta paginado para evitar respuestas enormes en memoria. Parametros disponibles:

```text
pagina=1
por_pagina=500
```

`por_pagina` acepta hasta 2000 registros por respuesta. La respuesta incluye `total_registros`, `registros_devueltos` y `hay_mas`. Para exportaciones muy grandes, infraestructura o producto debe definir si se permite paginar manualmente o si se implementara una exportacion asincrona posterior.

La busqueda por nombre respeta RBAC: responsables de unidad solo buscan en su unidad, administradores estatales solo en su entidad y super administradores en todo el padron.

## Checklist de entrega

- `DATABASE_URL` valida contra el servidor PostgreSQL externo.
- `python tools/validate_production_config.py` termina correctamente sin imprimir secretos.
- `FERNET_KEY` generada, respaldada y no expuesta en el repo.
- `JWT_SECRET_KEY` generada con minimo 32 caracteres.
- `FRONTEND_URL` contiene solo dominios permitidos para CORS.
- `VITE_API_BASE_URL` apunta a la API productiva.
- `alembic upgrade head` ejecuta correctamente.
- `python -m pytest tests` ejecuta las pruebas smoke.
- `npm run build` ejecuta correctamente en `frontend/` con `VITE_API_BASE_URL` definido.
- `/health` responde `status: ok` y `database: ok`.
- Login y cambio de password temporal funcionan.
- RBAC validado para `SUPER_ADMIN`, `ADMIN_ESTATAL` y `RESPONSABLE_UNIDAD`.
- Busqueda por nombre validada para que respete el alcance de cada rol.
- Reporte detallado validado con paginacion y volumen de datos realista.
- Datos sensibles se guardan cifrados en PostgreSQL.

## Fuera de alcance de la aplicacion

- Provisionamiento del servidor.
- Firewall y reglas de red.
- Certificados TLS y terminacion HTTPS.
- Backups y pruebas de restauracion de PostgreSQL.
- Monitoreo de CPU, RAM, disco y logs centralizados.
- Rotacion institucional de credenciales.
