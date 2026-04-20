# Graph Report - C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai  (2026-04-20)

## Corpus Check
- 17 files · ~601,649 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 174 nodes · 268 edges · 21 communities detected
- Extraction: 69% EXTRACTED · 31% INFERRED · 0% AMBIGUOUS · INFERRED: 84 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]

## God Nodes (most connected - your core abstractions)
1. `Config` - 25 edges
2. `AgentState` - 24 edges
3. `chunk_documents()` - 13 edges
4. `load_documents()` - 12 edges
5. `parse_frontmatter()` - 10 edges
6. `scrape_document()` - 8 edges
7. `_make_doc()` - 8 edges
8. `_clean_chunk()` - 7 edges
9. `build_vectorstore()` - 7 edges
10. `get_vectorstore()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Compiles the core LangGraph structure for LexAssist AI.` --uses--> `AgentState`  [INFERRED]
  C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\graph.py → C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\state.py
- `Summarize history if it gets too long, otherwise just pass.` --uses--> `AgentState`  [INFERRED]
  C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\nodes.py → C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\state.py
- `Classify the user's intent into rag, tool, or chitchat.` --uses--> `AgentState`  [INFERRED]
  C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\nodes.py → C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\state.py
- `HyDE rewriting: Generate a hypothetical legal passage to improve retrieval.` --uses--> `AgentState`  [INFERRED]
  C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\nodes.py → C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\state.py
- `Retrieve top contextual documents via MMR.` --uses--> `AgentState`  [INFERRED]
  C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\nodes.py → C:\PERSONAL FILES\MY FILES\agentic ai project\lexassist-ai\graph\state.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.1
Nodes (37): chunk_documents(), _clean_chunk(), load_documents(), parse_frontmatter(), Load all .txt files from docs_dir, parse frontmatter, return     a list of LangC, Split documents into overlapping chunks suitable for RAG retrieval.      Strateg, Remove leading/trailing divider lines and collapse excess whitespace., Split YAML frontmatter from document body.      Expects documents that start wit (+29 more)

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (27): Config, config.py — Centralised configuration for LexAssist AI.  Every tuneable constant, Return config as a plain dict (useful for logging and Streamlit debug panels)., Coerce types and normalise paths right after construction., Validate all settings and raise with a clear message on any issue.         Call, conftest.py — Shared pytest fixtures. Add reusable fixtures here as the test sui, A config instance safe for testing (no real API key required)., A minimal valid AgentState for unit tests. (+19 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (15): add_practical_notes_prompt(), build_frontmatter(), clean_text(), DocTarget, extract_text(), fetch_page(), main(), knowledge_base/scraper.py ───────────────────────── Scrapes full legal text for (+7 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (13): Deterministic mini-tools for direct lookups without LLM extraction., Generates the grounded response strictly using the provided context., Evaluate hallucination: Verify that the drafted answer accurately maps to the re, Overrides hallucinated or unsupported answers with a standard failure output., Logs the final state mapping into an SQLite tracking table to ensure auditabilit, Summarize history if it gets too long, otherwise just pass., Classify the user's intent into rag, tool, or chitchat., HyDE rewriting: Generate a hypothetical legal passage to improve retrieval. (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.26
Nodes (12): build_vectorstore(), _get_embeddings(), get_vectorstore(), inspect_vectorstore(), main(), knowledge_base/ingest.py ───────────────────────── Document loader, chunker, emb, Load the embedding model (cached after first call by HuggingFace)., Embed chunks and persist them to ChromaDB.      If chroma_store already exists a (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.31
Nodes (8): answer_node(), _get_llm(), _get_vs(), Generates the grounded response strictly using the provided context., HyDE rewriting: Generate a hypothetical legal passage to improve retrieval., Retrieve top contextual documents via MMR., retrieval_node(), rewrite_node()

### Community 6 - "Community 6"
Cohesion: 0.29
Nodes (7): Logs the final state mapping into an SQLite tracking table to ensure auditabilit, Classify the user's intent into rag, tool, or chitchat., router_node(), save_node(), test_router_returns_rag(), test_router_returns_tool(), test_save_node_writes_to_db()

### Community 7 - "Community 7"
Cohesion: 0.38
Nodes (6): check_version(), main(), parse_version(), verify_install.py — Dependency verification script for LexAssist AI.  Run this a, Convert '1.2.3' to (1, 2, 3) for numeric comparison., Return (installed_version, meets_minimum).

### Community 8 - "Community 8"
Cohesion: 0.53
Nodes (5): build_frontmatter(), file_needs_generation(), generate_with_groq(), main(), knowledge_base/generate_missing.py ──────────────────────────────────── Fills an

### Community 9 - "Community 9"
Cohesion: 0.5
Nodes (1): Test suite for LexAssist AI.

### Community 10 - "Community 10"
Cohesion: 0.67
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 0.67
Nodes (2): build_graph(), Compiles the core LangGraph structure for LexAssist AI.

### Community 12 - "Community 12"
Cohesion: 0.67
Nodes (3): eval_node(), Evaluate hallucination: Verify that the drafted answer accurately maps to the re, test_eval_low_score_triggers_fallback()

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (3): grader_node(), Filter irrelevant retrieved chunks, keeping strictly relevant ones., test_grader_filters_irrelevant_doc()

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (3): fallback_node(), Overrides hallucinated or unsupported answers with a standard failure output., test_fallback_returns_correct_message()

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (2): Deterministic mini-tools for direct lookups without LLM extraction., tool_node()

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (2): memory_node(), Summarize history if it gets too long, otherwise just pass.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Coerce types and normalise paths right after construction.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Validate all settings and raise with a clear message on any issue.         Call

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return config as a plain dict (useful for logging and Streamlit debug panels).

## Knowledge Gaps
- **42 isolated node(s):** `config.py — Centralised configuration for LexAssist AI.  Every tuneable constant`, `Coerce types and normalise paths right after construction.`, `Validate all settings and raise with a clear message on any issue.         Call`, `Return config as a plain dict (useful for logging and Streamlit debug panels).`, `verify_install.py — Dependency verification script for LexAssist AI.  Run this a` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (2 nodes): `test_e2e.py`, `run()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `Deterministic mini-tools for direct lookups without LLM extraction.`, `tool_node()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `memory_node()`, `Summarize history if it gets too long, otherwise just pass.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Coerce types and normalise paths right after construction.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Validate all settings and raise with a clear message on any issue.         Call`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return config as a plain dict (useful for logging and Streamlit debug panels).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_vectorstore()` connect `Community 4` to `Community 5`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `_get_vs()` connect `Community 5` to `Community 4`?**
  _High betweenness centrality (0.158) - this node is a cross-community bridge._
- **Why does `AgentState` connect `Community 3` to `Community 5`, `Community 6`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 16`, `Community 17`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `Config` (e.g. with `tests/test_config.py — Unit tests for config.py. Run: pytest tests/test_config.p` and `__post_init__ resolves paths relative to project root.`) actually correct?**
  _`Config` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `AgentState` (e.g. with `Compiles the core LangGraph structure for LexAssist AI.` and `Summarize history if it gets too long, otherwise just pass.`) actually correct?**
  _`AgentState` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `chunk_documents()` (e.g. with `test_chunk_documents_raises_on_empty_list()` and `test_chunk_documents_returns_list_of_documents()`) actually correct?**
  _`chunk_documents()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `load_documents()` (e.g. with `test_load_documents_raises_on_missing_dir()` and `test_load_documents_raises_on_empty_dir()`) actually correct?**
  _`load_documents()` has 7 INFERRED edges - model-reasoned connections that need verification._