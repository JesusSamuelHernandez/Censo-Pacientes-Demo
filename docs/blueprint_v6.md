# Blueprint v6 — Prescripciones y Gestión de Continuidad

> **Versión 6** — Iniciado 2026-04-27.
> Cambios respecto a v5: tabla `recetas` renombrada a `registros`; nuevos campos en `registros`
> (`peso`, `talla`, `estatus_diagnostico`, `fecha_fin_tratamiento`, `prescripcion`);
> flujo de registro combinado paciente+prescripción; lógica de continuidad (inactividad lazy);
> endpoint de búsqueda nacional por CURP; notificaciones al login.

---

## Decisiones Tomadas (2026-04-27)

| Decisión | Detalle |
|---|---|
| `clues_unidad_adscripcion` en `pacientes` | **Se conserva.** RBAC existente no cambia. |
| Búsqueda nacional por CURP | Nuevo endpoint exclusivo, sin filtro RBAC. Los 3 roles pueden buscar en todo el país. |
| `peso` y `talla` | Van en **`registros`**, no en `pacientes`. Se registran por prescripción. |
| `fecha_fin_tratamiento` | El médico la ingresa manualmente. Se le suma 1 mes para la ventana de continuidad. |
| Inactividad automática | **Marcado lazy**: el backend marca vencidos en BD justo antes de devolver la lista de registros. Sin scheduler externo. |
| Notificaciones | Endpoint `GET /notificaciones` que el frontend consulta al cargar el dashboard (login diario). |

---

## Cambios en el Modelo de Datos (v5 → v6)

### Tabla `recetas` → **`registros`**

| Cambio | Tipo |
|---|---|
| Nombre de tabla: `recetas` → `registros` | Renombre |
| `fecha_primera_admin` → `fecha_primera_administracion` | Renombre de columna |
| NUEVO: `fecha_fin_tratamiento` (Date, nullable) | Nueva columna |
| NUEVO: `peso` (Numeric 5,2, nullable) | Nueva columna |
| NUEVO: `talla` (Numeric 5,2, nullable) | Nueva columna |
| NUEVO: `estatus_diagnostico` (String 50, nullable) | Nueva columna |
| NUEVO: `prescripcion` (Text, nullable) | Nueva columna |

### Tabla `pacientes`

| Cambio | Tipo |
|---|---|
| Sin cambios estructurales | — |
| `clues_unidad_adscripcion` se **conserva** | Sin cambio |

---

## Plan de Implementación — Pasos

---

### PASO 1 — Renombrar `recetas` → `registros`

**Estado:** Pendiente
**Complejidad:** Media (muchas referencias, sin lógica nueva)
**Archivos afectados:** `app/models.py`, `app/schemas.py`, `app/main.py`, `frontend/src/api/recetas.js`, `frontend/src/pages/recetas/`

#### Backend — `app/models.py`
- [ ] Renombrar clase `Receta` → `Registro`
- [ ] Cambiar `__tablename__ = "recetas"` → `"registros"`
- [ ] Renombrar columna `fecha_primera_admin` → `fecha_primera_administracion`
- [ ] Actualizar `relationship` en `CatMedicamento`, `UnidadMedica`, `Usuario`, `Paciente`

#### Backend — `app/schemas.py`
- [ ] Renombrar clases: `RecetaBase/Create/Update/Response/ListResponse` → `RegistroBase/...`
- [ ] Renombrar campo `fecha_primera_admin` → `fecha_primera_administracion` en los schemas

#### Backend — `app/main.py`
- [ ] Cambiar todas las rutas `/recetas` → `/registros`
- [ ] Renombrar variables y funciones que usen `receta` → `registro`
- [ ] Actualizar importaciones de schemas

#### Frontend — `frontend/src/api/recetas.js`
- [ ] Renombrar archivo a `registros.js`
- [ ] Cambiar todas las URLs `/recetas` → `/registros`
- [ ] Renombrar funciones exportadas: `listarRecetas→listarRegistros`, etc.

#### Frontend — `frontend/src/pages/recetas/`
- [ ] Renombrar carpeta a `registros/`
- [ ] Actualizar imports en los componentes
- [ ] Actualizar imports en `App.jsx`

#### Base de datos
- [ ] DROP tabla `recetas` existente (datos de prueba — se puede borrar)
- [ ] Ejecutar backend para recrear tablas (SQLAlchemy con `Base.metadata.create_all`)

#### Validación del paso
- [ ] `POST /registros` crea un registro sin error
- [ ] `GET /registros` devuelve lista
- [ ] El frontend carga la página sin errores de consola

---

### PASO 2 — Nuevos campos en `registros`

**Estado:** Pendiente (hacer después del Paso 1)
**Complejidad:** Baja
**Archivos afectados:** `app/models.py`, `app/schemas.py`

#### Backend — `app/models.py`
- [ ] Agregar a clase `Registro`:
  - `fecha_fin_tratamiento: Mapped[date | None] = mapped_column(Date, nullable=True)`
  - `peso: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)`
  - `talla: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)`
  - `estatus_diagnostico: Mapped[str | None] = mapped_column(String(50), nullable=True)`
  - `prescripcion: Mapped[str | None] = mapped_column(Text, nullable=True)`

#### Backend — `app/schemas.py`
- [ ] Agregar campos en `RegistroBase`: `fecha_fin_tratamiento`, `peso`, `talla`, `estatus_diagnostico`, `prescripcion`
- [ ] Definir lista de valores válidos para `estatus_diagnostico` (ej. `"ACTIVO"`, `"REMISION"`, `"SEGUIMIENTO"`)
- [ ] Agregar validador de `estatus_diagnostico` si se define lista cerrada

#### Validación del paso
- [ ] `POST /registros` acepta los nuevos campos
- [ ] `GET /registros/{id}` devuelve los nuevos campos en la respuesta

---

### PASO 3 — Endpoint de búsqueda nacional por CURP

**Estado:** Pendiente
**Complejidad:** Baja-Media
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `frontend/src/api/pacientes.js`

**Objetivo:** Cuando el médico escribe una CURP en el formulario de prescripciones, el sistema busca si ese paciente ya existe en cualquier unidad del país.

#### Backend — `app/main.py`
- [ ] Nuevo endpoint: `GET /pacientes/buscar`
  - Query param: `curp: str`
  - **Sin filtro RBAC** — busca en toda la tabla `pacientes`
  - Si existe: devuelve `{ existe: true, id_paciente, nombre_completo, clues_unidad_adscripcion, registros_count }`
  - Si no existe: devuelve `{ existe: false }`
  - Usa `curp_hash` (SHA-256 del CURP) para la búsqueda — nunca texto plano

#### Backend — `app/schemas.py`
- [ ] Nuevo schema `BusquedaCurpResponse`

#### Frontend — `frontend/src/api/pacientes.js`
- [ ] Nueva función: `buscarPacientePorCurp(curp)`

#### Validación del paso
- [ ] Buscar una CURP existente devuelve los datos del paciente
- [ ] Buscar una CURP inexistente devuelve `{ existe: false }`
- [ ] Un `SUPER_ADMIN` puede ver pacientes de cualquier unidad con este endpoint

---

### PASO 4 — Formulario combinado: registrar paciente + prescripción

**Estado:** Pendiente (requiere Paso 3)
**Complejidad:** Media-Alta
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `frontend/src/pages/registros/RegistroFormPage.jsx`

**Objetivo:** Un solo formulario para registrar la prescripción. Si el paciente no existe, sus datos se capturan ahí mismo y se crean en `pacientes`. Si ya existe, se carga su información.

#### Flujo
1. Médico escribe CURP → frontend llama `GET /pacientes/buscar?curp=xxx`
2. **Si existe:** muestra nombre, diagnóstico y enlace a "Ver historial del paciente". Médico puede continuar llenando la prescripción.
3. **Si no existe:** aparecen los campos de datos del paciente (nombre, diagnóstico, CLUES).
4. Al guardar: el frontend llama `POST /registros/completo`

#### Backend — `app/main.py`
- [ ] Nuevo endpoint: `POST /registros/completo`
  - Recibe datos del paciente (opcionales si ya existe) + datos de la prescripción
  - Lógica transaccional:
    1. Si `curp_paciente` no existe en BD → crear paciente
    2. Si ya existe → usar `id_paciente` existente
    3. Crear registro (prescripción) con el `id_paciente` obtenido
  - Devuelve el registro creado con datos del paciente incluidos

#### Backend — `app/schemas.py`
- [ ] Nuevo schema `RegistroCompletoCreate` (paciente + prescripción en un solo payload)
- [ ] Nuevo schema `RegistroCompletoResponse`

#### Frontend
- [ ] Modificar `RegistroFormPage.jsx` para implementar el flujo descrito
- [ ] Al detectar CURP existente: mostrar datos del paciente + enlace a detalles
- [ ] Al guardar: llamar al nuevo endpoint `/registros/completo`
- [ ] El botón "Regresar" desde la vista de detalles del paciente debe regresar al formulario de prescripción con los datos pre-llenados

#### Validación del paso
- [ ] Registrar un paciente nuevo + prescripción en un solo POST
- [ ] Registrar una nueva prescripción a un paciente ya existente
- [ ] El enlace al historial funciona y el botón regresar vuelve al formulario

---

### PASO 5 — Lógica de inactividad automática (marcado lazy)

**Estado:** Pendiente (requiere Paso 2 — necesita `fecha_fin_tratamiento`)
**Complejidad:** Media
**Archivos afectados:** `app/main.py`

**Regla:** Si `fecha_fin_tratamiento + 30 días <= hoy` y el registro no fue validado → `es_activo = False`.

**Estrategia:** Marcado lazy — el backend ejecuta el UPDATE antes de devolver cualquier lista de registros o notificaciones. Sin scheduler externo.

#### Backend — `app/main.py`
- [ ] Nueva función utilitaria `marcar_registros_vencidos(db: Session)`:
  ```python
  # Busca registros activos cuyo plazo de continuidad ya venció
  # y los marca es_activo = False en la BD
  ```
- [ ] Llamar a `marcar_registros_vencidos(db)` al inicio de:
  - `GET /registros` (listar)
  - `GET /notificaciones`
  - `GET /pacientes/{id}` (detalle — para que el estado de sus registros sea correcto)

#### Validación del paso
- [ ] Crear un registro con `fecha_fin_tratamiento` en el pasado (más de 30 días)
- [ ] Al consultar `GET /registros`, ese registro aparece como `es_activo = False`
- [ ] Verificar directamente en BD que el campo cambió

---

### PASO 6 — Validación de continuidad

**Estado:** Pendiente (requiere Paso 5)
**Complejidad:** Baja-Media
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `frontend/`

**Objetivo:** El médico puede confirmar que un paciente continúa con el medicamento, extendiendo la fecha de fin del tratamiento.

#### Backend — `app/main.py`
- [ ] Nuevo endpoint: `PATCH /registros/{id_registro}/validar-continuidad`
  - Solo `RESPONSABLE_UNIDAD` (el médico responsable de esa unidad)
  - Recibe: `{ nueva_fecha_fin_tratamiento: date }`
  - Lógica:
    1. Verificar que el registro pertenezca a la unidad del usuario (RBAC)
    2. Actualizar `fecha_fin_tratamiento = nueva_fecha_fin_tratamiento`
    3. Si el registro estaba inactivo por vencimiento, reactivarlo: `es_activo = True`
  - Devuelve el registro actualizado

#### Backend — `app/schemas.py`
- [ ] Nuevo schema `ValidarContinuidadRequest { nueva_fecha_fin_tratamiento: date }`

#### Frontend
- [ ] Botón "Validar continuidad" en la lista de notificaciones
- [ ] Modal/form simple con datepicker para la nueva fecha
- [ ] Llamar al endpoint y refrescar la lista

#### Validación del paso
- [ ] Un registro vencido puede ser reactivado con una nueva fecha
- [ ] El RBAC impide que un usuario valide registros de otra unidad

---

### PASO 7 — Notificaciones al login

**Estado:** Pendiente (requiere Pasos 5 y 6)
**Complejidad:** Media
**Archivos afectados:** `app/main.py`, `frontend/src/pages/` (dashboard o layout)

**Objetivo:** Al cargar el dashboard (login diario), el médico ve cuántos registros requieren validación.

#### Backend — `app/main.py`
- [ ] Nuevo endpoint: `GET /notificaciones`
  - Llama a `marcar_registros_vencidos(db)` primero
  - Devuelve registros activos donde `fecha_fin_tratamiento + 30 días <= hoy + 7 días` (margen de aviso anticipado)
  - Filtro RBAC: `RESPONSABLE_UNIDAD` solo ve su unidad
  - Respuesta: lista de registros con nombre del paciente, medicamento y fecha límite

#### Backend — `app/schemas.py`
- [ ] Nuevo schema `NotificacionResponse`

#### Frontend
- [ ] Badge/contador en el menú lateral con el número de registros pendientes
- [ ] Nueva sección "Notificaciones" o zona visible en el dashboard
- [ ] Cada notificación muestra: nombre del paciente, medicamento, fecha límite
- [ ] Botón directo "Validar continuidad" desde la notificación

#### Validación del paso
- [ ] Al hacer login con registros próximos a vencer, aparece el badge con el conteo
- [ ] Al hacer click en la notificación se llega al formulario de validación
- [ ] Después de validar, el badge se actualiza

---

## Archivos a Modificar por Paso (Resumen)

| Archivo | Paso 1 | Paso 2 | Paso 3 | Paso 4 | Paso 5 | Paso 6 | Paso 7 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `app/models.py` | ✏️ | ✏️ | — | — | — | — | — |
| `app/schemas.py` | ✏️ | ✏️ | ✏️ | ✏️ | — | ✏️ | ✏️ |
| `app/main.py` | ✏️ | — | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ |
| `frontend/src/api/recetas.js→registros.js` | ✏️ | — | — | ✏️ | — | ✏️ | — |
| `frontend/src/api/pacientes.js` | — | — | ✏️ | ✏️ | — | — | — |
| `frontend/src/pages/recetas/→registros/` | ✏️ | ✏️ | — | ✏️ | — | ✏️ | — |
| `frontend/src/pages/pacientes/` | — | — | ✏️ | ✏️ | — | — | — |
| `frontend/src/App.jsx` | ✏️ | — | — | ✏️ | — | — | ✏️ |
| `frontend/src/components/layout/Sidebar.jsx` | ✏️ | — | — | — | — | — | ✏️ |

---

---

### PASO 8 — Pacientes activos = pacientes con prescripción activa

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `frontend/src/pages/pacientes/PacientesPage.jsx`

**Regla de negocio:** Un paciente se considera "activo" únicamente si tiene al menos una prescripción (`registro`) con `es_activo = True`. El campo `es_activo` en la tabla `pacientes` se conserva exclusivamente para la baja manual (soft delete).

**Decisiones:**
- `GET /pacientes?solo_activos=true` → `es_activo=True` **Y** `EXISTS (registro activo para ese paciente)`
- `GET /pacientes?solo_activos=false` → todos los pacientes sin filtro de prescripciones
- Se agrega `tiene_prescripcion_activa: bool` al `PacienteResponse`
- El `es_activo` del response sigue siendo el flag manual de baja — no se sobreescribe

#### Backend — `app/main.py`
- [ ] Modificar `listar_pacientes`: cuando `solo_activos=True`, agregar filtro `EXISTS` sobre `Registro.es_activo == True`
- [ ] Modificar `obtener_paciente`: calcular y agregar `tiene_prescripcion_activa` en la respuesta
- [ ] Modificar `_paciente_to_response`: incluir `tiene_prescripcion_activa`

#### Backend — `app/schemas.py`
- [ ] Agregar campo `tiene_prescripcion_activa: bool` a `PacienteResponse`

#### Frontend — `PacientesPage.jsx`
- [ ] El badge de estado del paciente debe mostrar "Sin prescripción activa" cuando `tiene_prescripcion_activa=False` y `es_activo=True`

#### Validación
- [ ] Un paciente registrado sin prescripciones **no** aparece en `solo_activos=true`
- [ ] Un paciente con prescripción activa **sí** aparece
- [ ] Un paciente con todas sus prescripciones vencidas/anuladas **no** aparece
- [ ] Un paciente dado de baja manualmente (`es_activo=false`) **no** aparece en ningún caso

---

## Estado General

| Paso | Nombre | Estado |
|---|---|---|
| 1 | Renombrar recetas → registros | ✅ Completado 2026-04-27 |
| 2 | Nuevos campos en registros | ✅ Completado 2026-04-27 |
| 3 | Búsqueda nacional por CURP | ✅ Completado 2026-04-27 |
| 4 | Formulario combinado paciente+prescripción | ✅ Completado 2026-04-27 |
| 5 | Lógica de inactividad (marcado lazy) | ✅ Completado 2026-04-27 |
| 6 | Validación de continuidad | ✅ Completado 2026-04-27 |
| 7 | Notificaciones al login | ✅ Completado 2026-04-27 |
| 8 | Pacientes activos = con prescripción activa | ⏳ Pendiente |
