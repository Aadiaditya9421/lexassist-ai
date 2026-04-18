"""
config.py — Centralised configuration for LexAssist AI.
All tuneable constants live here. Import Config() everywhere else.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.0          # deterministic — legal answers must be consistent
    max_tokens: int = 1024

    # ── Embeddings ────────────────────────────────────────────────────────────
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_store"
    collection_name: str = "legal_docs"
    retrieval_k: int = 6              # final docs returned to LLM
    mmr_fetch_k: int = 12             # candidates before MMR re-ranking
    mmr_lambda: float = 0.6           # 0=max diversity, 1=max relevance

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 120

    # ── Evaluation ────────────────────────────────────────────────────────────
    faithfulness_threshold: float = 0.50   # below this → trigger fallback node

    # ── Memory ────────────────────────────────────────────────────────────────
    sqlite_path: str = "./chat_history.db"
    history_summary_threshold: int = 20   # summarise after N messages

    # ── API key (loaded from .env) ────────────────────────────────────────────
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    def validate(self) -> None:
        """Raise early with a clear message if config is invalid."""
        if not self.openai_api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example → .env and add your key."
            )
        if not (0.0 <= self.faithfulness_threshold <= 1.0):
            raise ValueError("faithfulness_threshold must be between 0.0 and 1.0")
        if self.retrieval_k > self.mmr_fetch_k:
            raise ValueError("retrieval_k must be ≤ mmr_fetch_k")


config = Config()
