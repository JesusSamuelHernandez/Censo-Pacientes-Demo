# Plan de Cambios — Recálculo de Fin de Tratamiento y Validación de Prescripción

> Iniciado: 2026-05-08
> Relacionado con: blueprint_prescripcion_calculada.md

---

## Contexto y Objetivo

Este plan extiende el trabajo de prescripción calculada con las siguientes mejoras:

1. **Campo `cantidad`** — complementa a `dosis` para expresar "2 tabletas **de 10 mg**"
2. **`unidad_de_medida`** en catálogo — define si la cantidad se mide en mg, ml, etc.
3. **Auto-cálculo de `fecha_fin_tratamiento`** a partir de `fecha_primera_administracion` + duración
4. **Rediseño del flujo "Validar continuidad"** — confirma duración sin elegir fecha manual
5. **"Editar y validar" desde Notificaciones** — crea nueva prescripción, anula la anterior, guarda vínculo
6. **Modal de detalle en historial del paciente** — ver prescripción sin salir de la página

---

## Nuevos campos en BD

| Tabla | Campo | Tipo | Descripción |
|---|---|---|---|
| `cat_medicamentos` | `unidad_de_medida` | VARCHAR(50) | Ej. "mg", "ml", "UI" |
| `registros` | `cantidad` | FLOAT | Cantidad por unidad (ej. 10 para "10 mg") |
| `registros` | `id_registro_origen` | INTEGER FK nullable | Apunta al registro que esta prescripción reemplaza |

---

## Fórmula de texto de prescripción actualizada

```
Con cantidad:
"{dosis} {unidad}(s) de {cantidad} {unidad_de_medida}, cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
→ "2 tabletas de 10 mg, cada 8 horas, por 7 días"

Sin cantidad (comportamiento anterior):
"{dosis} {unidad}(s), cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
→ "2 tabletas, cada 8 horas, por 7 días"
```

## Cálculo automático de `fecha_fin_tratamiento`

```
fecha_fin_tratamiento = fecha_primera_administracion + duracion_dias

duracion_dias:
  unidad_tiempo = "días"    → duracion × 1
  unidad_tiempo = "semanas" → duracion × 7
  unidad_tiempo = "meses"   → duracion × 30

Regla: si se llenan los campos de posología, fecha_primera_administracion es OBLIGATORIA.
Si no se llena posología, fecha_fin_tratamiento puede seguir siendo null.
```

## Flujo "Validar continuidad" (nuevo)

```
Antes: el médico elegía manualmente una nueva fecha de fin.
Ahora: el sistema calcula  nueva_fecha_fin = hoy + duracion_dias (usando la duración guardada).

Si el registro NO tiene duración guardada → se muestra el selector de fecha como fallback.
```

## Flujo "Editar y validar" desde Notificaciones

```
1. Médico abre detalle de prescripción vencida/próxima a vencer desde Notificaciones
2. Hace clic en "Editar y validar"
3. Ve el formulario de edición con los datos actuales precargados
4. Modifica los campos necesarios y guarda
5. El backend:
   a. Crea un nuevo Registro con los datos modificados + id_registro_origen = id_original
   b. Marca el Registro original como es_activo = False (anulada)
   c. El nuevo registro queda activo
6. En el historial del paciente aparecen ambas prescripciones
   (la nueva activa, la original anulada con indicador visual de reemplazo)
```

---

## PASO 1 — Migración de BD

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `scripts/migrar_recalculo_fin.py`

- [ ] Crear `scripts/migrar_recalculo_fin.py` con `IF NOT EXISTS`:
  ```sql
  ALTER TABLE cat_medicamentos ADD COLUMN IF NOT EXISTS unidad_de_medida VARCHAR(50);
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS cantidad FLOAT;
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS id_registro_origen INTEGER
      REFERENCES registros(id_registro) ON DELETE SET NULL;
  ```
- [ ] Script idempotente con resumen de columnas agregadas / ya existentes

#### Validación
- [ ] Ejecutar script y verificar columnas

---

## PASO 2 — Modelos ORM y Schemas

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `app/models.py`, `app/schemas.py`

### `app/models.py`
- [ ] `CatMedicamento`: agregar `unidad_de_medida: Mapped[str | None]`
- [ ] `Registro`: agregar `cantidad: Mapped[float | None]` y
  `id_registro_origen: Mapped[int | None]` (FK self-referencial a `registros`)

### `app/schemas.py`
- [ ] `MedicamentoBase` y `MedicamentoUpdate`: agregar `unidad_de_medida: str | None`
- [ ] `RegistroBase`: agregar `cantidad: float | None`
- [ ] `RegistroUpdate`: agregar `cantidad: float | None`
- [ ] `RegistroResponse`: agregar `cantidad`, `id_registro_origen`

#### Validación
- [ ] `python -m py_compile app/models.py app/schemas.py` sin errores

---

## PASO 3 — Lógica de backend

**Estado:** ⏳ Pendiente
**Complejidad:** Alta
**Archivos afectados:** `app/main.py`

### 3.1 Actualizar `_calcular_prescripcion_y_total`

- [ ] Recibir también `cantidad: float | None` y `unidad_de_medida: str | None`
- [ ] Si están presentes, insertar `"de {cantidad} {unidad_de_medida}"` en el texto:
  ```
  "2 tabletas de 10 mg, cada 8 horas, por 7 días"
  ```
- [ ] Si no están, mantener comportamiento actual sin ese fragmento

### 3.2 Actualizar `_aplicar_posologia`

- [ ] Además de calcular `prescripcion` y `total_medicamento`, calcular
  `fecha_fin_tratamiento` si `fecha_primera_administracion` está presente:
  ```python
  registro.fecha_fin_tratamiento = (
      registro.fecha_primera_administracion + timedelta(days=duracion_dias)
  )
  ```
- [ ] Pasar también `cantidad` y `unidad_de_medida` al helper de texto

### 3.3 Agregar validación en `crear_registro` y `crear_registro_completo`

- [ ] Si los 4 campos de posología están presentes y `fecha_primera_administracion`
  es None → devolver `422` con detalle:
  `"La fecha de primera administración es obligatoria cuando se indica posología."`

### 3.4 Actualizar `PATCH /registros/{id}/validar-continuidad`

- [ ] Ya **no** recibe `nueva_fecha_fin_tratamiento` como parámetro obligatorio
- [ ] Nueva lógica:
  - Si el registro tiene `duracion` y `unidad_tiempo` guardados:
    calcular `nueva_fecha_fin = date.today() + timedelta(days=duracion_dias)`
  - Si **no** los tiene (registro legacy sin posología):
    seguir aceptando `nueva_fecha_fin_tratamiento` del payload como fallback
- [ ] Actualizar `ValidarContinuidadRequest` en schemas:
  ```python
  nueva_fecha_fin_tratamiento: date | None = None  # fallback para registros sin duración
  ```
- [ ] Reactivar el registro: `es_activo = True`

### 3.5 Nuevo endpoint `POST /registros/{id}/reemplazar`

- [ ] Crea una nueva prescripción con los datos del payload modificado
- [ ] Asigna `id_registro_origen = id` en el nuevo registro
- [ ] Marca el original como `es_activo = False`
- [ ] Solo accesible para `RESPONSABLE_UNIDAD` (de la unidad del paciente) y `SUPER_ADMIN`
- [ ] Response: `RegistroCompletoResponse` del nuevo registro con `paciente_creado = False`
- [ ] RBAC: mismas reglas que `crear_registro`

#### Validación
- [ ] Continuidad sin posología → acepta fecha manual
- [ ] Continuidad con posología → calcula desde hoy
- [ ] Reemplazar → nuevo registro activo + original anulado + `id_registro_origen` enlazado

---

## PASO 4 — Catálogo: campo `unidad_de_medida`

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `frontend/src/pages/catalogos/MedicamentosPage.jsx`

- [ ] Agregar `unidad_de_medida` a los schemas Zod (`schemaCrear`, `schemaEditar`)
- [ ] Agregar `unidad_de_medida` a `defaultValues` del modal
- [ ] Agregar campo de texto en el formulario junto a "Unidad de dosis":
  placeholder `"ej. mg, ml, UI, mcg"`
- [ ] Agregar columna "U. Medida" en la tabla del catálogo
- [ ] Incluir en los payloads de crear y editar

#### Validación
- [ ] Guardar medicamento con `unidad_de_medida = "mg"` → reflejado en el catálogo

---

## PASO 5 — Formulario de registro: `cantidad`, `fecha_fin` auto-calculada

**Estado:** ⏳ Pendiente
**Complejidad:** Media
**Archivos afectados:** `frontend/src/pages/registros/RegistroFormPage.jsx`

### Cambios en la sección de Posología

- [ ] Agregar campo `cantidad` (number, step=0.01) con etiqueta dinámica
  usando `unidad_de_medida` del medicamento seleccionado:
  ```
  Cantidad por unidad
  [10.00] mg  (etiqueta: unidad_de_medida del medicamento)
  ```
- [ ] Mover `fecha_primera_administracion` **dentro** de la sección Posología
  (deja de ser un campo independiente genérico y pasa a ser parte del cálculo)
- [ ] Marcarla como **obligatoria** cuando hay posología: mostrar asterisco y
  validar en `onSubmit`
- [ ] **Eliminar** el campo manual `fecha_fin_tratamiento` del formulario
  (ahora se calcula automáticamente en el backend)
- [ ] Actualizar el preview de prescripción para incluir `cantidad`:
  `"2 tabletas de 10 mg, cada 8 horas, por 7 días"`
- [ ] Mostrar en el preview la fecha de fin calculada:
  ```
  Fin de tratamiento estimado: 15/05/2026
  ```

### Modo edición

- [ ] Cargar `cantidad` desde el registro existente
- [ ] Mostrar `fecha_fin_tratamiento` actual como informativo (no editable directamente)
- [ ] Recalcular si se modifica algún campo de posología o `fecha_primera_administracion`

### `_prepararPayload`

- [ ] Parsear `cantidad` → `parseFloat`
- [ ] NO enviar `fecha_fin_tratamiento` (el backend la calcula)

#### Validación
- [ ] Guardar con posología sin `fecha_primera_administracion` → error de validación
- [ ] Preview muestra: `"2 tabletas de 10 mg, cada 8 horas, por 7 días"` y fecha fin

---

## PASO 6 — Notificaciones: nuevo flujo de validación y edición

**Estado:** ⏳ Pendiente
**Complejidad:** Alta
**Archivos afectados:** `frontend/src/pages/notificaciones/NotificacionesPage.jsx`,
`frontend/src/api/registros.js`, `frontend/src/pages/registros/RegistroFormPage.jsx`

### 6.1 Modal "Validar continuidad" rediseñado

- [ ] Hacer el modal más ancho (`max-w-lg` en lugar de `max-w-sm`) para que
  se vea el nombre completo del medicamento
- [ ] **Si el registro tiene duración guardada**: mostrar duración y fecha calculada,
  y un botón "Confirmar" que llama al endpoint sin parámetros adicionales:
  ```
  ┌──────────────────────────────────────────┐
  │ Validar continuidad                       │
  │ Martínez López J C                        │
  │ IMIGLUCERASA - SOLUCIÓN INYECTABLE 400U   │
  │                                           │
  │ Duración del tratamiento: 7 días          │
  │ Nueva fecha fin: 15/05/2026               │
  │                                           │
  │ [Cancelar]          [Confirmar]           │
  └──────────────────────────────────────────┘
  ```
- [ ] **Si el registro NO tiene duración** (legacy): mostrar el selector de fecha
  como antes (fallback)

### 6.2 Actualizar llamada a `validarContinuidad` en `registros.js`

- [ ] La función ya no envía `nueva_fecha_fin_tratamiento` cuando hay duración;
  solo envía payload vacío `{}`
- [ ] El endpoint del backend decide si necesita la fecha o no

### 6.3 Botón "Editar y validar" en `RegistroDetallePage`

- [ ] Cuando `location.state?.from === "notificaciones"`:
  mostrar botón **"Editar y validar"** (además del botón "Editar" normal que ya existe)
- [ ] El botón navega a `/registros/:id/editar` con
  `{ ...state, modo: "reemplazar" }` en `location.state`
- [ ] Agregar `reemplazarRegistro(id, payload)` en `registros.js`
  → `POST /registros/{id}/reemplazar`

### 6.4 Modificar `RegistroFormPage` en modo "reemplazar"

- [ ] Si `location.state?.modo === "reemplazar"`:
  - Cambiar el título a "Editar y validar prescripción"
  - Agregar aviso: *"Al guardar se creará una nueva prescripción activa y la actual quedará anulada."*
  - El botón "Guardar" llama a `reemplazarRegistro` en lugar de `actualizarRegistro`
  - Al completar: navegar a `/notificaciones` con un toast de éxito

### 6.5 Indicador visual de reemplazo en historial

- [ ] En `PacienteDetallePage`, en la tabla de historial, mostrar junto a las
  prescripciones anuladas que tienen `id_registro_origen` un badge pequeño
  `"Reemplazada"` (diferente al badge `"Anulada"`)
- [ ] En las prescripciones que tienen `id_registro_origen` (son reemplazos)
  mostrar badge `"Validada"` junto al estado

#### Validación
- [ ] Validar con duración → modal muestra fecha calculada, sin selector de fecha
- [ ] Validar sin duración → modal muestra selector de fecha (legacy)
- [ ] Editar y validar → nueva prescripción activa + original anulada + vínculo
- [ ] Historial muestra badges "Reemplazada" y "Validada" correctamente

---

## PASO 7 — Modal de detalle en historial del paciente

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `frontend/src/pages/pacientes/PacienteDetallePage.jsx`

- [ ] Al hacer clic en cualquier fila de la tabla de historial, abrir un modal
  con los detalles completos de la prescripción (solo lectura)
- [ ] El modal muestra:
  - ID, estado, medicamento (clave + descripción completa)
  - Médico prescriptor
  - Posología completa: dosis, cantidad, frecuencia, duración, prescripción generada
  - Total de medicamento
  - Fechas: inicio, primera administración, fin de tratamiento
  - Peso y talla
  - Estatus diagnóstico, confirmado por
  - Si tiene `id_registro_origen`: enlace "Ver prescripción original #ID"
- [ ] Cursor `cursor-pointer` en las filas de la tabla para indicar que son clicables
- [ ] Botón "Cerrar" para volver al historial sin perder el contexto

#### Validación
- [ ] Clic en fila abre modal con todos los datos de la prescripción
- [ ] Clic en "Cerrar" cierra el modal y el historial permanece visible
- [ ] El modal muestra el vínculo a la prescripción original cuando aplica

---

## Archivos afectados por paso

| Archivo | P1 | P2 | P3 | P4 | P5 | P6 | P7 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `scripts/migrar_recalculo_fin.py` | ✏️ | — | — | — | — | — | — |
| `app/models.py` | — | ✏️ | — | — | — | — | — |
| `app/schemas.py` | — | ✏️ | ✏️ | — | — | — | — |
| `app/main.py` | — | — | ✏️ | — | — | — | — |
| `MedicamentosPage.jsx` | — | — | — | ✏️ | — | — | — |
| `RegistroFormPage.jsx` | — | — | — | — | ✏️ | ✏️ | — |
| `NotificacionesPage.jsx` | — | — | — | — | — | ✏️ | — |
| `registros.js` (api) | — | — | — | — | — | ✏️ | — |
| `RegistroDetallePage.jsx` | — | — | — | — | — | ✏️ | — |
| `PacienteDetallePage.jsx` | — | — | — | — | — | ✏️ | ✏️ |

---

## Dependencias entre pasos

```
P1 → P2 → P3 → P5
               P4 (independiente de P3)
               P6 (depende de P3 para endpoint /reemplazar)
P7 (independiente, puede hacerse en paralelo con P4)
```

---

## Estado General

| Paso | Nombre | Estado |
|---|---|---|
| 1 | Migración de BD | ✅ Completado |
| 2 | Modelos ORM y Schemas | ✅ Completado |
| 3 | Lógica de backend | ✅ Completado |
| 4 | Catálogo: campo unidad_de_medida | ✅ Completado |
| 5 | Formulario de registro: cantidad y fecha_fin auto | ✅ Completado |
| 6 | Notificaciones: nuevo flujo validación y edición | ✅ Completado |
| 7 | Modal de detalle en historial del paciente | ✅ Completado |
