from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    display_name: str | None


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    avatar_url: str | None
    memory_count: int


class IngestRequest(BaseModel):
    source_type: str
    title: str | None = None
    url: str | None = None
    file_path: str | None = None
    file_hash: str | None = None
    raw_text: str


class IngestResponse(BaseModel):
    memory_id: str
    status: str


class SearchResult(BaseModel):
    memory_id: str
    chunk_id: str
    score: float
    similarity: float
    recency_score: float
    title: str | None
    url: str | None
    file_path: str | None
    source_type: str
    snippet: str
    domain: str | None
    captured_at: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    latency_ms: int


class MemoryResponse(BaseModel):
    id: str
    source_type: str
    title: str | None
    url: str | None
    file_path: str | None
    status: str
    domain: str | None
    captured_at: str
    indexed_at: str | None
    chunk_count: int | None


class DashboardStats(BaseModel):
    total_memories: int
    web_count: int
    pdf_count: int
    code_count: int
    text_count: int
    recent_activity: list[dict]


class HeatmapEntry(BaseModel):
    date: str
    count: int


class DomainStats(BaseModel):
    domain: str
    count: int


class BlocklistEntry(BaseModel):
    id: str
    domain: str
    created_at: str


DEFAULT_BLOCKED_DOMAINS = [
    "mail.google.com",
    "outlook.live.com",
    "outlook.office.com",
    "accounts.google.com",
    "login.microsoftonline.com",
    "bankofamerica.com",
    "chase.com",
    "paypal.com",
    "1password.com",
    "lastpass.com",
    "bitwarden.com",
]
