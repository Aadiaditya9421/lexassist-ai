"""
tests/test_nodes.py — Unit tests for graph/nodes.py
Run:  venv/Scripts/python.exe -m pytest tests/test_nodes.py -v
"""

import pytest
import sqlite3
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from config import config
from graph.nodes import (
    memory_node, router_node, rewrite_node, tool_node,
    answer_node, fallback_node, eval_node, grader_node, save_node,
)


# ── Router Node ──────────────────────────────────────────────────────────────

def test_router_returns_rag():
    """A query about constitutional bail procedure is unambiguously RAG territory."""
    state = {"query": "What is the procedure for bail under CrPC?"}
    result = router_node(state)
    assert result["route"] == "rag"

def test_router_returns_tool():
    state = {"query": "What is the current date and time?"}
    result = router_node(state)
    assert result["route"] == "tool"

def test_router_returns_chitchat():
    state = {"query": "Hello, good morning!"}
    result = router_node(state)
    assert result["route"] == "chitchat"


# ── Memory Node (BUG-01 / BUG-02 fix verification) ──────────────────────────

def test_memory_node_resets_transient_state():
    """After a tool query, transient fields like tool_result must be zeroed
    on the next invocation to prevent state leakage (BUG-01)."""
    leaked_state = {
        "query": "New question about bail",
        "tool_result": "IPC Section 302: old leftover value",
        "should_fallback": True,
        "route": "tool",
        "confidence": 0.9,
    }
    result = memory_node(leaked_state)
    assert result["tool_result"] is None
    assert result["should_fallback"] is False
    assert result["route"] == ""
    assert result["confidence"] == 0.0

def test_memory_node_appends_human_message():
    """memory_node must append a HumanMessage for multi-turn context (BUG-02)."""
    state = {"query": "What is IPC 302?"}
    result = memory_node(state)
    assert "chat_history" in result
    assert len(result["chat_history"]) == 1
    assert isinstance(result["chat_history"][0], HumanMessage)
    assert result["chat_history"][0].content == "What is IPC 302?"


# ── Tool Node ────────────────────────────────────────────────────────────────

def test_tool_node_returns_date():
    state = {"query": "What is the current date and time?"}
    result = tool_node(state)
    assert result["tool_result"] is not None
    assert "current date and time" in result["answer"].lower()

def test_tool_node_returns_ipc_302():
    state = {"query": "What is IPC 302?"}
    result = tool_node(state)
    assert "302" in result["answer"]
    assert "murder" in result["answer"].lower()

def test_tool_node_returns_none_for_unknown():
    """Queries outside the tool's hardcoded scope return None,
    causing the graph to reroute to RAG."""
    state = {"query": "What is the RTI Act filing process?"}
    result = tool_node(state)
    assert result["tool_result"] is None


# ── Answer Node ──────────────────────────────────────────────────────────────

def test_answer_node_chitchat():
    state = {"query": "Hi!", "route": "chitchat"}
    result = answer_node(state)
    assert "LexAssist AI" in result["answer"]

def test_answer_node_skips_when_tool_result_present():
    state = {"query": "test", "route": "tool", "tool_result": "Some tool answer"}
    result = answer_node(state)
    assert result == {}


# ── Fallback Node ────────────────────────────────────────────────────────────

def test_fallback_returns_correct_message():
    state = {"query": "Tell me about cars."}
    result = fallback_node(state)
    assert "Consult a qualified lawyer." in result["answer"]
    assert "I don't have sufficient information" in result["answer"]


# ── Eval Node ────────────────────────────────────────────────────────────────

def test_eval_skips_for_non_rag():
    """Eval node should skip LLM call for non-rag routes."""
    state = {"route": "tool", "should_fallback": False}
    result = eval_node(state)
    assert result["confidence"] == 1.0
    assert result["should_fallback"] is False

def test_eval_preserves_existing_fallback():
    """If should_fallback is already True (from grader), eval must not reset it."""
    state = {"route": "rag", "should_fallback": True}
    result = eval_node(state)
    assert result["should_fallback"] is True


# ── Grader Node ──────────────────────────────────────────────────────────────

def test_grader_filters_irrelevant_doc():
    docs = [Document(page_content="The weather today is sunny with clouds.",
                     metadata={"source": "Weather API"})]
    state = {"query": "What is the punishment for cheating under IPC?",
             "documents": docs}
    result = grader_node(state)
    assert len(result["relevant_docs"]) == 0
    assert result["should_fallback"] is True


# ── Save Node ────────────────────────────────────────────────────────────────

def test_save_node_writes_to_db():
    state = {
        "thread_id": "test_thread",
        "query": "test query",
        "answer": "test answer",
        "confidence": 0.9,
        "sources": [{"title": "Test Source", "source": "test.txt"}],
        "route": "rag",
    }
    save_node(state)

    conn = sqlite3.connect(config.sqlite_path)
    c = conn.cursor()
    c.execute("SELECT query FROM chat_log WHERE thread_id=?", ("test_thread",))
    row = c.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "test query"

def test_save_node_appends_ai_message():
    """save_node must append an AIMessage for multi-turn context (BUG-02)."""
    state = {"query": "q", "answer": "Final legal answer"}
    result = save_node(state)
    assert "chat_history" in result
    assert len(result["chat_history"]) == 1
    assert result["chat_history"][0].content == "Final legal answer"
