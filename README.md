# LexAssist AI

> Agentic RAG system for Indian legal information — grounded, citation-backed, hallucination-free.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-red.svg)](https://streamlit.io)

---

## What it does

LexAssist answers questions about Indian law (IPC, CrPC, Constitution, RTI, Consumer
Protection, Labour Law) using a LangGraph StateGraph pipeline that retrieves relevant
legal provisions, scores faithfulness, and refuses to answer when it isn't confident.

**No hallucinated section numbers. Ever.**

---

## Architecture

```
User query
    │
    ▼
memory_node → router_node
                 │
         ┌───────┼───────┐
        rag     tool  chitchat
         │       │       │
    rewrite    tool    answer
         │     node       │
    retrieve     │    evaluate
         │       │       │
      grade   evaluate  save
         │       │
       answer   save
         │
      evaluate
         │
    ┌────┴────┐
   save   fallback
              │
            save
```

## Tech stack

| Layer        | Technology                              |
|--------------|-----------------------------------------|
| Agent        | LangGraph 0.2+ (StateGraph)             |
| LLM          | GPT-4o mini (OpenAI)                    |
| Embeddings   | all-MiniLM-L6-v2 (HuggingFace)         |
| Vector DB    | ChromaDB 0.5                            |
| Memory       | MemorySaver / SqliteSaver               |
| Evaluation   | LLM-as-judge (RAGAS-compatible)         |
| Frontend     | Streamlit 1.40                          |
| Persistence  | SQLite                                  |
| Deployment   | Streamlit Community Cloud               |

---

## Quick start

```bash
# 1. Clone and enter
git clone https://github.com/<your-username>/lexassist-ai.git
cd lexassist-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Build the knowledge base (first time only)
python -m knowledge_base.ingest

# 6. Run the app
streamlit run app.py
```

---

## Project structure

```
lexassist-ai/
├── app.py                        # Streamlit UI entry point
├── config.py                     # Centralised configuration
├── requirements.txt
├── .env.example                  # Template — copy to .env
│
├── graph/
│   ├── state.py                  # AgentState TypedDict
│   ├── nodes.py                  # All 10 LangGraph node functions
│   └── graph.py                  # StateGraph wiring + compilation
│
├── knowledge_base/
│   ├── ingest.py                 # Document loading, chunking, embedding
│   └── docs/                     # 12 plain-text legal source files
│
├── tests/
│   ├── conftest.py               # Shared pytest fixtures
│   ├── test_nodes.py             # Unit tests for node functions
│   └── red_team_results.md       # Documented adversarial test cases
│
└── docs/
    └── capstone_report.pdf       # Final submission document
```

---

## Running tests

```bash
pytest tests/ -v --cov=graph --cov-report=term-missing
```

---

## Deployment

This app is deployed on Streamlit Community Cloud.

**Live URL:** `https://<your-app>.streamlit.app` *(update after deployment)*

To deploy your own instance:
1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the entry point
4. Add `OPENAI_API_KEY` in the Secrets panel
5. Deploy

---

## Evaluation

| Metric                      | Target   | Achieved |
|-----------------------------|----------|----------|
| Mean faithfulness score     | ≥ 0.80   | TBD      |
| Router accuracy             | ≥ 90%    | TBD      |
| Fallback on OOD queries     | 100%     | TBD      |
| Mean response latency       | < 8s     | TBD      |

---

## Academic context

Capstone project for Agentic AI course.
**Student:** Aditya | KIIT University — Roll No. 23052212
**Course:** Agentic AI Systems

---

## Disclaimer

LexAssist provides legal *information* only, not legal *advice*.
Always consult a qualified advocate for your specific situation.
