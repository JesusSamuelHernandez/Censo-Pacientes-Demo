# Active Context — Plan Actual y Notas Técnicas

## Estado al inicio de esta jornada (2026-04-03)
El backend tiene implementados los siguientes módulos completos:
- `app/database.py` ✅ — Conexión a PostgreSQL, pool configurado.
- `app/models.py` ✅ — Los 5 modelos ORM del Blueprint completos.
- `app/schemas.py` ✅ — Todos los schemas Pydantic (Create/Update/Response).
- `app/auth.py` ✅ — JWT, RBAC, `apply_rbac_filter()`, dependencias de rol.
- `app/main.py` ✅ — Todos los endpoints del Blueprint (Auth, Pacientes, Suministros, Reportes, Catálogos).

## Bloqueante Pendiente de Validar
**Problema bcrypt/passlib** (heredado de Gemini):
- `auth.py:47` usa `CryptContext(schemes=["bcrypt"], deprecated="auto")`.
- Con versiones recientes de bcrypt, passlib falla con `AttributeError: module 'bcrypt' has no attribute '__about__'`.
- El login (`POST /auth/login`) devuelve Error 500 si este bug está activo.
- **Acción requerida**: Verificar versiones instaladas y corregir si aplica.

## Estado al cierre de jornada — 2026-04-04

El backend está **completamente validado**. Todos los módulos del Blueprint funcionan correctamente. No hay bloqueantes técnicos pendientes.

**Datos de prueba cargados en la BD:**
- Usuario SUPER_ADMIN: `jesus.hernandezh@imssbienestar.gob.mx` (id=1)
- Usuario ADMIN_ESTATAL: `admin.bc@test.com`, Baja California (id=2)
- Usuario RESPONSABLE_UNIDAD: `responsable.ensenada@test.com`, BCIMB000010 (id=3)
- Unidad Médica: `BCIMB000010` — Hospital General de Ensenada, Baja California
- Medicamento: `010.000.0291.00` — Metilsulfato de neostigmina
- Paciente: `HEHJ871224HGRRRS01` — Samuel Hernandez, hipertiroidismo, adherencia 384 días
- Suministro: `id=1` — Neostigmina 0.5 mg, primera administración 2025-03-15

## Plan para la siguiente jornada — 2026-04-05

1. **Revisión del backend** — recorrido de la arquitectura para preparar presentación.
2. **Presentación de arquitectura** — documentar stack, herramientas, decisiones técnicas y flujos clave.
3. **Git y GitHub** — inicializar repositorio, definir `.gitignore`, primer commit y subir a GitHub.
4. **Planeación general del frontend** — definir stack (framework, librerías), pantallas principales y flujo de navegación.

**Nota:** Los catálogos reales (CLUES y Clave CNIS) aún no están disponibles. Se cargarán cuando se obtengan los archivos oficiales.
