"""Utilidades genéricas reutilizables: contraseñas, motivo de baja y normalización de texto."""
import secrets
import unicodedata

_MOTIVO_BAJA_SEP = ", "


def _generar_password_placeholder() -> str:
    """
    Genera una contraseña aleatoria que nadie llega a conocer: se usa para
    poblar `hashed_password` (NOT NULL) al crear una cuenta que todavía no
    tiene contraseña propia. El login solo es posible tras activar la
    cuenta con el enlace de un solo uso (app.services.activacion, SAST-14) —
    a diferencia de la password temporal anterior, esta nunca se envía por
    correo ni se devuelve en ninguna respuesta.
    """
    return secrets.token_urlsafe(32)


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
