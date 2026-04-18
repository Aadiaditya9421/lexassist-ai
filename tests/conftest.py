"""
conftest.py — Shared pytest fixtures.
Add reusable fixtures here as the test suite grows.
"""

import pytest
from config import Config


@pytest.fixture
def test_config():
    """A config instance safe for testing (no real API key required)."""
    cfg = Config()
    cfg.openai_api_key = "sk-test-placeholder"
    cfg.faithfulness_threshold = 0.50
    return cfg


@pytest.fixture
def sample_state():
    """A minimal valid AgentState for unit tests."""
    return {
        "query": "What is IPC Section 302?",
        "rewritten_query": "",
        "thread_id": "test-thread-001",
        "route": "",
        "documents": [],
        "relevant_docs": [],
        "context": "",
        "tool_result": None,
        "answer": "",
        "sources": [],
        "confidence": 0.0,
        "chat_history": [],
        "should_fallback": False,
    }
