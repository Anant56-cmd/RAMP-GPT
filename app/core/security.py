"""
Security & Access Control Module.
Provides thread-safe in-memory sliding window rate limiting, API key authentication,
and Role-Based Access Control (RBAC) mapping for client requests.
"""
import time
import threading
from collections import defaultdict
from typing import Tuple
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from app.config import (
    API_KEY_NAME, ALLOWED_API_KEYS, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
)

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

class SlidingWindowRateLimiter:
    """Lightweight, in-memory, thread-safe sliding window rate limiter."""
    def __init__(self, requests_limit: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            self.history[client_id] = [t for t in self.history[client_id] if t > window_start]
            if len(self.history[client_id]) >= self.requests_limit:
                oldest = self.history[client_id][0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                return False, retry_after
            self.history[client_id].append(now)
            return True, 0

rate_limiter = SlidingWindowRateLimiter()

def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validates API Key from header against authorized keys."""
    if api_key in ALLOWED_API_KEYS:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid or missing API Key")

def get_role_for_key(api_key: str) -> str:
    """Returns RBAC role for the provided API key."""
    return ALLOWED_API_KEYS.get(api_key, "unknown")
