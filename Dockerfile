# =============================================================
# Dockerfile — Hotspot Auth Flask
# =============================================================
FROM python:3.12-slim

# Metadados
LABEL maintainer="ISP Hotspot Auth"
LABEL description="Servidor de autenticação Hotspot MikroTik via número de celular"

# Variáveis de ambiente base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências primeiro (cache de layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY app.py .
COPY templates/ templates/

# Cria o volume de dados persistente (logs)
RUN mkdir -p /data && chmod 777 /data

# Porta exposta
EXPOSE 5000

# Healthcheck interno do Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" || exit 1

# Inicia com Gunicorn (produção) — 2 workers, timeout 60s
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
