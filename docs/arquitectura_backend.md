# Arquitectura del Backend — App "Medicamentos de Alto Costo"

> Última actualización: 2026-06-22 (confirmado_mediante + caso relacionado con amparo/derechos humanos en Registro)

## 1. Visión General

El sistema es una **API REST** que centraliza el censo de pacientes que reciben medicamentos de alto costo en unidades médicas del sector salud (IMSS Bienestar). El backend gestiona los datos, aplica las reglas de seguridad y expone la información a cualquier cliente (web, móvil, reportes).

---

## 2. Stack Tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.13 |
| Framework API | FastAPI | Latest (con Swagger automático en `/docs`) |
| ORM | SQLAlchemy | 2.0.36 |
| Base de Datos | PostgreSQL | 15 (Docker en dev, Railway en prod) |
| Validación de datos | Pydantic | v2 |
| Autenticación | python-jose (JWT HS256) | — |
| Hash de contraseñas | bcrypt (uso directo, sin passlib) | — |
| Cifrado de datos sensibles | cryptography (Fernet) | — |
| Servidor | Uvicorn | — |
| Entorno | venv (`.venv/`) | — |

**Nota sobre bcrypt:** Se usa `bcrypt.hashpw()` / `bcrypt.checkpw()` directamente, sin passlib, para evitar el error `AttributeError: module 'bcrypt' has no attribute '__about__'` de versiones recientes.

---

## 3. Decisiones de Diseño Clave

### Soft Delete (es_activo)
Los datos de pacientes y registros son registros médicos. Ningún dato se elimina físicamente: se da de baja lógicamente (`es_activo = False`). Esto garantiza trazabilidad histórica, auditoría y posibilidad de recuperar datos.

### RBAC con filtro geográfico automático
La función `apply_rbac_filter()` centraliza toda la lógica de restricción de visibilidad. Ningún endpoint puede "olvidar" aplicarla. El filtro de prescripciones sigue al **paciente** (por su unidad de adscripción actual), no a la unidad donde se generó la prescripción.

### Adherencia calculada en runtime
La adherencia es `(date.today() - registro.fecha_inicio_tratamiento).days` usando el registro activo más reciente del paciente. Al calcularla en consulta, el dato siempre es exacto sin procesos de actualización.

### Cifrado Fernet para datos sensibles
CURP, nombre completo, diagnóstico, nombre del médico y cédula se almacenan cifrados con Fernet (clave simétrica). El campo `curp_hash` (SHA-256) permite búsquedas sin descifrar. El campo cifrado se almacena como `LargeBinary` en PostgreSQL.

### fecha_fin_tratamiento como fecha exclusiva
Cuando hay posología completa, `fecha_fin_tratamiento` se auto-calcula como:
`fecha_primera_administracion + duracion * factor`
siendo `factor` = 1 (días), 7 (semanas) o 30 (meses). La fecha es **exclusiva** (el tratamiento termina el día anterior). Nunca se pide al usuario que la ingrese manualmente si existe posología.

### Marcado lazy de registros vencidos
No hay scheduler externo. La función `marcar_registros_vencidos()` se llama al inicio de los endpoints de lectura relevantes y ejecuta un `UPDATE` masivo con SQLAlchemy core para eficiencia. Condición: `fecha_fin_tratamiento + 30 días <= hoy`.

### Registro reemplaza a Receta (Blueprint v6)
El modelo `Registro` amplía el concepto de "receta" con posología completa (dosis, frecuencia, duración), cálculo automático de `fecha_fin_tratamiento`, trazabilidad de reemplazos (`id_registro_origen`) y validación de continuidad.

### Estatus de evolución del paciente (banderín)
`Paciente.estatus_evolucion` (default `"Inicia tx"`) representa el avance clínico del paciente y se muestra como un banderín de color en el frontend (solo en "Pacientes Activos"). Se actualiza vía el mismo `PATCH /pacientes/{curp_paciente}` que el resto de los datos del paciente — no hay endpoint dedicado, por lo que reutiliza el RBAC existente (las 3 roles que pueden editar a un paciente también pueden cambiar su estatus de evolución). Cada cambio estampa `id_usuario_ultimo_cambio_estatus` y `fecha_ultimo_cambio_estatus`.

### CURP opcional (pacientes sin CURP, ej. recién nacidos)
`Paciente.curp_hash` y `curp_paciente` son `nullable` (Postgres permite múltiples `NULL` en una columna `unique`). Un paciente sin CURP se identifica y localiza por `id_paciente`. El helper `_obtener_paciente_por_identificador(identificador, db)` resuelve el segmento `{curp_paciente}` de las rutas existentes: si `identificador.isdigit()` busca por `id_paciente`, si no por `curp_hash`. Esto permite que rutas como `GET /pacientes/{curp_paciente}` acepten también un `id_paciente` numérico sin cambiar su definición. La búsqueda de estos pacientes se hace por nombre vía `GET /pacientes/buscar-por-nombre` (ver §7.2).

---

## 4. Estructura de Archivos

```
app/
├── database.py          → Conexión a PostgreSQL, pool de conexiones, get_db().
├── models.py            → 11 tablas ORM: CatDiagnostico, CatMedicamento, UnidadMedica (cat_unidades),
│                          Usuario, Paciente, Medico, Registro, NotificacionTransferencia,
│                          UnidadMedicamento (unidad_medicamentos — relación N:M unidad↔medicamento),
│                          ExpedientePaciente (expedientes_paciente),
│                          ReaccionAdversa (reacciones_adversas).
├── schemas.py           → Validación de entrada/salida con Pydantic v2.
├── auth.py              → JWT, bcrypt, RBAC: apply_rbac_filter(), dependencias de rol.
├── crypto.py            → cifrar(), descifrar(), descifrar_o_none(), hash_sha256() con Fernet.
└── main.py              → Todos los endpoints de la API (versión 3.0.0).
```

**Flujo de una petición:**
```
Cliente → main.py (endpoint) → auth.py (validar JWT + rol) → database.py (sesión BD)
       → models.py (query ORM) → schemas.py (serializar respuesta) → Cliente
```

---

## 5. Modelos ORM

### 5.0 CatDiagnostico — `cat_diagnosticos`

Catálogo de diagnósticos clínicos. El diagnóstico se asocia a cada **prescripción** (`Registro`), no al paciente directamente. Un paciente con más de un medicamento puede tener más de un diagnóstico activo.

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_diagnostico` | Integer | PK, autoincrement | |
| `nombre` | String(500) | NOT NULL, unique | Nombre completo del diagnóstico |
| `codigo_cie10` | String(20) | nullable | Código CIE-10 (ej. "E75.2") |
| `es_activo` | Boolean | NOT NULL, default=True | Soft Delete |

**Relaciones:** `registros` (→ `Registro`, back_populates), `unidades` (N:M vía `UnidadMedicamento`)

---

### 5.1 CatMedicamento — `cat_medicamentos`

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `clave_cnis` | String(50) | PK | Clave oficial CNIS |
| `descripcion` | Text | NOT NULL | |
| `grupo` | String(150) | nullable | |
| `tipo_clave` | String(100) | nullable | |
| `unidad` | String(100) | nullable | Unidad singular del medicamento (ej. "tableta") |
| `unidad_de_medida` | String(50) | nullable | Unidad de medida de la cantidad (ej. "mg", "ml") |
| `es_activo` | Boolean | NOT NULL, default=True | Soft Delete |

**Relaciones:** `registros` (→ `Registro`, back_populates)

---

### 5.2 UnidadMedica — `cat_unidades`

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `clues` | String(20) | PK | Clave Única de Establecimiento de Salud |
| `nombre_de_la_unidad` | String(255) | NOT NULL | |
| `id_entidad` | String(100) | NOT NULL, index | Identificador de la entidad federativa |
| `categoria_gerencial` | String(150) | nullable | |

**Relaciones:** `usuarios`, `pacientes`, `medicos`, `registros`, `medicamentos` (N:M vía `UnidadMedicamento`)

---

### 5.3 Usuario — `usuarios`

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_usuario` | Integer | PK, autoincrement | |
| `nombre_usuario` | String(150) | NOT NULL | |
| `email` | String(255) | unique, NOT NULL, index | |
| `hashed_password` | String(255) | NOT NULL | bcrypt hash |
| `rol_nombre` | String(30) | NOT NULL | SUPER_ADMIN / ADMIN_ESTATAL / RESPONSABLE_UNIDAD |
| `clues_unidad_asignada` | String(20) | FK → cat_unidades, nullable | Solo RESPONSABLE_UNIDAD |
| `id_entidad` | String(100) | nullable | Solo ADMIN_ESTATAL |
| `debe_cambiar_password` | Boolean | NOT NULL, default=True | Forzar cambio en primer login |

**Relaciones:** `unidad_asignada`, `pacientes_registrados`, `registros_registrados`

---

### 5.4 Paciente — `pacientes`

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_paciente` | Integer | PK, autoincrement | |
| `curp_hash` | String(64) | unique, nullable, index | SHA-256 de la CURP para búsquedas. `NULL` si el paciente no tiene CURP (ej. recién nacidos) |
| `curp_paciente` | LargeBinary | nullable | CURP cifrada con Fernet. `NULL` si el paciente no tiene CURP |
| `nombre_completo` | LargeBinary | NOT NULL | Nombre cifrado con Fernet |
| `diagnostico_actual` | LargeBinary | nullable | Diagnóstico cifrado con Fernet |
| `fecha_nacimiento` | Date | nullable | Fecha de nacimiento del paciente |
| `clues_unidad_adscripcion` | String(20) | FK → cat_unidades, NOT NULL, index | |
| `es_activo` | Boolean | NOT NULL, default=True | Soft Delete |
| `estatus_evolucion` | String(30) | NOT NULL, default="Inicia tx", server_default | Banderín de evolución. Valores válidos: `ESTATUS_EVOLUCION_OPTIONS` (ver §6.4) |
| `id_usuario_ultimo_cambio_estatus` | Integer | FK → usuarios (SET NULL), nullable | Auditoría del último cambio de `estatus_evolucion` |
| `fecha_ultimo_cambio_estatus` | DateTime(timezone=True) | nullable | Timestamp del último cambio de `estatus_evolucion` |
| `id_usuario_registro` | Integer | FK → usuarios (SET NULL), nullable | Auditoría |
| `fecha_registro` | DateTime(timezone=True) | NOT NULL, server_default=now() | Timestamp automático BD |

**Relaciones:** `unidad_adscripcion`, `usuario_registro`, `registros` (cascade all, delete-orphan), `expedientes` (→ `ExpedientePaciente`, cascade all, delete-orphan), `reacciones_adversas` (→ `ReaccionAdversa`, cascade all, delete-orphan)

---

### 5.4b ExpedientePaciente — `expedientes_paciente`

Número de expediente clínico del paciente en cada unidad médica donde ha sido atendido. El mismo paciente puede tener expedientes distintos en distintas unidades (el número cambia al transferirse).

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_paciente` | Integer | PK compuesta, FK → pacientes (CASCADE) | |
| `clues` | String(20) | PK compuesta, FK → cat_unidades (RESTRICT) | |
| `numero_expediente` | String(100) | NOT NULL | |

**PK compuesta:** `(id_paciente, clues)` — un solo expediente por combinación paciente-unidad. `CASCADE` en `id_paciente` limpia los expedientes si se elimina el paciente.

**Relaciones:** `paciente` (→ `Paciente`, back_populates=`expedientes`), `unidad`

---

### 5.4c ReaccionAdversa — `reacciones_adversas`

Registro histórico de reacciones adversas a medicamentos reportadas para un paciente. No tienen `es_activo` — son inmutables una vez creadas (históricas).

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_reaccion` | Integer | PK, autoincrement | |
| `id_paciente` | Integer | FK → pacientes (CASCADE), NOT NULL, index | |
| `clave_cnis` | String(50) | FK → cat_medicamentos (RESTRICT), NOT NULL | |
| `comentario` | Text | NOT NULL | Descripción de la reacción |
| `id_usuario_registro` | Integer | FK → usuarios (SET NULL), nullable | Quién registró la reacción |
| `fecha_registro` | DateTime(timezone=True) | NOT NULL, server_default=now() | Timestamp automático BD |

**Relaciones:** `paciente` (→ `Paciente`), `medicamento` (→ `CatMedicamento`), `usuario_registro` (→ `Usuario | None`)

---

### 5.5 Medico — `medicos`

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_medico` | Integer | PK, autoincrement | |
| `cedula_hash` | String(64) | unique, NOT NULL, index | SHA-256 de cédula para búsquedas |
| `nombre_medico` | LargeBinary | NOT NULL | Nombre cifrado con Fernet |
| `cedula` | LargeBinary | NOT NULL | Cédula cifrada con Fernet |
| `email` | String(255) | nullable | Texto plano |
| `clues_adscripcion` | String(20) | FK → cat_unidades, NOT NULL, index | |
| `es_activo` | Boolean | NOT NULL, default=True | Soft Delete |

**Relaciones:** `unidad_adscripcion`, `registros`

---

### 5.6 Registro — `registros`

La PK es autoincremental. Reemplaza al modelo `Receta` desde Blueprint v6.

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id_registro` | Integer | PK, autoincrement | |
| `id_medico` | Integer | FK → medicos (RESTRICT), NOT NULL, index | |
| `id_paciente` | Integer | FK → pacientes (CASCADE), NOT NULL, index | |
| `clave_cnis` | String(50) | FK → cat_medicamentos (RESTRICT), NOT NULL, index | |
| `clues` | String(20) | FK → cat_unidades (RESTRICT), NOT NULL, index | Unidad donde se generó la prescripción |
| `fecha_inicio_tratamiento` | Date | nullable | |
| `fecha_primera_administracion` | Date | nullable | Fecha real de la primera dosis |
| `fecha_fin_tratamiento` | Date | nullable | Auto-calculada desde posología (fecha **exclusiva**) |
| `dosis_administrada` | String(100) | nullable | Texto libre, ej. "200 mg" |
| `peso` | Numeric(5,2) | nullable | Peso en kg |
| `talla` | Numeric(5,2) | nullable | Talla en cm |
| `estatus_diagnostico` | String(50) | nullable | "confirmado" / "por confirmar" |
| `confirmado_por` | String(100) | nullable | Área que confirmó el diagnóstico |
| `confirmado_mediante` | String(200) | nullable | Método mediante el cual se confirmó el diagnóstico (texto libre) |
| `tratamiento_amparo` | Boolean | NOT NULL, default=False | Caso relacionado con tratamiento por amparo. Mutuamente excluyente con `queja_derechos_humanos` (aplicado en frontend) |
| `queja_derechos_humanos` | Boolean | NOT NULL, default=False | Caso relacionado con queja de derechos humanos. Si ambos son False, equivale a "No aplica" |
| `prescripcion` | Text | nullable | Auto-generado por `_aplicar_posologia()` |
| `dosis` | Float | nullable | Unidades por toma (posología) |
| `cantidad` | Float | nullable | Cantidad de medicamento por unidad |
| `frecuencia` | Integer | nullable | Horas entre tomas (ej. 8, 12, 24) |
| `unidad_tiempo` | String(50) | nullable | "días", "semanas" o "meses" |
| `duracion` | Integer | nullable | Número de unidades de tiempo |
| `id_diagnostico` | Integer | FK → cat_diagnosticos (RESTRICT), nullable, index | Diagnóstico de esta prescripción |
| `total_medicamento` | Float | nullable | Total calculado por `_aplicar_posologia()` |
| `id_registro_origen` | Integer | FK → registros (SET NULL), nullable | Auto-referencia para trazabilidad de reemplazos |
| `fecha_registro_sistema` | DateTime(timezone=True) | NOT NULL, server_default=now() | Timestamp automático BD |
| `id_usuario_registro` | Integer | FK → usuarios (SET NULL), nullable | Auditoría |
| `es_activo` | Boolean | NOT NULL, default=True | Soft Delete |

**Relaciones:** `medico`, `paciente`, `medicamento`, `unidad`, `diagnostico`, `usuario_registro`

---

### 5.7 NotificacionTransferencia — `notificaciones_transferencia`

Generada automáticamente cuando un paciente cambia de unidad de adscripción.

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `id_paciente` | Integer | FK → pacientes (CASCADE), NOT NULL, index | |
| `clues_unidad_origen` | String(20) | FK → cat_unidades (RESTRICT), NOT NULL, index | Unidad que pierde al paciente |
| `clues_unidad_destino` | String(20) | FK → cat_unidades (RESTRICT), NOT NULL | Unidad que recibe al paciente |
| `id_usuario_traslado` | Integer | FK → usuarios (SET NULL), nullable | Usuario que realizó el traslado |
| `fecha_traslado` | DateTime(timezone=True) | NOT NULL, server_default=now() | |
| `leida` | Boolean | NOT NULL, default=False | False = pendiente de aceptar |
| `id_usuario_leida` | Integer | FK → usuarios (SET NULL), nullable | Usuario que marcó como leída |
| `fecha_leida` | DateTime(timezone=True) | nullable | |

**Relaciones:** `paciente`, `unidad_origen`, `unidad_destino`, `usuario_traslado`, `usuario_leida`

---

### 5.8 UnidadMedicamento — `unidad_medicamentos`

Tabla de relación N:M entre `cat_unidades` y `cat_medicamentos`. No todas las unidades tienen disponibles todos los medicamentos; esta tabla define exactamente qué medicamentos puede prescribir cada unidad.

| Campo | Tipo SQLAlchemy | Restricciones | Notas |
|---|---|---|---|
| `clues` | String(20) | PK, FK → cat_unidades (CASCADE) | Clave de la unidad médica |
| `clave_cnis` | String(50) | PK, FK → cat_medicamentos (CASCADE) | Clave CNIS del medicamento |

**PK compuesta:** `(clues, clave_cnis)` — sin ID surrogate. `CASCADE` en ambas FK garantiza limpieza automática si se elimina una unidad o un medicamento del catálogo.

**Uso:** `GET /catalogos/medicamentos?clues=XXXXX` hace JOIN con esta tabla para devolver solo los medicamentos asignados a esa unidad. Sin el parámetro, devuelve todo el catálogo (comportamiento original, retrocompatible).

**Carga:** Script `scripts/cargar_unidad_medicamentos.py` lee `scripts/data/unidad_medicamentos.xlsx` (columnas: `clues`, `clave_cnis`). Idempotente — omite duplicados.

---

## 6. Schemas Pydantic (v2)

### 6.0 CatDiagnostico

| Schema | Campos |
|---|---|
| `DiagnosticoBase` | `nombre` (str, 1-500), `codigo_cie10` (opt, max 20) |
| `DiagnosticoCreate` | Idéntico a Base |
| `DiagnosticoUpdate` | Todos opcionales: `nombre`, `codigo_cie10`, `es_activo` |
| `DiagnosticoResponse` | Base + `id_diagnostico` (int), `es_activo` (bool). `from_attributes=True` |

---

### 6.1 CatMedicamento

| Schema | Campos |
|---|---|
| `MedicamentoBase` | `descripcion` (str, 1-2000), `grupo` (opt), `tipo_clave` (opt), `unidad` (opt, max 100), `unidad_de_medida` (opt, max 50) |
| `MedicamentoCreate` | Base + `clave_cnis` (ClaveCnisStr) |
| `MedicamentoUpdate` | Todos opcionales: `descripcion`, `grupo`, `tipo_clave`, `unidad`, `unidad_de_medida`, `es_activo` |
| `MedicamentoResponse` | Base + `clave_cnis` (str), `es_activo` (bool). `from_attributes=True` |

---

### 6.2 UnidadMedica

| Schema | Campos |
|---|---|
| `UnidadMedicaBase` | `nombre_de_la_unidad` (str, 1-255), `id_entidad` (str, 1-100), `categoria_gerencial` (opt) |
| `UnidadMedicaCreate` | Base + `clues` (CluesStr) |
| `UnidadMedicaUpdate` | Todos opcionales: `nombre_de_la_unidad`, `id_entidad`, `categoria_gerencial` |
| `UnidadMedicaResponse` | Base + `clues` (str). `from_attributes=True` |

---

### 6.3 Usuario

| Schema | Campos destacados |
|---|---|
| `UsuarioBase` | `nombre_usuario`, `email` (EmailStr), `rol_nombre` (validado), `clues_unidad_asignada` (req. si RESPONSABLE_UNIDAD), `id_entidad` (req. si ADMIN_ESTATAL). Validadores: `rol_debe_ser_valido`, `validar_contexto_por_rol` |
| `UsuarioCreate` | Extiende `UsuarioBase`. La contraseña la genera el backend. |
| `UsuarioUpdate` | Opcionales: `nombre_usuario`, `rol_nombre`, `clues_unidad_asignada`, `id_entidad`, `password` (min 8) |
| `UsuarioResponse` | `id_usuario`, `nombre_usuario`, `email`, `rol_nombre`, `clues_unidad_asignada`, `id_entidad`, `debe_cambiar_password` |
| `UsuarioCreateResponse` | Extiende `UsuarioResponse` + `password_temporal` (solo en POST /usuarios) |

---

### 6.4 Paciente

`ESTATUS_EVOLUCION_OPTIONS = ["Inicia tx", "Tx fase intermedia", "Recaída", "Curación"]` — constante a nivel módulo en `schemas.py`, valores válidos para `estatus_evolucion`.

| Schema | Campos destacados |
|---|---|
| `PacienteBase` | `nombre_completo` (str, 2-255), `diagnostico_actual` (opt, max 5000), `clues_unidad_adscripcion` (CluesStr, normalizado a mayúsculas), `fecha_nacimiento` (opt) |
| `PacienteCreate` | Base + `curp_paciente` (CurpStr, validado contra regex oficial) |
| `PacienteUpdate` | Opcionales: `nombre_completo`, `diagnostico_actual`, `clues_unidad_adscripcion`, `fecha_nacimiento`, `es_activo`, `estatus_evolucion` (validado contra `ESTATUS_EVOLUCION_OPTIONS`) |
| `PacienteResponse` | `id_paciente`, `curp_paciente` (descifrado, `str \| None` — `None` si el paciente no tiene CURP), `nombre_completo` (descifrado), `diagnostico_actual` (descifrado, legacy), `clues_unidad_adscripcion`, `fecha_nacimiento`, `es_activo`, `estatus_evolucion`, `fecha_registro`, `id_usuario_registro`, `dias_adherencia` (calculado, registro activo más reciente), `tiene_prescripcion_activa`, `medicamentos_activos` (list[str]), `adherencia_medicamentos` (list[int \| None] — días de adherencia por medicamento activo, alineado posicionalmente con `medicamentos_activos`), `diagnosticos_activos` (list[str] — nombres de diagnósticos de prescripciones activas), `tiene_reaccion_adversa` (bool — True si existe al menos una reacción adversa en `reacciones_adversas`) |
| `PacienteListResponse` | `total`, `pagina`, `por_pagina`, `resultados` (list[PacienteResponse]) |
| `BusquedaCurpResponse` | `existe`, `id_paciente`, `nombre_completo`, `fecha_nacimiento`, `clues_unidad_adscripcion`, `nombre_unidad`, `total_registros` |
| `BusquedaNombreItem` | `id_paciente`, `nombre_completo`, `fecha_nacimiento` (opt), `curp_paciente` (opt, descifrado), `clues_unidad_adscripcion`, `nombre_unidad` (opt), `total_registros` |
| `BusquedaNombreResponse` | `resultados` (list[BusquedaNombreItem]) |

---

### 6.4b Expediente

| Schema | Campos destacados |
|---|---|
| `ExpedienteCreate` | `clues` (CluesStr, normalizado a mayúsculas), `numero_expediente` (str, 1-100) |
| `ExpedienteUpdate` | `numero_expediente` (str, 1-100) |
| `ExpedienteResponse` | `id_paciente`, `clues`, `numero_expediente`. `from_attributes=True` |

---

### 6.4c ReaccionAdversa

| Schema | Campos destacados |
|---|---|
| `ReaccionAdversaCreate` | `clave_cnis` (str), `comentario` (str, 1-2000) |
| `ReaccionAdversaResponse` | `id_reaccion`, `clave_cnis`, `nombre_medicamento` (de `medicamento.descripcion`), `comentario`, `nombre_usuario_registro` (`str \| None`), `email_usuario_registro` (`str \| None`), `fecha_registro`. `from_attributes=True` |

---

### 6.5 Medico

| Schema | Campos destacados |
|---|---|
| `MedicoBase` | `nombre_medico` (str, 2-255), `cedula` (str, 1-30), `email` (opt), `clues_adscripcion` (CluesStr) |
| `MedicoCreate` | Idéntico a Base |
| `MedicoUpdate` | Todos opcionales: `nombre_medico`, `cedula`, `email`, `clues_adscripcion`, `es_activo` (Soft Delete) |
| `MedicoResponse` | `id_medico`, `nombre_medico` (descifrado), `cedula` (descifrada), `email`, `clues_adscripcion`, `es_activo` |

---

### 6.6 Registro

| Schema | Campos destacados |
|---|---|
| `RegistroBase` | `id_medico`, `id_paciente`, `clave_cnis`, `clues` (normalizado), `id_diagnostico` (opt, FK → cat_diagnosticos), `fecha_inicio_tratamiento` (opt), `fecha_primera_administracion` (opt), `fecha_fin_tratamiento` (opt), `dosis_administrada` (opt), `peso` (opt), `talla` (opt), `estatus_diagnostico` (opt), `confirmado_por` (opt), `confirmado_mediante` (opt, str, max 200 — texto libre), `tratamiento_amparo` (bool, default False), `queja_derechos_humanos` (bool, default False), `prescripcion` (opt), `dosis` (opt, >0), `cantidad` (opt, >0), `frecuencia` (opt, >0), `unidad_tiempo` (opt), `duracion` (opt, >0) |
| `RegistroCreate` | Idéntico a Base |
| `RegistroUpdate` | Todos opcionales, incluye `id_diagnostico` y `es_activo` (Soft Delete) |
| `RegistroResponse` | Base + `id_registro`, `es_activo`, `fecha_registro_sistema`, `id_usuario_registro`, `nombre_paciente` (descifrado), `curp_paciente` (descifrado), `total_medicamento` (calculado), `id_registro_origen`, `medicamento` (MedicamentoResponse embebido), `medico` (MedicoResponse embebido), `diagnostico` (DiagnosticoResponse embebido, nullable) |
| `RegistroListResponse` | `total`, `pagina`, `por_pagina`, `resultados` (list[RegistroResponse]) |
| `RegistroCompletoCreate` | Un solo payload que crea/reutiliza paciente + prescripción: `id_paciente` (opt — paciente ya identificado por búsqueda, con o sin CURP), `curp_paciente` (opt, `CurpStr \| None`), `nombre_completo` (req si el paciente es nuevo), `fecha_nacimiento` (opt, solo si paciente nuevo), `clues_unidad_adscripcion` (opt), `id_diagnostico` (opt), `numero_expediente` (opt — si se provee, hace upsert del expediente del paciente en la unidad de la prescripción), más todos los campos de posología. Ver §7.4 para los 3 casos de identificación del paciente |
| `RegistroCompletoResponse` | Extiende `RegistroResponse` + `paciente_creado` (bool) |

---

### 6.7 Notificaciones de Continuidad

| Schema | Campos |
|---|---|
| `NotificacionResponse` | `id_registro`, `id_paciente`, `nombre_paciente`, `clave_cnis`, `descripcion_medicamento`, `clues`, `fecha_fin_tratamiento`, `fecha_limite` (fin + 30 días), `dias_restantes` (negativo = vencida), `es_activo`, `fecha_inicio_tratamiento`, `dosis_administrada`, `peso`, `talla`, `prescripcion`, `duracion`, `unidad_tiempo` |
| `NotificacionListResponse` | `total`, `resultados` (list[NotificacionResponse]) |
| `ValidarContinuidadRequest` | `nueva_fecha_fin_tratamiento` (opt Date) — requerida solo si el registro no tiene posología guardada |

---

### 6.8 Notificaciones de Transferencia

| Schema | Campos |
|---|---|
| `NotificacionTransferenciaResponse` | `id`, `id_paciente`, `nombre_paciente` (descifrado), `curp_paciente` (descifrado), `clues_unidad_origen`, `nombre_unidad_origen`, `clues_unidad_destino`, `nombre_unidad_destino`, `nombre_usuario_traslado`, `fecha_traslado` |
| `NotificacionTransferenciaListResponse` | `total`, `resultados` |

---

### 6.9 Requerimiento Teórico Mensual (RTM)

| Schema | Campos |
|---|---|
| `RtmMesItem` | `anio` (int), `mes` (int 1-12), `etiqueta` (str, ej. "Mayo 2026"), `cantidad` (float) |
| `RtmFilaResponse` | `clave_cnis`, `descripcion`, `grupo`, `unidad_de_medida`, `meses` (list[RtmMesItem]) |
| `RtmResponse` | `clues`, `nombre_unidad`, `generado_en`, `cabeceras` (list[str]), `filas` (list[RtmFilaResponse]) |

---

### 6.10 Autenticación

| Schema | Campos |
|---|---|
| `LoginRequest` | `email` (EmailStr), `password` (str, min 1) |
| `TokenResponse` | `access_token`, `token_type` ("bearer"), `rol_nombre`, `id_usuario`, `debe_cambiar_password`, `email`, `nombre_usuario`, `clues_unidad_asignada` (nullable), `nombre_unidad` (nullable), `id_entidad` (nullable) |
| `CambiarPasswordRequest` | `password_actual` (str, min 1), `password_nueva` (str, min 8) |

---

### Tipos anotados reutilizables

| Tipo | Restricción |
|---|---|
| `CurpStr` | str, exactly 18 chars, regex oficial SEP/RENAPO |
| `CluesStr` | str, 1-20 chars, patrón `^[A-Z0-9]+$` |
| `ClaveCnisStr` | str, 1-50 chars |
| `RolStr` | str, validado contra `Rol.TODOS` |

---

## 7. Endpoints

### 7.1 Autenticación (`/auth`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| POST | `/auth/login` | Público | Login. Recibe `OAuth2PasswordRequestForm` (form-data). Devuelve JWT + rol + `debe_cambiar_password`. |

---

### 7.2 Pacientes (`/pacientes`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/pacientes` | Todos | Lista paginada con filtro RBAC automático. Params: `solo_activos`, `pagina`, `por_pagina`, `clave_cnis`. Llama `marcar_registros_vencidos()`. |
| POST | `/pacientes` | Todos | Crear nuevo paciente. CURP cifrada + hash. Conflicto 409 si CURP duplicada. |
| GET | `/pacientes/buscar` | Todos | Búsqueda nacional por CURP. Sin filtro RBAC. |
| GET | `/pacientes/buscar-por-nombre` | Todos | Búsqueda nacional por nombre (para pacientes sin CURP). Sin filtro RBAC. Param: `q` (min 3 chars), `limite` (default 15, max 50). Descifra y normaliza (mayúsculas, sin acentos) cada `nombre_completo`; hace match si cada token de `q` es prefijo de algún token del nombre (acepta apellido-primero o nombre-primero). |
| GET | `/pacientes/{curp_paciente}` | Todos | Detalle completo. Lectura nacional sin restricción RBAC. |
| PATCH | `/pacientes/{curp_paciente}` | Todos (con restricciones por rol) | Actualización parcial. Si cambia `clues_unidad_adscripcion`, genera `NotificacionTransferencia` automáticamente. Si el payload incluye `estatus_evolucion`, estampa `id_usuario_ultimo_cambio_estatus` y `fecha_ultimo_cambio_estatus` antes de aplicar los cambios. |
| DELETE | `/pacientes/{curp_paciente}` | Todos (con acceso) | Soft Delete (`es_activo = False`). |
| GET | `/pacientes/{curp_paciente}/registros` | Todos | Todas las prescripciones del paciente, sin filtro de unidad. Param: `solo_activos`. |
| GET | `/pacientes/{curp_paciente}/expedientes` | Todos | Lista los expedientes (número de expediente por unidad) del paciente. |
| POST | `/pacientes/{curp_paciente}/expedientes` | Todos (con restricciones por rol) | Crea o actualiza (upsert) el número de expediente del paciente en una unidad (`clues` + `numero_expediente`). RESPONSABLE_UNIDAD solo puede gestionar expedientes de su propia unidad (403 si no coincide). 201 Created. |
| GET | `/pacientes/{curp_paciente}/reacciones-adversas` | Todos | Lista todas las reacciones adversas del paciente en orden descendente de fecha. Sin filtro RBAC (lectura nacional). Devuelve `list[ReaccionAdversaResponse]` |
| POST | `/pacientes/{curp_paciente}/reacciones-adversas` | Todos (con restricciones de acceso) | Registra una nueva reacción adversa. Aplica `_verificar_acceso_paciente()` (RESPONSABLE_UNIDAD → solo su unidad, ADMIN_ESTATAL → solo su estado). Guarda `id_usuario_registro`. 201 Created. |

> **Nota:** En todas las rutas con `{curp_paciente}`, el segmento acepta también el `id_paciente` numérico de un paciente sin CURP — resuelto por `_obtener_paciente_por_identificador()` (ver §3, "CURP opcional").

---

### 7.3 Médicos (`/medicos`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/medicos` | Todos | Lista activos (`es_activo=True`) con filtro RBAC geográfico automático. Param opcional: `clues_adscripcion`. |
| POST | `/medicos` | ADMIN_ESTATAL, SUPER_ADMIN | Crear médico. RESPONSABLE_UNIDAD: 403 (ya no puede registrar médicos). ADMIN_ESTATAL: unidades de su estado. SUPER_ADMIN: sin restricción. Nombre y cédula cifrados. |
| GET | `/medicos/{id_medico}` | Todos | Perfil de un médico. |
| PATCH | `/medicos/{id_medico}` | Todos con RBAC | Actualizar datos o dar de baja (`es_activo=False`). RBAC geográfico: RESPONSABLE_UNIDAD solo su unidad, ADMIN_ESTATAL solo su estado. Re-cifra nombre/cédula si cambian. |
| DELETE | `/medicos/{id_medico}` | Solo SUPER_ADMIN | Eliminación física (204 No Content). |

---

### 7.4 Registros (`/registros`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/registros` | Todos | Lista paginada. Filtro RBAC por **unidad actual del paciente** (no por unidad de la prescripción). Llama `marcar_registros_vencidos()`. |
| POST | `/registros` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Crear prescripción. Llama `_aplicar_posologia()` si hay campos de posología. |
| POST | `/registros/completo` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Crea (o reutiliza) paciente + prescripción en una llamada. Identificación del paciente, 3 casos: (1) `id_paciente` → paciente existente (con o sin CURP), reactiva si estaba inactivo; (2) `curp_paciente` → busca por `curp_hash`, crea uno nuevo con CURP si no existe; (3) ninguno → crea paciente nuevo sin CURP (`curp_hash=None`), requiere `nombre_completo`. 422 si se envían `id_paciente` y `curp_paciente` simultáneamente. |
| GET | `/registros/{id_registro}` | Todos | Detalle con validación RBAC. |
| PATCH | `/registros/{id_registro}` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Actualización parcial. Recalcula posología si se modifican campos de posología. ADMIN_ESTATAL recibe 403. |
| DELETE | `/registros/{id_registro}` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Soft Delete (`es_activo = False`). ADMIN_ESTATAL recibe 403. |
| PATCH | `/registros/{id_registro}/validar-continuidad` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Reactiva el registro y recalcula `fecha_fin_tratamiento`. Con posología: calcula desde hoy. Sin posología (legacy): requiere `nueva_fecha_fin_tratamiento` en el body. ADMIN_ESTATAL recibe 403. |
| POST | `/registros/{id_registro}/reemplazar` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Crea nuevo registro activo copiando el original con los cambios del payload; anula el original. Guarda `id_registro_origen` para trazabilidad. ADMIN_ESTATAL recibe 403. |

---

### 7.5 Notificaciones (`/notificaciones`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/notificaciones` | Todos | Registros con `fecha_fin_tratamiento + 30 días <= hoy + 7 días` (ventana de 7 días de alerta). Filtro RBAC aplicado. Llama `marcar_registros_vencidos()`. |
| GET | `/notificaciones/transferencias` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Traslados con `leida=False`. RESPONSABLE_UNIDAD solo ve traslados de su unidad origen. ADMIN_ESTATAL recibe 403. |
| PATCH | `/notificaciones/transferencias/{id_notificacion}/leer` | SUPER_ADMIN, RESPONSABLE_UNIDAD | Marca la notificación como leída. Guarda `id_usuario_leida` y `fecha_leida`. Retorna `{"ok": True}`. |

---

### 7.6 Reportes (`/reportes`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/reportes/resumen-detallado` | Todos | Datos crudos para Excel/PDF. Params: `fecha_inicio`, `fecha_fin`, `solo_activos`. Filtro RBAC por unidad actual del paciente. |
| GET | `/reportes/estatal` | ADMIN_ESTATAL, SUPER_ADMIN | Agrupados por unidad: total pacientes activos + total registros activos. Scope por entidad para ADMIN_ESTATAL. |
| GET | `/reportes/rtm` | Solo SUPER_ADMIN | Requerimiento Teórico Mensual. Params: `clues` (req), `meses` (1-24, default 7). Calcula consumo mensual proporcional por medicamento usando overlap de fechas con límites exclusivos. Solo prescripciones con posología completa. |

---

### 7.7 Catálogos (`/catalogos`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/catalogos/diagnosticos` | Todos | Lista diagnósticos. Param: `solo_activos` (default True). |
| POST | `/catalogos/diagnosticos` | Solo SUPER_ADMIN | Crear nuevo diagnóstico. Conflicto 409 si nombre duplicado. |
| PATCH | `/catalogos/diagnosticos/{id_diagnostico}` | Solo SUPER_ADMIN | Actualizar o desactivar diagnóstico. |
| GET | `/catalogos/medicamentos` | Todos | Lista del catálogo. Params: `solo_activos` (default True), `clues` (opcional — filtra solo medicamentos asignados a esa unidad vía JOIN con `unidad_medicamentos`). |
| POST | `/catalogos/medicamentos` | Solo SUPER_ADMIN | Crear nueva clave CNIS. Conflicto 409 si duplicada. |
| PATCH | `/catalogos/medicamentos/{clave_cnis}` | Solo SUPER_ADMIN | Actualizar o desactivar medicamento. |
| GET | `/catalogos/unidades` | Todos | Lista de unidades. Param: `id_entidad`. |
| POST | `/catalogos/unidades` | Solo SUPER_ADMIN | Crear nueva unidad. Conflicto 409 si CLUES duplicada. |
| PATCH | `/catalogos/unidades/{clues}` | Solo SUPER_ADMIN | Actualizar datos de una unidad. |

---

### 7.8 Usuarios (`/usuarios`)

| Método | Ruta | Rol requerido | Descripción |
|---|---|---|---|
| GET | `/usuarios` | Solo SUPER_ADMIN | Lista completa de usuarios. |
| POST | `/usuarios` | Solo SUPER_ADMIN | Crear usuario. Genera `password_temporal` aleatoria (12 chars alfanuméricos). La devuelve una sola vez en la respuesta. |
| POST | `/usuarios/me/cambiar-password` | Todos (sin require_password_cambiado) | Cambiar contraseña propia. Verifica contraseña actual. Pone `debe_cambiar_password = False`. |
| PATCH | `/usuarios/{id_usuario}` | Solo SUPER_ADMIN | Actualizar datos. Si incluye `password`, la hashea con bcrypt. |
| DELETE | `/usuarios/{id_usuario}` | Solo SUPER_ADMIN | Eliminación física. No puede eliminar la propia cuenta. |

---

## 8. Sistema RBAC

### Clase `Rol` (constants centralizadas en models.py)
```python
class Rol:
    SUPER_ADMIN         = "SUPER_ADMIN"
    ADMIN_ESTATAL       = "ADMIN_ESTATAL"
    RESPONSABLE_UNIDAD  = "RESPONSABLE_UNIDAD"
    TODOS = {SUPER_ADMIN, ADMIN_ESTATAL, RESPONSABLE_UNIDAD}
```

### `apply_rbac_filter(usuario: UsuarioActivo)` — Función central (auth.py)

| Rol | Filtro aplicado |
|---|---|
| `SUPER_ADMIN` | Sin filtro (ve todo) |
| `ADMIN_ESTATAL` | `UnidadMedica.id_entidad == usuario.id_entidad` |
| `RESPONSABLE_UNIDAD` | `Paciente.clues_unidad_adscripcion == usuario.clues_unidad_asignada` |

**Regla de registros (prescripciones):** El filtro RBAC de registros usa la **unidad actual del paciente** (`Paciente.clues_unidad_adscripcion`), no la unidad donde se generó la prescripción (`Registro.clues`). Esto implementa la regla "la prescripción sigue al paciente".

### Dependencias de FastAPI (auth.py)

| Dependencia | Descripción |
|---|---|
| `require_cualquier_rol` | Cualquier usuario autenticado con JWT válido |
| `require_password_cambiado` | Igual que anterior + `debe_cambiar_password = False` |
| `require_super_admin` | Solo SUPER_ADMIN |
| `require_admin_estatal_o_superior` | SUPER_ADMIN o ADMIN_ESTATAL |

### Helpers de verificación de acceso (main.py)

- `_verificar_acceso_paciente(paciente, usuario, db)`: Valida que el usuario puede operar sobre un paciente concreto.
- `_verificar_acceso_registro(registro, usuario, db)`: Valida acceso a un registro concreto usando la unidad del paciente, no la del registro.

---

## 9. Helpers Internos (main.py)

### `_aplicar_posologia(registro, unidad_medicamento, unidad_de_medida)`
Si todos los campos `dosis`, `frecuencia`, `duracion`, `unidad_tiempo` están presentes:
1. Genera el texto de `prescripcion` vía `_calcular_prescripcion_y_total()`.
2. Calcula `total_medicamento`.
3. Auto-calcula `fecha_fin_tratamiento = fecha_primera_administracion + duracion * factor` (fecha exclusiva).

### `_calcular_prescripcion_y_total(dosis, frecuencia, duracion, unidad_tiempo, unidad, cantidad, unidad_de_medida)`
- `factor` = `{"días": 1, "semanas": 7, "meses": 30}[unidad_tiempo]`
- `total = dosis * (24 / frecuencia) * duracion * factor`
- Texto: `"{dosis} {unidad_txt} de {cantidad} {unidad_de_medida}, cada {frecuencia} horas, por {duracion} {unidad_tiempo}"`

### `_pluralizar_unidad(unidad, cantidad)`
Pluraliza el nombre de la unidad del medicamento:
- `cantidad == 1` → devuelve singular.
- Unidades invariables (`ml`, `mg`, `mcg`, `g`, `ui`, `dosis`) → sin cambio.
- Termina en `-ón` → reemplaza por `-ones`.
- Termina en vocal → agrega `-s`.
- Caso general → agrega `-es`.

### `marcar_registros_vencidos(db)`
`UPDATE registros SET es_activo=False WHERE es_activo=True AND fecha_fin_tratamiento IS NOT NULL AND fecha_fin_tratamiento <= (hoy - 30 días)`. Patrón **lazy marking** sin scheduler externo.

### `_calcular_adherencia(id_paciente, db)`
Retorna `(date.today() - registro.fecha_inicio_tratamiento).days` del registro activo más reciente. Retorna `None` si no hay ninguno.

### RTM — cálculo de overlap mensual
```python
# Ambos límites son exclusivos para consistencia con fecha_fin_tratamiento
fin_mes_exclusivo = date(ay+1, 1, 1) if am == 12 else date(ay, am+1, 1)
overlap_inicio = max(inicio_mes, r.fecha_primera_administracion)
overlap_fin    = min(fin_mes_exclusivo, r.fecha_fin_tratamiento)
if overlap_inicio < overlap_fin:
    dias = (overlap_fin - overlap_inicio).days  # sin +1
    consumo_diario = r.dosis * (24 / r.frecuencia) * (r.cantidad or 1)
    totales[r.clave_cnis][(ay, am)] += consumo_diario * dias
```

---

## 10. Variables de Entorno Requeridas

```env
DATABASE_URL=postgresql://usuario:password@host:puerto/nombre_db
JWT_SECRET_KEY=<mínimo 32 caracteres aleatorios>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
FERNET_KEY=<clave Fernet base64 generada con Fernet.generate_key()>
```

En Railway (producción), `DATABASE_URL` apunta al servicio PostgreSQL interno:
`postgresql://postgres:<password>@<servicio>.railway.internal:5432/railway`

---

## 11. Despliegue en Railway

El backend se despliega usando el `Dockerfile` raíz del repositorio:

```dockerfile
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
```

Railway inyecta `$PORT` automáticamente. `--host 0.0.0.0` es obligatorio en contenedor. Las variables de entorno (`DATABASE_URL`, `JWT_SECRET_KEY`, `FERNET_KEY`, etc.) se configuran en el panel de Railway como "Service Variables" (disponibles en runtime).

---

## 12. Convenciones Importantes

| Convención | Descripción |
|---|---|
| **Soft Delete** | `es_activo = False` en `Paciente`, `Registro` y `Medico`. Nunca DELETE físico para estos modelos. |
| **Fernet** | CURP, nombre completo, diagnóstico (Paciente), nombre y cédula (Medico) se almacenan como `LargeBinary` cifrado. |
| **SHA-256** | `curp_hash` y `cedula_hash` permiten lookups eficientes sin descifrar. |
| **fecha_fin exclusiva** | `fecha_fin_tratamiento` marca el primer día que ya NO es parte del tratamiento. El frontend resta 1 al mostrar "último día real". |
| **Timestamps** | `server_default=func.now()` para que la BD estampe la hora (no el código Python). |
| **Paginación** | `pagina` (1-based), `por_pagina` (default 20, max 500). Offset = `(pagina - 1) * por_pagina`. |
| **Normalización** | `.strip().upper()` en validators Pydantic para CLUES y CURP antes de cualquier consulta. |
