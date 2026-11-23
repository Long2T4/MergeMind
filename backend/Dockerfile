# MergeMind API image (Stage 14). Build from backend/: docker build -t mergemind-api .
# Runs one uvicorn worker: AI limits for beginner explanations and background
# pull request reviews live in this process. Migrations are NOT run here;
# apply them deliberately (see docs/deployment.md).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Semgrep in its own environment: its dependencies conflict with the backend's.
COPY requirements-semgrep.txt .
RUN python -m venv /opt/semgrep && /opt/semgrep/bin/pip install -r requirements-semgrep.txt

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home --uid 10001 mergemind
USER mergemind

ENV SEMGREP_EXECUTABLE=/opt/semgrep/bin/semgrep \
    API_DOCS_ENABLED=false \
    PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
