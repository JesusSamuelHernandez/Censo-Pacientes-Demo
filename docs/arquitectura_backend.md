# Arquitectura del Backend — App "Medicamentos de Alto Costo"

## 1. Visión General

El sistema es una **API REST** que centraliza el censo de pacientes que reciben medicamentos de alto costo en unidades médicas del sector salud. El backend es el núcleo del sistema: gestiona los datos, aplica las reglas de seguridad y expone la información a cualquier cliente (web, móvil, reportes).

---

## 2. Stack Tecnológico — El "¿Por qué?"

### Python 3.13
**¿Por qué?**
- Lenguaje dominante en sistemas de salud y análisis de datos (Big Data, Machine Learning).
- Ecosistema maduro para desarrollo web y procesamiento de datos.
- El equipo ya tiene conocimiento en Python.
- Preparamos el terreno para análisis estadísticos futuros sobre los datos de adherencia.

---

### FastAPI
**¿Por qué FastAPI y no Django o Flask?**

| Criterio | Flask | Django | **FastAPI** |
|----------|-------|--------|-------------|
| Velocidad de desarrollo | Media | Media | **Alta** |
| Documentación automática | No | No | **Sí (Swagger)** |
| Validación de datos | Manual | Parcial | **Automática (Pydantic)** |
| Rendimiento | Medio | Medio | **Alto (asíncrono)** |
| Tipado estático | No | No | **Sí** |

**Decisión clave:** FastAPI genera automáticamente la documentación interactiva (Swagger UI en `/docs`), lo que nos permitió probar y validar todos los endpoints sin escribir una sola línea de código de prueba adicional. Para un equipo pequeño, esto acelera el desarrollo significativamente.

---

### PostgreSQL 15
**¿Por qué PostgreSQL y no MySQL o SQLite?**
- **Integridad referencial robusta** — Las llaves foráneas (FK) entre tablas (paciente → unidad, receta → paciente → médico) son críticas en un sistema de salud. PostgreSQL las aplica de forma estricta.
- **Soporte de tipos avanzados** — Timestamps con zona horaria (`TIMESTAMPTZ`), esencial para registros de auditoría confiables.
- **Escalabilidad** — Preparado para crecer de cientos a millones de registros sin cambiar de motor.
- **Estándar institucional** — PostgreSQL es el motor de base de datos más adoptado en sistemas gubernamentales y de salud en México.
- **SQLite** fue descartado porque no es apto para producción con múltiples usuarios simultáneos.

---

### SQLAlchemy 2.0 (ORM)
**¿Por qué un ORM y no SQL directo?**
- **Seguridad** — Previene inyección SQL automáticamente al parametrizar todas las consultas.
- **Productividad** — Las tablas se definen como clases Python (`models.py`), no como scripts SQL separados. Un solo archivo describe toda la estructura de la BD.
- **Mantenibilidad** — Si cambia una columna, se cambia en un solo lugar (el modelo), no en decenas de queries SQL dispersas.
- **Versión 2.0** — Usamos la sintaxis moderna con `Mapped` y `mapped_column`, que tiene tipado estático completo y detecta errores antes de ejecutar.

---

### JWT (JSON Web Tokens) con python-jose
**¿Por qué JWT y no sesiones tradicionales?**
- **Sin estado (stateless)** — El servidor no guarda sesiones en memoria. Cada token se valida de forma independiente. Esto permite escalar el sistema horizontalmente (múltiples servidores) sin sincronizar sesiones.
- **RBAC en el token** — El rol del usuario (`SUPER_ADMIN`, `ADMIN_ESTATAL`, `RESPONSABLE_UNIDAD`) y su contexto geográfico (CLUES, entidad) viajan dentro del token. El backend no consulta la BD para saber qué puede ver el usuario — ya lo sabe desde el token.
- **Estándar de la industria** — Compatible con cualquier cliente futuro (app móvil, otro sistema).

---

### bcrypt (hash de contraseñas)
**¿Por qué bcrypt?**
- Es el algoritmo estándar de la industria para almacenar contraseñas de forma segura.
- Incorpora un "salt" aleatorio automáticamente — dos usuarios con la misma contraseña generan hashes diferentes.
- Resistente a ataques de fuerza bruta por su diseño computacionalmente costoso.
- **Nunca** se almacena la contraseña en texto plano — solo el hash.

---

### Docker (contenedor PostgreSQL)
**¿Por qué Docker para la base de datos?**
- **Entorno reproducible** — Cualquier desarrollador levanta la misma BD con un solo comando (`docker compose up`), sin instalar PostgreSQL manualmente.
- **Aislamiento** — La BD corre en su propio contenedor, sin interferir con el sistema operativo.
- **Preparación para producción** — El mismo `docker-compose.yml` puede adaptarse para despliegue en servidor.

---

## 3. Decisiones de Diseño Clave

### Soft Delete (es_activo)
**¿Por qué no DELETE físico?**
Los datos de pacientes y recetas son registros médicos. En el sector salud, **ningún dato se elimina** — se da de baja lógicamente (`es_activo = False`). Esto garantiza:
- Trazabilidad histórica completa.
- Auditoría ante cualquier revisión legal o administrativa.
- Posibilidad de recuperar registros dados de baja por error.

### RBAC con filtro geográfico automático
**¿Por qué centralizar el filtro en `apply_rbac_filter()`?**
La regla del Blueprint es clara: *"Toda consulta de datos debe pasar por un filtro de pertenencia"*. En lugar de repetir la lógica en cada endpoint, se centraliza en una sola función. Esto garantiza que:
- Ningún endpoint puede "olvidar" aplicar el filtro.
- Si la lógica de RBAC cambia, se modifica en un solo lugar.

### Adherencia calculada en runtime
**¿Por qué no guardar `dias_adherencia` en la BD?**
La adherencia es `(fecha_actual - receta.fecha_inicio_tratamiento).days`, usando la receta activa más reciente del paciente. Si se guardara en la BD, habría que actualizarla diariamente para todos los pacientes. Al calcularla en el momento de la consulta, el dato siempre es exacto sin ningún proceso de actualización.

### Recetas vs. Suministros (Blueprint v5)
**¿Por qué reemplazar `suministros` con `medicos` + `recetas`?**
La tabla `suministros` original era un registro simple de dosis sin contexto clínico. En v5 se separó en dos entidades:
- **`medicos`** — Catálogo de profesionales médicos adscritos a unidades. Permite trazabilidad de quién prescribe.
- **`recetas`** — Registro de prescripción que vincula médico + paciente + medicamento + unidad + fechas de tratamiento. Esto refleja el flujo real del sector salud (una receta genera la dispensación) y permite calcular la adherencia por esquema de tratamiento específico, no por el historial global del paciente.

Adicionalmente, `fecha_inicio_tratamiento` se movió de `pacientes` a `recetas` porque un paciente puede tener múltiples esquemas de tratamiento a lo largo del tiempo, cada uno con su propia fecha de inicio.

---

## 4. Estructura de Archivos

```
app/
├── database.py   → Conexión a PostgreSQL, pool de conexiones, sesión por request.
├── models.py     → Las 6 tablas ORM: CatMedicamento, UnidadMedica (cat_unidades),
│                   Usuario, Paciente, Medico, Receta.
├── schemas.py    → Validación de entrada/salida con Pydantic (CURP, CLUES, roles).
├── auth.py       → JWT, bcrypt, RBAC: apply_rbac_filter(), dependencias de rol.
└── main.py       → Todos los endpoints de la API (7 módulos del Blueprint).
```

**Flujo de una petición:**
```
Cliente → main.py (endpoint) → auth.py (validar JWT + rol) → database.py (sesión BD)
       → models.py (query ORM) → schemas.py (serializar respuesta) → Cliente
```
