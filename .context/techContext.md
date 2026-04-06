# Tech Context — Stack, Dependencias y Arquitectura

## Stack Tecnológico
| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Lenguaje | Python | 3.13 |
| Framework API | FastAPI | Latest |
| ORM | SQLAlchemy | 2.0.36 |
| Base de Datos | PostgreSQL | 15 (Docker) |
| Autenticación | python-jose (JWT) + Passlib/bcrypt | — |
| Entorno | venv (`.venv/`) | — |
| Servidor | Uvicorn | — |

## Estructura de Archivos Clave
```
Censo_de_pacientes_01/
├── app/
│   ├── __init__.py
│   ├── database.py     # Conexión SQLAlchemy + get_db() + Base
│   ├── models.py       # ORM: CatMedicamento, UnidadMedica, Usuario, Paciente, Suministro
│   ├── schemas.py      # Pydantic v2: XxxCreate, XxxUpdate, XxxResponse
│   ├── auth.py         # JWT, bcrypt, RBAC (UsuarioActivo, apply_rbac_filter)
│   └── main.py         # Todos los endpoints FastAPI
├── create_admin.py     # Script manual para crear SUPER_ADMIN (usa bcrypt directo)
├── .env                # DATABASE_URL, JWT_SECRET_KEY, etc. (NO en git)
├── .env.example        # Plantilla de variables de entorno
└── .context/           # Banco de memoria del protocolo multi-agente
```

## Modelos ORM (SQLAlchemy 2.0 Mapped)
- `CatMedicamento` — `clave_cnis` (PK), `descripcion`, `grupo`, `tipo_clave`, `es_activo`
- `UnidadMedica` — `clues` (PK), `nombre_de_la_unidad`, `id_entidad`, `categoria_gerencial`
- `Usuario` — `id_usuario` (PK), `email` (unique), `hashed_password`, `rol_nombre`, `clues_unidad_asignada` (FK), `id_entidad`
- `Paciente` — `curp_paciente` (PK, 18 chars), `nombre_completo`, `diagnostico_actual`, `fecha_inicio_tratamiento`, `clues_unidad_adscripcion` (FK), `es_activo`, `id_usuario_registro` (FK), `fecha_registro` (auto)
- `Suministro` — `id_suministro` (PK, autoincrement), `curp_paciente` (FK), `clave_cnis_med` (FK), `dosis_administrada`, `fecha_primera_administracion`, `fecha_registro_sistema` (auto), `id_usuario_registro` (FK), `es_activo`

## Problema Conocido: bcrypt/passlib Incompatibilidad
- **Error**: `AttributeError: module 'bcrypt' has no attribute '__about__'` + errores de 72 bytes.
- **Causa**: Versiones recientes de `bcrypt` eliminaron `__about__`; `passlib` lo buscaba.
- **Estado actual**: `auth.py` usa `CryptContext(schemes=["bcrypt"], deprecated="auto")` vía passlib. Puede seguir fallando según la versión instalada.
- **Workaround documentado**: Usar bcrypt directamente sin passlib, o aplicar patch `import bcrypt; bcrypt.__about__ = type('', (), {'__version__': bcrypt.__version__})()`.
- **Solución recomendada**: Reemplazar passlib con llamadas directas a `bcrypt.hashpw()` / `bcrypt.checkpw()`.

## Variables de Entorno Requeridas (.env)
```
DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db
JWT_SECRET_KEY=<mínimo 32 caracteres aleatorios>
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
```

## Convenciones de Código
- Schemas Pydantic: `XxxBase → XxxCreate / XxxUpdate / XxxResponse`
- `model_config = ConfigDict(from_attributes=True)` en todos los Response schemas.
- Soft Delete vía `es_activo: bool` (nunca DELETE físico en pacientes/suministros).
- `server_default=func.now()` para timestamps automáticos en BD.
- RBAC centralizado en `apply_rbac_filter()` — no duplicar lógica en endpoints.
