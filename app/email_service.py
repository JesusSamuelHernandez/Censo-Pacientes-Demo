"""
app/email_service.py — Envío de correos institucionales (SMTP / SendGrid).

Adaptado del servicio usado en el Sistema de Programación Quirúrgica
IMSS-BIENESTAR (mismo mecanismo SMTP, credenciales propias del Censo de
Pacientes). Se usa para:
    - Autoservicio de alta de usuarios (POST /auth/solicitar-acceso)
    - Alta manual de usuarios (POST /usuarios, "Nuevo usuario")

El envío nunca bloquea ni revierte la operación que lo invoca: si SMTP falla
(credenciales, red, etc.) se registra el error en consola y la cuenta queda
creada igual — el SUPER_ADMIN puede comunicar el password por otro medio.
"""
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")


def enviar_correo(destinatario: str, asunto: str, contenido: str) -> bool:
    """
    Envía un correo simple en texto plano. Devuelve True si se envió, False si
    falló (el error queda registrado en el log, no se propaga como excepción).
    """
    if not destinatario:
        logger.error("enviar_correo: destinatario vacío, no se envía nada.")
        return False

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.error(
            "enviar_correo: faltan variables SMTP_HOST/SMTP_USER/SMTP_PASSWORD "
            "en el entorno — no se puede enviar el correo a %s.", destinatario,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = SMTP_FROM
    msg["To"] = destinatario
    msg.set_content(contenido)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("enviar_correo: fallo al enviar correo a %s.", destinatario)
        return False


def enviar_correo_acceso(destinatario: str, password_temporal: str) -> bool:
    """
    Correo de acceso al Censo de Pacientes — Medicamentos de Alto Costo.
    Incluye el password temporal (el "token" de acceso) y el enlace de login.
    Se usa tanto para el autoservicio (correo preautorizado) como para el alta
    manual desde "Nuevo usuario".
    """
    asunto = "Acceso al Censo de Pacientes — Medicamentos de Alto Costo"

    contenido = f"""
Hola,

Se ha generado un acceso para ti en el Censo de Pacientes — Medicamentos de
Alto Costo, IMSS-BIENESTAR.

Correo:               {destinatario}
Contraseña temporal:  {password_temporal}

Ingresa aquí:
{APP_BASE_URL}

Por seguridad, al iniciar sesión deberás capturar tu nombre de usuario y
crear una contraseña nueva.

Este correo fue generado automáticamente. No respondas a este mensaje.
"""

    return enviar_correo(
        destinatario=destinatario,
        asunto=asunto,
        contenido=contenido,
    )
