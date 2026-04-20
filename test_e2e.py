from graph.graph import graph
import uuid

def run():
    print("=== LexAssist AI End-to-End Smoke Test ===\n")
    thread_id = str(uuid.uuid4())
    config_dict = {"configurable": {"thread_id": thread_id}}

    queries = [
        {"desc": "IPC Question (RAG Route)", "query": "What is the punishment for cheating under the IPC if someone induces the delivery of property?"},
        {"desc": "Date Question (Tool Route)", "query": "What is the current date today?"},
        {"desc": "Greeting (ChitChat Route)", "query": "Hi there! I need some legal help."},
        {"desc": "Out-of-Scope (Fallback Route)", "query": "Can you explain the US Constitution's second amendment?"},
        {"desc": "Multi-turn Follow-up", "query": "What if they only attempted to cheat but didn't succeed? How does that change the previous IPC section punishment?"}
    ]

    for q in queries:
        print(f"Testing: {q['desc']}")
        print(f"User Query: {q['query']}")
        
        initial_state = {"query": q["query"]}
        
        # We catch exceptions here to trace them and show exactly where it fails
        try:
            result = graph.invoke(initial_state, config_dict)
            print(f"Assigned Route: {result.get('route')}")
            print(f"Confidence: {result.get('confidence', 'N/A')}")
            print(f"Fallback Tripped: {result.get('should_fallback', False)}")
            print(f"Answer: {result.get('answer')}")
            print("-" * 50)
        except Exception as e:
            print(f"ERROR processing query '{q['query']}': {e}")
            print("-" * 50)

if __name__ == "__main__":
    run()
