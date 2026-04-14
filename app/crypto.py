"""
crypto.py — Utilidades de cifrado simétrico y hashing para columnas sensibles.

Cifrado:
    Usa Fernet (AES-128-CBC + HMAC-SHA256) de la librería `cryptography`.
    La clave se lee de la variable de entorno FERNET_KEY.
    Para generar una clave nueva:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Hashing:
    SHA-256 en hex (64 caracteres). Se usa para búsquedas y validación de
    unicidad sin necesidad de descifrar el valor almacenado.

Columnas cifradas:
    Paciente  : curp_paciente, nombre_completo, diagnostico_actual
    Medico    : nombre_medico, cedula
"""
import hashlib
import os

from cryptography.fernet import Fernet

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


def hash_sha256(texto: str) -> str:
    """
    Devuelve el hash SHA-256 en hexadecimal (64 chars) del texto en minúsculas.
    Se normaliza a minúsculas para que la búsqueda sea case-insensitive.
    """
    return hashlib.sha256(texto.strip().upper().encode("utf-8")).hexdigest()
