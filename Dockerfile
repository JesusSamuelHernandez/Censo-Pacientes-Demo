# Imagen fijada por digest (SAST-16): un tag como "3.11-slim" es mutable y
# puede cambiar de contenido sin aviso. Verificar/actualizar el digest con:
#   docker buildx imagetools inspect python:3.11-slim
FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

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

# Usuario no-root (SAST-16): gunicorn no necesita privilegios de root dentro
# del contenedor.
RUN groupadd --system app && useradd --system --gid app --no-create-home app \
    && chown -R app:app /app
USER app

# Infraestructura puede ajustar WEB_CONCURRENCY según CPU/RAM y conexiones disponibles.
ENTRYPOINT ["sh", "-c", "gunicorn -w ${WEB_CONCURRENCY:-2} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000}"]