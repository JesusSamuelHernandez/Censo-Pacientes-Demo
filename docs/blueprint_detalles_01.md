# Blueprint Detalles 01 — Mejoras de UX y Visualización

> Iniciado: 2026-04-28
> Continuación del Blueprint v6. Mejoras de interfaz, visualización de datos y correcciones de flujo.

---

## Decisiones Técnicas Globales

| Decisión | Detalle |
|---|---|
| "Vencida" vs "Anulada" | Calculado en **frontend**: `es_activo=False` + `fecha_fin_tratamiento + 30 días <= hoy` → "Vencida"; si no → "Anulada". Sin cambio en BD. |
| Nombre/CURP en prescripciones | Backend agrega `nombre_paciente` y `curp_paciente` a `RegistroResponse` via joinedload del paciente. |
| CURP persiste al regresar | Frontend: al navegar al historial pasa `{ from: "registro-form", curpOrigen: curp }`. Al regresar, navega a `/registros/nuevo` con ese estado y el formulario lo lee al montar. |
| Medicamentos activos en pacientes | Backend agrega `medicamentos_activos: list[str]` a `PacienteResponse`. Una sola query adicional por página (sin N+1). |

---

## PASO 1 — Renombres de módulos y etiquetas

**Estado:** ⏳ Pendiente
**Complejidad:** Mínima — solo cambios de texto en frontend
**Archivos afectados:** `Sidebar.jsx`, `RegistrosPage.jsx`, `App.jsx` (si aplica)

### Cambios

| Elemento | Texto actual | Texto nuevo |
|---|---|---|
| Label nav "Prescripciones" en Sidebar | "Prescripciones" | "Registrar Paciente" |
| Botón en RegistrosPage | "Registrar Prescripción" | "Registrar Paciente" |
| Título h2 en RegistrosPage | "Prescripciones" | "Registrar Paciente" |
| Label nav "Pacientes" en Sidebar | "Pacientes" | "Pacientes Activos" |

#### Frontend — `Sidebar.jsx`
- [ ] Cambiar label del nav item que apunta a `/registros`: "Prescripciones" → "Registrar Paciente"
- [ ] Cambiar label del nav item que apunta a `/pacientes`: "Pacientes" → "Pacientes Activos"

#### Frontend — `RegistrosPage.jsx`
- [ ] Cambiar texto del botón de creación: "Registrar Prescripción" → "Registrar Paciente"
- [ ] Cambiar el `h2` del encabezado: "Prescripciones" → "Registrar Paciente"
- [ ] Actualizar el subtítulo a: "X prescripciones registradas"

#### Validación
- [ ] El sidebar muestra los nuevos nombres
- [ ] El botón y el título de la lista reflejan los cambios

---

## PASO 2 — Etiqueta "Vencida" para prescripciones expiradas

**Estado:** ⏳ Pendiente
**Complejidad:** Baja — lógica pura en frontend
**Archivos afectados:** `RegistrosPage.jsx`, `PacienteDetallePage.jsx`

### Lógica de cálculo (frontend)

```
Si es_activo = false:
  Si fecha_fin_tratamiento != null
    Y fecha_fin_tratamiento + 30 días <= hoy
  → mostrar "Vencida" (badge rojo)
  Si no → mostrar "Anulada" (badge gris)
Si es_activo = true → mostrar "Activa" (badge verde)
```

#### Frontend — `RegistrosPage.jsx`
- [ ] Crear función utilitaria `getEstadoRegistro(registro)` que retorna `"activa" | "vencida" | "anulada"`
- [ ] Reemplazar el badge de estado actual por uno que use esa función
- [ ] Colores: Activa = verde, Vencida = rojo, Anulada = gris

#### Frontend — `PacienteDetallePage.jsx`
- [ ] Aplicar la misma función `getEstadoRegistro()` en la tabla de historial de prescripciones

#### Validación
- [ ] Una prescripción con `es_activo=False` y `fecha_fin` hace más de 30 días muestra "Vencida"
- [ ] Una prescripción anulada manualmente (sin `fecha_fin` o sin haber vencido) muestra "Anulada"

---

## PASO 3 — Nombre y CURP del paciente en la lista de prescripciones

**Estado:** ⏳ Pendiente
**Complejidad:** Media — requiere cambio en backend (joinedload + descifrado)
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `RegistrosPage.jsx`

### Objetivo
La tabla de prescripciones actualmente muestra solo `#id_paciente`. Mostrar nombre completo y CURP, y opcionalmente un link al historial del paciente.

#### Backend — `app/schemas.py`
- [ ] Agregar a `RegistroResponse`:
  - `nombre_paciente: str | None = None`
  - `curp_paciente: str | None = None`

#### Backend — `app/main.py`
- [ ] En `listar_registros`: agregar `joinedload(Registro.paciente)` a la query
- [ ] En `_registro_to_response`: descifrar y poblar `nombre_paciente` y `curp_paciente` desde `r.paciente`
- [ ] Mismo cambio en `obtener_registro`

#### Frontend — `RegistrosPage.jsx`
- [ ] Reemplazar la columna "Paciente ID" por "Paciente" que muestre nombre completo y CURP
- [ ] El nombre del paciente será un link clickeable que navega a `/pacientes/{curp_paciente}`
  - Navega con `state: { from: "registro-form" }` para mostrar el botón regresar

#### Validación
- [ ] La lista de prescripciones muestra nombre y CURP en cada fila
- [ ] Al hacer click en el nombre, navega al historial del paciente
- [ ] El botón "Regresar al formulario" en el historial funciona

---

## PASO 4 — CURP persiste al volver del historial

**Estado:** ⏳ Pendiente
**Complejidad:** Baja — manejo de estado de navegación
**Archivos afectados:** `RegistroFormPage.jsx`, `PacienteDetallePage.jsx`

### Problema
Al navegar al historial del paciente desde el formulario de prescripción y volver, la CURP que se había escrito desaparece porque React desmonta y remonta el componente.

### Solución
Cambiar el flujo de navegación para pasar la CURP como estado:

1. **Al ir al historial** (desde el widget de CURP): navegar con `{ from: "registro-form", curpOrigen: curpBusqueda }`
2. **Al regresar** (en `PacienteDetallePage`): en lugar de `navigate(-1)`, navegar a `/registros/nuevo` con `{ curpPreCargado: location.state.curpOrigen }`
3. **Al montar el formulario**: leer `location.state?.curpPreCargado` y pre-cargar la CURP

#### Frontend — `RegistroFormPage.jsx`
- [ ] Importar `useLocation` de react-router-dom
- [ ] Al montar: si `location.state?.curpPreCargado` existe, hacer `setCurpBusqueda(location.state.curpPreCargado)`
- [ ] Al navegar al historial: pasar también `curpOrigen: curpBusqueda` en el state

#### Frontend — `PacienteDetallePage.jsx`
- [ ] Cambiar el botón "Regresar al formulario":
  - Si viene de registro-form: `navigate("/registros/nuevo", { state: { curpPreCargado: location.state?.curpOrigen } })`
  - Si no: `navigate(-1)` (comportamiento actual para otros contextos)

#### Validación
- [ ] Escribir CURP en el formulario → ver historial → regresar → la CURP sigue escrita
- [ ] La búsqueda nacional se dispara automáticamente con la CURP pre-cargada

---

## PASO 5 — Tarjeta de detalle de prescripción en notificaciones

**Estado:** ⏳ Pendiente
**Complejidad:** Baja — solo frontend
**Archivos afectados:** `NotificacionesPage.jsx`

### Objetivo
Antes de validar la continuidad de una prescripción, el médico puede ver todos sus datos en una tarjeta expandible.

### Diseño
Cada fila de la tabla de notificaciones tendrá un botón "Ver detalle" que expande una tarjeta inline (debajo de la fila o en un panel lateral) con:
- Nombre completo del paciente
- Medicamento (clave + descripción)
- Unidad (CLUES)
- Fecha de inicio de tratamiento
- Fecha de fin de tratamiento
- Días restantes / vencida hace N días
- Dosis administrada (si existe)
- Peso / Talla (si existen)
- Prescripción (texto, si existe)

El botón "Validar" permanece accesible desde la tarjeta expandida.

**Nota:** La mayoría de estos datos ya vienen en `NotificacionResponse`. Los que no vienen (`fecha_inicio_tratamiento`, `dosis_administrada`, `peso`, `talla`, `prescripcion`) hay que agregar al schema y al endpoint.

#### Backend — `app/schemas.py`
- [ ] Agregar a `NotificacionResponse`:
  - `fecha_inicio_tratamiento: date | None`
  - `dosis_administrada: str | None`
  - `peso: Decimal | None`
  - `talla: Decimal | None`
  - `prescripcion: str | None`

#### Backend — `app/main.py`
- [ ] Poblar los nuevos campos en `listar_notificaciones` desde cada `Registro`

#### Frontend — `NotificacionesPage.jsx`
- [ ] Estado `filaExpandida: int | null` para controlar qué fila está expandida
- [ ] Botón "Ver detalle" / "Ocultar" en cada fila
- [ ] Panel expandible que muestra la tarjeta con todos los datos

#### Validación
- [ ] Al hacer click en "Ver detalle" se expande la tarjeta con la info completa
- [ ] El botón "Validar" sigue funcionando desde la tarjeta expandida

---

## PASO 6 — Medicamentos activos en lista de pacientes + filtro

**Estado:** ⏳ Pendiente
**Complejidad:** Media — requiere cambio en backend y frontend
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `PacientesPage.jsx`

### Objetivo
La lista de pacientes activos muestra, por cada paciente, los medicamentos de sus prescripciones activas. Además, hay un filtro para ver solo los pacientes con un medicamento específico.

#### Backend — `app/schemas.py`
- [ ] Agregar a `PacienteResponse`:
  - `medicamentos_activos: list[str]` — lista de descripciones (o clave_cnis si descripción no existe)

#### Backend — `app/main.py`
- [ ] En `listar_pacientes`: agregar query param `clave_cnis: str | None = None`
  - Si se provee: filtrar pacientes que tienen un registro activo con esa clave
- [ ] Calcular `medicamentos_activos` de forma eficiente: una sola query para toda la página actual, agrupada por `id_paciente`
- [ ] Actualizar `_paciente_to_response` para aceptar y pasar `medicamentos_activos`
- [ ] Actualizar `obtener_paciente` para calcular y devolver `medicamentos_activos`

#### Frontend — `PacientesPage.jsx`
- [ ] Nueva columna "Medicamentos" en la tabla que muestra las descripciones (badges por medicamento)
- [ ] Nuevo filtro: `ComboBox` de medicamentos (llama `GET /catalogos/medicamentos`) arriba de la tabla
- [ ] Al seleccionar un medicamento: recargar la lista con el filtro `clave_cnis=xxx`
- [ ] Al limpiar el filtro: volver a la lista sin filtro

#### Validación
- [ ] La columna "Medicamentos" muestra las claves/descripciones de prescripciones activas
- [ ] Seleccionar un medicamento en el filtro muestra solo pacientes con esa prescripción activa
- [ ] Limpiar el filtro restaura la lista completa

---

## Archivos afectados por paso

| Archivo | P1 | P2 | P3 | P4 | P5 | P6 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `app/schemas.py` | — | — | ✏️ | — | ✏️ | ✏️ |
| `app/main.py` | — | — | ✏️ | — | ✏️ | ✏️ |
| `Sidebar.jsx` | ✏️ | — | — | — | — | — |
| `RegistrosPage.jsx` | ✏️ | ✏️ | ✏️ | — | — | — |
| `RegistroFormPage.jsx` | — | — | — | ✏️ | — | — |
| `PacienteDetallePage.jsx` | — | ✏️ | — | ✏️ | — | — |
| `NotificacionesPage.jsx` | — | — | — | — | ✏️ | — |
| `PacientesPage.jsx` | — | — | — | — | — | ✏️ |

---

## Estado General

| Paso | Nombre | Estado |
|---|---|---|
| 1 | Renombres de módulos y etiquetas | ✅ Completado 2026-04-28 |
| 2 | Etiqueta "Vencida" para prescripciones expiradas | ⏳ Pendiente |
| 3 | Nombre y CURP del paciente en prescripciones | ⏳ Pendiente |
| 4 | CURP persiste al volver del historial | ⏳ Pendiente |
| 5 | Tarjeta de detalle en notificaciones | ⏳ Pendiente |
| 6 | Medicamentos activos en lista de pacientes + filtro | ⏳ Pendiente |
