import sys
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Parche de compatibilidad para bcrypt
# Esto evita el error 'AttributeError: module bcrypt has no attribute __about__'
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type('About', (object,), {'__version__': bcrypt.__version__})

# Aseguramos que Python encuentre la carpeta 'app' para las importaciones
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app.models import Base, Usuario


def create_additional_admin():
    # 1. Conexión y creación de tablas (si aún no existen)
    print("Conectando a la base de datos y verificando tablas...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Leer credenciales desde variables de entorno
        email_admin = os.getenv("ADDITIONAL_ADMIN_EMAIL")
        password_plana = os.getenv("ADDITIONAL_ADMIN_PASSWORD")

        if not email_admin:
            raise ValueError("La variable de entorno ADDITIONAL_ADMIN_EMAIL es obligatoria")
        if not password_plana:
            raise ValueError("La variable de entorno ADDITIONAL_ADMIN_PASSWORD es obligatoria")

        # Derivar nombre_usuario desde la parte local del email (antes del @)
        # Ej: "jesus.hernandezh@imssbienestar.gob.mx" → "Jesus"
        local_part = email_admin.split("@")[0]          # "jesus.hernandezh"
        first_name = local_part.split(".")[0].capitalize()  # "Jesus"

        # 3. Verificar si el usuario ya existe para no duplicar
        user_exists = db.query(Usuario).filter(Usuario.email == email_admin).first()

        if user_exists:
            print(f"El usuario '{email_admin}' ya existe en la base de datos. No se realizaron cambios.")
            return

        # 4. Proceso de seguridad: hashear la contraseña con bcrypt
        print(f"Encriptando contraseña y preparando usuario: {email_admin}...")

        salt = bcrypt.gensalt()
        password_hasheada = bcrypt.hashpw(password_plana.encode('utf-8'), salt).decode('utf-8')

        # 5. Creación del objeto Usuario en la base de datos
        nuevo_usuario = Usuario(
            nombre_usuario=first_name,
            email=email_admin,
            hashed_password=password_hasheada,
            rol_nombre="SUPER_ADMIN",
            clues_unidad_asignada=None,
            id_entidad=None,
            debe_cambiar_password=False,
        )

        db.add(nuevo_usuario)
        db.commit()

        print("--------------------------------------------------")
        print("¡ÉXITO! Usuario Admin adicional registrado.")
        print(f"Nombre   : {first_name}")
        print(f"Usuario  : {email_admin}")
        print(f"Rol      : SUPER_ADMIN")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"Error al crear el usuario: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_additional_admin()
