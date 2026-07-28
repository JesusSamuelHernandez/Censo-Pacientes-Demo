"""
crypto.py — Utilidades de cifrado simétrico y hashing para columnas sensibles.

Cifrado:
    Usa Fernet (AES-128-CBC + HMAC-SHA256) de la librería `cryptography`.
    La clave se lee de la variable de entorno FERNET_KEY.
    Para generar una clave nueva:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Hashing:
    HMAC-SHA256 en hex (64 caracteres), con clave propia (HASH_KEY, distinta
    de FERNET_KEY). Se usa para búsquedas y validación de unicidad sin
    necesidad de descifrar el valor almacenado. La clave evita que alguien
    con acceso solo a la base de datos (sin las variables de entorno) pueda
    reconstruir el hash de un CURP/cédula conocido y así confirmar por fuerza
    bruta la identidad detrás de un registro (SAST-10).

Columnas cifradas:
    Paciente            : curp_paciente, nombre_completo, diagnostico_actual
    Medico              : nombre_medico, cedula
    ExpedientePaciente  : numero_expediente
    ReaccionAdversa     : comentario
    Registro            : prescripcion, confirmado_mediante, peso, talla

    Quedan sin cifrar las relaciones que identifican diagnostico/medicamento
    (Registro.clave_cnis, Registro.id_diagnostico): son llaves foraneas que
    sostienen joins, catalogos e indices, y cifrarlas rompería la integridad
    referencial. Ese riesgo residual se mitiga con privilegios SQL acotados y
    cifrado a nivel de volumen/backup, no a nivel de columna (SAST-11).
"""
import hashlib
import hmac
import os
from decimal import Decimal

from cryptography.fernet import Fernet
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

# ---------------------------------------------------------------------------
# Inicialización — la instancia Fernet se crea una sola vez al importar.
# ---------------------------------------------------------------------------
_FERNET_KEY: str | None = os.getenv("FERNET_KEY")

if not _FERNET_KEY:
    raise RuntimeError(
        "Variable de entorno FERNET_KEY no definida. "
        "Genera una clave con: python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\" y agrégala a tu archivo .env."
    )

_fernet = Fernet(_FERNET_KEY.encode())

_HASH_KEY: str | None = os.getenv("HASH_KEY")

if not _HASH_KEY:
    raise RuntimeError(
        "Variable de entorno HASH_KEY no definida. "
        "Genera una clave con: python -c \"import secrets; print(secrets.token_urlsafe(32))\" "
        "y agrégala a tu archivo .env. Debe ser distinta de FERNET_KEY."
    )

_hash_key_bytes = _HASH_KEY.encode("utf-8")


# ---------------------------------------------------------------------------
# Tipo SQLAlchemy — cifra/descifra automáticamente en columnas del modelo.
# ---------------------------------------------------------------------------
class EncryptedString(TypeDecorator):
    """Columna LargeBinary que cifra/descifra automáticamente con Fernet."""
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> bytes | None:
        if value is None:
            return None
        return _fernet.encrypt(value.encode("utf-8"))

    def process_result_value(self, value: bytes | None, dialect) -> str | None:
        if value is None:
            return None
        return _fernet.decrypt(value).decode("utf-8")


class EncryptedDecimal(TypeDecorator):
    """Columna LargeBinary que cifra/descifra automáticamente un Decimal."""
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect) -> bytes | None:
        if value is None:
            return None
        return _fernet.encrypt(str(value).encode("utf-8"))

    def process_result_value(self, value: bytes | None, dialect) -> Decimal | None:
        if value is None:
            return None
        return Decimal(_fernet.decrypt(value).decode("utf-8"))


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def cifrar(texto: str) -> bytes:
    """Cifra un string y devuelve los bytes cifrados (token Fernet)."""
    return _fernet.encrypt(texto.encode("utf-8"))


def descifrar(datos: bytes) -> str:
    """Descifra bytes cifrados con Fernet y devuelve el string original."""
    return _fernet.decrypt(datos).decode("utf-8")


def descifrar_o_none(datos: bytes | None) -> str | None:
    """Descifra bytes opcionales. Devuelve None si el valor es None."""
    if datos is None:
        return None
    return descifrar(datos)


def hash_identificador(texto: str) -> str:
    """
    Devuelve el HMAC-SHA256 en hexadecimal (64 chars) de un identificador
    (CURP, cédula). Se normaliza (strip + mayúsculas) para que la búsqueda
    sea insensible a mayúsculas/espacios. Usa HASH_KEY para que el hash no
    pueda recalcularse sin acceso a las variables de entorno (SAST-10).
    """
    return hmac.new(
        _hash_key_bytes, texto.strip().upper().encode("utf-8"), hashlib.sha256
    ).hexdigest()
