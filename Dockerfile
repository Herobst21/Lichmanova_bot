# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/app

# Базовые системные зависимости для сборки колёс и нормального SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/*

# Обновим pip
RUN python -m pip install --upgrade pip

# Сначала копируем только метаданные проекта, чтобы кешировать установку зависимостей,
# но у нас setuptools find_packages, так что проще сразу весь проект.
COPY . .

# Ставим зависимости проекта по pyproject.toml
# (aiogram, SQLAlchemy, asyncpg, psycopg[binary], alembic, fastapi, uvicorn и пр. подтянутся отсюда)
RUN pip install -e .

# По умолчанию запускаем ВЕБ. Для бота в docker-compose выставь ENV RUN_TARGET=bot
ENV RUN_TARGET=web

EXPOSE 8080

# Универсальная точка входа: web или bot
CMD [ "sh", "-lc", "if [ \"$RUN_TARGET\" = \"bot\" ]; then python -m app.main; else uvicorn app.web.server:app --host 0.0.0.0 --port 8080 --log-level info; fi" ]

COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]