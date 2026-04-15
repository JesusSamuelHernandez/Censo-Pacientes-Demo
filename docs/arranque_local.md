# Arranque local — Medicamentos de Alto Costo

Guía para levantar el sistema completo (backend + frontend) en un equipo de desarrollo.

---

## Requisitos previos

| Herramienta | Versión mínima |
|---|---|
| Python | 3.11 |
| Node.js | 18 |
| PostgreSQL | 14 |
| Git | cualquiera |

---

## 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd Censo_de_pacientes_01
```

---

## 2. Backend (FastAPI)

### 2.1 Crear y activar entorno virtual

```bash
# Crear el entorno
python -m venv venv

# Activar en Windows
venv\Scripts\activate

# Activar en macOS/Linux
source venv/bin/activate
```

### 2.2 Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2.3 Configurar variables de entorno

Copia el archivo de ejemplo y rellena los valores reales:

```bash
cp .env.example .env
```

Edita `.env` con los datos de tu entorno:

```env
DATABASE_URL=postgresql://usuario:password@localhost:5432/censo_pacientes
JWT_SECRET_KEY=<clave generada con el comando de abajo>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
FERNET_KEY=<clave generada con el comando de abajo>
```

Para generar `JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Para generar `FERNET_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **Importante:** una vez que la BD tenga datos cifrados, **no cambies** `FERNET_KEY`. Los datos no podrán descifrarse con una clave diferente.

### 2.4 Crear la base de datos en PostgreSQL

```sql
CREATE DATABASE censo_pacientes;
```

### 2.5 Iniciar el servidor

```bash
uvicorn app.main:app --reload
```

El backend queda disponible en `http://localhost:8000`.  
Documentación interactiva: `http://localhost:8000/docs`

### 2.6 Crear el usuario Super Administrador (solo la primera vez)

```bash
python create_admin.py
```

---

## 3. Cargar catálogos iniciales (solo la primera vez)

Los Excel de unidades y medicamentos deben estar en `scripts/data/`.

```bash
# Cargar unidades médicas (~8 000 registros)
python scripts/cargar_unidades.py

# Cargar medicamentos CNIS (24 claves)
python scripts/cargar_medicamentos.py
```

---

## 4. Frontend (React + Vite)

### 4.1 Instalar dependencias

Solo es necesario la primera vez, o cuando cambie `package.json`:

```bash
cd frontend
npm install
```

### 4.2 Iniciar el servidor de desarrollo

```bash
npm run dev
```

El frontend queda disponible en `http://localhost:5173`.

---

## 5. Orden de arranque en el día a día

Cada vez que vayas a trabajar con el sistema:

```
1. Asegúrate de que PostgreSQL está corriendo
2. Activa el entorno virtual:   venv\Scripts\activate
3. Levanta el backend:          uvicorn app.main:app --reload
4. En otra terminal, levanta el frontend:
                                cd frontend
                                npm run dev
5. Abre el navegador en:        http://localhost:5173
```

---

## 6. Credenciales de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| El que creaste con `create_admin.py` | La que definiste | SUPER_ADMIN |

> Los usuarios con contraseña temporal deben cambiarla en su primer inicio de sesión.

---

## 7. Solución de problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `uvicorn` no arranca | Entorno virtual no activado | Ejecuta `venv\Scripts\activate` primero |
| Error de conexión a BD | PostgreSQL no está corriendo o credenciales incorrectas | Verifica `DATABASE_URL` en `.env` |
| Frontend muestra pantalla en blanco tras login | Loop de redirección (ya corregido) | Asegúrate de tener la versión más reciente del código |
| 422 en algún endpoint | Payload no coincide con el schema | Revisa la documentación en `http://localhost:8000/docs` |
| Campos cifrados en respuestas | `FERNET_KEY` incorrecto | Verifica que `.env` tiene la misma clave con la que se cifraron los datos |
