"""
Structured Telemetry & Audit Logging Service.
Appends immutable, structured JSON records to audit_logs.jsonl under a thread-safe
lock, capturing client IP, session context, execution latency, and error attribution.
"""
import os
import json
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.config import AUDIT_LOG_PATH

_LOG_LOCK = threading.Lock()

def log_audit_event(
    role: str = "anonymous",
    client_ip: Optional[str] = None,
    session_id: Optional[str] = "default",
    query: str = "",
    resolved_query: Optional[str] = None,
    sql: Optional[str] = None,
    latency_ms: float = 0.0,
    pii_masked: bool = False,
    cached: bool = False,
    row_count: int = 0,
    status: str = "SUCCESS",
    engine: Optional[str] = None,
    error_detail: Optional[str] = None
) -> Dict[str, Any]:
    """
    Appends an immutable, structured audit entry to audit_logs.jsonl in a thread-safe manner.
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "client_ip": client_ip or "127.0.0.1",
        "session_id": session_id or "default",
        "user_query": query,
        "resolved_query": resolved_query if (resolved_query and resolved_query != query) else None,
        "sql": sql,
        "latency_ms": round(latency_ms, 2),
        "pii_masked": pii_masked,
        "cached": cached,
        "row_count": row_count,
        "status": status,
        "engine": engine,
        "error_detail": error_detail
    }
    
    try:
        line = json.dumps(event, ensure_ascii=False)
        with _LOG_LOCK:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        print(f"> Audit Logging Warning: Failed to write audit log: {e}")
        
    return event

def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent audit log entries in reverse chronological order.
    """
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
        
    logs = []
    try:
        with _LOG_LOCK:
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except Exception:
                            continue
        return list(reversed(logs[-limit:]))
    except Exception as e:
        print(f"> Audit Retrieval Warning: {e}")
        return []
