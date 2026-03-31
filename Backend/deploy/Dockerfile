# Stage 1: Dependency Resolution
FROM python:3.11-slim as builder

WORKDIR /app
COPY Backend/pyproject.toml ./pyproject.toml

RUN pip install --no-cache-dir build poetry uv

# Adopt standard Linux venv separation bounds isolating logic code from bin commands
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias desde el directorio Backend
COPY Backend/ ./
RUN pip install --no-cache-dir .

# Stage 2: Production Minimal Container
FROM python:3.11-slim as runner

WORKDIR /app

RUN useradd -m crmuser
USER crmuser

# Secure migration
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY Backend/app/ ./app/

ENV ENVIRONMENT="production"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Aggressive memory scaling with context workers defined by host limits, discarding debug traces in raw proxy stdout (Uvicorn access-log)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
