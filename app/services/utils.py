"""Utilidades genéricas reutilizables: contraseñas, motivo de baja y normalización de texto."""
import secrets
import string
import unicodedata

_MOTIVO_BAJA_SEP = ", "


def _generar_password_temporal(longitud: int = 15) -> str:
    """Genera una contraseña aleatoria alfanumérica para el primer acceso.

    15 caracteres para cumplir el mínimo de la política de contraseñas
    (app.services.password_policy) aunque esta no pase por esa validación.
    """
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))


def _serializar_motivo_baja(motivos: list[str]) -> str:
    """Une varios motivos de baja en un solo string para guardar en BD."""
    return _MOTIVO_BAJA_SEP.join(motivos)


def _deserializar_motivo_baja(valor: str | None) -> list[str] | None:
    """Separa el string guardado en BD de vuelta a la lista de motivos."""
    if not valor:
        return None
    return [m.strip() for m in valor.split(",") if m.strip()]


def _normalizar_texto(texto: str) -> str:
    """Mayúsculas, sin espacios extremos y sin acentos (NFD, quitando categoría Mn)."""
    sin_acentos = unicodedata.normalize("NFD", texto.strip().upper())
    return "".join(c for c in sin_acentos if unicodedata.category(c) != "Mn")
