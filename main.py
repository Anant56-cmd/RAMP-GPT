"""
RAMP-GPT NL2SQL Application Entrypoint.
Initializes the FastAPI application, mounts CORS middleware, registers modular API routes,
and exposes core security and model schemas.
"""
import sys
import os

# Ensure UTF-8 console output encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.routes import router
from app.core.security import get_api_key, rate_limiter, SlidingWindowRateLimiter
from app.models.schemas import QueryRequest, QueryResponse, FeedbackRequest

app = FastAPI(
    title="RAMP-GPT NL2SQL API",
    description="Enterprise API for translating natural language to garage database queries.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular API routes
app.include_router(router)

# Re-exports for backward compatibility
__all__ = [
    "app",
    "get_api_key",
    "rate_limiter",
    "SlidingWindowRateLimiter",
    "QueryRequest",
    "QueryResponse",
    "FeedbackRequest"
]

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)