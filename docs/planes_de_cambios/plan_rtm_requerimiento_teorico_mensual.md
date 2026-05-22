# Plan de Cambios — Requerimiento Teórico Mensual (RTM)

> Iniciado: 2026-05-22
> Relacionado con: blueprint_prescripcion_calculada.md, plan_recalculo_fin_tratamiento.md

---

## Contexto y Objetivo

Con la posología ya almacenada en cada prescripción activa (`dosis`, `cantidad`,
`frecuencia`, `duracion`, `unidad_tiempo`, `fecha_fin_tratamiento`) es posible calcular
cuánto medicamento necesitará cada unidad en los próximos meses.

El **Requerimiento Teórico Mensual (RTM)** es un reporte exclusivo de SUPER_ADMIN que,
dada una unidad médica (CLUES), muestra una tabla con:

- **Filas**: medicamentos con al menos una prescripción activa en esa unidad
- **Columnas**: mes actual + los 6 meses siguientes (7 columnas)
- **Celda**: suma total del medicamento requerido en ese mes (en ml, mg, etc.)

---

## No se requiere tabla nueva

El cálculo es 100 % derivado de datos existentes:
- `registros` → posología y fechas de cada prescripción
- `cat_medicamentos` → descripción, grupo y `unidad_de_medida`
- `cat_unidades` → nombre de la unidad

---

## Fórmula de cálculo

```
Para cada mes M (mes_inicio … mes_inicio + 6):
  inicio_M  = primer día del mes M
  fin_M     = último día del mes M

  Para cada prescripción activa con posología completa de la unidad U:
    overlap_inicio = max(inicio_M, fecha_primera_administracion)
    overlap_fin    = min(fin_M,    fecha_fin_tratamiento)

    Si overlap_inicio <= overlap_fin:
      dias_activos   = (overlap_fin - overlap_inicio).days + 1
      consumo_diario = dosis × cantidad × (24 / frecuencia)
      aporte         = consumo_diario × dias_activos
      total[clave_cnis][M] += aporte

Excluir:
  - Prescripciones sin posología completa (dosis/cantidad/frecuencia/duracion/unidad_tiempo nulos)
  - Prescripciones con es_activo = False
  - Prescripciones sin fecha_primera_administracion o fecha_fin_tratamiento
```

**Ejemplo:**
- Galsulfasa, dosis=1 inyección, cantidad=50 ml, frecuencia=24 h, activa 20-may → 10-jun
- Mayo (12 días activos): 1 × 50 × 1 × 12 = **600 ml**
- Junio (10 días activos): 1 × 50 × 1 × 10 = **500 ml**

---

## PASO 1 — Backend: nuevo endpoint y schema

**Estado:** ⏳ Pendiente
**Complejidad:** Media
**Archivos afectados:** `app/schemas.py`, `app/main.py`

### `app/schemas.py` — Nuevos schemas

```python
class RtmMesItem(BaseModel):
    anio: int
    mes: int          # 1–12
    etiqueta: str     # "Mayo 2026"
    cantidad: float   # total calculado, redondeado a 2 decimales

class RtmFilaResponse(BaseModel):
    clave_cnis: str
    descripcion: str
    grupo: str | None
    unidad_de_medida: str | None  # ml, mg, UI…
    meses: list[RtmMesItem]       # 7 ítems en orden cronológico

class RtmResponse(BaseModel):
    clues: str
    nombre_unidad: str | None
    generado_en: str
    cabeceras: list[str]           # ["Mayo 2026", …] — 7 etiquetas
    filas: list[RtmFilaResponse]   # una fila por medicamento con datos
```

### `app/main.py` — Endpoint `GET /reportes/rtm`

- [ ] Solo accesible por `SUPER_ADMIN` (`require_super_admin`)
- [ ] Query params:
  - `clues: str` — CLUES de la unidad (requerido)
  - `meses: int = 7` — número de meses a proyectar (default 7: actual + 6 siguientes)
- [ ] Algoritmo:
  1. Calcular lista de (año, mes) para los próximos `meses` meses desde el mes actual
  2. Buscar todas las prescripciones activas de la unidad con posología completa:
     ```python
     db.query(Registro).join(CatMedicamento).filter(
         Registro.clues == clues,
         Registro.es_activo == True,
         Registro.dosis.isnot(None),
         Registro.cantidad.isnot(None),
         Registro.frecuencia.isnot(None),
         Registro.fecha_primera_administracion.isnot(None),
         Registro.fecha_fin_tratamiento.isnot(None),
     )
     ```
  3. Para cada prescripción y cada mes: calcular el aporte con la fórmula
  4. Agrupar por `clave_cnis`, sumar aportes
  5. Ordenar filas por `clave_cnis`; incluir solo medicamentos con al menos un mes > 0
  6. Retornar `RtmResponse`

#### Validación
- [ ] Prescripción que cruza meses → cantidades proporcionales en cada columna
- [ ] Prescripción sin posología → excluida del resultado
- [ ] Unidad sin prescripciones activas con posología → lista vacía

---

## PASO 2 — Frontend: nueva API call

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `frontend/src/api/reportes.js`

- [ ] Nueva función:
  ```js
  export const getRtm = async (clues) => {
    const { data } = await axiosClient.get("/reportes/rtm", { params: { clues } });
    return data; // RtmResponse
  };
  ```

#### Validación
- [ ] Llamada devuelve `{ clues, nombre_unidad, cabeceras, filas }` correctamente

---

## PASO 3 — Frontend: nueva pestaña en ReportesPage

**Estado:** ⏳ Pendiente
**Complejidad:** Media
**Archivos afectados:** `frontend/src/pages/reportes/ReportesPage.jsx`

### 3.1 Nueva pestaña

- [ ] Agregar pestaña "RTM" visible **solo para SUPER_ADMIN**
  (junto a "Reporte Detallado" y "Reporte Estatal"):
  ```jsx
  {rolNombre === "SUPER_ADMIN" && (
    <TabBtn activo={tab === "rtm"} onClick={() => setTab("rtm")} icon={TrendingUp}>
      RTM
    </TabBtn>
  )}
  {tab === "rtm" && rolNombre === "SUPER_ADMIN" && <ReporteRTM />}
  ```

### 3.2 Componente `ReporteRTM`

- [x] **Selector de entidad**: `<select>` con las 32 entidades (igual que `UnidadesPage`)
- [x] Al elegir entidad: carga `listarUnidades(entidad)` y muestra tabla de resultados
- [x] **Buscador**: filtra client-side la lista por CLUES o nombre de unidad
- [x] Al hacer clic en una fila: selecciona la unidad y llama a `getRtm(clues)`
- [x] Unidad seleccionada: se muestra en un encabezado con botón "Cambiar unidad"
- [x] Mientras no haya unidad seleccionada: placeholder instructivo
- [ ] **Tabla**:
  ```
  | Clave CNIS | Descripción | Grupo | U. Medida | May 2026 | Jun 2026 | … (7 cols) |
  ```
  - Las celdas de cantidad muestran el valor redondeado a 2 decimales + la unidad de medida
    (ej. `600.00 ml`); si es 0 muestra `—`
  - Si no hay filas: mensaje "No hay prescripciones activas con posología en esta unidad"
  - Columnas de meses con fondo `bg-neutral-light` para distinguirlas de las descriptivas
  - El mes actual se resalta con borde o color diferente

- [ ] **Botón "Exportar Excel"** genera un `.xlsx` con la misma estructura de la tabla:
  - Nombre del archivo: `rtm_{clues}_{YYYY-MM}.xlsx`
  - Hoja: "RTM"
  - Fila de cabecera: Clave CNIS, Descripción, Grupo, U. Medida, mes1…mes7

#### Validación
- [ ] Sin selección → no hace petición al backend
- [ ] Al cambiar la unidad → recarga automáticamente
- [ ] Excel descargado con 7 columnas de meses y cantidades correctas
- [ ] Mes actual visualmente diferenciado del resto

---

## Archivos afectados por paso

| Archivo | P1 | P2 | P3 |
|---|:---:|:---:|:---:|
| `app/schemas.py` | ✏️ | — | — |
| `app/main.py` | ✏️ | — | — |
| `frontend/src/api/reportes.js` | — | ✏️ | — |
| `frontend/src/pages/reportes/ReportesPage.jsx` | — | — | ✏️ |

---

## Estado General

| Paso | Nombre | Estado |
|---|---|---|
| 1 | Backend: endpoint y schema | ✅ Completado |
| 2 | Frontend: API call | ✅ Completado |
| 3 | Frontend: pestaña RTM en ReportesPage | ✅ Completado |

---

## Correcciones post-implementación

### Bug 1 — Off-by-one en días activos (2026-05-22)

**Síntoma:** Una prescripción de 1 semana (7 días, 20 ml/día) mostraba **160 ml** en lugar de **140 ml**.

**Causa:** El cálculo usaba `(overlap_fin - overlap_inicio).days + 1` y la condición `overlap_inicio <= overlap_fin`. Como `fecha_fin_tratamiento` es **exclusiva** (primer día fuera del tratamiento), el `+1` contaba un día extra.

**Corrección en `app/main.py`:**
```python
# Antes (incorrecto)
if overlap_inicio <= overlap_fin:
    dias = (overlap_fin - overlap_inicio).days + 1

# Después (correcto)
if overlap_inicio < overlap_fin:
    dias = (overlap_fin - overlap_inicio).days
```

**Corrección en frontend** — los tres archivos que mostraban la "fecha estimada de fin" también usaban `+1` visualmente:
- `RegistroFormPage.jsx` → preview en sección Posología
- `RegistroDetallePage.jsx` → `calcularNuevaFechaFin()`
- `NotificacionesPage.jsx` → `calcularNuevaFechaFin()`

Todos corregidos a `fecha.setDate(fecha.getDate() + dur * factor - 1)` para mostrar el **último día inclusivo** real.

---

### Bug 2 — Inconsistencia en límite de fin de mes (2026-05-22)

**Síntoma:** Una prescripción activa durante 4 meses completos (20 ml/día) sumaba **4 640 ml** en lugar de **4 800 ml** (240 días × 20 ml).

**Causa:** El fin de mes se calculaba como el último día calendario del mes (límite **inclusivo**), pero `fecha_fin_tratamiento` es **exclusiva**. La comparación `min(fin_mes_inclusivo, fecha_fin_exclusiva)` producía un solapamiento incorrecto: por cada mes interno se perdía 1 día.

Ejemplo en junio (30 días): `overlap_fin = min(30-jun, 01-jul) = 30-jun` (inclusivo), luego `(30-jun - 01-jun).days = 29` días en lugar de 30.

**Corrección en `app/main.py`:**
```python
# Antes (incorrecto — fin de mes inclusivo)
_, ultimo_dia = calendar.monthrange(ay, am)
fin_mes = date(ay, am, ultimo_dia)          # ej. 30-jun (inclusivo)
overlap_fin = min(fin_mes, r.fecha_fin_tratamiento)
if overlap_inicio < overlap_fin:
    dias = (overlap_fin - overlap_inicio).days

# Después (correcto — fin de mes exclusivo, consistente con fecha_fin_tratamiento)
fin_mes_exclusivo = date(ay + 1, 1, 1) if am == 12 else date(ay, am + 1, 1)  # ej. 01-jul
overlap_fin = min(fin_mes_exclusivo, r.fecha_fin_tratamiento)
if overlap_inicio < overlap_fin:
    dias = (overlap_fin - overlap_inicio).days
```

**Principio clave:** Ambos extremos del intervalo de solapamiento deben ser del **mismo tipo** (ambos exclusivos o ambos inclusivos). La solución consistente es usar límites exclusivos en ambos lados.
