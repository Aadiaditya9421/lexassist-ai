from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

class AgentState(TypedDict):
    """
    Represents the state of the LexAssist AI LangGraph.
    Data is passed through the nodes during execution.
    """
    
    # User Input
    query: str
    rewritten_query: str
    thread_id: str
    
    # Decisions & History
    route: str  # e.g., "rag", "tool", "chitchat"
    chat_history: Annotated[List[BaseMessage], operator.add]
    
    # RAG specific context
    documents: List[Document]  # Raw retrieved documents
    relevant_docs: List[Document]  # Filtered relevant documents
    context: str  # Joined string of relevant text chunks
    sources: List[Dict[str, Any]]  # Metadata sources cited
    
    # Execution Flags & Outputs
    tool_result: Optional[str]  # Output from specialized tools
    answer: str  # Final or draft generated answer
    confidence: float  # Faithfulness evaluation score (0.0 - 1.0)
    should_fallback: bool  # Flag indicating a failure/hallucination risk
