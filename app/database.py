"""
database.py — Conexión a PostgreSQL y gestión de sesiones con SQLAlchemy.
"""
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import database_url_from_env, env_int, postgres_connect_args

# La URL de conexión se lee desde una variable de entorno para no exponer credenciales.
# Formato: postgresql://usuario:contraseña@host:puerto/nombre_db
load_dotenv(encoding='utf-8')  # Carga las variables de entorno del archivo .env

DATABASE_URL = database_url_from_env()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Verifica la conexión antes de usarla (evita conexiones muertas).
    pool_size=env_int("DB_POOL_SIZE", 10),
    max_overflow=env_int("DB_MAX_OVERFLOW", 20),
    pool_timeout=env_int("DB_POOL_TIMEOUT", 30),
    pool_recycle=env_int("DB_POOL_RECYCLE", 1800),
    connect_args=postgres_connect_args(),
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
