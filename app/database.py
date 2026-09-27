"""
Database Connection & Pool Management.
Configures SQLAlchemy QueuePool engine with automatic pre-ping health checks,
statement timeouts, socket read/write limits, and LangChain SQLDatabase bindings.
"""
import urllib.parse
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text, QueuePool
from langchain_community.utilities import SQLDatabase
from app.config import (
    DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, DB_STATEMENT_TIMEOUT_MS
)

_ENGINE = None
_SQL_DATABASE = None

def get_engine():
    """
    Initializes and returns singleton SQLAlchemy engine with QueuePool.
    URL-encodes password to safely handle special characters like '@'.
    Applies 5-second statement timeout circuit breaker via MySQL init_command.
    """
    global _ENGINE
    if _ENGINE is None:
        encoded_password = urllib.parse.quote(str(DB_PASSWORD), safe='')
        db_uri = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        _ENGINE = create_engine(
            db_uri,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=10,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args={
                "init_command": f"SET SESSION max_execution_time={DB_STATEMENT_TIMEOUT_MS}",
                "connect_timeout": 5,
                "read_timeout": 10,
                "write_timeout": 10
            }
        )
    return _ENGINE

def get_db_connection() -> SQLDatabase:
    """Returns singleton LangChain SQLDatabase instance restricted to workshop business tables."""
    global _SQL_DATABASE
    if _SQL_DATABASE is None:
        engine = get_engine()
        include_tables = [
            "customer_vehicle_info",
            "employee_info",
            "job_card_details",
            "vehicle_service_details",
            "vehicle_service_summary",
            "workshop_info"
        ]
        _SQL_DATABASE = SQLDatabase(engine, include_tables=include_tables)
    return _SQL_DATABASE

def get_pool_status() -> Dict[str, Any]:
    """Returns current connection pool health and statistics."""
    engine = get_engine()
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.checkedin() + pool.checkedout()
    }

def test_connection() -> bool:
    """Verifies that the database is reachable and active."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1"))
            return res.scalar() == 1
    except Exception:
        return False
