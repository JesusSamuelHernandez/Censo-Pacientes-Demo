# Project Brief — App Web "Medicamentos de Alto Costo"

## Objetivo Macro
Desarrollar un backend REST API con FastAPI y PostgreSQL para gestionar el **censo nacional de pacientes** que reciben medicamentos de alto costo en unidades médicas del sector salud en México.

## Visión del Proyecto
- Centralizar el registro de pacientes y la asignación de medicamentos de alto costo.
- Proveer control de acceso basado en roles (RBAC) con 3 niveles jerárquicos.
- Habilitar reportes y análisis de datos (Big Data) con métricas de adherencia al tratamiento.
- Garantizar trazabilidad completa mediante Soft Delete y auditoría de usuarios.

## Alcance del Backend (Blueprint v4)
1. **Autenticación** — JWT OAuth2, login vía email/password.
2. **Pacientes** — CRUD completo con RBAC automático por unidad/estado.
3. **Suministros** — Registro de asignación de medicamentos por paciente.
4. **Reportes** — Resumen detallado (Excel/PDF) y reporte estatal agregado.
5. **Catálogos** — Medicamentos (CNIS), Unidades Médicas, Usuarios (solo SUPER_ADMIN).

## Roles RBAC
| Rol | Acceso |
|-----|--------|
| `SUPER_ADMIN` | Sin filtro geográfico. Gestión total de catálogos y usuarios. |
| `ADMIN_ESTATAL` | Solo lectura de datos de su estado (`id_entidad`). |
| `RESPONSABLE_UNIDAD` | CRUD en su propia unidad médica (`clues_unidad_asignada`). |

## Reglas de Negocio Clave
- **Soft Delete**: Nunca DELETE físico. Solo `es_activo = False`.
- **Trazabilidad**: `id_usuario_registro` + timestamp en cada cambio.
- **Adherencia**: Calculada como `(date.today() - fecha_inicio_tratamiento).days` — no se persiste en BD.
