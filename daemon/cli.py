import yaml
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".echomemory" / "config.yaml"

SUPPORTED_EXTENSIONS = {
    '.pdf', '.txt', '.md',
    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.rb',
}


def init_config():
    config_dir = Path.home() / ".echomemory"
    config_dir.mkdir(exist_ok=True)

    print("EchoMemory Daemon Configuration")
    print("=" * 40)

    api_url = input("API URL (e.g., http://localhost:8000): ").strip()
    if not api_url:
        api_url = "http://localhost:8000"

    default_dirs = [
        str(Path.home() / "Documents"),
        str(Path.home() / "Downloads"),
    ]
    print(f"\nWatch directories (comma-separated, empty for defaults):")
    print(f"  Default: {', '.join(default_dirs)}")
    dirs_input = input("  > ").strip()
    watch_dirs = (
        [d.strip() for d in dirs_input.split(",") if d.strip()]
        if dirs_input
        else default_dirs
    )

    config = {
        "api_url": api_url,
        "watch_directories": [str(Path(d).expanduser()) for d in watch_dirs],
    }

    CONFIG_PATH.write_text(yaml.dump(config))
    print(f"\nConfig saved to {CONFIG_PATH}")

    token_path = config_dir / "token"
    if not token_path.exists():
        print("\nNo auth token found. After logging in via the web app,")
        print("run: echomemory auth <token>")


def save_token(token: str):
    config_dir = Path.home() / ".echomemory"
    config_dir.mkdir(exist_ok=True)
    token_path = config_dir / "token"
    token_path.write_text(token.strip())
    print(f"Token saved to {token_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m daemon.cli init|auth <token>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        init_config()
    elif cmd == "auth":
        if len(sys.argv) < 3:
            print("Usage: python -m daemon.cli auth <token>")
            sys.exit(1)
        save_token(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
