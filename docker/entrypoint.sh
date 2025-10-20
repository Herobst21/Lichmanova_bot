#!/usr/bin/env sh
set -e

# ждем БД
python - <<'PY'
import os, time
from sqlalchemy import create_engine
dsn = (os.getenv("DATABASE_URL") or "postgresql+psycopg://app:app@db:5432/app").replace("+asyncpg","+psycopg")
for i in range(60):
    try:
        create_engine(dsn).connect().close()
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("DB is not reachable")
PY

# миграции
alembic upgrade head

# запускаем основной процесс контейнера
exec "$@"
