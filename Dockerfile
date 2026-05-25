FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway inyecta $PORT automáticamente; --host 0.0.0.0 es obligatorio en contenedor
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"