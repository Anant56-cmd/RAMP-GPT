import os
from typing import Tuple, Any, Optional
from langchain_ollama import OllamaLLM
from app.config import (
    GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL, GEMINI_API_KEY
)

def safe_print(msg: str):
    """Safely print strings even if console encoding does not support special characters."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass

_SQL_LLM = None
_CHAT_LLM = None
_ACTIVE_ENGINE = "qwen2.5-coder:7b (Local)"
_FALLBACK_SQL_LLM = None
_FALLBACK_CHAT_LLM = None

def get_models() -> Tuple[Any, Any, None, str, Any, Any]:
    """
    Hybrid Model Provider:
    - Primary: Groq Cloud (Qwen 3.8-27B) if GROQ_API_KEY is configured.
    - Secondary: Google Gemini if GEMINI_API_KEY is configured.
    - Fallback: Local Ollama (qwen2.5-coder:7b).
    """
    global _SQL_LLM, _CHAT_LLM, _ACTIVE_ENGINE, _FALLBACK_SQL_LLM, _FALLBACK_CHAT_LLM

    threads = min(8, os.cpu_count() or 4)

    # Initialize fallback local models if not already active
    if _FALLBACK_SQL_LLM is None:
        try:
            _FALLBACK_SQL_LLM = OllamaLLM(
                model=OLLAMA_MODEL,
                temperature=0.0,
                num_thread=threads,
                num_predict=200,
                num_ctx=2048,
                keep_alive=-1
            )
            _FALLBACK_CHAT_LLM = OllamaLLM(
                model=OLLAMA_MODEL,
                temperature=0.6,
                num_thread=threads,
                num_ctx=1024,
                keep_alive=-1
            )
        except Exception as e:
            safe_print(f"> Local Ollama model init note: {e}")

    # 1. Primary: Groq Cloud
    cloud_initialized = False
    if GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            _SQL_LLM = ChatGroq(
                model_name=GROQ_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=0.0
            )
            _CHAT_LLM = ChatGroq(
                model_name=GROQ_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=0.6
            )
            _ACTIVE_ENGINE = f"{GROQ_MODEL} (Groq Cloud)"
            cloud_initialized = True
        except Exception as e:
            safe_print(f"> Warning: Failed to init Groq Cloud LLM ({e}). Trying secondary...")

    # 2. Secondary: Gemini Cloud
    if not cloud_initialized and GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
            _SQL_LLM = ChatGoogleGenerativeAI(
                model=gemini_model,
                temperature=0.0,
                google_api_key=GEMINI_API_KEY
            )
            _CHAT_LLM = ChatGoogleGenerativeAI(
                model=gemini_model,
                temperature=0.6,
                google_api_key=GEMINI_API_KEY
            )
            _ACTIVE_ENGINE = f"{gemini_model} (Gemini Cloud)"
            cloud_initialized = True
        except Exception as e:
            safe_print(f"> Warning: Failed to init Gemini Cloud LLM ({e}). Falling back to Local Qwen...")

    # 3. Fallback: Local Qwen
    if not cloud_initialized:
        _SQL_LLM = _FALLBACK_SQL_LLM
        _CHAT_LLM = _FALLBACK_CHAT_LLM
        _ACTIVE_ENGINE = f"{OLLAMA_MODEL} (Local)"

    return _SQL_LLM, _CHAT_LLM, None, _ACTIVE_ENGINE, _FALLBACK_SQL_LLM, _FALLBACK_CHAT_LLM
