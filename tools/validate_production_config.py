"""Valida configuracion productiva sin imprimir secretos."""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from app.config import database_url_from_env, inspect_database_url, postgres_connect_args, require_env


def _ok(mensaje: str) -> None:
    print(f"OK  {mensaje}")


def _warn(mensaje: str) -> None:
    print(f"WARN {mensaje}")


def _error(mensaje: str) -> None:
    print(f"ERR {mensaje}")


def _validate_frontend_url() -> None:
    raw_value = require_env("FRONTEND_URL")
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError("FRONTEND_URL debe incluir al menos un origen.")
    if "*" in origins:
        raise RuntimeError("FRONTEND_URL no debe usar wildcard (*).")

    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("FRONTEND_URL contiene un origen invalido.")

    _ok(f"FRONTEND_URL contiene {len(origins)} origen(es) valido(s).")


def _validate_frontend_api_url() -> None:
    try:
        api_base_url = require_env("VITE_API_BASE_URL")
    except RuntimeError:
        _warn("VITE_API_BASE_URL no esta definida en este entorno. Es obligatoria para construir el frontend.")
        return

    parsed = urlparse(api_base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("VITE_API_BASE_URL debe ser una URL http(s) valida.")
    _ok("VITE_API_BASE_URL tiene formato valido.")


def _validate_database_url() -> str | URL:
    database_url = database_url_from_env()
    if isinstance(database_url, str):
        info = inspect_database_url(database_url)
        if not info.username_set:
            raise RuntimeError("DATABASE_URL debe incluir usuario.")
        if not info.password_set:
            raise RuntimeError("DATABASE_URL debe incluir contrasena.")
        if not info.port_set:
            _warn("DATABASE_URL no incluye puerto explicito; se usara el default de PostgreSQL.")
        _ok("DATABASE_URL tiene formato PostgreSQL valido.")
    else:
        _ok("Variables DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD tienen formato valido.")
    return database_url


def _validate_database_ssl_mode() -> None:
    """
    'prefer' (y 'disable'/sin definir) permiten que la conexion continue sin
    cifrado si el servidor no ofrece TLS -o ante un downgrade activo en la
    red-, exponiendo credenciales y datos clinicos en texto plano (SAST-09).
    'require' fuerza TLS sin verificar certificado/hostname (transicion
    aceptable si el proveedor no entrega CA); 'verify-ca'/'verify-full' son
    el objetivo cuando se cuenta con DATABASE_SSL_ROOT_CERT.
    """
    modo = (os.getenv("DATABASE_SSL_MODE") or "").strip().lower()
    if modo in {"verify-ca", "verify-full"}:
        _ok(f"DATABASE_SSL_MODE='{modo}' verifica certificado del servidor.")
    elif modo == "require":
        _ok("DATABASE_SSL_MODE='require' fuerza TLS (sin verificar certificado/hostname).")
    else:
        raise RuntimeError(
            f"DATABASE_SSL_MODE='{modo or '(sin definir)'}' permite una conexion sin cifrar. "
            "En produccion usa al menos 'require', o 'verify-full' con DATABASE_SSL_ROOT_CERT."
        )


def _validate_secrets() -> None:
    require_env("JWT_SECRET_KEY", min_length=32)
    _ok("JWT_SECRET_KEY esta definida con longitud minima.")

    fernet_key = require_env("FERNET_KEY")
    try:
        Fernet(fernet_key.encode())
    except Exception as exc:
        raise RuntimeError("FERNET_KEY no es una clave Fernet valida.") from exc
    _ok("FERNET_KEY tiene formato Fernet valido.")


def _check_database_connection(database_url: str | URL) -> None:
    connect_args = postgres_connect_args()
    if "connect_timeout" not in connect_args:
        connect_args["connect_timeout"] = 5

    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        _ok("Conexion a base de datos verificada con SELECT 1.")
    except SQLAlchemyError as exc:
        error_msg = str(exc).lower()
        
        # error de SSL
        if "ssl" in error_msg or "tls" in error_msg:
            raise RuntimeError(
                "Error de SSL/TLS: El servidor requiere SSL o los certificados/configuracion local fueron rechazados."
            ) from exc
            
        # autenticacion fallida
        elif "password authentication failed" in error_msg or "ident authentication failed" in error_msg:
            raise RuntimeError(
                "Error de Autenticacion: El usuario o la contrasena son incorrectos para esta base de datos."
            ) from exc
            
        # no existe la base de datos
        elif "database" in error_msg and "does not exist" in error_msg:
            raise RuntimeError(
                "Base de datos inexistente: El nombre de la base de datos (DB_NAME) no existe en el servidor."
            ) from exc
            
        # timeout
        elif "timeout expired" in error_msg or "connect_timeout" in error_msg or "time out" in error_msg:
            raise RuntimeError(
                "Timeout: Se agoto el tiempo de espera al intentar conectar. Revisa la latencia o el connect_timeout."
            ) from exc
            
        # host inaccesible / red / puerto cerrado
        elif "could not connect to server" in error_msg or "connection refused" in error_msg or "is the server running" in error_msg:
            raise RuntimeError(
                "Host inaccesible: No se pudo establecer conexion con el servidor. "
                "Verifica que DB_HOST y DB_PORT sean correctos, y que no haya un firewall bloqueando el acceso."
            ) from exc
            
        # error generico de SQLAlchemy/Postgres
        else:
            raise RuntimeError(f"Error de conexion a la base de datos: {str(exc)}") from exc
    finally:
        engine.dispose()


def main() -> int:
    # 1. CARGAR EL ENTORNO ANTES DE CUALQUIER VALIDACIÓN
    load_dotenv(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Valida configuracion sin revelar secretos.")
    parser.add_argument(
        "--check-db",
        action="store_true",
        help="Intenta conectar a PostgreSQL y ejecutar SELECT 1.",
    )
    args = parser.parse_args()

    try:
        # 2. Ahora sí, las funciones leerán las variables del .env correctamente
        database_url = _validate_database_url()
        _validate_database_ssl_mode()
        _validate_secrets()
        _validate_frontend_url()
        _validate_frontend_api_url()
        if args.check_db:
            _check_database_connection(database_url)
    except RuntimeError as exc:
        _error(str(exc))
        return 1

    _ok("Configuracion validada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())