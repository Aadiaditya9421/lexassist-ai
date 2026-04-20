import streamlit as st
import uuid
import json
from graph.graph import graph

# 1. Page Configuration for premium UI aesthetic
st.set_page_config(page_title="LexAssist AI", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

# 2. Session Management
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

def reset_session():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_query = None

# 3. Sidebar Configuration
with st.sidebar:
    st.title("⚖️ LexAssist AI")
    st.markdown("Your hallucination-free, citation-backed Indian legal intelligence assistant.")
    st.divider()
    
    st.text(f"Session ID: {st.session_state.thread_id[:8]}...")
    st.button("🔄 New Session", on_click=reset_session, type="primary")
    
    st.divider()
    st.markdown("### Example Queries")
    
    # Callback to handle button clicks populating the chat input indirectly
    def set_query(q):
        st.session_state.pending_query = q

    st.button("What is the IPC punishment for murder?", on_click=set_query, args=("What is the IPC punishment for murder?",))
    st.button("What is the current date?", on_click=set_query, args=("What is the current date?",))
    st.button("Explain the Limitation Act for property.", on_click=set_query, args=("Explain the Limitation Act for property.",))
    st.button("Can I fly a spaceship under IPC?", on_click=set_query, args=("Can I fly a spaceship under IPC?",))
    st.button("Hi there!", on_click=set_query, args=("Hi there!",))

# 4. Main Area Layout
st.header("LexAssist AI - Legal Chatbot", divider="grey")

# Render existing chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Render metrics if this was an assistant message that generated them
        if msg["role"] == "assistant" and "metrics" in msg:
            m = msg["metrics"]
            cols = st.columns(3)
            cols[0].metric("Path Route", m.get("route", "Unknown"))
            cols[1].metric("Faithfulness", f"{m.get('confidence', 0.0):.2f}")
            cols[2].metric("Sources", str(m.get("source_count", 0)))
            
            if m.get("sources"):
                with st.expander("View Cited Sources"):
                    for s in m["sources"]:
                        st.markdown(f"- **{s.get('title', 'Document')}**: {s.get('source', '')}")

# 5. Handle Input Processing
user_input = st.chat_input("Ask a legal question...")
pending = st.session_state.pending_query

if pending:
    user_input = pending
    st.session_state.pending_query = None

if user_input:
    # Render user message immediately
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Process through LangGraph
    with st.chat_message("assistant"):
        with st.spinner("Analyzing legal context..."):
            initial_state = {"query": user_input}
            config_dict = {"configurable": {"thread_id": st.session_state.thread_id}}
            
            try:
                result = graph.invoke(initial_state, config_dict)
                answer = result.get("answer", "I encountered an error retrieving the response.")
                
                # Fetch metrics from state
                route = result.get("route", "N/A")
                confidence = result.get("confidence", 0.0)
                sources = result.get("sources", [])
                
                st.markdown(answer)
                
                # Render Metrics
                cols = st.columns(3)
                cols[0].metric("Path Route", route)
                cols[1].metric("Faithfulness", f"{confidence:.2f}")
                cols[2].metric("Sources", str(len(sources)))
                
                if sources:
                    with st.expander("View Cited Sources"):
                        for s in sources:
                            st.markdown(f"- **{s.get('title', 'Document')}**: {s.get('source', '')}")
                
                # Save to session history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer,
                    "metrics": {
                        "route": route,
                        "confidence": confidence,
                        "source_count": len(sources),
                        "sources": sources
                    }
                })
                
            except Exception as e:
                err_msg = f"Graph Execution Error: {str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
