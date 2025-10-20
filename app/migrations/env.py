from __future__ import annotations

import os
import sys
import hashlib
import importlib
import inspect
from logging.config import fileConfig
from pathlib import Path
from pprint import pformat
from datetime import datetime

from alembic import context
from sqlalchemy import engine_from_config, pool

# ------------------------------------------------------------------------------
# PYTHONPATH и базовая диагностика процесса
# ------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _sha256(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return "<nohash>"

HERE = Path(__file__).resolve()
BOOT_BANNER = f"""
=== ALEMBIC ENV BOOT ===
time: {datetime.utcnow().isoformat()}Z
pid: {os.getpid()}
cwd: {os.getcwd()}
env.py: {HERE} (sha256={_sha256(HERE)})
sys.path[0]: {sys.path[0]}
PYTHONPATH: {os.environ.get('PYTHONPATH')}
DATABASE_URL: {os.environ.get('DATABASE_URL')}
POSTGRES_DSN: {os.environ.get('POSTGRES_DSN')}
========================
"""
print(BOOT_BANNER, flush=True)

# ------------------------------------------------------------------------------
# Alembic config + логирование
# ------------------------------------------------------------------------------
config = context.config
if config.config_file_name and os.path.exists(config.config_file_name):
    try:
        fileConfig(config.config_file_name)
    except Exception as e:
        print(f"[env.py] fileConfig error: {e}", flush=True)

# ------------------------------------------------------------------------------
# Грузим правильный Base и МОДУЛИ МОДЕЛЕЙ ЖЁСТКО
# ------------------------------------------------------------------------------
print("[env.py] importing Base and model modules...", flush=True)
from app.models.base import Base  # единый Base с naming_convention

# Модули моделей: перечисляем явно
MODEL_MODULES = [
    "app.models.user",
    "app.models.subscription",
    "app.models.payment",
    "app.models.access_grant",
    "app.models.access_link",
    "app.models.reminder",
    "app.models.setting",
    "app.models.material",
    "app.models.churn_reason",
]

_loaded = {}
for mod in MODEL_MODULES:
    try:
        m = importlib.import_module(mod)
        path = Path(inspect.getfile(m)).resolve()
        _loaded[mod] = {"file": str(path), "sha256": _sha256(path)}
    except Exception as e:
        _loaded[mod] = {"error": repr(e)}

print("[env.py] loaded model modules:\n" + pformat(_loaded), flush=True)

# Печатаем, что реально в metadata
tables = sorted(Base.metadata.tables.keys())
print(f"[env.py] Base id={id(Base)} metadata id={id(Base.metadata)}", flush=True)
print("[env.py] tables in Base.metadata:", tables, flush=True)

# Если ключевые таблицы не видны — валимся громко
required = {"users", "subscriptions", "payments", "access_grants"}
missing = required.difference(tables)
if missing:
    raise RuntimeError(f"[env.py] Missing tables in Base.metadata: {missing}")

# ------------------------------------------------------------------------------
# DSN конверсия
# ------------------------------------------------------------------------------
def _to_sync_dsn(dsn: str) -> str:
    if "+asyncpg" in dsn:
        return dsn.replace("+asyncpg", "+psycopg")
    if "+aiopg" in dsn:
        return dsn.replace("+aiopg", "+psycopg")
    return dsn

env_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
if not env_url:
    env_url = "postgresql+psycopg://app:app@db:5432/app"
config.set_main_option("sqlalchemy.url", _to_sync_dsn(env_url))

# ------------------------------------------------------------------------------
# MetaData
# ------------------------------------------------------------------------------
target_metadata = Base.metadata

# ------------------------------------------------------------------------------
# Миграции
# ------------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    print(f"[env.py] offline migrations, url={url}", flush=True)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        print(f"[env.py] online migrations, dsn={connection.engine.url}", flush=True)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            print("[env.py] running migrations...", flush=True)
            context.run_migrations()
            print("[env.py] migrations done.", flush=True)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
