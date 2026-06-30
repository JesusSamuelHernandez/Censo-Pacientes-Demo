FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Infraestructura puede ajustar WEB_CONCURRENCY según CPU/RAM y conexiones disponibles.
ENTRYPOINT ["sh", "-c", "gunicorn -w ${WEB_CONCURRENCY:-2} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000}"]