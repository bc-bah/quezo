FROM ghcr.io/astral-sh/uv:0.12.17 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app/postgres
ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY postgres/pyproject.toml postgres/uv.lock ./
RUN uv sync --locked --no-dev
COPY postgres/alembic.ini ./
COPY postgres/src ./src
COPY postgres/migrations ./migrations
COPY infra/keycloak /app/infra/keycloak

USER 10001:10001
EXPOSE 4000
CMD [".venv/bin/uvicorn", "--app-dir", "src", "quezo_api.app:create_app", "--factory", "--loop", "quezo_api.database:database_loop_factory", "--host", "0.0.0.0", "--port", "4000", "--no-server-header", "--no-access-log"]
