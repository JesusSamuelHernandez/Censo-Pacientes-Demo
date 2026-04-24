FROM node:20-alpine

WORKDIR /app

# Copiar archivos de configuración
COPY package*.json ./

# Instalar dependencias
RUN npm install

# Copiar código fuente
COPY . .

# Exponer puerto de desarrollo de Vite
EXPOSE 5173

# Ejecutar servidor de desarrollo
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
