from logging.config import fileConfig
import os
from urllib.parse import urlparse, parse_qs
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base
from app.models import User, Memory, MemoryChunk, DomainBlocklist


def _clean_url(raw: str) -> str:
    url = raw or ""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs.pop("sslmode", None)
    qs.pop("channel_binding", None)
    clean_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
    netloc = parsed.netloc
    if "@" in netloc:
        user_pass, host = netloc.split("@", 1)
        netloc = f"{user_pass}@{host}"
    path = parsed.path or ""
    return f"{parsed.scheme}://{netloc}{path}?{clean_query}" if clean_query else f"{parsed.scheme}://{netloc}{path}"


raw_url = os.environ.get("DATABASE_URL")
if not raw_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Copy .env.example to .env and fill in your database credentials."
    )
clean_url = _clean_url(raw_url)


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=clean_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    async_engine = create_async_engine(
        clean_url,
        echo=False,
        connect_args={"server_settings": {"sslmode": "require"}},
    )
    import asyncio
    asyncio.run(_run_online(async_engine))


async def _run_online(async_engine):
    async with async_engine.connect() as connection:
        await connection.run_sync(lambda conn: context.configure(
            connection=conn,
            target_metadata=target_metadata,
        ))
        with connection.begin():
            await connection.run_sync(context.run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
