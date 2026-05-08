# Blueprint — Prescripción Calculada y Total de Medicamento

> Iniciado: 2026-05-08
> Relacionado con: Blueprint v6, Blueprint Transferencia Paciente

---

## Contexto y Objetivo

Al registrar una prescripción queremos capturar **cómo** se toma el medicamento
(dosis + frecuencia + duración) para:

1. Generar automáticamente el campo `prescripcion` como texto legible:
   *"2 tabletas, cada 8 horas, por 7 días"*
2. Calcular y guardar `total_medicamento` (ej. 42 tabletas) para uso futuro
   en el **Requerimiento Teórico Mensual (RTM)** por medicamento y por unidad.

El campo `cat_medicamentos.unidad` indicará la unidad de la dosis (tabletas,
inyecciones, ml, etc.) y será la base tanto del texto de prescripción como del RTM.

---

## Fórmula de cálculo

```
duracion_dias:
  unidad_tiempo = "días"    → duracion × 1
  unidad_tiempo = "semanas" → duracion × 7
  unidad_tiempo = "meses"   → duracion × 30

total_medicamento = dosis × (24 / frecuencia) × duracion_dias

prescripcion = "{dosis} {unidad}, cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
```

Ejemplo: dosis=2, frecuencia=8, duracion=7, unidad_tiempo="días", unidad="tabletas"
→ total = 2 × 3 × 7 = **42**
→ prescripcion = **"2 tabletas, cada 8 horas, por 7 días"**

---

## Nuevos campos en BD

| Tabla | Campo | Tipo | Descripción |
|---|---|---|---|
| `cat_medicamentos` | `unidad` | VARCHAR(100) | Ej. "tabletas", "inyecciones", "ml" |
| `registros` | `dosis` | FLOAT | Cantidad de unidades por toma |
| `registros` | `frecuencia` | INT | Horas entre tomas (ej. 8, 12, 24) |
| `registros` | `unidad_tiempo` | VARCHAR(50) | "días", "semanas" o "meses" |
| `registros` | `duracion` | INT | Número de unidades de tiempo |
| `registros` | `total_medicamento` | FLOAT | Calculado: dosis × (24/frecuencia) × días. No se muestra en el formulario |

> ⚠️ Los campos existentes `dosis_administrada` (VARCHAR) y `prescripcion` (TEXT)
> **permanecen en la BD** pero se ocultan del formulario. `prescripcion` se
> sobreescribe con el texto auto-generado.

---

## PASO 1 — Migración de BD

**Estado:** ✅ Completado — ejecutado 2026-05-08, 6 columnas agregadas
**Complejidad:** Baja
**Archivos afectados:** `scripts/migrar_prescripcion.py`

`create_all` solo crea tablas nuevas, no agrega columnas a tablas existentes.
Se necesita un script de migración con los `ALTER TABLE`.

### Script — `scripts/migrar_prescripcion.py`
- [ ] Conectar a la BD vía `SessionLocal` / `engine`
- [ ] Ejecutar los siguientes `ALTER TABLE` (con `IF NOT EXISTS` para idempotencia):
  ```sql
  ALTER TABLE cat_medicamentos ADD COLUMN IF NOT EXISTS unidad VARCHAR(100);
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS dosis FLOAT;
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS frecuencia INT;
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS unidad_tiempo VARCHAR(50);
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS duracion INT;
  ALTER TABLE registros ADD COLUMN IF NOT EXISTS total_medicamento FLOAT;
  ```
- [ ] Imprimir resumen de columnas agregadas / ya existentes

#### Validación
- [ ] Ejecutar script y verificar columnas en la BD con `\d registros` y `\d cat_medicamentos`

---

## PASO 2 — Modelos ORM y Schemas

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `app/models.py`, `app/schemas.py`

### Backend — `app/models.py`

- [ ] En `CatMedicamento`: agregar `unidad: Mapped[str | None] = mapped_column(String(100), nullable=True)`
- [ ] En `Registro`: agregar los 5 nuevos campos:
  ```python
  dosis: Mapped[float | None] = mapped_column(nullable=True)
  frecuencia: Mapped[int | None] = mapped_column(Integer, nullable=True)
  unidad_tiempo: Mapped[str | None] = mapped_column(String(50), nullable=True)
  duracion: Mapped[int | None] = mapped_column(Integer, nullable=True)
  total_medicamento: Mapped[float | None] = mapped_column(nullable=True)
  ```

### Backend — `app/schemas.py`

- [ ] En `MedicamentoResponse`: agregar `unidad: str | None = None`
- [ ] En `MedicamentoCreate` y `MedicamentoUpdate`: agregar `unidad: str | None = None`
- [ ] En `RegistroBase`: agregar `dosis`, `frecuencia`, `unidad_tiempo`, `duracion`
  (NO `total_medicamento` — se calcula en backend, no lo envía el cliente)
- [ ] En `RegistroUpdate`: mismos 4 campos opcionales
- [ ] En `RegistroResponse`: agregar los 5 campos (`total_medicamento` incluido, solo lectura)

#### Validación
- [ ] El servidor arranca sin errores tras los cambios

---

## PASO 3 — Lógica de cálculo en backend

**Estado:** ⏳ Pendiente
**Complejidad:** Media
**Archivos afectados:** `app/main.py`

### Helper `_pluralizar_unidad` (singular/plural español)

- [ ] Nueva función auxiliar para pluralizar la unidad del medicamento:
  ```python
  def _pluralizar_unidad(unidad: str, cantidad: float) -> str:
      if cantidad == 1:
          return unidad
      u = unidad.lower()
      if u in {"ml", "mg", "mcg", "g", "ui", "dosis"}:   # invariables
          return unidad
      if u.endswith("ón"):                                  # inyección → inyecciones
          return unidad[:-2] + "ones"
      if u[-1] in "aeiouáéíóú":                            # tableta → tabletas
          return unidad + "s"
      return unidad + "es"                                  # consonante genérica
  ```

### Helper `_calcular_prescripcion_y_total`

- [ ] Nueva función auxiliar:
  ```python
  def _calcular_prescripcion_y_total(
      dosis: float,
      frecuencia: int,
      duracion: int,
      unidad_tiempo: str,   # "días" | "semanas" | "meses"
      unidad: str,          # singular, de cat_medicamentos.unidad, ej. "tableta"
  ) -> tuple[str, float]:
      """Retorna (texto_prescripcion, total_medicamento)."""
      factor = {"días": 1, "semanas": 7, "meses": 30}.get(unidad_tiempo, 1)
      duracion_dias = duracion * factor
      total = dosis * (24 / frecuencia) * duracion_dias
      unidad_txt = _pluralizar_unidad(unidad, dosis)
      texto = f"{dosis:g} {unidad_txt}, cada {frecuencia} horas, por {duracion} {unidad_tiempo}"
      return texto, round(total, 2)
  ```

> **Regla de plural**: `unidad` se guarda en singular en el catálogo (ej. "tableta",
> "inyección"). El helper aplica: invariables (ml, mg…) sin cambio; terminación en
> "-ón" → "-ones"; vocal final → + "s"; otra consonante → + "es".

### Aplicar en endpoints

- [ ] En `crear_registro` (`POST /registros`): si los 4 campos están presentes,
  buscar `cat_medicamentos.unidad`, llamar al helper y guardar `prescripcion` y
  `total_medicamento` en el registro antes del commit.

- [ ] En `actualizar_registro` (`PATCH /registros/{id}`): mismo criterio —
  si alguno de los 4 campos llega en el payload, recalcular.

- [ ] En `crear_registro_completo` (`POST /registros/completo`): mismo criterio.

#### Validación
- [ ] `POST /registros/completo` con dosis=2, frecuencia=8, duracion=7, unidad_tiempo="días"
  devuelve `prescripcion="2 tabletas, cada 8 horas, por 7 días"` y `total_medicamento=42`
- [ ] Sin los 4 campos completos: `prescripcion` y `total_medicamento` quedan en `null`

---

## PASO 4 — Catálogo de medicamentos: campo `unidad`

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `frontend/src/pages/catalogos/MedicamentosPage.jsx`

El campo `unidad` debe poder editarse desde el catálogo para que los médicos
al registrar una prescripción vean la unidad correcta del medicamento.

### Frontend — `MedicamentosPage.jsx`
- [ ] En el formulario de creación/edición de medicamento: agregar campo de texto
  `unidad` con placeholder "ej. tabletas, inyecciones, ml"
- [ ] En la tabla del catálogo: agregar columna "Unidad" junto a descripción

#### Validación
- [ ] Guardar un medicamento con unidad "tabletas" → se refleja en `GET /catalogos/medicamentos`

---

## PASO 5 — Formulario de registro (frontend)

**Estado:** ⏳ Pendiente
**Complejidad:** Media
**Archivos afectados:** `frontend/src/pages/registros/RegistroFormPage.jsx`,
`frontend/src/api/pacientes.js`

### Cambios en el formulario

**Ocultar** (sin eliminar del schema):
- [ ] Campo `dosis_administrada` (VARCHAR) — oculto, se deja de enviar
- [ ] Campo `prescripcion` como textarea manual — ahora lo genera el backend

**Agregar sección "Posología"** con 3 controles:

| Campo | Control | Detalle |
|---|---|---|
| `dosis` | `<input type="number" step="0.5" min="0.5">` | Etiqueta dinámica: "{unidad}" del medicamento (o "Dosis" si no tiene unidad) |
| `frecuencia` | `<input type="number" min="1">` | Prefijo "Cada", sufijo "horas" |
| `duracion` + `unidad_tiempo` | `<input type="number">` + `<select>` | Select: Días / Semanas / Meses |

- [ ] Al cargar un medicamento por CURP (`buscarPacientePorCurp` ya devuelve el med),
  mostrar la `unidad` del medicamento como etiqueta del campo `dosis`
- [ ] Los 3 controles son opcionales — si no se llenan, el registro se guarda sin
  `prescripcion` y `total_medicamento`
- [ ] Si se llenan los 3, el backend calcula y guarda ambos campos automáticamente

> ⚠️ La `unidad` del medicamento se necesita en el frontend solo para la etiqueta
> visual. Ya viene en `RegistroResponse.medicamento.unidad` al cargar un registro
> para editar.

#### Validación
- [ ] Llenar dosis=1, frecuencia=24, duracion=3, unidad_tiempo=Días con medicamento
  unidad="inyecciones" → backend guarda `prescripcion="1 inyecciones, cada 24 horas, por 3 días"`,
  `total_medicamento=3`
- [ ] Sin llenar posología → registro se guarda igual que antes

---

## PASO 6 — Visualización: historial, reportes y Excel

**Estado:** ⏳ Pendiente
**Complejidad:** Baja
**Archivos afectados:** `PacienteDetallePage.jsx`, `ReportesPage.jsx`

### `PacienteDetallePage.jsx` — Historial de prescripciones
- [ ] Columna "Dosis" → renombrar a "Prescripción"
- [ ] Mostrar `r.prescripcion` en lugar de `r.dosis_administrada`
- [ ] Si `r.prescripcion` es null: mostrar "—"

### `ReportesPage.jsx` — Reporte Detallado (tabla)
- [ ] Columna "Dosis" → renombrar a "Prescripción"
- [ ] Mostrar `r.dosis_administrada` → `r.prescripcion` (campo del objeto de reporte)
  > ⚠️ Verificar que `reporte_resumen_detallado` en `main.py` incluya `prescripcion`
  > en su dict de respuesta (actualmente incluye `dosis_administrada`)

### `ReportesPage.jsx` — Excel
- [ ] En `exportarExcel`: cambiar `"Dosis": r.dosis_administrada` →
  `"Prescripción": r.prescripcion`

#### Validación
- [ ] Historial del paciente muestra "2 tabletas, cada 8 horas, por 7 días" en la columna Prescripción
- [ ] Excel descargado incluye columna "Prescripción" con el texto correcto

---

## Archivos afectados por paso

| Archivo | P1 | P2 | P3 | P4 | P5 | P6 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `scripts/migrar_prescripcion.py` | ✏️ nuevo | — | — | — | — | — |
| `app/models.py` | — | ✏️ | — | — | — | — |
| `app/schemas.py` | — | ✏️ | — | — | — | — |
| `app/main.py` | — | — | ✏️ | — | — | ✏️ |
| `MedicamentosPage.jsx` | — | — | — | ✏️ | — | — |
| `RegistroFormPage.jsx` | — | — | — | — | ✏️ | — |
| `PacienteDetallePage.jsx` | — | — | — | — | — | ✏️ |
| `ReportesPage.jsx` | — | — | — | — | — | ✏️ |

---

## Estado General

| Paso | Nombre | Estado |
|---|---|---|
| 1 | Migración de BD (ALTER TABLE) | ✅ Completado |
| 2 | Modelos ORM y Schemas | ✅ Completado |
| 3 | Lógica de cálculo en backend | ✅ Completado |
| 4 | Catálogo de medicamentos: campo unidad | ✅ Completado |
| 5 | Formulario de registro (frontend) | ✅ Completado |
| 6 | Visualización: historial, reportes y Excel | ✅ Completado |
