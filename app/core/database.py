from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from urllib.parse import urlparse, parse_qs


def _build_async_url() -> str:
    url = settings.DATABASE_URL
    if not url:
        return ""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs.pop("sslmode", None)
    qs.pop("channel_binding", None)
    clean_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}" if clean_query else f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


engine = create_async_engine(
    _build_async_url(),
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {"sslmode": "require"},
    },
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
