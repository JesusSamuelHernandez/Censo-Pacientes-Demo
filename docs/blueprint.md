# El Blueprint Final v5: App Web "Medicamentos de Alto Costo"

> **Versión 5** — Actualizado 2026-04-14.  
> Cambios respecto a v4: tabla `suministros` eliminada; nuevas tablas `medicos` y `recetas`;
> campo `fecha_inicio_tratamiento` movido de `pacientes` a `recetas`;
> tabla `unidades_medicas` renombrada a `cat_unidades`.

---

## 1. Definición del Stack Tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.13 |
| Framework API | FastAPI |
| Base de Datos | PostgreSQL 15 (Docker) |
| ORM | SQLAlchemy 2.0 |
| Autenticación | OAuth2 con JWT (JSON Web Tokens) |
| Servidor | Uvicorn |
| Entorno | venv (`.venv/`) |

---

## 2. Modelo de Datos (Esquema de Tablas)

### Tabla: `cat_medicamentos` (Catálogo Maestro)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `clave_cnis` **(PK)** | Texto (50) | Clave oficial del medicamento (ej: `010.000.0291.00`). Llave Primaria. |
| `descripcion` | Texto largo | Descripción completa del medicamento. |
| `grupo` | Texto (150) | Grupo terapéutico al que pertenece. |
| `tipo_clave` | Texto (100) | Tipo de clave CNIS. |
| `es_activo` | Booleano | `True/False`. Soft Delete del catálogo. |

---

### Tabla: `cat_unidades` (Establecimientos de Salud)

> Antes llamada `unidades_medicas`. Renombrada en Blueprint v5.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `clues` **(PK)** | Texto (20) | Clave Única de Establecimientos de Salud (CLUES). |
| `nombre_de_la_unidad` | Texto (255) | Nombre del hospital o clínica. |
| `id_entidad` | Texto (100) | Estado al que pertenece (ej: `"Baja California"`). |
| `categoria_gerencial` | Texto (150) | Categoría de la unidad (ej: `"Hospital General"`). |

---

### Tabla: `usuarios`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_usuario` **(PK)** | Entero (Autoincremental) | Identificador único del usuario. |
| `nombre_usuario` | Texto (150) | Nombre del usuario de la plataforma. |
| `email` | Texto (255) único | Nombre de usuario para el login. |
| `hashed_password` | Texto (255) | Contraseña encriptada con bcrypt (nunca en texto plano). |
| `rol_nombre` | Texto (30) | Rol asignado: `SUPER_ADMIN`, `ADMIN_ESTATAL` o `RESPONSABLE_UNIDAD`. |
| `clues_unidad_asignada` **(FK)** | Texto (20) | FK → `cat_unidades.clues`. Solo para `RESPONSABLE_UNIDAD`. |
| `id_entidad` | Texto (100) | Contexto geográfico. Solo para `ADMIN_ESTATAL`. |

---

### Tabla: `pacientes`

> **Cambio v5:** se eliminó el campo `fecha_inicio_tratamiento`. Ahora ese dato vive en la receta.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `curp_paciente` **(PK)** | Texto (18) | CURP oficial. Identificador único del paciente. |
| `nombre_completo` | Texto (255) | Nombre completo del paciente. |
| `diagnostico_actual` | Texto largo | Diagnóstico médico actual. |
| `clues_unidad_adscripcion` **(FK)** | Texto (20) | FK → `cat_unidades.clues`. Unidad donde se atiende. |
| `es_activo` | Booleano | Soft Delete. `False` = paciente dado de baja. |
| `id_usuario_registro` **(FK)** | Entero | FK → `usuarios.id_usuario`. Auditoría: quién capturó. |
| `fecha_registro` | Timestamp (auto) | Fecha y hora de creación en el sistema (automática). |

---

### Tabla: `medicos` *(Nueva en v5)*

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_medico` **(PK)** | Entero (Autoincremental) | Identificador único del médico. |
| `nombre_medico` | Texto (255) | Nombre completo del profesional. |
| `cedula` | Texto (30) único | Cédula profesional. Debe ser única en el sistema. |
| `email` | Texto (255) | Correo electrónico de contacto (opcional). |
| `clues_adscripcion` **(FK)** | Texto (20) | FK → `cat_unidades.clues`. Unidad a la que está adscrito. |

---

### Tabla: `recetas` *(Nueva en v5 — sustituye a `suministros`)*

> Registra la prescripción de un medicamento a un paciente por un médico.  
> La **adherencia** se calcula desde `fecha_inicio_tratamiento` de la receta activa más reciente del paciente: `(fecha_actual - fecha_inicio_tratamiento).days`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_receta` **(PK)** | Texto (50) | Folio de la receta (provisto por el usuario capturista). |
| `id_medico` **(FK)** | Entero | FK → `medicos.id_medico`. Médico que prescribe. |
| `curp_paciente` **(FK)** | Texto (18) | FK → `pacientes.curp_paciente`. Paciente que recibe. |
| `clave_cnis` **(FK)** | Texto (50) | FK → `cat_medicamentos.clave_cnis`. Medicamento prescrito. |
| `clues` **(FK)** | Texto (20) | FK → `cat_unidades.clues`. Unidad donde se genera la receta. |
| `fecha_inicio_tratamiento` | Fecha | Inicio del esquema de tratamiento de esta receta. |
| `fecha_primera_admin` | Fecha | Fecha real de la primera dosis administrada. |
| `dosis_administrada` | Texto (100) | Ej: `"200 mg"`, `"1 ampolleta"`. |
| `fecha_registro_sistema` | Timestamp (auto) | Fecha y hora de captura en el sistema (automática). |
| `id_usuario_registro` **(FK)** | Entero | FK → `usuarios.id_usuario`. Auditoría: quién capturó. |
| `es_activo` | Booleano | Soft Delete. `False` = receta anulada por error de captura. |

---

## 3. Lógica de Negocio y Reportes

- **Soft Delete:** Ningún `DELETE` físico en pacientes ni recetas. Solo cambiar `es_activo = False`.
- **Trazabilidad:** Cada registro de paciente o receta guarda `id_usuario_registro` (quién capturó) y timestamp automático (cuándo).
- **Adherencia:** Calculada en el endpoint como `(date.today() - receta.fecha_inicio_tratamiento).days`, usando la receta activa (`es_activo = True`) más reciente del paciente. Se devuelve en el campo `dias_adherencia` del response de paciente.

---

## 4. Matriz de Seguridad (RBAC)

Toda consulta de datos pasa por un filtro de pertenencia automático:

- `RESPONSABLE_UNIDAD`: `WHERE clues = usuario.clues_unidad_asignada`
- `ADMIN_ESTATAL`: `WHERE id_entidad = usuario.id_entidad`
- `SUPER_ADMIN`: Sin filtro (ámbito nacional)

| Entidad | RESPONSABLE_UNIDAD | ADMIN_ESTATAL | SUPER_ADMIN |
|---------|-------------------|---------------|-------------|
| Pacientes | C, R, U (solo su unidad) | R (todo su estado) | C, R, U, D (nacional) |
| Médicos | C (solo su unidad) | Sin acceso | C, R, U, D (nacional) |
| Recetas | C, R, U (solo su unidad) | R (todo su estado) | C, R, U, D (nacional) |
| Medicamentos | R (lectura) | R (lectura) | C, R, U, D |
| Unidades | R (lectura) | R (lectura) | C, R, U, D |
| Usuarios | Sin acceso | Sin acceso | C, R, U, D |
| Reporte Estatal | Sin acceso (HTTP 403) | R (su estado) | R (nacional) |
| Reporte Detallado | R (su unidad) | R (su estado) | R (nacional) |

---

## 5. Definición de Endpoints (Rutas de la API)

### 5.1 Módulo de Autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/login` | Recibe credenciales, valida y entrega un Token JWT. Respuesta: `access_token` + `rol_nombre` + `id_usuario`. |

---

### 5.2 Módulo de Pacientes

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/pacientes` | Lista paginada. Filtro automático por rol. |
| `POST` | `/pacientes` | Registrar nuevo paciente (CURP, nombre, diagnóstico, CLUES). |
| `GET` | `/pacientes/{curp_paciente}` | Detalle del paciente + `dias_adherencia` calculada. |
| `PATCH` | `/pacientes/{curp_paciente}` | Actualizar datos (diagnóstico, nombre, unidad, `es_activo`). |

---

### 5.3 Módulo de Médicos *(Nuevo en v5)*

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/medicos` | Lista de médicos (filtrado por rol). |
| `POST` | `/medicos` | Registrar nuevo médico (nombre, cédula, email, CLUES). |
| `GET` | `/medicos/{id_medico}` | Detalle de un médico. |
| `PATCH` | `/medicos/{id_medico}` | Actualizar datos del médico. Solo `SUPER_ADMIN`. |
| `DELETE` | `/medicos/{id_medico}` | Eliminar médico. Solo `SUPER_ADMIN`. |

---

### 5.4 Módulo de Recetas *(Nuevo en v5 — sustituye a Suministros)*

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/recetas` | Lista paginada de recetas (filtrado por rol). |
| `POST` | `/recetas` | Registrar nueva receta (folio, médico, paciente, medicamento, dosis, fechas). |
| `GET` | `/recetas/{id_receta}` | Detalle de una receta con datos embebidos de medicamento y médico. |
| `PATCH` | `/recetas/{id_receta}` | Actualizar fechas, dosis o anular (`es_activo = False`). |
| `DELETE` | `/recetas/{id_receta}` | Soft Delete de la receta (anulación por error de captura). |

---

### 5.5 Módulo de Inteligencia y Reportes

| Método | Ruta | Acceso mínimo | Descripción |
|--------|------|--------------|-------------|
| `GET` | `/reportes/resumen-detallado` | `RESPONSABLE_UNIDAD` | JSON con datos crudos para generar Excel/PDF. Filtrado por rol. |
| `GET` | `/reportes/estatal` | `ADMIN_ESTATAL` | Datos agregados (sumatorias por unidad). HTTP 403 para `RESPONSABLE_UNIDAD`. |

---

### 5.6 Módulo de Catálogos

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| `GET` | `/catalogos/medicamentos` | Todos | Consultar catálogo oficial (Clave CNIS). |
| `POST` | `/catalogos/medicamentos` | `SUPER_ADMIN` | Agregar nueva clave al catálogo. |
| `GET` | `/catalogos/medicamentos/{clave}` | Todos | Detalle de un medicamento. |
| `PATCH` | `/catalogos/medicamentos/{clave}` | `SUPER_ADMIN` | Actualizar o desactivar medicamento. |
| `GET` | `/catalogos/unidades` | Todos | Consultar unidades médicas registradas. |
| `POST` | `/catalogos/unidades` | `SUPER_ADMIN` | Registrar nueva unidad médica. |
| `GET` | `/catalogos/unidades/{clues}` | Todos | Detalle de una unidad. |
| `PATCH` | `/catalogos/unidades/{clues}` | `SUPER_ADMIN` | Actualizar datos de una unidad. |

---

### 5.7 Módulo de Usuarios

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| `GET` | `/usuarios` | `SUPER_ADMIN` | Lista de todos los usuarios. |
| `POST` | `/usuarios` | `SUPER_ADMIN` | Crear nueva cuenta de usuario. |
| `GET` | `/usuarios/{id}` | `SUPER_ADMIN` | Detalle de un usuario. |
| `PATCH` | `/usuarios/{id}` | `SUPER_ADMIN` | Actualizar rol, unidad o contraseña. |
