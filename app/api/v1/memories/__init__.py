from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.memory import Memory, MemoryChunk
from app.api.v1.schemas import MemoryResponse
from google.cloud import storage
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


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


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    source_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    query = select(Memory).where(Memory.user_id == user.id)
    if source_type:
        query = query.where(Memory.source_type == source_type)
    query = query.order_by(Memory.captured_at.desc()).limit(limit).offset(offset)
    rows = await db.execute(query)
    memories = rows.scalars().all()

    return [
        MemoryResponse(
            id=str(m.id),
            source_type=m.source_type,
            title=m.title,
            url=m.url,
            file_path=m.file_path,
            status=m.status,
            domain=m.domain,
            captured_at=m.captured_at.isoformat(),
            indexed_at=m.indexed_at.isoformat() if m.indexed_at else None,
            chunk_count=m.chunk_count,
        )
        for m in memories
    ]


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    result = await db.execute(
        select(Memory).where(Memory.id == uuid.UUID(memory_id), Memory.user_id == user.id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryResponse(
        id=str(memory.id),
        source_type=memory.source_type,
        title=memory.title,
        url=memory.url,
        file_path=memory.file_path,
        status=memory.status,
        domain=memory.domain,
        captured_at=memory.captured_at.isoformat(),
        indexed_at=memory.indexed_at.isoformat() if memory.indexed_at else None,
        chunk_count=memory.chunk_count,
    )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    result = await db.execute(
        select(Memory).where(Memory.id == uuid.UUID(memory_id), Memory.user_id == user.id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    try:
        gcs_client = storage.Client()
        bucket = gcs_client.bucket("")
        bucket.blob(memory.gcs_blob_path).delete()
    except Exception:
        pass

    user.memory_count = max(0, user.memory_count - 1)
    await db.delete(memory)
    await db.commit()
    return {"message": "Memory deleted"}


@router.delete("")
async def delete_all_memories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user_from_token),
):
    result = await db.execute(select(Memory).where(Memory.user_id == user.id))
    memories = result.scalars().all()

    gcs_client = storage.Client()
    bucket = gcs_client.bucket("")

    for memory in memories:
        try:
            bucket.blob(memory.gcs_blob_path).delete()
        except Exception:
            pass

    await db.execute(
        select(Memory).where(Memory.user_id == user.id)
    )
    user.memory_count = 0
    await db.commit()
    return {"message": "All memories deleted"}
