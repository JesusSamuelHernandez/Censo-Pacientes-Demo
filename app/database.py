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

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Verifica la conexión antes de usarla (evita conexiones muertas).
    pool_size=10,             # Conexiones simultáneas mantenidas en el pool.
    max_overflow=20,          # Conexiones extras permitidas en picos de carga.
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
