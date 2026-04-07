from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.memory import Memory
from app.api.v1.schemas import DashboardStats, HeatmapEntry, DomainStats
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


async def get_user_from_token(
    db: AsyncSession = Depends(get_db),
    authorization: str = "",
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = authorization.split("Bearer ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    counts = await db.execute(
        select(
            func.count(Memory.id).label("total"),
            func.sum(func.cast(Memory.source_type == "web", type_=Integer)).label("web"),
            func.sum(func.cast(Memory.source_type == "pdf", type_=Integer)).label("pdf"),
            func.sum(func.cast(Memory.source_type == "code", type_=Integer)).label("code"),
            func.sum(func.cast(Memory.source_type == "text", type_=Integer)).label("text"),
        ).where(Memory.user_id == user.id)
    )
    row = counts.one()

    recent = await db.execute(
        select(Memory)
        .where(Memory.user_id == user.id)
        .order_by(Memory.captured_at.desc())
        .limit(5)
    )
    recent_memories = recent.scalars().all()

    return DashboardStats(
        total_memories=row.total or 0,
        web_count=row.web or 0,
        pdf_count=row.pdf or 0,
        code_count=row.code or 0,
        text_count=row.text or 0,
        recent_activity=[
            {
                "title": m.title or m.url or m.file_path,
                "source_type": m.source_type,
                "captured_at": m.captured_at.isoformat(),
            }
            for m in recent_memories
        ],
    )


@router.get("/heatmap", response_model=list[HeatmapEntry])
async def get_heatmap(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    from sqlalchemy import Integer
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(
            func.date(Memory.captured_at).label("date"),
            func.count(Memory.id).label("count"),
        )
        .where(Memory.user_id == user.id, Memory.captured_at >= thirty_days_ago)
        .group_by(func.date(Memory.captured_at))
        .order_by(func.date(Memory.captured_at))
    )
    rows = result.all()
    return [HeatmapEntry(date=str(r.date), count=r.count) for r in rows]


@router.get("/domains", response_model=list[DomainStats])
async def get_domains(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    result = await db.execute(
        select(Memory.domain, func.count(Memory.id).label("count"))
        .where(Memory.user_id == user.id, Memory.domain.isnot(None))
        .group_by(Memory.domain)
        .order_by(func.count(Memory.id).desc())
        .limit(10)
    )
    rows = result.all()
    return [DomainStats(domain=r.domain or "", count=r.count) for r in rows]
