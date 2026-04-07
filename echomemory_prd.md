# EchoMemory — Product Requirements Document

**Version:** 1.0  
**Status:** Draft  
**Stack:** Python (FastAPI) + Next.js + PostgreSQL (pgvector) + GCP  
**Deployment Target:** Google Cloud Platform (Cloud Run)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Success Metrics](#3-goals--success-metrics)
4. [Users & Personas](#4-users--personas)
5. [Feature Requirements](#5-feature-requirements)
6. [System Architecture](#6-system-architecture)
7. [Tech Stack](#7-tech-stack)
8. [Data Models](#8-data-models)
9. [API Design](#9-api-design)
10. [Capture Layer — Browser Extension & File Watcher](#10-capture-layer--browser-extension--file-watcher)
11. [Ingestion & Embedding Pipeline](#11-ingestion--embedding-pipeline)
12. [Semantic Search Engine](#12-semantic-search-engine)
13. [GCP Infrastructure (Cost-Optimised)](#13-gcp-infrastructure-cost-optimised)
14. [Security & Privacy](#14-security--privacy)
15. [Non-Functional Requirements](#15-non-functional-requirements)
16. [Milestones & MVP Scope](#16-milestones--mvp-scope)
17. [Out of Scope (v1)](#17-out-of-scope-v1)

---

## 1. Executive Summary

EchoMemory is a personal semantic memory layer that passively and automatically indexes everything a user interacts with — web pages, PDFs, source code files, documents — and makes it all searchable through natural language, without any manual effort.

Unlike note-taking tools (Obsidian, Notion) or file search utilities (Everything, Alfred), EchoMemory requires zero input from the user. It runs silently in the background, understands the *meaning* of content (not just keywords), and surfaces the right memory when asked — days, weeks, or months later.

The platform consists of:

- A **Chrome browser extension** that captures web pages as the user browses
- A **Python file watcher daemon** that monitors the local filesystem for opened PDFs, code files, and documents
- A **Python (FastAPI) backend** that runs the ingestion pipeline, generates embeddings via Vertex AI, and exposes a semantic search API
- A **PostgreSQL database with pgvector** (hosted on Neon.tech) for storing memory chunks and their vector embeddings
- A **Cloud Storage bucket** for raw content blobs
- A **Cloud Tasks queue** for async, non-blocking embedding jobs
- A **Next.js frontend** for the search interface and memory timeline dashboard
- Everything deployed on **Google Cloud Run** — serverless, scales to zero, minimal cost

---

## 2. Problem Statement

The modern knowledge worker interacts with hundreds of pieces of information daily — research papers, Stack Overflow answers, GitHub issues, config files, documentation, blog posts. The problem is not access to information. The problem is *recall.*

- You read a paper about a technique three weeks ago. You cannot remember the title. You cannot find it.
- You opened a config file for a deployment two months ago. You remember the setting, not the path.
- You browsed a library's documentation yesterday. You cannot find the exact page.
- Ctrl+F only works if you still have the tab open. Browser history is chronological, not semantic.

Existing tools fail because they require manual effort (Notion, Obsidian, bookmarks), search by keyword not meaning (browser history, Spotlight), or only cover one content type (PDF readers, IDE file search).

EchoMemory solves this with a zero-friction, always-on, meaning-aware memory layer.

---

## 3. Goals & Success Metrics

### Primary Goals

- Capture and index content passively with no user action required
- Return accurate, relevant memories from a natural language query in under 500ms
- Support heterogeneous content types: web pages, PDFs, plain text, source code
- Keep all data private — user-owned, encrypted at rest, never used for training

### Success Metrics (Month 1 — Submission Baseline)

| Metric | Target |
|--------|--------|
| Memories captured (per user/day) | 20+ |
| Successful semantic searches | 50+ |
| Search relevance (manual eval top-3) | > 70% |
| Ingestion pipeline latency (p95) | < 5s per memory |
| Search API latency (p95) | < 500ms |
| Uptime | > 99% |

### Success Metrics (Post-Launch, 3 Months)

| Metric | Target |
|--------|---------|
| Active users | 200+ |
| Memories indexed (total) | 50,000+ |
| Daily searches per active user | 5+ |
| Retention (D30) | > 40% |

---

## 4. Users & Personas

### Persona 1 — The Researcher

> Aditya, 26, PhD student in ML. Reads 10–15 papers a week on arXiv and Semantic Scholar. Takes notes in Notion but half his reading happens outside it. Three weeks later, he vaguely remembers a paper about sparse attention but cannot find it. He spends 20 minutes searching browser history and Google Scholar.

**Needs:**
- Automatic capture of every paper he opens in the browser
- Search by concept ("that paper about sparse attention in transformers") not just title
- Timeline view of what he read last week

**Pain points today:**
- Browser history is chronological and keyword-only
- Notion requires him to paste links manually — he often forgets

---

### Persona 2 — The Developer

> Meera, 29, backend engineer. Jumps between five repos daily. Frequently looks up docs, Stack Overflow answers, and GitHub issues. Remembers solving a specific Postgres connection pooling issue six weeks ago but cannot find the Stack Overflow answer she used.

**Needs:**
- Capture of web pages she actively reads (not just visits)
- Code file tracking — she edits many files across repos
- Search that understands code concepts, not just file names

**Pain points today:**
- Search history gives her 200 results for "postgres"
- She has no record of which files she touched for which project

---

### Persona 3 — The Curious Generalist

> Rishi, 32, product manager. Reads newsletters, blog posts, industry reports. Saves things to Pocket but never actually reads them there. Remembers reading something about a specific pricing strategy but has no idea where.

**Needs:**
- Effortless capture — he should never have to think about it
- Search that retrieves conceptual matches ("pricing strategy SaaS") not exact phrases
- A memory dashboard showing what topics he's been reading about

---

## 5. Feature Requirements

### 5.1 Authentication

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-01 | Users sign in via Google OAuth only | P0 |
| AUTH-02 | Session stored server-side using JWT | P0 |
| AUTH-03 | User profile auto-populated from Google (name, avatar, email) | P0 |
| AUTH-04 | Users can log out and delete all their data | P0 |
| AUTH-05 | Extension authenticates using the same JWT as the web app | P0 |

---

### 5.2 Browser Extension (Chrome)

| ID | Requirement | Priority |
|----|-------------|----------|
| EXT-01 | Extension captures page content when user spends > 10 seconds on a tab | P0 |
| EXT-02 | Extracts clean readable text (strips nav, ads, boilerplate) using Readability.js | P0 |
| EXT-03 | Sends page URL, title, extracted text, and timestamp to backend | P0 |
| EXT-04 | Deduplicates: does not re-capture the same URL within 24 hours | P0 |
| EXT-05 | Popup shows capture status (enabled / paused) and memory count | P1 |
| EXT-06 | User can pause capturing per-tab or globally from the popup | P1 |
| EXT-07 | Domain blocklist (user can exclude sites like banking, email) | P1 |
| EXT-08 | Captures PDF files opened directly in the browser tab | P1 |

---

### 5.3 File Watcher Daemon

| ID | Requirement | Priority |
|----|-------------|----------|
| DAEMON-01 | Python daemon runs as a background process on the user's machine | P0 |
| DAEMON-02 | Watches configured directories (e.g., ~/Downloads, ~/Documents, ~/code) | P0 |
| DAEMON-03 | Triggers on file open event (inotify on Linux, FSEvents on Mac) | P0 |
| DAEMON-04 | Supported file types: `.pdf`, `.txt`, `.md`, `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.cpp` | P0 |
| DAEMON-05 | Extracts text from PDFs using pdfplumber | P0 |
| DAEMON-06 | Sends file path, filename, extracted text, and modification time to backend | P0 |
| DAEMON-07 | Deduplicates by file hash — does not re-index unchanged files | P0 |
| DAEMON-08 | Configurable via a simple `~/.echomemory/config.yaml` | P1 |
| DAEMON-09 | System tray icon (pystray) showing daemon status | P1 |

---

### 5.4 Semantic Search

| ID | Requirement | Priority |
|----|-------------|----------|
| SEARCH-01 | Natural language query returns top-10 most semantically relevant memory chunks | P0 |
| SEARCH-02 | Each result shows: title, source URL or file path, snippet, captured date | P0 |
| SEARCH-03 | Results ranked by a combined score: vector similarity + recency decay | P0 |
| SEARCH-04 | Filter by source type: web / pdf / code / text | P1 |
| SEARCH-05 | Filter by date range (e.g., "last 7 days", "last month") | P1 |
| SEARCH-06 | Keyboard shortcut to open search from anywhere (Cmd+Shift+E) | P2 |
| SEARCH-07 | Instant search — results appear as user types after 300ms debounce | P1 |

---

### 5.5 Memory Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| DASH-01 | Timeline view of all captured memories, newest first | P0 |
| DASH-02 | Memory count by source type (web / file / PDF) | P0 |
| DASH-03 | Topic clusters — automatically grouped memories by semantic similarity | P1 |
| DASH-04 | Heatmap of capture activity over the last 30 days | P1 |
| DASH-05 | Most visited domains | P1 |
| DASH-06 | User can delete individual memories | P0 |
| DASH-07 | User can delete all memories (full wipe) | P0 |

---

### 5.6 Ingestion Pipeline

| ID | Requirement | Priority |
|----|-------------|----------|
| PIPE-01 | Received content is chunked into 512-token overlapping segments | P0 |
| PIPE-02 | Each chunk is embedded via Vertex AI text-embedding-004 | P0 |
| PIPE-03 | Embeddings stored in PostgreSQL using pgvector (vector(768)) | P0 |
| PIPE-04 | Raw content stored in Cloud Storage (for re-indexing and display) | P0 |
| PIPE-05 | Embedding jobs processed asynchronously via Cloud Tasks | P0 |
| PIPE-06 | Ingestion is idempotent — duplicate submissions are safely ignored | P0 |
| PIPE-07 | Failed embedding jobs are retried up to 3 times with exponential backoff | P1 |

---

## 6. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CAPTURE LAYER                                 │
│                                                                        │
│   Chrome Extension          File Watcher Daemon (Python)               │
│   - Readability.js          - watchdog (filesystem events)             │
│   - 10s dwell-time gate     - pdfplumber for PDFs                      │
│   - Domain blocklist        - file hash deduplication                  │
│                                                                        │
│          │  POST /api/v1/ingest (JWT auth, raw content)                │
└──────────┼─────────────────────────────────────────────────────────────┘
           │ HTTPS
┌──────────▼─────────────────────────────────────────────────────────────┐
│                    BACKEND LAYER (GCP Cloud Run)                       │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  FastAPI Application (Python)                    │  │
│  │                                                                  │  │
│  │   /api/v1/auth/*        →  Google OAuth handler                 │  │
│  │   /api/v1/ingest        →  Capture receiver (ext + daemon)      │  │
│  │   /api/v1/search        →  Semantic search endpoint             │  │
│  │   /api/v1/memories/*    →  CRUD, timeline, delete               │  │
│  │   /api/v1/dashboard/*   →  Stats, topic clusters, heatmap       │  │
│  │                                                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐      │  │
│  │   │          Ingestion Pipeline (internal service)       │      │  │
│  │   │  1. Receive raw content                              │      │  │
│  │   │  2. Detect content type                              │      │  │
│  │   │  3. Clean & extract text                             │      │  │
│  │   │  4. Chunk into 512-token overlapping windows         │      │  │
│  │   │  5. Enqueue embedding job → Cloud Tasks              │      │  │
│  │   │  6. Store raw content → Cloud Storage                │      │  │
│  │   └──────────────────────────────────────────────────────┘      │  │
│  │                                                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐      │  │
│  │   │          Embedding Worker (Cloud Run Job)            │      │  │
│  │   │  1. Pull job from Cloud Tasks                        │      │  │
│  │   │  2. Fetch chunks from DB                             │      │  │
│  │   │  3. Call Vertex AI text-embedding-004                │      │  │
│  │   │  4. Store vector(768) in pgvector                    │      │  │
│  │   └──────────────────────────────────────────────────────┘      │  │
│  │                                                                  │  │
│  │   ┌──────────────────────────────────────────────────────┐      │  │
│  │   │          Search Engine (internal service)            │      │  │
│  │   │  1. Embed query via Vertex AI                        │      │  │
│  │   │  2. ANN search via pgvector HNSW index               │      │  │
│  │   │  3. Re-rank with recency decay                       │      │  │
│  │   │  4. Return top-10 chunks with parent memory context  │      │  │
│  │   └──────────────────────────────────────────────────────┘      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────────┬──────────────────────────────┘
           │                              │
┌──────────▼──────────┐      ┌────────────▼────────────────┐
│   Neon.tech          │      │   GCP Services               │
│   PostgreSQL + pgvec │      │                              │
│                      │      │   Cloud Storage  (raw blobs) │
│   - users            │      │   Cloud Tasks    (embed jobs)│
│   - memories         │      │   Vertex AI      (embeddings)│
│   - memory_chunks    │      │   Secret Manager (keys)      │
│   - domains_blocked  │      │   Artifact Registry (Docker) │
└──────────────────────┘      │   Cloud Build    (CI/CD)     │
                              │   Cloud Logging  (logs)      │
                              └──────────────────────────────┘
```

### Request Flow — Browser Captures a Web Page

```
1. User spends 12s on a blog post  →  Extension triggers capture
2. Readability.js extracts clean text from the DOM
3. Extension  →  POST /api/v1/ingest  {url, title, text, source_type: "web"}
4. FastAPI  →  Dedup check (same URL within 24h?)  →  Skip if duplicate
5. FastAPI  →  Create memory row in DB (status: pending)
6. FastAPI  →  Store raw text in Cloud Storage
7. FastAPI  →  Enqueue embedding task in Cloud Tasks
8. Cloud Tasks  →  Triggers Embedding Worker
9. Embedding Worker  →  Chunk text into 512-token segments
10. Embedding Worker  →  Batch call Vertex AI text-embedding-004
11. Embedding Worker  →  INSERT chunks + vector(768) into memory_chunks
12. Embedding Worker  →  Update memory status: "indexed"
```

### Request Flow — User Performs a Semantic Search

```
1. User types "that paper about sparse attention"
2. Browser  →  GET /api/v1/search?q=...&limit=10
3. FastAPI  →  Embed query via Vertex AI (single vector)
4. FastAPI  →  pgvector ANN query:
               SELECT chunk_id, 1 - (embedding <=> query_vec) AS similarity
               FROM memory_chunks
               WHERE user_id = $user_id
               ORDER BY embedding <=> query_vec
               LIMIT 40
5. FastAPI  →  Re-rank top-40 by: final_score = 0.7 * similarity + 0.3 * recency_score
6. FastAPI  →  Hydrate top-10 with parent memory metadata (title, url, captured_at)
7. FastAPI  →  Return ranked results JSON
8. Next.js  →  Render results with snippet highlighting
```

---

## 7. Tech Stack

### Backend — Python (FastAPI)

| Component | Technology | Reason |
|-----------|-----------|--------|
| Web framework | FastAPI 0.111+ | Async, fast, automatic OpenAPI docs |
| ASGI server | Uvicorn | Production-ready, pairs natively with FastAPI |
| ORM | SQLAlchemy 2.0 (async) | Async support, works with pgvector via custom types |
| Migrations | Alembic | Seamless with SQLAlchemy, supports raw SQL for pgvector |
| Auth | Authlib (Google OAuth) + PyJWT | OAuth2 PKCE flow + JWT session tokens |
| HTTP client | httpx | Async HTTP for Vertex AI and GCP API calls |
| PDF extraction | pdfplumber | Best-in-class structured text extraction from PDFs |
| Text chunking | langchain-text-splitters | Recursive character splitting with overlap |
| AI embeddings | google-cloud-aiplatform (Vertex AI) | text-embedding-004, 768-dim, GCP-native |
| Task queue | google-cloud-tasks | Async embedding job queue, retries, GCP-native |
| Storage client | google-cloud-storage | Raw content blob storage |
| Env management | python-dotenv | Local dev; Secret Manager in production |
| Testing | pytest + pytest-asyncio | Async test support |
| Linting | ruff | Fast Python linter |

### Frontend — Next.js

| Component | Technology | Reason |
|-----------|-----------|--------|
| Framework | Next.js 14 (App Router) | SSR, file-based routing, fast |
| Language | TypeScript | Type safety across the stack |
| Styling | Tailwind CSS + shadcn/ui | Rapid UI, accessible components |
| State | React Query (TanStack) | Search result caching, background refetch |
| Auth client | NextAuth.js | Google OAuth session on frontend |
| Charts | Recharts | Capture heatmap, topic distribution chart |
| Search UX | cmdk | Command-palette style search modal |

### Browser Extension

| Component | Technology | Reason |
|-----------|-----------|--------|
| Runtime | Chrome Manifest V3 | Current standard, required for Chrome Web Store |
| Content extraction | @mozilla/readability | Mozilla's own article extractor — battle-tested |
| Build | Vite + CRXJS | Fast extension bundler |
| Language | TypeScript | Type-safe message passing between content/background scripts |

### Database

| Component | Technology | Reason |
|-----------|-----------|--------|
| Database | PostgreSQL 16 + pgvector | Relational + vector search in a single DB, no separate vector store needed |
| Hosting | Neon.tech (free tier) | Serverless Postgres with pgvector support, $0 cost, 0.5GB |
| Driver | asyncpg | Fastest async PostgreSQL driver for Python |
| Vector index | HNSW (pgvector) | Sub-millisecond approximate nearest neighbor at scale |

### Infrastructure (GCP)

| Component | Technology | Reason |
|-----------|-----------|--------|
| Compute | Cloud Run | Serverless, scales to zero, no server management |
| Async jobs | Cloud Tasks | Managed embedding job queue with retries |
| AI embeddings | Vertex AI (text-embedding-004) | GCP-native, 768-dim, 2,048 token context |
| Raw storage | Cloud Storage | Cheap blob storage for text snapshots |
| Container registry | Artifact Registry | Docker image storage |
| CI/CD | Cloud Build | Auto-deploy on push to main |
| Secrets | Secret Manager | Secure credential storage |
| Monitoring | Cloud Logging + Cloud Run metrics | Free with Cloud Run |

---

## 8. Data Models

### users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_id       VARCHAR(255) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    display_name    VARCHAR(255),
    avatar_url      TEXT,
    memory_count    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### memories

```sql
CREATE TABLE memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type     VARCHAR(20) NOT NULL
                    CHECK (source_type IN ('web', 'pdf', 'code', 'text')),
    title           TEXT,
    url             TEXT,             -- for web captures
    file_path       TEXT,             -- for daemon captures
    file_hash       VARCHAR(64),      -- SHA-256, for deduplication
    gcs_blob_path   TEXT NOT NULL,    -- path to raw content in Cloud Storage
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'indexed', 'failed')),
    word_count      INTEGER,
    chunk_count     SMALLINT,
    domain          VARCHAR(255),     -- extracted from URL
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    indexed_at      TIMESTAMPTZ
);

CREATE INDEX idx_memories_user_id ON memories (user_id, captured_at DESC);
CREATE INDEX idx_memories_status ON memories (status);
CREATE INDEX idx_memories_domain ON memories (user_id, domain);
CREATE UNIQUE INDEX idx_memories_url_user ON memories (user_id, url)
    WHERE url IS NOT NULL;
CREATE UNIQUE INDEX idx_memories_hash_user ON memories (user_id, file_hash)
    WHERE file_hash IS NOT NULL;
```

---

### memory_chunks

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id       UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_index     SMALLINT NOT NULL,       -- position within the memory
    chunk_text      TEXT NOT NULL,
    token_count     SMALLINT,
    embedding       vector(768),             -- Vertex AI text-embedding-004 output
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW index for approximate nearest neighbour search
-- m=16 and ef_construction=64 are good defaults for recall vs speed
CREATE INDEX idx_chunks_embedding ON memory_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_chunks_user_id ON memory_chunks (user_id);
CREATE INDEX idx_chunks_memory_id ON memory_chunks (memory_id);
```

---

### domain_blocklist

```sql
CREATE TABLE domain_blocklist (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain      VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, domain)
);
```

---

## 9. API Design

All endpoints prefixed with `/api/v1`. FastAPI auto-generates OpenAPI docs at `/docs`.

### Authentication

```
POST  /api/v1/auth/google          →  Initiate Google OAuth flow
GET   /api/v1/auth/callback        →  Handle Google callback, return JWT
POST  /api/v1/auth/logout          →  Invalidate session
GET   /api/v1/auth/me              →  Return current user from JWT
```

### Ingest

```
POST  /api/v1/ingest               →  Receive capture from extension or daemon
      Body: { source_type, title?, url?, file_path?, file_hash?, raw_text }
      Returns: { memory_id, status: "queued" }
```

### Search

```
GET   /api/v1/search               →  Semantic search
      ?q=sparse+attention+transformer
      ?source_type=web|pdf|code|text
      ?since=2025-01-01
      ?limit=10
      Returns: ranked list of memory chunks with parent memory metadata
```

### Memories

```
GET   /api/v1/memories             →  Paginated timeline of all memories
      ?source_type=web
      ?limit=20&offset=0

GET   /api/v1/memories/{id}        →  Full memory detail + all chunks
DELETE /api/v1/memories/{id}       →  Delete memory + chunks + GCS blob
DELETE /api/v1/memories            →  Wipe all memories for current user
```

### Dashboard

```
GET   /api/v1/dashboard/stats      →  Memory count, type breakdown, recent activity
GET   /api/v1/dashboard/heatmap    →  Daily capture counts for last 30 days
GET   /api/v1/dashboard/domains    →  Top 10 captured domains
GET   /api/v1/dashboard/clusters   →  Semantic topic clusters (k-means on embeddings)
```

### Settings

```
GET   /api/v1/settings/blocklist        →  User's domain blocklist
POST  /api/v1/settings/blocklist        →  Add domain to blocklist
DELETE /api/v1/settings/blocklist/{id}  →  Remove domain
```

---

### Example Response — Search Results

```json
{
  "query": "sparse attention transformers",
  "results": [
    {
      "memory_id": "3f2a1c...",
      "chunk_id": "8e4b9d...",
      "score": 0.91,
      "similarity": 0.88,
      "recency_score": 0.95,
      "title": "Longformer: The Long-Document Transformer",
      "url": "https://arxiv.org/abs/2004.05150",
      "source_type": "web",
      "snippet": "...uses a combination of windowed local-context self-attention and task motivated global attention that scales linearly with the sequence length...",
      "domain": "arxiv.org",
      "captured_at": "2025-03-15T14:22:00Z"
    }
  ],
  "total": 10,
  "latency_ms": 187
}
```

---

## 10. Capture Layer — Browser Extension & File Watcher

### Browser Extension Architecture

The extension uses three scripts communicating via Chrome message passing:

```
content_script.js  →  injected into every page
    - Tracks time-on-tab with a 10-second threshold
    - Runs Readability.js to extract clean article text
    - Sends message to background.js: { type: "CAPTURE", url, title, text }

background.js  →  service worker
    - Receives CAPTURE messages
    - Checks dedup cache (chrome.storage.local — last 24h URLs)
    - If not duplicate: POST /api/v1/ingest with JWT from storage
    - Updates badge count on success

popup.html/popup.js  →  extension popup
    - Shows capture status, memory count
    - Toggle global pause / per-site pause
    - Opens full dashboard in new tab
```

### Extension — Content Script (core logic)

```javascript
// content_script.js

import { Readability } from '@mozilla/readability';

let dwellTimer = null;
const DWELL_THRESHOLD_MS = 10000;

function captureCurrentPage() {
  const documentClone = document.cloneNode(true);
  const article = new Readability(documentClone).parse();

  if (!article || article.textContent.trim().length < 200) return;

  chrome.runtime.sendMessage({
    type: 'CAPTURE',
    url: window.location.href,
    title: article.title || document.title,
    text: article.textContent.trim().slice(0, 50000),  // max 50k chars
    source_type: 'web'
  });
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    dwellTimer = setTimeout(captureCurrentPage, DWELL_THRESHOLD_MS);
  } else {
    clearTimeout(dwellTimer);
  }
});
```

---

### File Watcher Daemon

```python
# daemon/watcher.py

import hashlib
import yaml
import pdfplumber
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import httpx
import asyncio

SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.md',
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.rb'
}

class EchoMemoryHandler(FileSystemEventHandler):
    def __init__(self, config: dict, token: str):
        self.api_url = config['api_url']
        self.token = token
        self.seen_hashes: set[str] = set()

    def on_opened(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        asyncio.run(self._ingest_file(path))

    async def _ingest_file(self, path: Path):
        raw = path.read_bytes()
        file_hash = hashlib.sha256(raw).hexdigest()

        if file_hash in self.seen_hashes:
            return
        self.seen_hashes.add(file_hash)

        text = self._extract_text(path, raw)
        if not text or len(text.strip()) < 100:
            return

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.api_url}/api/v1/ingest",
                json={
                    "source_type": "code" if path.suffix in {'.py','.js','.ts','.go','.rs'} else "pdf" if path.suffix == '.pdf' else "text",
                    "title": path.name,
                    "file_path": str(path),
                    "file_hash": file_hash,
                    "raw_text": text[:50000]
                },
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10.0
            )

    def _extract_text(self, path: Path, raw: bytes) -> str:
        if path.suffix == '.pdf':
            with pdfplumber.open(path) as pdf:
                return '\n'.join(
                    page.extract_text() or '' for page in pdf.pages
                )
        return raw.decode('utf-8', errors='ignore')
```

---

## 11. Ingestion & Embedding Pipeline

### Ingest Endpoint

```python
# app/api/ingest.py

from google.cloud import storage, tasks_v2
import json

async def ingest_capture(payload: IngestRequest, user: User, db: AsyncSession):
    # 1. Deduplication check
    existing = await db.scalar(
        select(Memory).where(
            Memory.user_id == user.id,
            Memory.url == payload.url if payload.url else Memory.file_hash == payload.file_hash
        )
    )
    if existing:
        return {"memory_id": str(existing.id), "status": "duplicate"}

    # 2. Store raw text in Cloud Storage
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(settings.GCS_BUCKET)
    blob_path = f"users/{user.id}/memories/{uuid4()}.txt"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(payload.raw_text, content_type="text/plain")

    # 3. Create memory row
    memory = Memory(
        user_id=user.id,
        source_type=payload.source_type,
        title=payload.title,
        url=payload.url,
        file_path=payload.file_path,
        file_hash=payload.file_hash,
        gcs_blob_path=blob_path,
        domain=extract_domain(payload.url) if payload.url else None,
        status="pending"
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)

    # 4. Enqueue embedding job in Cloud Tasks
    tasks_client = tasks_v2.CloudTasksClient()
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{settings.WORKER_URL}/internal/embed",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"memory_id": str(memory.id)}).encode()
        }
    }
    tasks_client.create_task(
        parent=settings.CLOUD_TASKS_QUEUE_PATH,
        task=task
    )

    return {"memory_id": str(memory.id), "status": "queued"}
```

---

### Embedding Worker

```python
# app/workers/embedder.py

from vertexai.language_models import TextEmbeddingModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google.cloud import storage

model = TextEmbeddingModel.from_pretrained("text-embedding-004")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    length_function=len
)

async def embed_memory(memory_id: str, db: AsyncSession):
    memory = await db.get(Memory, memory_id)
    if not memory:
        return

    # Fetch raw text from Cloud Storage
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(settings.GCS_BUCKET)
    raw_text = bucket.blob(memory.gcs_blob_path).download_as_text()

    # Chunk the text
    chunks = splitter.split_text(raw_text)
    memory.chunk_count = len(chunks)

    # Batch embed — Vertex AI allows up to 250 texts per request
    batch_size = 250
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        embeddings = model.get_embeddings(batch)

        for i, (chunk_text, embedding_obj) in enumerate(zip(batch, embeddings)):
            chunk = MemoryChunk(
                memory_id=memory.id,
                user_id=memory.user_id,
                chunk_index=batch_start + i,
                chunk_text=chunk_text,
                token_count=len(chunk_text.split()),
                embedding=embedding_obj.values   # list[float] of len 768
            )
            db.add(chunk)

    memory.status = "indexed"
    memory.indexed_at = datetime.utcnow()
    await db.commit()
```

---

## 12. Semantic Search Engine

### Recency-Weighted Vector Search

```python
# app/services/search.py

from vertexai.language_models import TextEmbeddingModel
from datetime import datetime, timedelta
import math

model = TextEmbeddingModel.from_pretrained("text-embedding-004")

async def semantic_search(
    query: str,
    user_id: str,
    db: AsyncSession,
    source_type: str | None = None,
    since: datetime | None = None,
    limit: int = 10
) -> list[SearchResult]:

    # 1. Embed the query
    query_embedding = model.get_embeddings([query])[0].values

    # 2. Build base ANN query — retrieve top 40 candidates
    filters = [MemoryChunk.user_id == user_id]
    if source_type:
        filters.append(Memory.source_type == source_type)
    if since:
        filters.append(Memory.captured_at >= since)

    rows = await db.execute(
        select(
            MemoryChunk,
            Memory,
            (1 - MemoryChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        )
        .join(Memory, MemoryChunk.memory_id == Memory.id)
        .where(*filters)
        .order_by(MemoryChunk.embedding.cosine_distance(query_embedding))
        .limit(40)
    )
    candidates = rows.all()

    # 3. Re-rank with recency decay
    now = datetime.utcnow()
    results = []
    for chunk, memory, similarity in candidates:
        age_days = (now - memory.captured_at).days
        # Exponential decay: half-life of 30 days
        recency_score = math.exp(-0.693 * age_days / 30)
        final_score = 0.70 * similarity + 0.30 * recency_score

        results.append(SearchResult(
            memory_id=memory.id,
            chunk_id=chunk.id,
            score=round(final_score, 4),
            similarity=round(similarity, 4),
            recency_score=round(recency_score, 4),
            title=memory.title,
            url=memory.url,
            file_path=memory.file_path,
            source_type=memory.source_type,
            snippet=chunk.chunk_text[:400],
            domain=memory.domain,
            captured_at=memory.captured_at
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
```

---

### Topic Clustering (Dashboard)

```python
# app/services/clustering.py

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

async def get_topic_clusters(user_id: str, db: AsyncSession, k: int = 6):
    # Fetch one embedding per memory (the first chunk is representative)
    rows = await db.execute(
        select(MemoryChunk.embedding, Memory.title, Memory.id)
        .join(Memory)
        .where(MemoryChunk.user_id == user_id, MemoryChunk.chunk_index == 0)
        .limit(500)
    )
    data = rows.all()

    if len(data) < k:
        return []

    embeddings = np.array([r.embedding for r in data])
    embeddings = normalize(embeddings)

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    clusters = {}
    for i, (_, title, mem_id) in enumerate(data):
        label = int(labels[i])
        clusters.setdefault(label, []).append({"title": title, "memory_id": str(mem_id)})

    return [{"cluster_id": k, "memories": v[:5]} for k, v in clusters.items()]
```

---

## 13. GCP Infrastructure (Cost-Optimised)

### Services Used

| Service | Purpose | Estimated Monthly Cost |
|---------|---------|----------------------|
| Cloud Run (API) | FastAPI backend | ~$0–3 |
| Cloud Run (Worker) | Embedding worker | ~$0–2 |
| Cloud Tasks | Async embedding job queue | ~$0 (free tier: 1M ops/month) |
| Vertex AI (text-embedding-004) | Embeddings generation | ~$0–2 (free tier: 250 calls/day) |
| Cloud Storage | Raw content blobs | ~$0.02 (per GB) |
| Artifact Registry | Docker image storage | ~$0.10 |
| Cloud Build | CI/CD pipeline | ~$0 (free tier) |
| Secret Manager | Credentials & keys | ~$0.40 |
| Cloud Logging | Application logs | ~$0 |
| Neon.tech | PostgreSQL + pgvector | $0 (free tier) |
| **Total** | | **~$0.50–8/month** |

---

### Dockerfile (Backend)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

### Cloud Run Deployment

```bash
# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/echomemory-api

# Deploy API — scale to zero
gcloud run deploy echomemory-api \
  --image gcr.io/$PROJECT_ID/echomemory-api \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 5 \
  --memory 1Gi \
  --cpu 1 \
  --set-secrets DATABASE_URL=echomemory-db-url:latest \
  --set-secrets GOOGLE_CLIENT_ID=google-client-id:latest \
  --set-secrets GOOGLE_CLIENT_SECRET=google-client-secret:latest \
  --set-secrets JWT_SECRET=jwt-secret:latest \
  --set-secrets GCS_BUCKET=gcs-bucket-name:latest

# Deploy Embedding Worker
gcloud run deploy echomemory-worker \
  --image gcr.io/$PROJECT_ID/echomemory-worker \
  --platform managed \
  --region asia-south1 \
  --no-allow-unauthenticated \
  --min-instances 0 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1
```

---

### Cloud Tasks Queue Setup

```bash
# Create the embedding queue
gcloud tasks queues create embedding-jobs \
  --location=asia-south1 \
  --max-attempts=3 \
  --min-backoff=5s \
  --max-backoff=60s \
  --max-doublings=3
```

---

### Cloud Storage Bucket Setup

```bash
# Create private bucket for raw content blobs
gsutil mb -l asia-south1 gs://echomemory-raw-$PROJECT_ID

# No public access
gsutil uniformbucketlevelaccess set on gs://echomemory-raw-$PROJECT_ID

# Lifecycle policy: delete raw blobs after 90 days to save cost
gsutil lifecycle set lifecycle.json gs://echomemory-raw-$PROJECT_ID
```

---

### Cloud Build CI/CD (`cloudbuild.yaml`)

```yaml
steps:
  - name: 'python:3.12'
    entrypoint: bash
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        pytest tests/ -v --tb=short

  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/echomemory-api', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/echomemory-api']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'echomemory-api'
      - '--image=gcr.io/$PROJECT_ID/echomemory-api'
      - '--region=asia-south1'
      - '--platform=managed'

images:
  - 'gcr.io/$PROJECT_ID/echomemory-api'
```

---

### Secret Manager Setup

```bash
echo -n "postgresql+asyncpg://..." | gcloud secrets create echomemory-db-url --data-file=-
echo -n "your-jwt-secret-256bit"   | gcloud secrets create jwt-secret --data-file=-
echo -n "your-google-client-id"    | gcloud secrets create google-client-id --data-file=-
echo -n "your-google-client-secret"| gcloud secrets create google-client-secret --data-file=-
echo -n "echomemory-raw-$PROJECT"  | gcloud secrets create gcs-bucket-name --data-file=-

gcloud secrets add-iam-policy-binding echomemory-db-url \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 14. Security & Privacy

| Concern | Mitigation |
|---------|-----------|
| All data is user-private | Every DB query is scoped to `user_id` extracted from JWT — no cross-user data leakage possible |
| JWT security | Signed with 256-bit secret, 7-day expiry, server-side invalidation on logout |
| Extension auth | JWT stored in `chrome.storage.local` (not `localStorage`) — inaccessible to page scripts |
| Raw content in GCS | Bucket is private; Cloud Run service account has read-only access; no public URLs |
| SQL injection | SQLAlchemy ORM with parameterised queries throughout — no raw string interpolation |
| Sensitive site capture | Domain blocklist prevents capture of banking, email, password manager domains by default |
| Embedding API calls | Vertex AI calls are server-side only — raw text never leaves your GCP project |
| CORS | FastAPI CORS middleware restricted to registered extension origin + frontend origin |
| Data deletion | Hard delete cascade on `memories` removes chunks + GCS blob — nothing retained |
| Secrets | All credentials in Secret Manager; never in Dockerfiles, env files, or source code |

### Default Blocked Domains (seeded on account creation)

```python
DEFAULT_BLOCKED_DOMAINS = [
    "mail.google.com", "outlook.live.com", "outlook.office.com",
    "accounts.google.com", "login.microsoftonline.com",
    "bankofamerica.com", "chase.com", "paypal.com",
    "1password.com", "lastpass.com", "bitwarden.com",
]
```

---

## 15. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Search API response time (p95) | < 500ms (includes Vertex AI embedding of query) |
| Ingestion endpoint response time | < 200ms (async — just queues the job) |
| Embedding worker throughput | 100 memories/minute at peak |
| Cold start (Cloud Run) | < 4s |
| pgvector HNSW search (1M chunks) | < 50ms |
| Uptime | > 99% (Cloud Run SLA) |
| Database connection pool | 5–10 connections (asyncpg) |
| Test coverage | > 75% on ingestion pipeline and search engine |
| Extension bundle size | < 500KB (fast install) |
| Mobile responsiveness | All pages responsive at 375px+ |

---

## 16. Milestones & MVP Scope

### Week 1 — Foundation
- [ ] FastAPI project scaffold (routers, models, DB connection)
- [ ] Neon.tech PostgreSQL + pgvector setup + Alembic migrations
- [ ] Google OAuth login + JWT session
- [ ] User model + profile endpoint
- [ ] Cloud Storage bucket setup
- [ ] Dockerfile + Cloud Run first deploy

### Week 2 — Ingestion Pipeline
- [ ] `/api/v1/ingest` endpoint (receive + GCS upload + DB row)
- [ ] Cloud Tasks queue setup + embedding worker (Cloud Run)
- [ ] Vertex AI text-embedding-004 integration
- [ ] Text chunking with RecursiveCharacterTextSplitter
- [ ] pgvector HNSW index + MemoryChunk model
- [ ] End-to-end test: POST ingest → chunks embedded → chunks queryable

### Week 3 — Capture Layer + Search
- [ ] Chrome extension (content script + background + popup)
- [ ] Readability.js integration + 10s dwell gate
- [ ] Extension → backend ingest flow working end-to-end
- [ ] File watcher daemon (watchdog + pdfplumber)
- [ ] `/api/v1/search` semantic search endpoint
- [ ] Recency-weighted re-ranking

### Week 4 — Frontend + Polish
- [ ] Next.js app: search page (cmdk palette)
- [ ] Memory timeline dashboard
- [ ] Stats page (heatmap, domain breakdown)
- [ ] Domain blocklist settings UI
- [ ] Cloud Build CI/CD pipeline
- [ ] Secret Manager integration
- [ ] README + demo video
- [ ] Submission

---

## 17. Out of Scope (v1)

The following are explicitly deferred to post-submission:

- Firefox extension support
- macOS / Windows native packaging for the daemon
- Re-indexing memories when model is updated (embedding drift)
- Vertex AI Vector Search (Matching Engine) — pgvector is sufficient for v1
- Full-text search fallback (BM25 hybrid retrieval)
- Sharing memories with other users
- Mobile app
- Browser history import (retroactive indexing)
- Email / Slack / Notion connector integrations
- LLM-generated memory summaries
- Offline mode / local-only deployment

---

*Document maintained by the EchoMemory core team. Last updated: April 2026.*
