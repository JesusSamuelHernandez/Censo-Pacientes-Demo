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

# Script de inicio inline (Railway inyecta $PORT automáticamente)
#CMD sh -c "python create_admin.py 2>/dev/null || true && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
CMD sed -i -e 's/80/'"$PORT"'/g' /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'