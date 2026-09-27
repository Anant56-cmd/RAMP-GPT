# RAMP-GPT — Self-Healing Text-to-SQL Analytics Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.64+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)

An enterprise-grade internal Text-to-SQL analytics agent designed for RAMP Smart Garage Management Systems and automotive workshops. Translates natural language operational queries into executable, multi-table MySQL statements with sub-second latency, self-healing validation, and dynamic visualization.

---

## Key Features

- **Dynamic Schema Routing**: Contextually routes questions to specific schema domains (HR vs. Operations vs. Full), cutting LLM prompt token consumption by ~65%.
- **Zero-Bloat Semantic Cache**: In-memory caching engine using token-set Jaccard overlap and normalized sequence matching. Delivers <1 ms query retrieval and eliminates 2.5 GB of vector database (ChromaDB/PyTorch) dependencies.
- **10-Layer Self-Healing Pipeline**: Heuristic regex interceptor automatically repairs hallucinated join keys, ambiguous aggregations, model synonym mismatches, and column confusions before execution.
- **AST Read-Only Enforcement**: Query sanitization guardrail that blocks destructive commands (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `INSERT`).
- **PII Scrubbing**: Context-aware redaction of customer phone numbers, emails, and dates of birth.
- **Autonomous Feedback Loop**: Instant golden-query persistence from thumbs-up user ratings with zero-restart hot-reloading.
- **Interactive Streamlit Dashboard**: Full-featured web dashboard with real-time analytics, dynamic charting, structured tables with 1-click CSV download, collapsible SQL inspector, and quick prompts.

---

## System Architecture

```
ramp-gpt/
├── app/
│   ├── config.py              # Environment configuration & security constants
│   ├── database.py            # SQLAlchemy QueuePool connection manager
│   ├── core/
│   │   ├── security.py        # API key verification & sliding-window rate limiting
│   │   ├── sql_validator.py   # Read-only AST & query security validation
│   │   └── pii_masker.py      # Customer/employee PII redaction
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response schemas
│   ├── services/
│   │   ├── agent_service.py   # Primary query coordination pipeline
│   │   ├── llm_factory.py     # Hybrid model provider (Groq Cloud + Ollama Local)
│   │   ├── schema_router.py   # Dynamic table routing & categorical mapping
│   │   ├── retriever.py       # Zero-bloat in-memory semantic cache
│   │   ├── sql_healer.py      # 10-layer regex & heuristic SQL healing
│   │   ├── visualizer.py      # Semantic data parser & metrics classifier
│   │   ├── memory_service.py  # Conversational session memory & pronoun resolution
│   │   └── audit_service.py   # Thread-safe JSONL telemetry logger
│   └── api/
│       └── routes.py          # FastAPI route controllers
├── data/
│   └── golden_queries.json    # Verified query-SQL knowledge base
├── scripts/
│   └── manage_golden_queries.py # CLI golden query management utility
├── streamlit_app.py           # Streamlit analytics dashboard UI
├── main.py                    # Application entrypoint (FastAPI REST API)
├── requirements.txt           # Production dependencies
├── .env.example               # Environment template
└── codebase architecture.pdf  # Comprehensive architecture & engineering manual
```

---

## Documentation & Architecture Manual

For an exhaustive, file-by-file technical breakdown, refer to the included PDF manual:
- **`codebase architecture.pdf`**: Complete engineering manual detailing:
  - Exact module roles, internal mechanics, requirements, and architectural importance for every file.
  - Step-by-step query execution pipeline lifecycle (context resolution, caching, routing, healing, AST validation, execution, PII masking, translation, visualization).
  - Deep-dive analysis into core engineering innovations (Zero-bloat Jaccard cache vs Vector DBs, 10-layer heuristic SQL healing, dynamic schema pruning, connection pool circuit breakers).

---

## Quick Start

### 1. Clone & Environment Setup
```bash
# Clone the repository
git clone https://github.com/Anant56-cmd/RAMP-GPT.git
cd RAMP-GPT

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```ini
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=rag

# Primary Engine (Groq LPU Cloud)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=qwen/qwen3.8-27b

# Local Fallback Engine (Ollama)
OLLAMA_MODEL=qwen2.5-coder:7b
```

### 3. Launch the Streamlit Analytics Dashboard
```bash
streamlit run streamlit_app.py
```
The Streamlit interface will start at `http://localhost:8501`.

### 4. (Optional) Run the FastAPI REST Server
```bash
python main.py
```
The FastAPI backend will start at `http://127.0.0.1:8000`.

---

## API Reference

### Query Endpoint
`POST /api/v1/query`
- **Headers**: `X-API-Key: 123`
- **Body**:
```json
{
  "query": "What is the total service amount for Volkswagen Virtus?",
  "session_id": "default"
}
```
- **Response**:
```json
{
  "status": "success",
  "natural_language_answer": "The total service amount for the Volkswagen Virtus is ₹54,289.42.",
  "sql": "SELECT COALESCE(SUM(s.total_amt), 0) AS total_spent FROM vehicle_service_summary s INNER JOIN customer_vehicle_info c ON s.customer_id = c.customer_id WHERE c.vehicle_type = 'Volkswagen-VIRTUS-TOPLINE TSI';",
  "cached": true,
  "chart_data": { ... },
  "table_data": { ... },
  "execution_time_ms": 1.2
}
```

### Health Check
`GET /health`
Returns connection pool statistics, rate limiter state, and active LLM engine status.

---

## CLI Utilities

Manage and validate the golden query cache directly from the command line:

```bash
# Validate all golden queries
python scripts/manage_golden_queries.py --validate

# List verified golden queries
python scripts/manage_golden_queries.py --list

# Add a verified golden query
python scripts/manage_golden_queries.py --add --query "..." --sql "..."
```

---

## License
MIT License. Free for commercial and non-commercial use.
