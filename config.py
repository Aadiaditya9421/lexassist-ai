"""
config.py — Centralised configuration for LexAssist AI.

Every tuneable constant lives here. All other modules import the
module-level `config` singleton — never hardcode values elsewhere.

Usage:
    from config import config

    model = config.llm_model
    config.validate()          # call once at app startup
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (no-op in production where env vars are set directly)
load_dotenv()

# Project root — used to resolve all relative paths consistently regardless
# of which directory the user runs the app from.
_ROOT = Path(__file__).parent.resolve()


@dataclass
class Config:
    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_model: str = "gpt-4o-mini"
    # temperature=0.0 -> deterministic outputs, critical for legal accuracy
    temperature: float = 0.0
    max_tokens: int = 1024

    # ── Embeddings ────────────────────────────────────────────────────────────
    # all-MiniLM-L6-v2: 384-dim, fast, runs CPU-only, good legal domain perf
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chroma_persist_dir: str = str(_ROOT / "chroma_store")
    collection_name: str = "legal_docs"
    retrieval_k: int = 6        # final docs passed to LLM context
    mmr_fetch_k: int = 12       # candidate pool before MMR re-ranking
    mmr_lambda: float = 0.6     # 0.0 = max diversity, 1.0 = max relevance

    # ── Text chunking ─────────────────────────────────────────────────────────
    chunk_size: int = 800       # tokens per chunk (fits well in 4k context)
    chunk_overlap: int = 120    # overlap prevents cutting mid-provision

    # ── Knowledge base ────────────────────────────────────────────────────────
    docs_dir: str = str(_ROOT / "knowledge_base" / "docs")

    # ── Evaluation ────────────────────────────────────────────────────────────
    # Answers scoring below this trigger the fallback "I don't know" node
    faithfulness_threshold: float = 0.50

    # ── Memory & persistence ─────────────────────────────────────────────────
    sqlite_path: str = str(_ROOT / "chat_history.db")
    # Summarise chat history after this many messages to keep context tight
    history_summary_threshold: int = 20

    # ── API key ───────────────────────────────────────────────────────────────
    # Loaded from OPENAI_API_KEY env var (set in .env locally, Secrets on Cloud)
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # ── App metadata ──────────────────────────────────────────────────────────
    app_name: str = "LexAssist AI"
    app_version: str = "1.0.0"
    app_description: str = "Indian legal information assistant — grounded, cited, hallucination-free."

    def __post_init__(self) -> None:
        """Coerce types and normalise paths right after construction."""
        self.temperature = float(self.temperature)
        self.faithfulness_threshold = float(self.faithfulness_threshold)
        self.retrieval_k = int(self.retrieval_k)
        self.mmr_fetch_k = int(self.mmr_fetch_k)
        self.chunk_size = int(self.chunk_size)
        self.chunk_overlap = int(self.chunk_overlap)

    def validate(self) -> None:
        """
        Validate all settings and raise with a clear message on any issue.
        Call once at app startup (top of app.py and graph.py).
        Skip in pytest by not calling it — test fixtures set a placeholder key.
        """
        errors: list[str] = []

        if not self.openai_api_key:
            errors.append(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example -> .env and paste your key."
            )

        if not (0.0 <= self.faithfulness_threshold <= 1.0):
            errors.append(
                f"faithfulness_threshold must be 0.0-1.0, "
                f"got {self.faithfulness_threshold}"
            )

        if self.retrieval_k > self.mmr_fetch_k:
            errors.append(
                f"retrieval_k ({self.retrieval_k}) must be <= "
                f"mmr_fetch_k ({self.mmr_fetch_k})"
            )

        if self.chunk_overlap >= self.chunk_size:
            errors.append(
                f"chunk_overlap ({self.chunk_overlap}) must be < "
                f"chunk_size ({self.chunk_size})"
            )

        if not Path(self.docs_dir).exists():
            errors.append(
                f"docs_dir not found: {self.docs_dir}. "
                f"Create knowledge_base/docs/ and add your .txt files."
            )

        if errors:
            bullet_list = "\n  * ".join(errors)
            raise EnvironmentError(
                f"LexAssist config validation failed:\n  * {bullet_list}"
            )

    def as_dict(self) -> dict:
        """Return config as a plain dict (useful for logging and Streamlit debug panels)."""
        return {
            "llm_model": self.llm_model,
            "temperature": self.temperature,
            "embed_model": self.embed_model,
            "chroma_persist_dir": self.chroma_persist_dir,
            "collection_name": self.collection_name,
            "retrieval_k": self.retrieval_k,
            "mmr_fetch_k": self.mmr_fetch_k,
            "mmr_lambda": self.mmr_lambda,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "faithfulness_threshold": self.faithfulness_threshold,
            "sqlite_path": self.sqlite_path,
            "history_summary_threshold": self.history_summary_threshold,
            "app_version": self.app_version,
            "openai_api_key_set": bool(self.openai_api_key),  # never log the key itself
        }

    def __repr__(self) -> str:
        return (
            f"Config(model={self.llm_model!r}, "
            f"embed={self.embed_model!r}, "
            f"k={self.retrieval_k}, "
            f"threshold={self.faithfulness_threshold}, "
            f"api_key_set={bool(self.openai_api_key)})"
        )


# ── Module-level singleton ────────────────────────────────────────────────────
# Import this everywhere: `from config import config`
config = Config()
