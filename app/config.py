"""Helpers de configuracion para entorno y conexion PostgreSQL."""
import os
from dataclasses import dataclass

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class DatabaseUrlInfo:
    drivername: str
    username_set: bool
    password_set: bool
    host_set: bool
    port_set: bool
    database_set: bool


def require_env(nombre: str, min_length: int | None = None) -> str:
    valor = os.getenv(nombre)
    if valor is None or valor.strip() == "":
        raise RuntimeError(f"Variable de entorno {nombre} no definida.")
    if min_length is not None and len(valor) < min_length:
        raise RuntimeError(
            f"Variable de entorno {nombre} debe tener al menos {min_length} caracteres."
        )
    return valor


def env_int(nombre: str, default: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or valor.strip() == "":
        return default
    try:
        return int(valor)
    except ValueError as exc:
        raise RuntimeError(f"Variable de entorno {nombre} debe ser un entero.") from exc


def _has_split_database_env() -> bool:
    return any(
        os.getenv(nombre)
        for nombre in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    )


def _validate_raw_database_url(database_url: str) -> None:
    prefix = "postgresql://"
    alt_prefix = "postgresql+psycopg2://"
    if database_url.startswith(prefix):
        rest = database_url[len(prefix):]
    elif database_url.startswith(alt_prefix):
        rest = database_url[len(alt_prefix):]
    else:
        return

    if "@" not in rest:
        return

    userinfo = rest.rsplit("@", 1)[0]
    if any(char in userinfo for char in ("/", "?", "#", ",")):
        raise RuntimeError(
            "DATABASE_URL contiene caracteres especiales sin codificar en usuario o contrasena. "
            "Usa variables separadas DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD, "
            "o codifica esos caracteres para URL."
        )


def database_url_from_env() -> str | URL:
    if _has_split_database_env():
        host = require_env("DB_HOST")
        database = require_env("DB_NAME")
        username = require_env("DB_USER")
        password = require_env("DB_PASSWORD")
        port = env_int("DB_PORT", 5432)
        return URL.create(
            "postgresql+psycopg2",
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
        )

    database_url = require_env("DATABASE_URL")
    _validate_raw_database_url(database_url)
    inspect_database_url(database_url)
    return database_url


def postgres_connect_args() -> dict[str, str | int]:
    connect_args: dict[str, str | int] = {}

    database_ssl_mode = os.getenv("DATABASE_SSL_MODE")
    if database_ssl_mode:
        connect_args["sslmode"] = database_ssl_mode

    database_ssl_root_cert = os.getenv("DATABASE_SSL_ROOT_CERT")
    if database_ssl_root_cert:
        connect_args["sslrootcert"] = database_ssl_root_cert

    database_connect_timeout = os.getenv("DATABASE_CONNECT_TIMEOUT")
    if database_connect_timeout:
        try:
            connect_args["connect_timeout"] = int(database_connect_timeout)
        except ValueError as exc:
            raise RuntimeError("DATABASE_CONNECT_TIMEOUT debe ser un entero.") from exc

    return connect_args


def inspect_database_url(database_url: str) -> DatabaseUrlInfo:
    _validate_raw_database_url(database_url)
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise RuntimeError(
            "DATABASE_URL no tiene un formato valido. "
            "Si la contrasena contiene caracteres como /, ?, #, @, %, espacios o comas, "
            "debe ir codificada para URL."
        ) from exc

    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("DATABASE_URL debe usar el driver postgresql.")
    if not url.host:
        raise RuntimeError("DATABASE_URL debe incluir host.")
    if not url.database:
        raise RuntimeError("DATABASE_URL debe incluir nombre de base de datos.")

    return DatabaseUrlInfo(
        drivername=url.drivername,
        username_set=bool(url.username),
        password_set=bool(url.password),
        host_set=bool(url.host),
        port_set=bool(url.port),
        database_set=bool(url.database),
    )
