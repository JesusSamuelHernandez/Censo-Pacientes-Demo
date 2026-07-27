"""Schemas de usuarios de plataforma."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import Rol
from app.schemas.common import RolStr


class UsuarioBase(BaseModel):
    email: EmailStr
    rol_nombre: RolStr
    clues_unidad_asignada: str | None = Field(
        None,
        max_length=20,
        description="Requerido solo para RESPONSABLE_UNIDAD.",
    )
    id_entidad: str | None = Field(
        None,
        max_length=100,
        description="Requerido solo para ADMIN_ESTATAL.",
    )

    @field_validator("rol_nombre")
    @classmethod
    def rol_debe_ser_valido(cls, v: str) -> str:
        if v not in Rol.TODOS:
            raise ValueError(
                f"rol_nombre '{v}' no es valido. Debe ser uno de: {sorted(Rol.TODOS)}"
            )
        return v

    @model_validator(mode="after")
    def validar_contexto_por_rol(self) -> "UsuarioBase":
        rol = self.rol_nombre
        if rol == Rol.RESPONSABLE_UNIDAD and not self.clues_unidad_asignada:
            raise ValueError(
                "clues_unidad_asignada es requerido para el rol RESPONSABLE_UNIDAD."
            )
        if rol == Rol.ADMIN_ESTATAL and not self.id_entidad:
            raise ValueError(
                "id_entidad es requerido para el rol ADMIN_ESTATAL."
            )
        return self


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioUpdate(BaseModel):
    nombre_usuario: str | None = Field(None, min_length=2, max_length=150)
    rol_nombre: str | None = None
    clues_unidad_asignada: str | None = Field(None, max_length=20)
    id_entidad: str | None = Field(None, max_length=100)
    password: str | None = Field(None, min_length=8)

    @field_validator("rol_nombre")
    @classmethod
    def rol_valido_si_presente(cls, v: str | None) -> str | None:
        if v is not None and v not in Rol.TODOS:
            raise ValueError(
                f"rol_nombre '{v}' no es valido. Debe ser uno de: {sorted(Rol.TODOS)}"
            )
        return v


class UsuarioResponse(BaseModel):
    id_usuario: int
    nombre_usuario: str | None
    email: str
    rol_nombre: str
    clues_unidad_asignada: str | None
    id_entidad: str | None
    debe_cambiar_password: bool

    model_config = ConfigDict(from_attributes=True)


class UsuarioCreateResponse(UsuarioResponse):
    """Respuesta exclusiva de POST /usuarios. Incluye la password temporal."""
    password_temporal: str


class CambiarPasswordResponse(UsuarioResponse):
    """
    Respuesta exclusiva de POST /usuarios/me/cambiar-password. Incluye un
    access_token nuevo porque cambiar la contraseña invalida el token con el
    que se hizo esta misma llamada (token_version) — sin este token nuevo,
    el siguiente request del usuario recibiría 401 inmediatamente.
    """
    access_token: str