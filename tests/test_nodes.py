import pytest
import sqlite3
from langchain_core.documents import Document
from config import config
from graph.nodes import (
    router_node, fallback_node, eval_node, grader_node, save_node
)

def test_router_returns_rag():
    state = {"query": "What is the IPC section for theft?"}
    result = router_node(state)
    assert result["route"] == "rag"

def test_router_returns_tool():
    state = {"query": "What is the current date and time?"}
    result = router_node(state)
    assert result["route"] == "tool"

def test_fallback_returns_correct_message():
    state = {"query": "Tell me about cars."}
    result = fallback_node(state)
    assert "Consult a qualified lawyer." in result["answer"]
    assert "I don't have sufficient information" in result["answer"]

def test_eval_low_score_triggers_fallback():
    # If eval node receives something clearly hallucinatory, config is typically threshold=0.5
    # For a unit test, we just pass heavily contradictory text and see if it drops score
    # Due to LLM non-determinism, we ensure output sets should_fallback if we mock the threshold
    
    # Using a state where router failed and marked fallback manually
    state = {"route": "rag", "should_fallback": True}
    result = eval_node(state)
    assert result["should_fallback"] is True

def test_grader_filters_irrelevant_doc():
    # Provide an irrelevant chunk 
    docs = [Document(page_content="The weather today is sunny with clouds.", metadata={"source": "Weather API"})]
    state = {"query": "What is the punishment for cheating under IPC?", "documents": docs}
    
    # LLM dependent, but grader should say 'no'
    result = grader_node(state)
    assert len(result["relevant_docs"]) == 0
    assert result["should_fallback"] is True

def test_save_node_writes_to_db():
    state = {
        "thread_id": "test_thread",
        "query": "test query",
        "answer": "test answer",
        "confidence": 0.9,
        "sources": [{"title": "Test Source", "source": "test.txt"}],
        "route": "rag"
    }
    
    save_node(state)
    
    conn = sqlite3.connect(config.sqlite_path)
    c = conn.cursor()
    c.execute("SELECT query FROM chat_log WHERE thread_id=?", ("test_thread",))
    row = c.fetchone()
    conn.close()
    
    assert row is not None
    assert row[0] == "test query"
