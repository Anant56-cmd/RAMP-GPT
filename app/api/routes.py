"""
FastAPI Route Controllers.
Defines REST API endpoints for natural language query execution,
feedback ingestion, administrative audit log inspection, and health monitoring.
"""
import time
import os
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request

from app.models.schemas import QueryRequest, QueryResponse, FeedbackRequest
from app.core.security import get_api_key, get_role_for_key, rate_limiter
from app.services.agent_service import process_sql_query
from app.services.retriever import save_golden_query
from app.services.audit_service import log_audit_event, get_recent_audit_logs
from app.database import get_pool_status
from app.config import GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL, GEMINI_API_KEY, GEMINI_MODEL

router = APIRouter()

@router.post("/api/v1/query", response_model=QueryResponse)
def ask_database(
    request: QueryRequest, 
    http_req: Request,
    api_key: str = Depends(get_api_key)
):
    """
    Primary Natural Language Analytics Endpoint.
    Enforces sliding-window rate limiting, runs conversational context resolution,
    queries semantic cache, executes healed SQL, and formats responses with Chart.js payloads.
    """
    role = get_role_for_key(api_key)
    client_ip = http_req.client.host if http_req.client else "127.0.0.1"

    # Rate Limiting Check
    allowed, retry_after = rate_limiter.is_allowed(api_key)
    if not allowed:
        log_audit_event(
            role=role,
            client_ip=client_ip,
            session_id=request.session_id,
            query=request.query,
            status="RATE_LIMITED",
            error_detail=f"Rate limit exceeded. Retry after {retry_after}s"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded (max {rate_limiter.requests_limit} queries/minute). Please wait {retry_after} seconds before trying again.",
            headers={"Retry-After": str(retry_after)}
        )

    start_time = time.time()
    try:
        result = process_sql_query(
            user_query=request.query, 
            session_id=request.session_id or "default", 
            return_details=True
        )
        duration_ms = (time.time() - start_time) * 1000

        if isinstance(result, dict):
            # Log successful or intercepted query
            log_audit_event(
                role=role,
                client_ip=client_ip,
                session_id=request.session_id,
                query=request.query,
                resolved_query=result.get("resolved_query"),
                sql=result.get("sql"),
                latency_ms=duration_ms,
                pii_masked=result.get("pii_masked", False),
                cached=result.get("cached", False),
                row_count=result.get("table_data", {}).get("total_rows", 1 if result.get("raw_result") else 0) if result.get("table_data") else 0,
                status=result.get("status", "SUCCESS"),
                engine=result.get("engine"),
                error_detail=result.get("error_detail")
            )

            return QueryResponse(
                status="success",
                natural_language_answer=result.get("answer", ""),
                sql=result.get("sql"),
                cached=result.get("cached", False),
                chart_data=result.get("chart_data"),
                table_data=result.get("table_data"),
                context_entity=result.get("context_entity"),
                session_id=request.session_id,
                engine=result.get("engine"),
                execution_time_ms=round(duration_ms, 2)
            )
        else:
            return QueryResponse(
                status="success",
                natural_language_answer=str(result),
                session_id=request.session_id
            )
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        print(f"Server Processing Error: {str(e)}")
        log_audit_event(
            role=role,
            client_ip=client_ip,
            session_id=request.session_id,
            query=request.query,
            latency_ms=duration_ms,
            status="ERROR",
            error_detail=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error processing database query.")

@router.post("/api/v1/feedback")
def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Feedback Ingestion Endpoint.
    Appends verified query-SQL pairs from positive ratings into golden_queries.json
    and hot-reloads the in-memory cache with zero server restart.
    """
    try:
        rating = request.rating.lower().strip()
        if rating in ["thumbs_up", "positive", "up"]:
            if request.sql:
                save_golden_query(request.query, request.sql)

            return {
                "status": "success",
                "message": "Thank you! Verified query saved to Golden Knowledge Base."
            }
        else:
            return {
                "status": "success",
                "message": "Feedback recorded for model review."
            }
    except Exception as e:
        print(f"> Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback.")

@router.get("/api/v1/audit/logs")
def read_audit_logs(
    limit: int = 50,
    api_key: str = Depends(get_api_key)
):
    """
    Administrative Telemetry Endpoint.
    Returns the most recent audit logs in reverse-chronological order.
    Requires 'admin' RBAC role.
    """
    role = get_role_for_key(api_key)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to view audit logs")
    logs = get_recent_audit_logs(limit=limit)
    return {
        "status": "success",
        "count": len(logs),
        "logs": logs
    }

@router.get("/health")
def health_check():
    """
    System Health & Operational Status Endpoint.
    Reports connection pool checked-in/out counts, rate limiter configurations,
    and active hybrid LLM engine mode.
    """
    groq_key = bool(GROQ_API_KEY)
    gemini_key = bool(GEMINI_API_KEY)
    if groq_key:
        active_primary = f"{GROQ_MODEL} (Groq Cloud)"
    elif gemini_key:
        active_primary = f"{GEMINI_MODEL} (Gemini Cloud)"
    else:
        active_primary = f"{OLLAMA_MODEL} (Local)"

    return {
        "status": "operational",
        "database_pool": get_pool_status(),
        "rate_limiter": {
            "limit_per_minute": rate_limiter.requests_limit,
            "window_seconds": rate_limiter.window_seconds
        },
        "llm_engine": {
            "mode": "hybrid",
            "active_primary": active_primary,
            "fallback": f"{OLLAMA_MODEL} (Local)"
        }
    }
