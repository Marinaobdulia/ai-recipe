FROM python:3.11-slim

WORKDIR /app

# Evita problemas con logs bufferizados
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema si hiciera falta
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (mejor cacheo)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Comando de arranque (ajústalo si tu entrypoint es distinto)
CMD ["python", "agent.py"]
