from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid
import hashlib
from urllib.parse import urlparse

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.memory import Memory
from app.api.v1.schemas import IngestRequest, IngestResponse
from google.cloud import storage

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def extract_domain(url: str) -> str | None:
    try:
        return urlparse(url).netloc
    except Exception:
        return None


@router.post("", response_model=IngestResponse)
async def ingest_memory(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.source_type not in ("web", "pdf", "code", "text"):
        raise HTTPException(status_code=400, detail="Invalid source_type")

    if payload.url:
        existing = await db.execute(
            select(Memory).where(
                Memory.user_id == user.id,
                Memory.url == payload.url,
            )
        )
        existing_mem = existing.scalar_one_or_none()
        if existing_mem:
            return IngestResponse(memory_id=str(existing_mem.id), status="duplicate")

    if payload.file_hash:
        existing = await db.execute(
            select(Memory).where(
                Memory.user_id == user.id,
                Memory.file_hash == payload.file_hash,
            )
        )
        existing_mem = existing.scalar_one_or_none()
        if existing_mem:
            return IngestResponse(memory_id=str(existing_mem.id), status="duplicate")

    memory = Memory(
        user_id=user.id,
        source_type=payload.source_type,
        title=payload.title,
        url=payload.url,
        file_path=payload.file_path,
        file_hash=payload.file_hash,
        gcs_blob_path=f"users/{user.id}/memories/{uuid.uuid4()}.txt",
        status="pending",
        domain=extract_domain(payload.url) if payload.url else None,
        word_count=len(payload.raw_text.split()),
    )
    db.add(memory)
    await db.flush()

    try:
        gcs_client = storage.Client()
        bucket = gcs_client.bucket(settings.GCS_BUCKET)
        blob = bucket.blob(memory.gcs_blob_path)
        blob.upload_from_string(payload.raw_text[:50000], content_type="text/plain")
    except Exception:
        pass

    user.memory_count += 1
    await db.commit()

    return IngestResponse(memory_id=str(memory.id), status="queued")
