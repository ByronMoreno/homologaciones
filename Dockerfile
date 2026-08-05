FROM python:3.10-slim

# Evitar que Python escriba archivos .pyc y forzar salida de logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL client (psycopg2) y herramientas de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos primero para aprovechar la caché de capas de Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . /app/

# Exponer el puerto
EXPOSE 5000

# Comando por defecto para desarrollo (con autorecarga y modo debug si se configura FLASK_DEBUG)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
