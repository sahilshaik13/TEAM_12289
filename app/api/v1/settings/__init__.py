from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.memory import DomainBlocklist
from app.api.v1.schemas import BlocklistEntry
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/settings/blocklist", tags=["settings"])


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


@router.get("", response_model=list[BlocklistEntry])
async def get_blocklist(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    result = await db.execute(
        select(DomainBlocklist).where(DomainBlocklist.user_id == user.id)
    )
    entries = result.scalars().all()
    return [
        BlocklistEntry(
            id=str(e.id),
            domain=e.domain,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.post("", response_model=BlocklistEntry)
async def add_blocklist_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    existing = await db.execute(
        select(DomainBlocklist).where(
            DomainBlocklist.user_id == user.id,
            DomainBlocklist.domain == domain,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Domain already blocked")

    entry = DomainBlocklist(user_id=user.id, domain=domain)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return BlocklistEntry(
        id=str(entry.id),
        domain=entry.domain,
        created_at=entry.created_at.isoformat(),
    )


@router.delete("/{entry_id}")
async def remove_blocklist_domain(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    result = await db.execute(
        select(DomainBlocklist).where(
            DomainBlocklist.id == uuid.UUID(entry_id),
            DomainBlocklist.user_id == user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    await db.delete(entry)
    await db.commit()
    return {"message": "Domain removed from blocklist"}
