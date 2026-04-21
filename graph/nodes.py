import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from config import config
from graph.state import AgentState

log = logging.getLogger("nodes")

# Lazy-load vectorstore and LLM to avoid import-time side effects
_vectorstore = None
_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        if config.llm_provider == "groq":
            from langchain_groq import ChatGroq
            _llm = ChatGroq(
                model=config.llm_model,
                temperature=config.temperature,
                groq_api_key=config.groq_api_key,
            )
        else:
            from langchain_openai import ChatOpenAI
            _llm = ChatOpenAI(
                model=config.llm_model,
                temperature=config.temperature,
            )
    return _llm

def _get_vs():
    global _vectorstore
    if _vectorstore is None:
        from knowledge_base.ingest import get_vectorstore
        _vectorstore = get_vectorstore()
    return _vectorstore

def memory_node(state: AgentState) -> dict:
    """Reset transient state and append the current query to chat history.

    Why the reset?  LangGraph's MemorySaver persists the FULL AgentState
    between invocations on the same thread_id.  Without explicitly zeroing
    transient fields here, values like tool_result and should_fallback
    leak from a previous query and corrupt the current one (BUG-01).

    chat_history uses an operator.add reducer, so returning a list APPENDS
    to the existing history — we cannot truncate via return value.
    Truncation is handled at read-time in answer_node instead.
    """
    return {
        # ── Append current query to conversation memory ──────────────
        "chat_history": [HumanMessage(content=state["query"])],
        # ── Reset ALL transient fields to prevent cross-invocation leak ─
        "route": "",
        "rewritten_query": "",
        "documents": [],
        "relevant_docs": [],
        "context": "",
        "sources": [],
        "tool_result": None,
        "answer": "",
        "confidence": 0.0,
        "should_fallback": False,
    }

def router_node(state: AgentState) -> dict:
    """Classify the user's intent into rag, tool, or chitchat."""
    system = """You are a routing agent for Indian Legal Queries. Analyze the user's input:
- If it asks for the current date/time, Limitation Act periods, or a quick lookup for IPC sections 302 (murder), 376 (rape), 420 (cheating), or 498A (cruelty) — including when the user mentions the crime name instead of the section number -> Output: 'tool'
- If it relates to detailed legal analysis, specific sections beyond 302/376/420/498A, constitutional rights, procedures, or acts -> Output: 'rag'
- If it is a generic greeting or conversational nicety -> Output: 'chitchat'
Output ONLY one word: rag, tool, or chitchat."""

    try:
        prompt = ChatPromptTemplate.from_messages([("system", system), ("user", "{query}")])
        chain = prompt | _get_llm()
        result = chain.invoke({"query": state["query"]})
        route = result.content.strip().lower()
        if route not in ["rag", "tool", "chitchat"]:
            route = "rag"
    except Exception as e:
        log.warning(f"Router LLM call failed: {e} — defaulting to 'rag'")
        route = "rag"
    return {"route": route}

def rewrite_node(state: AgentState) -> dict:
    """HyDE rewriting: Generate a hypothetical legal passage to improve retrieval."""
    system = "Write a short, authoritative sounding legal paragraph from an Indian court document that would answer the following query. Do not explain, just write the paragraph."
    try:
        prompt = ChatPromptTemplate.from_messages([("system", system), ("user", "{query}")])
        chain = prompt | _get_llm()
        result = chain.invoke({"query": state["query"]})
        return {"rewritten_query": result.content.strip()}
    except Exception as e:
        log.warning(f"Rewrite LLM call failed: {e} — using original query")
        return {"rewritten_query": state["query"]}

def retrieval_node(state: AgentState) -> dict:
    """Retrieve top contextual documents via MMR."""
    store = _get_vs()
    retriever = store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": config.retrieval_k, 
            "fetch_k": config.mmr_fetch_k, 
            "lambda_mult": config.mmr_lambda
        }
    )
    query_to_use = state.get("rewritten_query", state["query"])
    docs = retriever.invoke(query_to_use)
    return {"documents": docs}

def grader_node(state: AgentState) -> dict:
    """Filter irrelevant retrieved chunks, keeping strictly relevant ones."""
    system = """You are a strict Indian Legal Assessor. You will be given a query and a retrieved legal chunk.
If the chunk contains technical concepts, acts, or sections relevant to answering the query, output 'yes'.
If the chunk is irrelevant, output 'no'.
Do not grade the sentiment, only the legal applicability. Output ONLY 'yes' or 'no'."""
    prompt = ChatPromptTemplate.from_messages([("system", system), ("user", "Query: {query}\n\nChunk: {chunk}")])
    chain = prompt | _get_llm()

    relevant_docs = []
    sources = []

    for doc in state.get("documents", []):
        try:
            result = chain.invoke({"query": state["query"], "chunk": doc.page_content})
            grade = result.content.strip().lower()
        except Exception as e:
            log.warning(f"Grader LLM call failed for chunk: {e} — skipping")
            grade = "no"
        if "yes" in grade:
            relevant_docs.append(doc)
            source_meta = {"source": doc.metadata.get("source", "Unknown"), "title": doc.metadata.get("title", "Unknown Section")}
            if source_meta not in sources:
                sources.append(source_meta)

    should_fallback = len(relevant_docs) == 0
    context = "\n\n".join([d.page_content for d in relevant_docs])

    return {
        "relevant_docs": relevant_docs,
        "context": context,
        "sources": sources,
        "should_fallback": should_fallback
    }

def tool_node(state: AgentState) -> dict:
    """Deterministic mini-tools for direct lookups without LLM extraction."""
    query = state["query"].lower()
    tool_result = None
    
    # Tool 1: Date/Time
    if "current date" in query or "time" in query:
        tool_result = f"The current date and time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
    
    # Tool 2: Limitation Act Quick Table
    elif "limitation act" in query and "period" in query:
        tool_result = (
            "Limitation Periods Overview:\n"
            "1. Suit for money payable for money lent: 3 years\n"
            "2. Suit for possession of immovable property: 12 years\n"
            "3. Execution of a decree: 12 years\n"
            "4. Defamation suit: 1 year"
        )
        
    # Tool 3: IPC Quick Lookup
    elif "302" in query or "murder" in query:
        tool_result = "IPC Section 302: Punishment for murder is death or imprisonment for life, and shall also be liable to fine."
    elif "376" in query or "rape" in query:
        tool_result = "IPC Section 376: Punishment for rape is rigorous imprisonment of not less than 10 years, which may extend to life imprisonment, and shall also be liable to fine."
    elif "420" in query or "cheating" in query:
        tool_result = "IPC Section 420: Cheating and dishonestly inducing delivery of property. Punishable with imprisonment up to 7 years and a fine."
    elif "498a" in query or "cruelty" in query:
        tool_result = "IPC Section 498A: Husband or relative of husband of a woman subjecting her to cruelty. Punishable with imprisonment up to 3 years and a fine."
        
    if tool_result is None:
        return {"tool_result": None} # This forces fallback to RAG in the router wiring
    
    return {"tool_result": tool_result, "answer": tool_result}

def answer_node(state: AgentState) -> dict:
    """Generates the grounded response strictly using the provided context."""
    if state.get("route") == "chitchat":
        return {"answer": "Hello! I am LexAssist AI, an Indian Legal Assistant. How can I help you with Indian law today?"}

    if state.get("tool_result"):
        # Tool node already generated the answer
        return {}

    system = """You are an expert Legal Assistant specializing in Indian Law. 
Your primary directive is to provide comprehensive, well-researched, and highly educational answers using ONLY the provided context.

When explaining a legal concept based on the context:
1. Provide rich, detailed explanations of the provisions. Break down complex legal concepts, just like a senior legal associate would explain them to a client.
2. EXPLICITLY CITE the specific Acts, Sections, or Articles derived from the context. Format your citations prominently in **bold**.
3. Use clear Markdown structuring to make your answer highly readable (e.g., use bullet points, bold text, and subheadings like '### Legal Provision' or '### Explanation' where appropriate).
4. If applicable, explain the specific punishment, conditions, or exceptions clearly.

STRICT GUARDRAILS:
- You must NEVER hallucinate or use outside knowledge. If the context provided does not contain the answer, you must respond EXACTLY with: 'I don't have enough information to answer that based on the legal documents available to me.'
- ALWAYS end your response with: '\n\nConsult a qualified lawyer.'"""

    # Grab last 8 history messages for multi-turn context (truncation at read-time,
    # not at write-time, because operator.add reducer prevents list replacement).
    hist_string = ""
    history = state.get("chat_history", [])
    if history:
        last_n = history[-8:]
        hist_string = "\n".join([f"{msg.type}: {msg.content}" for msg in last_n])

    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("user", "Chat History:\n{history}\n\nContext:\n{context}\n\nUser Query: {query}")
        ])
        chain = prompt | _get_llm()
        result = chain.invoke({
            "history": hist_string,
            "context": state.get("context", ""),
            "query": state["query"]
        })
        return {"answer": result.content.strip()}
    except Exception as e:
        log.warning(f"Answer LLM call failed: {e}")
        return {"answer": "I encountered a temporary error generating the response. Please try again.\n\nConsult a qualified lawyer."}

def eval_node(state: AgentState) -> dict:
    """Evaluate hallucination: Verify that the drafted answer accurately maps to the retrieved context."""
    if state.get("route") != "rag" or state.get("should_fallback"):
        return {"confidence": 1.0, "should_fallback": state.get("should_fallback", False)}

    system = """Given the legal context provided and the generated draft response, rate how faithfully the response maps to the facts in the context.
Output ONLY a float between 0.0 and 1.0. 
0.0 = contains fabricated legal facts, citations, or relies on undocumented external knowledge.
1.0 = all legal facts and citations are perfectly grounded in the context.

NOTE: The response may contain formatting (Markdown), step-by-step reasoning, and plain-English explanations of the context. Do NOT penalize those as hallucination as long as the underlying legal facts are derived from the context.
Return ONLY the float value."""

    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("user", "Context: {context}\n\nDraft Answer: {answer}")
        ])
        chain = prompt | _get_llm()
        result = chain.invoke({
            "context": state.get("context", ""),
            "answer": state.get("answer", "")
        })
        try:
            score = float(result.content.strip())
        except (ValueError, TypeError):
            score = 0.0
    except Exception as e:
        log.warning(f"Eval LLM call failed: {e} — defaulting to score 0.0")
        score = 0.0

    should_fallback = state.get("should_fallback", False)
    if score < config.faithfulness_threshold:
        should_fallback = True

    return {"confidence": score, "should_fallback": should_fallback}

def fallback_node(state: AgentState) -> dict:
    """Overrides hallucinated or unsupported answers with a standard failure output."""
    return {"answer": "I don't have sufficient information to answer that based on the legal documents available to me.\n\nConsult a qualified lawyer."}

def save_node(state: AgentState) -> dict:
    """Logs the final state into SQLite and appends AIMessage to chat history."""
    db_path = config.sqlite_path
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS chat_log
                     (id TEXT PRIMARY KEY, thread_id TEXT, query TEXT, answer TEXT, 
                      confidence REAL, sources TEXT, route TEXT, created_at TEXT)''')

        log_id = str(uuid4())
        sources_json = json.dumps(state.get("sources", []))

        c.execute("INSERT INTO chat_log VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (log_id, state.get("thread_id", ""), state.get("query", ""),
                   state.get("answer", ""), state.get("confidence", 0.0),
                   sources_json, state.get("route", ""), datetime.now().isoformat()))

        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Failed to save to SQLite: {e}")

    # Append the final answer to chat_history so multi-turn context works.
    # operator.add reducer will concatenate this list with the existing history.
    answer = state.get("answer", "")
    return {"chat_history": [AIMessage(content=answer)]} if answer else {}
