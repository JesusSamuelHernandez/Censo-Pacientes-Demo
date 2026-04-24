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

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Usuario 

def create_first_admin():
    # 1. Conexión y creación de tablas
    # Esta línea crea físicamente las tablas en tu base de datos de Docker
    print("Conectando a la base de datos y verificando tablas...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Configuración de tus credenciales
        # Puedes cambiar estos valores si prefieres otros datos de acceso
        email_admin = os.getenv("ADMIN_EMAIL", "admin@example.com")
        password_plana = os.getenv("ADMIN_PASSWORD")

        if not password_plana:
            raise ValueError("La variable de entorno ADMIN_PASSWORD es obligatoria")

        # Verificar si el usuario ya existe para no duplicar
        user_exists = db.query(Usuario).filter(Usuario.email == email_admin).first()

        if user_exists:
            print(f"El usuario {email_admin} ya existe en la base de datos.")
            return

        # 3. Proceso de Seguridad
        print(f"Encriptando contraseña y preparando usuario: {email_admin}...")
        
        # Generamos el hash (la versión secreta) de la contraseña plana
        salt = bcrypt.gensalt()
        password_hasheada = bcrypt.hashpw(password_plana.encode('utf-8'), salt).decode('utf-8')

        # 4. Creación del objeto Usuario para la base de datos
        nuevo_usuario = Usuario(
            nombre_usuario="Carolina",
            email=email_admin,
            hashed_password=password_hasheada,
            rol_nombre="SUPER_ADMIN",
            clues_unidad_asignada=None,
            id_entidad=None,
            debe_cambiar_password=False,  # El admin inicial no requiere cambio de contraseña
        )

        db.add(nuevo_usuario)
        db.commit()
        print("--------------------------------------------------")
        print("¡ÉXITO! Tablas creadas y Usuario Admin registrado.")
        print(f"Usuario (Login): {email_admin}")
        print(f"Contraseña: {password_plana}")
        print("Ahora ya puedes iniciar el servidor con uvicorn.")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"Error al crear el usuario: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_first_admin()