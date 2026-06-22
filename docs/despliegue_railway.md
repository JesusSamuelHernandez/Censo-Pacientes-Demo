# Guía de Despliegue en Railway

Checklist completo para cada deploy a Railway. Seguir en orden.

---

## 1. Pre-requisitos (solo una vez)

- Tener instalado Railway CLI o acceso al dashboard de Railway.
- Tener la URL de la base de datos de Railway guardada (variable `DATABASE_URL` del servicio PostgreSQL).

---

## 2. Antes de hacer push

### 2a. Verificar que los cambios locales funcionan

```bash
# Terminal 1 — backend
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Probar el flujo completo en `http://localhost:5173` antes de subir.

### 2b. Commit y push a la rama correspondiente

```bash
git add <archivos>
git commit -m "descripción"
git push origin <rama>
```

Railway detecta el push automáticamente y hace el deploy.

---

## 3. Migraciones de base de datos en Railway

> **IMPORTANTE:** Cada vez que se agreguen tablas nuevas o columnas a tablas existentes, hay que correr los scripts de migración contra la BD de Railway. `create_all()` solo crea tablas nuevas, no modifica las existentes.

### Paso 1 — Apuntar al .env de Railway temporalmente

Edita el archivo `.env` en la raíz del proyecto y reemplaza `DATABASE_URL` con la URL de Railway:

```
DATABASE_URL=postgresql://usuario:password@host:puerto/nombre_bd
```

> **IMPORTANTE:** Usa la URL **pública** (servicio PostgreSQL → pestaña **Connect** → "Public Network" / variable `DATABASE_PUBLIC_URL`), no la interna que aparece en pestaña "Variables" (`postgres.railway.internal`). La interna solo es alcanzable entre servicios de Railway; desde tu máquina local el script se queda colgado tratando de conectar (sin error visible) porque ese host no es accesible desde fuera de la red privada de Railway.

### Paso 2 — Correr los scripts necesarios

> **Lección aprendida (2026-06-22):** `migrar_medico_baja.py` (columna `medicos.es_activo`, de Blueprint v5) nunca se había corrido contra producción y causó 500 en `/medicos`, `/registros` y `/reportes/resumen-detallado` por meses sin detectarse, porque el checklist de "Paso 2" solo se actualiza con las migraciones del deploy en curso. Todas estas migraciones son idempotentes (no rompen nada si ya están aplicadas) — ante cualquier sospecha de columnas faltantes, es más seguro correr **todos** los scripts de la tabla del §4, no solo los del deploy actual.

Correr solo los scripts que correspondan a los cambios de este deploy:

```bash
# Migración estructural (nueva tabla / columna)
python scripts/migrar_diagnosticos.py

# Migración Soft Delete de médicos (medicos.es_activo) — verificar SIEMPRE,
# se detectó faltante en producción el 2026-06-22 pese a ser de Blueprint v5
python scripts/migrar_medico_baja.py

# Migración campos nuevos: fecha_nacimiento, tabla expedientes_paciente
python scripts/migrar_campos_nuevos.py

# Migración estatus de evolución del paciente (banderín de color)
python scripts/migrar_estatus_evolucion.py

# Migración CURP opcional (pacientes.curp_hash / curp_paciente nullable)
python scripts/migrar_paciente_curp_opcional.py

# Migración reacciones adversas (crea tabla reacciones_adversas si no existe)
python scripts/migrar_reacciones_adversas.py

# Migración confirmado_mediante (registros.confirmado_mediante)
python scripts/migrar_confirmado_mediante.py

# Migración caso relacionado con amparo/derechos humanos
python scripts/migrar_amparo_derechos_humanos.py

# Migración motivo de baja del paciente
python scripts/migrar_motivo_baja.py

# Migración motivo de baja múltiple (amplía pacientes.motivo_baja a VARCHAR(300))
python scripts/migrar_motivo_baja_multiple.py

# Carga inicial de catálogo (solo si es la primera vez o hay entradas nuevas)
python scripts/cargar_diagnosticos.py

# Carga relación unidad-medicamento (medicamentos disponibles por unidad) —
# verificar SIEMPRE, se detectó faltante en producción el 2026-06-22
python scripts/cargar_unidad_medicamentos.py
```

Otros scripts disponibles:
```bash
python scripts/cargar_medicamentos.py --actualizar --sincronizar   # catálogo CNIS completo (ver nota)
python scripts/cargar_unidades.py       # unidades médicas
python scripts/create_admin.py          # crear usuario SUPER_ADMIN inicial
```

> **Nota sobre `cargar_medicamentos.py`:** sin flags, solo inserta claves nuevas (modo incremental). Con `--actualizar`, también actualiza descripción/grupo/tipo_clave de claves existentes. Con `--sincronizar`, además desactiva (`es_activo=False`, Soft Delete — no elimina físicamente) los medicamentos de la BD que ya no aparecen en el Excel. Usar `--actualizar --sincronizar` juntos cuando el Excel representa el catálogo completo vigente (ej. tras una actualización del cuadro básico), no un incremental.

### Paso 3 — Restaurar el .env local

Regresa `DATABASE_URL` a tu base de datos local para seguir desarrollando.

---

## 4. Scripts de migración — cuándo usar cada uno

| Script | Cuándo ejecutarlo |
|--------|-------------------|
| `migrar_diagnosticos.py` | Primera vez que se despliega la tabla `cat_diagnosticos` y la columna `registros.id_diagnostico` |
| `migrar_medico_baja.py` | Primera vez que se despliega el Soft Delete de médicos (columna `medicos.es_activo`) |
| `migrar_unidad_medicamentos.py` | Primera vez que se despliega la tabla `unidad_medicamentos` (medicamentos por unidad) |
| `migrar_recalculo_fin.py` | Si se modifica la lógica de `fecha_fin_tratamiento` en registros existentes |
| `migrar_campos_nuevos.py` | Primera vez que se despliegan: `pacientes.fecha_nacimiento`, tabla `expedientes_paciente` |
| `migrar_estatus_evolucion.py` | Primera vez que se despliega el banderín de estatus de evolución: `pacientes.estatus_evolucion`, `pacientes.id_usuario_ultimo_cambio_estatus`, `pacientes.fecha_ultimo_cambio_estatus` |
| `migrar_paciente_curp_opcional.py` | Primera vez que se despliega el registro de pacientes sin CURP: vuelve nullable `pacientes.curp_hash` y `pacientes.curp_paciente` |
| `migrar_reacciones_adversas.py` | Primera vez que se despliega el módulo de reacciones adversas: crea tabla `reacciones_adversas` (idempotente, `[--]` si ya existe) |
| `migrar_confirmado_mediante.py` | Primera vez que se despliega el campo `confirmado_mediante` en `registros` |
| `migrar_amparo_derechos_humanos.py` | Primera vez que se despliegan `registros.tratamiento_amparo` y `registros.queja_derechos_humanos` |
| `migrar_motivo_baja.py` | Primera vez que se despliega `pacientes.motivo_baja` |
| `migrar_motivo_baja_multiple.py` | Primera vez que se despliega la selección múltiple de motivo de baja (amplía la columna a VARCHAR(300)) |
| `cargar_diagnosticos.py` | Primera vez o cuando se agregan diagnósticos al catálogo |
| `cargar_medicamentos.py` | Primera vez o cuando se actualiza el catálogo CNIS |
| `cargar_unidades.py` | Primera vez o cuando se agregan unidades médicas |
| `cargar_unidad_medicamentos.py` | Cada vez que se actualice el Excel `scripts/data/unidad_medicamentos.xlsx` |
| `create_admin.py` | Solo una vez, al crear el entorno de Railway |

---

## 5. Variables de entorno en Railway

Verificar que los servicios de Railway tengan estas variables configuradas:

### Backend (servicio FastAPI)
| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | URL de PostgreSQL de Railway (auto-generada) |
| `SECRET_KEY` / `JWT_SECRET_KEY` | Clave secreta para JWT (generar con `openssl rand -hex 32`) |
| `FERNET_KEY` | Clave de cifrado Fernet (generar con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `FRONTEND_URL` | URL del servicio frontend en Railway |

> **CRÍTICO — `FERNET_KEY` y `JWT_SECRET_KEY` deben ser valores literales fijos, NUNCA `${{secret(...)}}`.**
> La plantilla `${{secret(...)}}` de Railway genera un valor **aleatorio nuevo en cada deploy**, y Railway no conserva historial de esos valores. Para `JWT_SECRET_KEY` esto solo desconecta a todos los usuarios en cada deploy (molesto). Para `FERNET_KEY` es **irreversible**: cualquier dato cifrado con la clave de un deploy anterior queda permanentemente ilegible en el siguiente — no hay forma de recuperarlo. Esto ya pasó una vez (2026-06-22, ver `.context/activeContext.md`) y costó perder 10 pacientes + 5 médicos de prueba. Verificar en Variables que ambas claves sean texto fijo (no una referencia `${{...}}`) y guardar una copia en un lugar seguro fuera de Railway.

### Frontend (servicio Vite/Node)
| Variable | Valor |
|----------|-------|
| `VITE_API_BASE_URL` | URL del servicio backend en Railway |

---

## 6. Configuración de los servicios en Railway

### Backend
- **Root Directory:** `/` (raíz del repositorio)
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Frontend
- **Root Directory:** `/frontend`
- **Build Command:** `npm run build`
- **Start Command:** `npm run preview -- --host 0.0.0.0 --port $PORT`
- En `vite.config.js` → `allowedHosts` debe incluir el dominio de Railway.

---

## 7. Verificación post-deploy

1. Abrir la URL del frontend en Railway.
2. Hacer login con el usuario SUPER_ADMIN.
3. Verificar que el módulo de Pacientes Activos carga sin errores.
4. Registrar una prescripción de prueba y verificar que el dropdown de diagnósticos aparece.
5. Verificar los campos nuevos del deploy de campos adicionales (junio 2026):
   - Al registrar un paciente, el campo **Fecha de nacimiento** aparece y se guarda.
   - Al buscar un paciente existente por CURP, el card muestra su fecha de nacimiento (si la tiene).
   - Al crear una prescripción, aparece el campo **Número de expediente**.
   - En el formulario de registro, el campo **Confirmado por** aparece deshabilitado y fijo en "Médico tratante".
6. Verificar el banderín de estatus de evolución (junio 2026):
   - En **Pacientes Activos**, cada paciente muestra un banderín de color a la izquierda de su nombre (verde por defecto).
   - Al hacer clic en el banderín se abre una ventana con la leyenda de colores y permite cambiar el estatus.
   - El cambio de color persiste al recargar la página.
7. Verificar CURP opcional / búsqueda por nombre (junio 2026):
   - Registrar un paciente nuevo **sin CURP** (solo nombre completo) y confirmar que se guarda correctamente.
   - Buscarlo por nombre desde "Registrar Paciente" (apellido o nombre primero, con/sin acentos) y confirmar que aparece con su fecha de nacimiento en formato DD/MM/AA.
   - Seleccionarlo y verificar que "Ver historial" carga su detalle.
8. Revisar los logs del backend en Railway si hay errores 500.
