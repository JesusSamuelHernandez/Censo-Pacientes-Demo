# Product Context — Lógica de Negocio y Flujos de Usuario

## Flujos Principales

### Login
1. Cliente envía `email` + `password` a `POST /auth/login`.
2. Backend verifica credenciales con `verify_password()` (bcrypt).
3. Respuesta: `access_token` (JWT) + `rol_nombre` + `id_usuario`.
4. El JWT incluye claims RBAC: `rol_nombre`, `clues_unidad_asignada`, `id_entidad`.

### Registro de Paciente (RESPONSABLE_UNIDAD)
1. Envía `POST /pacientes` con CURP (18 chars, validación regex), nombre, diagnóstico, fecha inicio, CLUES de la unidad.
2. Backend valida que el CLUES del payload sea igual al del usuario (RBAC).
3. Se guarda con `es_activo=True` y `id_usuario_registro` del token.

### Asignación de Medicamento (Suministro)
1. `POST /suministros` con CURP del paciente + clave CNIS + dosis + fecha primera administración.
2. Backend verifica existencia del paciente activo y del medicamento activo en catálogo.
3. Registro ligado al usuario que captura (auditoría).

### Soft Delete
- Pacientes: `DELETE /pacientes/{curp}` → `es_activo = False`.
- Suministros: `DELETE /suministros/{id}` → `es_activo = False`.
- Medicamentos: Vía `PATCH /catalogos/medicamentos/{clave}` con `es_activo: false`.

## Filtro RBAC Automático (Blueprint §4)
Toda query de datos pasa por `apply_rbac_filter()` en `auth.py`:
- `RESPONSABLE_UNIDAD` → `WHERE clues_unidad_adscripcion = usuario.clues_unidad_asignada`
- `ADMIN_ESTATAL` → `JOIN unidades_medicas WHERE id_entidad = usuario.id_entidad`
- `SUPER_ADMIN` → Sin filtro adicional.

## Matriz de Permisos (Blueprint §4)
| Entidad | RESPONSABLE_UNIDAD | ADMIN_ESTATAL | SUPER_ADMIN |
|---------|-------------------|---------------|-------------|
| Pacientes | C, R, U (su unidad) | R (su estado) | R (país) |
| Suministros | C, R, U (su unidad) | R (su estado) | R (país) |
| Medicamentos | R | R | C, R, U, D |
| Usuarios | Sin acceso | Sin acceso | C, R, U, D |
| Unidades/Edo | R | R | C, R, U, D |

## Reportes
- `GET /reportes/resumen-detallado` — JSON con suministros + paciente + medicamento + adherencia. Filtrable por fecha. Para exportar a Excel/PDF en el frontend.
- `GET /reportes/estatal` — Sumatorias por unidad médica. Solo ADMIN_ESTATAL y SUPER_ADMIN.
