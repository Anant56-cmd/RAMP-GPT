"""
Pydantic Request & Response Data Contracts.
Defines strict schema validation models for natural language queries,
structured query analytics responses, and autonomous feedback ingestion.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class QueryRequest(BaseModel):
    """Client inquiry payload containing user prompt and conversational session ID."""
    query: str
    session_id: Optional[str] = "default"

class QueryResponse(BaseModel):
    """Structured response payload containing answer, SQL, telemetry, and visual widgets."""
    status: str
    natural_language_answer: str
    sql: Optional[str] = None
    cached: Optional[bool] = False
    chart_data: Optional[Dict[str, Any]] = None
    table_data: Optional[Dict[str, Any]] = None
    context_entity: Optional[str] = None
    session_id: Optional[str] = None
    engine: Optional[str] = None
    execution_time_ms: Optional[float] = None

class FeedbackRequest(BaseModel):
    """User evaluation payload for verified golden query caching and reinforcement."""
    query: str
    sql: Optional[str] = None
    rating: str  # "thumbs_up" or "thumbs_down"
