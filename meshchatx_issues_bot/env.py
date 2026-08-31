from pathlib import Path

from dotenv import load_dotenv


def load_env_file() -> Path | None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)
            return path
    if load_dotenv(override=False):
        return Path.cwd() / ".env"
    return None
