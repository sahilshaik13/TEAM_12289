from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Integer
from datetime import datetime, timezone
import uuid
import math
import time

from app.core.database import get_db
from app.core.security import decode_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.memory import Memory, MemoryChunk
from app.api.v1.schemas import SearchResponse, SearchResult

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def get_embedding_model():
    from vertexai.language_models import TextEmbeddingModel
    return TextEmbeddingModel.from_pretrained("text-embedding-004")


@router.get("", response_model=SearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1),
    source_type: str | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = time.time()

    model = get_embedding_model()
    query_embedding = model.get_embeddings([q])[0].values

    filters = [MemoryChunk.user_id == user.id]
    if source_type:
        filters.append(Memory.source_type == source_type)
    if since:
        filters.append(Memory.captured_at >= since)

    ann_query = (
        select(
            MemoryChunk,
            Memory,
        )
        .join(Memory, MemoryChunk.memory_id == Memory.id)
        .where(*filters)
        .order_by(MemoryChunk.embedding.cosine_distance(query_embedding))
        .limit(40)
    )
    rows = await db.execute(ann_query)
    candidates = rows.all()

    now = datetime.now(timezone.utc)
    scored = []
    for chunk, memory in candidates:
        if chunk.embedding is None:
            continue
        similarity = 1 - chunk.embedding_cosine_distance(query_embedding)
        age_days = (now - memory.captured_at.replace(tzinfo=timezone.utc)).days
        recency_score = math.exp(-0.693 * age_days / 30)
        final_score = 0.70 * similarity + 0.30 * recency_score

        scored.append(SearchResult(
            memory_id=str(memory.id),
            chunk_id=str(chunk.id),
            score=round(final_score, 4),
            similarity=round(similarity, 4),
            recency_score=round(recency_score, 4),
            title=memory.title,
            url=memory.url,
            file_path=memory.file_path,
            source_type=memory.source_type,
            snippet=chunk.chunk_text[:400],
            domain=memory.domain,
            captured_at=memory.captured_at.isoformat(),
        ))

    scored.sort(key=lambda r: r.score, reverse=True)
    results = scored[:limit]
    latency_ms = int((time.time() - start) * 1000)

    return SearchResponse(
        query=q,
        results=results,
        total=len(results),
        latency_ms=latency_ms,
    )
