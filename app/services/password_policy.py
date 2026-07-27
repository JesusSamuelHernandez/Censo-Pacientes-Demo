"""
Política de contraseñas (SAST-06 / CWE-521 / NIST SP 800-63B-4).

Longitud mínima 15 (autenticación de un solo factor, sin MFA), máximo
compatible con el límite de 72 bytes de bcrypt, y blocklist de contraseñas
comunes/comprometidas en vez de reglas obligatorias de mayúsculas/símbolos
(que NIST desaconseja por fomentar patrones predecibles).
"""
import re

PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_BYTES = 72

# Subconjunto de las contraseñas más comunes en filtraciones públicas
# (listas tipo "10k most common passwords" / rockyou), suficientemente largas
# para pasar el mínimo de 15 solo al repetirse o concatenarse con dígitos —
# la comparación de abajo normaliza y busca coincidencia por substring, no
# solo exacta.
PASSWORDS_COMUNES_BLOQUEADAS = frozenset({
    "password", "contraseña", "contrasena", "12345678", "123456789",
    "1234567890", "qwertyuiop", "letmein", "iloveyou", "admin1234",
    "welcome1", "welcome123", "changeme", "changeme123", "trustno1",
    "abc123456", "password1", "password123", "passw0rd", "p@ssword",
    "administrador", "administrator", "superadmin", "master1234",
    "qwerty123", "asdfghjkl", "zxcvbnm123", "football1", "baseball1",
    "dragon123", "monkey123", "sunshine1", "princess1", "shadow123",
    "michael123", "jennifer1", "computer1", "internet1", "security1",
    "letmein123", "freedom123", "whatever1", "starwars1", "hunter123",
})

# Términos propios de este sistema/organización: bloquear que la contraseña
# los contenga evita el patrón más común de contraseña débil "adivinable"
# (nombre del sistema, de la institución o la palabra 'password').
CONTEXTO_BLOQUEADO = frozenset({
    "imssbienestar", "imss", "bienestar", "censodepacientes", "censo",
    "paciente", "pacientes", "medicamento", "password", "contraseña",
    "contrasena",
})


def _normalizar(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def validar_password_fuerte(password: str) -> str:
    """
    Valida longitud y blocklist. Pensada para usarse como field_validator de
    Pydantic: retorna el password sin cambios si es válido, o lanza
    ValueError con un mensaje presentable al usuario.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
        )

    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(
            f"La contraseña no puede exceder {PASSWORD_MAX_BYTES} bytes "
            "(aprox. igual número de caracteres si no usas emojis/acentos poco comunes)."
        )

    normalizado = _normalizar(password)

    for comun in PASSWORDS_COMUNES_BLOQUEADAS:
        if comun in normalizado:
            raise ValueError(
                "Esa contraseña es demasiado común o aparece en filtraciones conocidas. "
                "Elige una distinta."
            )

    for termino in CONTEXTO_BLOQUEADO:
        if termino in normalizado:
            raise ValueError(
                "La contraseña no puede contener el nombre del sistema, de la "
                "institución ni la palabra 'contraseña'."
            )

    return password
