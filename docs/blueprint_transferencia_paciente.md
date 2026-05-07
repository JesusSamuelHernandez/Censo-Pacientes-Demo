# Blueprint — Transferencia de Paciente y Visibilidad de Prescripciones

> Iniciado: 2026-05-06
> Relacionado con: Blueprint v6, Blueprint Detalles 01

---

## Contexto y Problema

Cuando un paciente se transfiere de Unidad A a Unidad B (cambiando `clues_unidad_adscripcion`),
se generan dos problemas:

1. **Historial incompleto**: El doctor en Unidad B ve el historial del paciente pero no ve las
   prescripciones generadas en Unidad A, porque el filtro RBAC actual usa `Registro.clues` (unidad
   donde se generó la prescripción), no la unidad a la que pertenece el paciente.

2. **Lista de prescripciones desactualizada**: El médico de Unidad B no ve en su lista de
   prescripciones las de Unidad A para los pacientes transferidos a su unidad.

3. **Unidad de origen sin aviso**: La Unidad A pierde visibilidad del paciente sin saber
   que fue transferido, por quién y hacia dónde.

---

## Decisiones Tomadas

| Decisión | Detalle |
|---|---|
| Historial del paciente | Siempre muestra TODAS las prescripciones del paciente, sin filtro de unidad |
| Lista de prescripciones (`GET /registros`) | `RESPONSABLE_UNIDAD` filtra por pacientes de su unidad (JOIN), no por unidad de prescripción |
| Prescripciones en Unidad A | Desaparecen de su lista cuando el paciente es transferido |
| ADMIN_ESTATAL | Sin cambios — ya puede ver todo su estado |
| SUPER_ADMIN | Sin cambios — ya ve todo |
| Notificación de transferencia | Se marca como leída **por unidad** (quien sea de la unidad que la acepte, desaparece para todos) |
| ⚠️ Pendiente confirmar | ¿La notificación se acepta por unidad o por usuario? |

---

## PASO 1 — Historial del paciente: todas sus prescripciones

**Estado:** ✅ Completado
**Complejidad:** Baja
**Archivos afectados:** `app/main.py`, `app/schemas.py`, `frontend/src/pages/pacientes/PacienteDetallePage.jsx`, `frontend/src/api/pacientes.js`

### Problema
`PacienteDetallePage` carga las prescripciones con `listarRegistros()` (RBAC-filtrado por unidad),
luego filtra client-side por `id_paciente`. Resultado: solo se ven prescripciones de la unidad
del médico actual, aunque el paciente tenga historial en otras unidades.

### Solución
Nuevo endpoint `GET /pacientes/{curp}/registros` que devuelve TODOS los registros del paciente,
sin filtro de unidad. El acceso a este endpoint requiere únicamente poder leer al paciente
(acceso ya abierto nacionalmente desde el Blueprint v6).

#### Backend — `app/main.py`
- [x] Nuevo endpoint: `GET /pacientes/{curp_paciente}/registros`
  - Busca al paciente por `curp_hash` (sin RBAC de unidad)
  - Devuelve todos sus registros con `joinedload(medicamento, medico)`
  - Sin filtro de `Registro.clues`
  - Sí aplica `marcar_registros_vencidos(db)` primero
  - Acepta query param `solo_activos: bool = False`
  - Response: `RegistroListResponse`

#### Frontend — `frontend/src/api/pacientes.js`
- [x] Nueva función: `listarRegistrosDePaciente(curp, soloActivos = false)`

#### Frontend — `PacienteDetallePage.jsx`
- [x] Reemplazar `listarRegistros(...)` + filtro client-side por `listarRegistrosDePaciente(curp)`
- [x] Quitar el `filter((reg) => reg.id_paciente === p.id_paciente)` que ya no es necesario

#### Validación
- [ ] Doctor en Unidad B ve prescripciones generadas en Unidad A al abrir el historial
- [ ] `GET /pacientes/{curp}/registros` devuelve todos los registros sin importar unidad

---

## PASO 2 — Lista de prescripciones: filtrar por pacientes de la unidad

**Estado:** ✅ Completado
**Complejidad:** Media
**Archivos afectados:** `app/main.py`

### Problema
`GET /registros` para `RESPONSABLE_UNIDAD` filtra por `Registro.clues == user.clues`.
Esto significa "prescripciones generadas EN mi unidad". Con la transferencia de pacientes,
se necesita "prescripciones de pacientes QUE PERTENECEN a mi unidad".

### Solución
Cambiar el filtro RBAC de `RESPONSABLE_UNIDAD` en `listar_registros` de:
```
Registro.clues == user.clues_unidad_asignada
```
a:
```
JOIN pacientes → paciente.clues_unidad_adscripcion == user.clues_unidad_asignada
```

Esto hace que las prescripciones "sigan al paciente": si se transfiere a Unidad B,
sus prescripciones de Unidad A ya aparecen en la lista de Unidad B (y desaparecen de A).

#### Backend — `app/main.py`
- [x] En `listar_registros`: cambiar el bloque RBAC de `RESPONSABLE_UNIDAD` a JOIN con Paciente
- [x] Mismo cambio en `_verificar_acceso_registro`: verifica unidad del paciente (no de la prescripción)
- [x] Mismo cambio en `reporte_resumen_detallado`: ya tenía el JOIN, solo se cambió el campo de filtro

**Decisión tomada**: RESPONSABLE_UNIDAD de Unidad B puede ver, editar y anular prescripciones
de pacientes transferidos a su unidad (Opción A — la prescripción sigue al paciente en todo).

#### Validación
- [ ] Doctor en Unidad B ve prescripciones de pacientes transferidos a su unidad
- [ ] Doctor en Unidad A ya NO ve prescripciones de pacientes transferidos a Unidad B
- [ ] Los reportes (`/reportes/resumen-detallado`) también reflejan el cambio

---

## PASO 3 — Notificación de transferencia de paciente

**Estado:** ✅ Completado
**Complejidad:** Alta
**Archivos afectados:** `app/models.py`, `app/schemas.py`, `app/main.py`, BD (nueva tabla), `frontend/`

### Objetivo
Cuando un médico transfiere a un paciente de Unidad A a Unidad B, la Unidad A recibe
una notificación con:
- Nombre y CURP del paciente
- Unidad destino (Unidad B)
- Usuario que realizó el traslado
- Fecha y hora del traslado

La notificación aparece en un nuevo apartado del módulo de Notificaciones.
Una vez que un usuario de Unidad A la acepta ("Enterado"), desaparece para toda la unidad.

### Modelo de datos — Nueva tabla `notificaciones_transferencia`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | Integer PK | Autoincremental |
| `id_paciente` | Integer FK | Paciente transferido |
| `clues_unidad_origen` | String(20) FK | Unidad que pierde al paciente |
| `clues_unidad_destino` | String(20) FK | Unidad que recibe al paciente |
| `id_usuario_traslado` | Integer FK | Usuario que realizó el cambio |
| `fecha_traslado` | DateTime | Timestamp automático |
| `leida` | Boolean | False = pendiente, True = aceptada |
| `id_usuario_leida` | Integer FK nullable | Quién la aceptó |
| `fecha_leida` | DateTime nullable | Cuándo fue aceptada |

#### Backend — `app/models.py`
- [x] Nueva clase `NotificacionTransferencia` con los campos del modelo

#### Backend — `app/schemas.py`
- [x] Nuevo schema `NotificacionTransferenciaResponse` y `NotificacionTransferenciaListResponse`

#### Backend — `app/main.py`

**Trigger al transferir paciente:**
- [x] En `actualizar_paciente`: captura `clues_anterior`, detecta cambio tras commit y crea notificación

**Nuevos endpoints:**
- [x] `GET /notificaciones/transferencias`
- [x] `PATCH /notificaciones/transferencias/{id}/leer`

#### BD — Migración
- [x] Tabla creada automáticamente por `Base.metadata.create_all` al reiniciar el servidor

#### Frontend — `NotificacionesPage.jsx`
- [x] Reestructurada con dos pestañas: "Prescripciones" y "Traslados"
- [x] Tarjetas de traslado con: nombre, CURP, unidad destino, usuario, fecha
- [x] Botón "Enterado" que llama al endpoint y recarga
- [x] Estado vacío: "Sin traslados pendientes"

#### Frontend — `Sidebar.jsx` (badge)
- [x] `Promise.allSettled` suma ambos conteos; errores 403 se ignoran silenciosamente

#### Validación
- [ ] Transferir paciente de A a B → aparece notificación en Unidad A
- [ ] Dar clic en "Enterado" desde Unidad A → desaparece la notificación
- [ ] El badge del sidebar refleja el conteo correcto incluyendo traslados

---

## Archivos afectados por paso

| Archivo | P1 | P2 | P3 |
|---|:---:|:---:|:---:|
| `app/models.py` | — | — | ✏️ |
| `app/schemas.py` | — | — | ✏️ |
| `app/main.py` | ✏️ | ✏️ | ✏️ |
| `frontend/src/api/pacientes.js` | ✏️ | — | — |
| `frontend/src/api/notificaciones.js` | — | — | ✏️ |
| `PacienteDetallePage.jsx` | ✏️ | — | — |
| `NotificacionesPage.jsx` | — | — | ✏️ |
| `Sidebar.jsx` | — | — | ✏️ |

---

## Pregunta pendiente antes de implementar Paso 2

¿Puede un médico de Unidad B **editar o anular** una prescripción que fue generada
en Unidad A pero cuyo paciente ahora pertenece a Unidad B?

- **Opción A**: Sí puede (prescripción sigue al paciente en todo)
- **Opción B**: Solo puede verla, no modificarla (la unidad que la creó mantiene la autoría)

---

## Estado General

| Paso | Nombre | Estado |
|---|---|---|
| 1 | Historial del paciente: todas sus prescripciones | ✅ Completado |
| 2 | Lista de prescripciones: filtrar por pacientes de la unidad | ✅ Completado |
| 3 | Notificación de transferencia de paciente | ✅ Completado |
