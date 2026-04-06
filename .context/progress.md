# Progress — Historial de Hitos y Tareas Pendientes

## Tareas Completadas (heredadas de sesión con Gemini)
- [x] Definir stack tecnológico (Blueprint v4).
- [x] Diseñar esquema de base de datos (5 tablas).
- [x] Definir matriz RBAC (Blueprint §4).
- [x] Definir endpoints completos (Blueprint §5.1–5.5).
- [x] Implementar `app/database.py` — Conexión PostgreSQL + `get_db()`.
- [x] Implementar `app/models.py` — Los 5 modelos ORM (SQLAlchemy 2.0 Mapped).
- [x] Implementar `app/schemas.py` — Pydantic v2 completo con validaciones CURP/CLUES.
- [x] Implementar `app/auth.py` — JWT, `apply_rbac_filter()`, dependencias de rol RBAC.
- [x] Implementar `app/main.py` — Todos los endpoints del Blueprint.
- [x] Crear `create_admin.py` — Script para insertar SUPER_ADMIN (usó bcrypt directo).
- [x] Configurar Docker + PostgreSQL 15.
- [x] Crear primer usuario SUPER_ADMIN en la BD.

## Tareas Pendientes
- [x] **FIX BLOQUEANTE**: Corregir incompatibilidad bcrypt/passlib en `app/auth.py` — reemplazado CryptContext por bcrypt directo.
- [x] Validar login exitoso vía Swagger UI (obtener `access_token`).
- [x] Poblar catálogo de Unidades Médicas — BCIMB000010 Hospital General de Ensenada, Baja California.
- [x] Poblar catálogo de Medicamentos — 010.000.0291.00 Metilsulfato de neostigmina.
- [x] Registrar paciente de prueba (HEHJ871224HGRRRS01 — Samuel Hernandez) y asignarle suministro.
- [x] Probar flujo completo: Login → Registrar Paciente → PATCH Paciente → Asignar Suministro ✅
- [x] Crear usuarios de prueba para los 3 roles y validar RBAC end-to-end ✅
  - SUPER_ADMIN: sin filtro, ámbito Nacional.
  - ADMIN_ESTATAL (admin.bc@test.com): filtro por Baja California.
  - RESPONSABLE_UNIDAD (responsable.ensenada@test.com): filtro por BCIMB000010.
- [x] Probar reportes (`/reportes/resumen-detallado` y `/reportes/estatal`) ✅
- [ ] Revisar y validar reportes (`/reportes/resumen-detallado` y `/reportes/estatal`).

## Logros del Día — 2026-04-03
- Se retomó el proyecto con Claude Code como agente activo (Arquitecto + Programador).
- Se leyeron y procesaron todos los documentos de contexto (Blueprint, notas Gemini, Protocolo).
- Se creó el banco de memoria `.context/` con los 5 archivos del Protocolo V3.0.
- Se actualizó la memoria persistente del proyecto.

## Logros del Día — 2026-04-04

### Jornada completa de validación end-to-end del backend

**Fix crítico:**
- Resuelto el bloqueante heredado de Gemini: incompatibilidad bcrypt/passlib en `app/auth.py`. Se reemplazó `CryptContext` de passlib por llamadas directas a `bcrypt.hashpw()` / `bcrypt.checkpw()`.

**Flujo core validado en Swagger UI:**
1. Login SUPER_ADMIN → JWT obtenido ✅
2. `POST /catalogos/unidades` → BCIMB000010 Hospital General de Ensenada ✅
3. `POST /catalogos/medicamentos` → 010.000.0291.00 Metilsulfato de neostigmina ✅
4. `POST /pacientes` → Samuel Hernandez, CURP HEHJ871224HGRRRS01 ✅
5. `PATCH /pacientes/{curp}` → Corrección fecha inicio tratamiento ✅
6. `POST /suministros` → Asignación medicamento con datos embebidos ✅
7. `GET /reportes/resumen-detallado` → JSON con adherencia=384 días ✅
8. `GET /reportes/estatal` → Sumatorias por unidad, ámbito Nacional ✅

**RBAC end-to-end validado:**
- ADMIN_ESTATAL (admin.bc@test.com): reporte estatal con `ambito: "Baja California"` ✅
- RESPONSABLE_UNIDAD (responsable.ensenada@test.com): GET /pacientes filtrado a BCIMB000010 ✅
- RESPONSABLE_UNIDAD intentando GET /reportes/estatal → HTTP 403 Forbidden ✅

**Estado del backend al cierre:** Todo el Blueprint implementado y validado. Sin pendientes técnicos bloqueantes.

## Pendientes para la siguiente jornada
- Decidir si se necesita frontend o se integra con algún cliente existente.
- Evaluar si se requiere carga masiva de catálogos (unidades y medicamentos reales).
- Revisar si se necesita endpoint de cambio de contraseña para el propio usuario.
- Considerar deshabilitar `/docs` en configuración de producción.

## Registro de Turnos
| # | Fecha | Agente | Acción | Estado |
|---|-------|--------|--------|--------|
| 0 | Prev. | Gemini | Diseño Blueprint + implementación base | ✅ Completado |
| 1 | 2026-04-03 | Claude | Lectura de contexto, creación `.context/`, diagnóstico | ✅ Completado |
| 2 | 2026-04-04 | Claude | Fix bcrypt, validación end-to-end completa, RBAC 3 roles | ✅ Completado |
