"""
auth.py — Seguridad: hasheo de contraseñas, generación/verificación de JWT
          y dependencias FastAPI para RBAC.

Flujo completo:
    1. Cliente  →  POST /auth/login  (email + password)
    2. Backend  →  verifica password, genera JWT con claims del usuario.
    3. Cliente  →  envía JWT en cada petición (header: Authorization: Bearer <token>).
    4. Backend  →  decodifica JWT con get_current_user().
    5. Endpoints →  usan dependencias de rol (require_super_admin, etc.) que
                    leen el contexto del usuario autenticado y aplican el filtro
                    geográfico correcto según el Blueprint:

        RESPONSABLE_UNIDAD  → filtra por clues_unidad_asignada
        ADMIN_ESTATAL       → filtra por id_entidad
        SUPER_ADMIN         → sin filtro

Variables de entorno requeridas:
    JWT_SECRET_KEY   : clave secreta para firmar los tokens (mín. 32 caracteres).
    JWT_ALGORITHM    : algoritmo de firma (default: HS256).
    JWT_EXPIRE_HOURS : duración del token en horas (default: 8).
"""
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rol, Usuario

# ---------------------------------------------------------------------------
# Configuración desde variables de entorno
# ---------------------------------------------------------------------------
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CAMBIA_ESTA_CLAVE_EN_PRODUCCION_min32chars!!")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# Esquema OAuth2: FastAPI leerá el token del header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")



# ---------------------------------------------------------------------------
# Dataclass: contexto del usuario autenticado
# Se usa como tipo de retorno de get_current_user() y de todas las dependencias.
# Lleva los campos RBAC directamente para no consultar la BD en cada request.
# ---------------------------------------------------------------------------
@dataclass
class UsuarioActivo:
    """
    Contexto del usuario autenticado, extraído del JWT.

    Campos clave para RBAC (Blueprint sección 4):
        clues_unidad_asignada : filtra datos si rol == RESPONSABLE_UNIDAD.
        id_entidad            : filtra datos si rol == ADMIN_ESTATAL.
    """
    id_usuario: int
    email: str
    rol_nombre: str
    clues_unidad_asignada: str | None   # Solo RESPONSABLE_UNIDAD
    id_entidad: str | None              # Solo ADMIN_ESTATAL

    # ------------------------------------------------------------------
    # Helpers de rol — evitan comparar strings sueltos en los endpoints.
    # ------------------------------------------------------------------
    @property
    def es_super_admin(self) -> bool:
        return self.rol_nombre == Rol.SUPER_ADMIN

    @property
    def es_admin_estatal(self) -> bool:
        return self.rol_nombre == Rol.ADMIN_ESTATAL

    @property
    def es_responsable_unidad(self) -> bool:
        return self.rol_nombre == Rol.RESPONSABLE_UNIDAD


# ---------------------------------------------------------------------------
# Utilidades de contraseña
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña en texto plano."""
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Retorna True si la contraseña coincide con el hash almacenado."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ---------------------------------------------------------------------------
# Utilidades JWT
# ---------------------------------------------------------------------------

def create_access_token(usuario: Usuario) -> str:
    """
    Genera un JWT firmado con los claims del usuario.

    Claims incluidos en el payload:
        sub                   : email del usuario (identificador estándar JWT).
        id_usuario            : PK en la tabla usuarios.
        rol_nombre            : rol RBAC.
        clues_unidad_asignada : contexto de unidad (RESPONSABLE_UNIDAD).
        id_entidad            : contexto estatal (ADMIN_ESTATAL).
        exp                   : fecha/hora de expiración (UTC).
    """
    expira_en = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)

    payload = {
        "sub": usuario.email,
        "id_usuario": usuario.id_usuario,
        "rol_nombre": usuario.rol_nombre,
        "clues_unidad_asignada": usuario.clues_unidad_asignada,
        "id_entidad": usuario.id_entidad,
        "exp": expira_en,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    """
    Decodifica y verifica el JWT. Lanza 401 si el token es inválido o expiró.
    Uso interno — los endpoints consumen get_current_user() en su lugar.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


# ---------------------------------------------------------------------------
# Dependencia base — inyectada en todos los endpoints protegidos
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UsuarioActivo:
    """
    Dependencia FastAPI: decodifica el JWT y devuelve el contexto del usuario.

    Verifica que el usuario siga existiendo en la BD (protege contra cuentas
    eliminadas o modificadas después de emitir el token).
    """
    payload = _decode_token(token)

    email: str | None = payload.get("sub")
    id_usuario: int | None = payload.get("id_usuario")

    if email is None or id_usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token con estructura inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario_db = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if usuario_db is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario del token ya no existe en el sistema.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UsuarioActivo(
        id_usuario=usuario_db.id_usuario,
        email=usuario_db.email,
        rol_nombre=usuario_db.rol_nombre,
        clues_unidad_asignada=usuario_db.clues_unidad_asignada,
        id_entidad=usuario_db.id_entidad,
    )


# ---------------------------------------------------------------------------
# Dependencias de Rol (RBAC)
# Úsalas directamente en la firma del endpoint con Depends().
# ---------------------------------------------------------------------------

def require_super_admin(
    current_user: UsuarioActivo = Depends(get_current_user),
) -> UsuarioActivo:
    """
    Solo permite acceso a SUPER_ADMIN.
    Uso: gestión de catálogos, usuarios y unidades (Blueprint sección 4).
    """
    if not current_user.es_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a Super Administrador.",
        )
    return current_user


def require_admin_estatal_o_superior(
    current_user: UsuarioActivo = Depends(get_current_user),
) -> UsuarioActivo:
    """
    Permite acceso a ADMIN_ESTATAL y SUPER_ADMIN.
    Uso: reportes estatales y lectura ampliada de pacientes/suministros.
    """
    if current_user.rol_nombre not in {Rol.ADMIN_ESTATAL, Rol.SUPER_ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a Administrador Estatal o superior.",
        )
    return current_user


def require_cualquier_rol(
    current_user: UsuarioActivo = Depends(get_current_user),
) -> UsuarioActivo:
    """
    Permite el acceso a cualquier usuario autenticado (los 3 roles).
    El filtro geográfico se aplica dentro del endpoint con apply_rbac_filter().
    """
    return current_user


# ---------------------------------------------------------------------------
# Helper RBAC: generador de filtros para queries SQLAlchemy
# Blueprint sección 4 — "Toda consulta de datos debe pasar por un filtro de pertenencia"
# ---------------------------------------------------------------------------

@dataclass
class FiltroRBAC:
    """
    Resultado de apply_rbac_filter().
    Encapsula las condiciones de filtrado que el endpoint debe aplicar a la query.

    Campos:
        filtrar_por_clues    : True → aplicar WHERE clues_unidad_adscripcion = valor_clues
        valor_clues          : CLUES de la unidad del usuario (RESPONSABLE_UNIDAD).
        filtrar_por_entidad  : True → aplicar WHERE id_entidad = valor_entidad
        valor_entidad        : entidad del usuario (ADMIN_ESTATAL).
        sin_filtro           : True → SUPER_ADMIN, sin restricciones.
    """
    filtrar_por_clues: bool
    valor_clues: str | None
    filtrar_por_entidad: bool
    valor_entidad: str | None
    sin_filtro: bool


def apply_rbac_filter(usuario: UsuarioActivo) -> FiltroRBAC:
    """
    Determina el filtro geográfico que debe aplicarse a una query según el rol.

    Implementa la Matriz de Seguridad del Blueprint (sección 4):
        RESPONSABLE_UNIDAD → WHERE clues_unidad_asignada = usuario.clues_unidad_asignada
        ADMIN_ESTATAL      → WHERE id_entidad = usuario.id_entidad
        SUPER_ADMIN        → Sin filtro

    Ejemplo de uso en un endpoint:
        filtro = apply_rbac_filter(current_user)
        query = db.query(Paciente).filter(Paciente.es_activo == True)

        if filtro.filtrar_por_clues:
            query = query.filter(
                Paciente.clues_unidad_adscripcion == filtro.valor_clues
            )
        elif filtro.filtrar_por_entidad:
            query = query.join(UnidadMedica).filter(
                UnidadMedica.id_entidad == filtro.valor_entidad
            )
        # sin_filtro → no se agrega ninguna condición adicional
    """
    if usuario.es_responsable_unidad:
        return FiltroRBAC(
            filtrar_por_clues=True,
            valor_clues=usuario.clues_unidad_asignada,
            filtrar_por_entidad=False,
            valor_entidad=None,
            sin_filtro=False,
        )

    if usuario.es_admin_estatal:
        return FiltroRBAC(
            filtrar_por_clues=False,
            valor_clues=None,
            filtrar_por_entidad=True,
            valor_entidad=usuario.id_entidad,
            sin_filtro=False,
        )

    # SUPER_ADMIN
    return FiltroRBAC(
        filtrar_por_clues=False,
        valor_clues=None,
        filtrar_por_entidad=False,
        valor_entidad=None,
        sin_filtro=True,
    )


# ---------------------------------------------------------------------------
# Lógica de autenticación (usada por POST /auth/login)
# ---------------------------------------------------------------------------

def autenticar_usuario(email: str, password: str, db: Session) -> Usuario:
    """
    Valida credenciales y retorna el objeto Usuario de la BD.
    Lanza 401 si el email no existe o la contraseña es incorrecta.
    Usa un mensaje genérico para no revelar si el email está registrado.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if usuario is None or not verify_password(password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario