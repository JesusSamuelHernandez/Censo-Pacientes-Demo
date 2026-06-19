"""
database.py — Conexión a PostgreSQL y gestión de sesiones con SQLAlchemy.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# La URL de conexión se lee desde una variable de entorno para no exponer credenciales.
# Formato: postgresql://usuario:contraseña@host:puerto/nombre_db
load_dotenv(encoding='utf-8')  # Carga las variables de entorno del archivo .env

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Variable de entorno DATABASE_URL no definida. "
        "Configura la conexion PostgreSQL antes de iniciar la aplicacion."
    )


def _env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or valor.strip() == "":
        return default
    try:
        return int(valor)
    except ValueError as exc:
        raise RuntimeError(f"Variable de entorno {nombre} debe ser un entero.") from exc


connect_args = {}
database_ssl_mode = os.getenv("DATABASE_SSL_MODE")
if database_ssl_mode:
    connect_args["sslmode"] = database_ssl_mode

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Verifica la conexión antes de usarla (evita conexiones muertas).
    pool_size=_env_int("DB_POOL_SIZE", 10),
    max_overflow=_env_int("DB_MAX_OVERFLOW", 20),
    pool_timeout=_env_int("DB_POOL_TIMEOUT", 30),
    pool_recycle=_env_int("DB_POOL_RECYCLE", 1800),
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos ORM."""
    pass


def get_db():
    """
    Dependencia de FastAPI: entrega una sesión de DB y la cierra al terminar la petición.
    Uso: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
