# ================================================================================
# ⚠️  DOCS FIRST: Antes de modificar este Dockerfile o el pipeline de deploy,
#     consultar la documentación oficial actualizada:
#     - FastAPI Quickstart: https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service
#     - Continuous Deployment: https://cloud.google.com/run/docs/continuous-deployment
#     - Cloud Build IAM: https://cloud.google.com/build/docs/securing-builds/configure-access-control
#     - Dockerfile best practices: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
#
# ⚠️  LOGGING: El proceso de deploy DEBE producir logs visibles en Cloud Build.
#     Si un deploy falla sin logs, resolver el problema de logging PRIMERO.
#
# ⚠️  ESTRUCTURA: Este Dockerfile es SELF-CONTAINED dentro de Backend/.
#     El build context de Cloud Build debe apuntar a /Backend/ (no a /).
#     Todas las rutas COPY son relativas a Backend/ — SIN prefijo "Backend/".
#     Esto sigue el patrón oficial del FastAPI Quickstart de Cloud Run.
# ================================================================================

# Stage 1: Dependency Resolution
FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml ./pyproject.toml

RUN pip install --no-cache-dir build poetry uv

# Standard Linux venv separation: isolate app deps from system packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install all dependencies from pyproject.toml
COPY . ./
RUN pip install --no-cache-dir .

# Stage 2: Production Minimal Container
FROM python:3.11-slim AS runner

WORKDIR /app

RUN useradd -m crmuser
USER crmuser

# Copy only the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the application code
COPY app/ ./app/

ENV ENVIRONMENT="production"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Uvicorn with single worker for Cloud Run (1 container = 1 instance)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
