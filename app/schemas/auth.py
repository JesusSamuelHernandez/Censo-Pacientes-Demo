"""Schemas de autenticacion y cambio de password."""
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.password_policy import PASSWORD_MIN_LENGTH, validar_password_fuerte


class SolicitarAccesoRequest(BaseModel):
    """POST /auth/solicitar-acceso: autoservicio desde la pantalla de login."""
    email: EmailStr


class SolicitarAccesoResponse(BaseModel):
    mensaje: str = (
        "Si tu correo esta autorizado, recibiras un correo con tus "
        "credenciales de acceso en unos minutos."
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol_nombre: str
    id_usuario: int
    debe_cambiar_password: bool
    email: str
    nombre_usuario: str | None = None
    clues_unidad_asignada: str | None = None
    nombre_unidad: str | None = None
    id_entidad: str | None = None


class CambiarPasswordRequest(BaseModel):
    password_actual: str = Field(..., min_length=1, description="Contrasena actual.")
    password_nueva: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=72,
        description=f"Nueva contrasena (minimo {PASSWORD_MIN_LENGTH} caracteres, NIST SP 800-63B-4).",
    )

    @field_validator("password_nueva")
    @classmethod
    def _validar_fortaleza(cls, v: str) -> str:
        return validar_password_fuerte(v)
    nombre_usuario: str | None = Field(
        None,
        min_length=2,
        max_length=150,
        description=(
            "Requerido solo si la cuenta aun no tiene nombre_usuario "
            "(autoservicio por correo o alta via 'Nuevo usuario')."
        ),
    )