"""
Central Configuration Module.
Loads environment variables from .env, resolves absolute project paths,
and exports typed operational parameters for database pooling, LLM providers,
and security thresholds.
"""
import os
import sys
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

# Load environment variables from .env located at project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Data paths
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
GOLDEN_DATA_PATH = os.path.join(DATA_DIR, "golden_queries.json")
AUDIT_LOG_PATH = os.path.join(PROJECT_ROOT, "audit_logs.jsonl")

# Database Configuration
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "rag")
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", 5000))

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()

# Security & Rate Limiting
API_KEY_NAME = "X-API-Key"
ALLOWED_API_KEYS = {
    "123": "admin",
    "456": "viewer"
}
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 20))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))
