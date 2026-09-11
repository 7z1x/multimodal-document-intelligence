FROM python:3.12-slim

WORKDIR /app
COPY services/api/pyproject.toml services/api/uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY services/api/app ./app
COPY services/api/alembic ./alembic
COPY services/api/alembic.ini ./alembic.ini

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
