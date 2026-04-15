Requisitos previos
Python 3.11+
Docker Desktop instalado y corriendo
Git
Pasos de instalación
1. Clonar el repositorio


git clone <url-del-repo>
cd Censo_de_pacientes_01
2. Crear el entorno virtual e instalar dependencias


python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
3. Crear el archivo .env


# Copiar la plantilla
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux
El .env.example ya tiene los valores correctos para desarrollo local. Para generar claves seguras usa estos comandos:

JWT_SECRET_KEY (mínimo 32 caracteres):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

FERNET_KEY:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

4. Levantar la base de datos con Docker


docker compose up -d
5. Crear el usuario SUPER_ADMIN


python create_admin.py
Tomar nota del email y contraseña que imprime.

6. Levantar el servidor


uvicorn app.main:app --reload
7. Verificar en el navegador

Swagger UI: http://127.0.0.1:8000/docs
Hacer login con las credenciales del paso 5.