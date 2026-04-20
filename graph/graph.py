from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import AgentState
from graph.nodes import (
    memory_node, router_node, rewrite_node, retrieval_node,
    grader_node, tool_node, answer_node, eval_node, fallback_node, save_node
)

def build_graph():
    """Compiles the core LangGraph structure for LexAssist AI."""
    workflow = StateGraph(AgentState)
    
    # 1. Add all 10 nodes
    workflow.add_node("memory", memory_node)
    workflow.add_node("router", router_node)
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("grader", grader_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("answer", answer_node)
    workflow.add_node("evaluate", eval_node)
    workflow.add_node("fallback", fallback_node)
    workflow.add_node("save", save_node)
    
    # 2. Set Entry Point
    workflow.set_entry_point("memory")
    
    # 3. Add Edges & Conditional Edges
    workflow.add_edge("memory", "router")
    
    def route_decision(state: AgentState):
        route = state.get("route", "rag")
        if route == "rag":
            return "rewrite"
        elif route == "tool":
            return "tool"
        elif route == "chitchat":
            return "answer"
        return "rewrite"
        
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "rewrite": "rewrite",
            "tool": "tool",
            "answer": "answer"
        }
    )
    
    workflow.add_edge("rewrite", "retrieval")
    workflow.add_edge("retrieval", "grader")
    
    def grade_decision(state: AgentState):
        return "fallback" if state.get("should_fallback") else "answer"
        
    workflow.add_conditional_edges(
        "grader",
        grade_decision,
        {
            "fallback": "fallback",
            "answer": "answer"
        }
    )
    
    def tool_decision(state: AgentState):
        return "evaluate" if state.get("tool_result") else "rewrite"
        
    workflow.add_conditional_edges(
        "tool",
        tool_decision,
        {
            "evaluate": "evaluate",
            "rewrite": "rewrite"
        }
    )
    
    workflow.add_edge("answer", "evaluate")
    
    def evaluate_decision(state: AgentState):
        return "fallback" if state.get("should_fallback") else "save"
        
    workflow.add_conditional_edges(
        "evaluate",
        evaluate_decision,
        {
            "fallback": "fallback",
            "save": "save"
        }
    )
    
    workflow.add_edge("fallback", "save")
    workflow.add_edge("save", END)
    
    # Checkpointer for conversation state thread persistence
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

# Export the compiled graph
graph = build_graph()
