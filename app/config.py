"""Configuração central (variáveis de ambiente)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


def _load_env_file():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()


def gemini_key() -> str | None:
    # lido sempre (do .env carregado ou do ambiente do deploy)
    return os.getenv("GEMINI_API_KEY")


MAX_TEXT_CHARS = 4000
MAX_CHAT_CHARS = 2000


def max_image_bytes() -> int:
    """Tamanho máximo da imagem do diagnóstico (decodificada). Padrão 5 MB; MAX_IMAGE_MB ajusta."""
    return int(float(os.getenv("MAX_IMAGE_MB", "5")) * 1024 * 1024)


def database_url() -> str:
    """DATABASE_URL (Postgres/Neon em produção). Sem ela: SQLite local.

    Na Vercel o disco é somente leitura (exceto /tmp), então o SQLite cai em /tmp
    (efêmero, serve só como fallback de demo).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/bip.db"
    (BASE_DIR / "data").mkdir(exist_ok=True)
    return f"sqlite:///{(BASE_DIR / 'data' / 'bip.db').as_posix()}"
