import hashlib
import yaml
import sys
import httpx
import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.md',
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.rb',
}

CONFIG_PATH = Path.home() / ".echomemory" / "config.yaml"

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


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
        try:
            raw = path.read_bytes()
        except Exception:
            return

        file_hash = hashlib.sha256(raw).hexdigest()
        if file_hash in self.seen_hashes:
            return
        self.seen_hashes.add(file_hash)

        text = self._extract_text(path, raw)
        if not text or len(text.strip()) < 100:
            return

        source_type = "code" if path.suffix.lower() in {
            '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.rb'
        } else "pdf" if path.suffix.lower() == '.pdf' else "text"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/ingest",
                    json={
                        "source_type": source_type,
                        "title": path.name,
                        "file_path": str(path),
                        "file_hash": file_hash,
                        "raw_text": text[:50000],
                    },
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=15.0,
                )
                if response.status_code == 200:
                    print(f"[EchoMemory] Indexed: {path.name}")
                elif response.status_code == 401:
                    print("[EchoMemory] Not authenticated. Run 'echomemory auth' first.")
                else:
                    print(f"[EchoMemory] Error {response.status_code}: {response.text}")
        except httpx.ConnectError:
            print(f"[EchoMemory] Cannot connect to {self.api_url}. Is the server running?")

    def _extract_text(self, path: Path, raw: bytes) -> str:
        if path.suffix.lower() == '.pdf':
            if not PDF_AVAILABLE:
                return ""
            try:
                with pdfplumber.open(path) as pdf:
                    return '\n'.join(
                        page.extract_text() or '' for page in pdf.pages
                    )
            except Exception:
                return ""
        try:
            return raw.decode('utf-8', errors='ignore')
        except Exception:
            return ""


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Config not found at {CONFIG_PATH}. Run 'echomemory init' first.")
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    token_path = Path.home() / ".echomemory" / "token"
    if not token_path.exists():
        raise SystemExit("Not authenticated. Run 'echomemory auth' first.")
    token = token_path.read_text().strip()

    handler = EchoMemoryHandler(config, token)
    observer = Observer()
    for directory in config.get('watch_directories', []):
        observer.schedule(handler, directory, recursive=False)
        print(f"[EchoMemory] Watching: {directory}")

    observer.start()
    print("[EchoMemory] Daemon started. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
