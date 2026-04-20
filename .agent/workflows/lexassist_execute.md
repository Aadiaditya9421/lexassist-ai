# Workflow: lexassist_execute
**Command:** /lexassist_execute
**Description:** Launch, test, and finalize the LexAssist AI platform while strictly adhering to Anti-Hallucination directives.

## Steps
1. **Initialize Grounding**: Read `lexassist_development_rules.md` immediately. You MUST strictly abide by the Anti-Hallucination Agentic Directives documented inside. Do not execute any further code without this full context.
2. **Setup ChromaDB**: Execute `python -m knowledge_base.ingest`. Parse the resulting log to confirm the chunking and embedding is successful (collection count > 100). Do not hallucinate dummy vectors if this fails.
3. **End-to-End Smoke Test**: Run `python test_e2e.py`. Analyze exactly which path (`rag`, `tool`, `chitchat`, or `fallback`) each of the 5 queries took. Debug any errors directly in `graph/nodes.py` or `graph/graph.py` without faking external APIs.
4. **Unit Testing Integrity**: Execute `pytest tests/test_nodes.py`. Fix any boundary failures caused by LLM non-determinism. Your goal is a verified 6/6 pass rate ensuring prompt stability.
5. **Red Teaming Validation**: Cross-reference your testing trace against `tests/red_team_results.md`. You must physically guarantee that the fallback mechanism intercepts the 8 adversarial hallucinations consistently.
6. **Interface Launch**: Once all logic holds, run `streamlit run app.py` to boot the finalized user application. 
7. **Graph Synchronization**: Whenever you modify the application architecture, you MUST automatically run `python -m graphify update .` to rebuild the context graph.

*Note for Claude Opus 4.6:* You are in a highly deterministic loop. Stop the workflow and trigger an "I don't know / I need input" constraint if dependencies fail.
