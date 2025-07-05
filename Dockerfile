FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del bot
COPY . .

# Hacer el script ejecutable
RUN chmod +x start.sh

# Exponer puertos
EXPOSE 8080

# Usar el script simple en lugar de supervisor
CMD ["./start.sh"]
