from vertexai.language_models import TextEmbeddingModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google.cloud import storage, tasks_v2
from google.cloud.aiplatform import AIPlatformException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import json
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import Base
from app.models.memory import Memory, MemoryChunk

model = TextEmbeddingModel.from_pretrained("text-embedding-004")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    length_function=lambda x: len(x.split()),
)

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def embed_memory(memory_id: str):
    async with async_session_maker() as db:
        result = await db.execute(select(Memory).where(Memory.id == uuid.UUID(memory_id)))
        memory = result.scalar_one_or_none()
        if not memory:
            return {"error": "Memory not found"}

        gcs_client = storage.Client()
        bucket = gcs_client.bucket(settings.GCS_BUCKET)
        blob = bucket.blob(memory.gcs_blob_path)

        try:
            raw_text = blob.download_as_text()
        except Exception:
            raw_text = ""

        if not raw_text:
            memory.status = "failed"
            await db.commit()
            return {"error": "Could not fetch raw text"}

        chunks = splitter.split_text(raw_text)
        memory.chunk_count = len(chunks)

        batch_size = 250
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start:batch_start + batch_size]
            try:
                embeddings = model.get_embeddings(batch)
            except AIPlatformException as e:
                memory.status = "failed"
                await db.commit()
                return {"error": f"Vertex AI error: {e}"}

            for i, (chunk_text, embedding_obj) in enumerate(zip(batch, embeddings)):
                chunk = MemoryChunk(
                    memory_id=memory.id,
                    user_id=memory.user_id,
                    chunk_index=batch_start + i,
                    chunk_text=chunk_text,
                    token_count=len(chunk_text.split()),
                    embedding=embedding_obj.values,
                )
                db.add(chunk)

        memory.status = "indexed"
        memory.indexed_at = datetime.now(timezone.utc)
        await db.commit()

        return {"memory_id": memory_id, "chunks_created": len(chunks), "status": "indexed"}


async def process_embedding_task(payload: dict):
    memory_id = payload.get("memory_id")
    if not memory_id:
        return {"error": "No memory_id in payload"}

    return await embed_memory(memory_id)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.workers.embedder <memory_id>")
        sys.exit(1)
    memory_id = sys.argv[1]
    result = embed_memory(memory_id)
    print(result)
