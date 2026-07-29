# Imagen fijada por digest (SAST-16): un tag como "20-alpine" es mutable.
# Verificar/actualizar con: docker buildx imagetools inspect node:20-alpine
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293

WORKDIR /app

# Copiar archivos de configuración
COPY package*.json ./

# npm ci (no npm install): instalacion reproducible desde el lockfile exacto
# (SAST-16).
RUN npm ci

# Copiar código fuente
COPY . .

# Usuario no-root (SAST-16): node:alpine ya trae un usuario "node" sin
# privilegios listo para usar; el servidor de dev de Vite no necesita root.
RUN chown -R node:node /app
USER node

# Exponer puerto de desarrollo de Vite
EXPOSE 5173

# Ejecutar servidor de desarrollo
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
