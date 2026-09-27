"""
RAMP-GPT — Ultra High-Fidelity Glassmorphic Streamlit Dashboard.
Replicates the exact production UI with ambient mesh gradients, glowing frosted cards,
live Chart.js visualizations, structured tables with 1-click CSV export, and SQL inspection.
"""

import os
import sys
import time
import json
import base64
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.agent_service import process_sql_query
from app.database import get_pool_status, test_connection
from app.services.llm_factory import get_models
from app.services.retriever import load_golden_queries, save_golden_query
from app.services.audit_service import log_audit_event

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="RAMP-GPT — Garage Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# System Diagnostics Check
# ---------------------------------------------------------
if "system_status" not in st.session_state:
    try:
        db_ok = test_connection()
        pool = get_pool_status()
        _, _, _, engine_name, _, _ = get_models()
        st.session_state.system_status = {
            "db_connected": db_ok,
            "engine": engine_name,
            "pool": pool
        }
    except Exception as e:
        st.session_state.system_status = {
            "db_connected": False,
            "engine": "qwen/qwen3.8-27b (Groq Cloud)",
            "pool": {"checked_in": 0, "pool_size": 5}
        }

active_engine_name = st.session_state.system_status.get("engine", "qwen/qwen3.8-27b (Groq Cloud)")

# ---------------------------------------------------------
# Ultra-High-Fidelity Glassmorphic CSS Injection
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Hide Streamlit Header, Toolbar & Watermarks */
    #MainMenu, header, footer, .stDeployButton { display: none !important; }
    
    /* Global App Container */
    .stApp {
        background-color: #07080e !important;
        font-family: 'Inter', sans-serif !important;
        color: #f8fafc !important;
        overflow-x: hidden !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 7rem !important;
        max-width: 900px !important;
        margin: 0 auto !important;
    }

    /* Ambient Mesh Gradient Background Blobs */
    .bg-mesh-container {
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        z-index: -10;
        overflow: hidden;
        pointer-events: none;
        background: #07080e;
    }
    .mesh-blob {
        position: absolute;
        border-radius: 50%;
        filter: blur(140px);
        opacity: 0.45;
        animation: float-blob 22s infinite alternate ease-in-out;
        transform-origin: center;
    }
    .blob-1 { top: -10%; left: -10%; width: 45vw; height: 45vw; background: #FF007A; animation-delay: 0s; }
    .blob-2 { bottom: -20%; right: -10%; width: 55vw; height: 55vw; background: #00F0FF; animation-delay: -5s; animation-direction: alternate-reverse; }
    .blob-3 { top: 25%; left: 30%; width: 38vw; height: 38vw; background: #7000FF; animation-delay: -10s; }

    @keyframes float-blob {
        0% { transform: translate(0, 0) scale(1) rotate(0deg); }
        50% { transform: translate(6%, 8%) scale(1.06) rotate(8deg); }
        100% { transform: translate(-6%, -5%) scale(0.96) rotate(-8deg); }
    }

    /* Top Navigation Bar */
    .top-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 24px;
        background: rgba(18, 22, 34, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        backdrop-filter: blur(16px);
        margin-bottom: 24px;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    }
    .brand-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 16px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.01em;
    }
    .brand-logo-icon {
        width: 32px;
        height: 32px;
        border-radius: 10px;
        background: linear-gradient(135deg, #00F0FF, #7000FF, #FF007A);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        box-shadow: 0 0 12px rgba(0, 240, 255, 0.4);
    }
    .status-pills-row {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .status-pill {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .pill-green {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .pill-gold {
        background: rgba(234, 179, 8, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(234, 179, 8, 0.35);
    }

    /* User Message Bubble */
    .user-bubble-wrapper {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 20px;
    }
    .user-bubble {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(14px);
        border-radius: 20px 20px 4px 20px;
        padding: 12px 22px;
        color: #ffffff;
        font-size: 15px;
        font-weight: 500;
        max-width: 80%;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    /* Assistant Message Card */
    .assistant-card {
        background: rgba(18, 22, 34, 0.82);
        border: 1px solid rgba(255, 255, 255, 0.09);
        backdrop-filter: blur(24px);
        border-radius: 24px;
        padding: 24px 28px;
        margin-bottom: 28px;
        box-shadow: 0 8px 36px 0 rgba(0, 0, 0, 0.4);
    }
    .card-top-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;
    }
    .card-agent-badge {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .agent-avatar-glow {
        width: 36px;
        height: 36px;
        border-radius: 11px;
        background: linear-gradient(135deg, #00F0FF, #7000FF, #FF007A);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 17px;
        box-shadow: 0 0 16px rgba(0, 240, 255, 0.35);
    }
    .agent-title-text {
        font-size: 12px;
        font-weight: 700;
        color: #a78bfa;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .entity-tag-pill {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 9999px;
        padding: 2px 10px;
        font-size: 11px;
        color: #cbd5e1;
        font-weight: 500;
        margin-left: 6px;
    }
    .card-engine-pill {
        background: rgba(234, 179, 8, 0.12);
        border: 1px solid rgba(234, 179, 8, 0.3);
        border-radius: 9999px;
        padding: 4px 12px;
        font-size: 11px;
        font-weight: 600;
        color: #fbbf24;
    }
    .card-cache-pill {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 9999px;
        padding: 4px 12px;
        font-size: 11px;
        font-weight: 600;
        color: #10b981;
    }
    .natural-answer-text {
        font-size: 16px;
        color: #f8fafc;
        line-height: 1.6;
        margin-bottom: 18px;
    }

    /* Structured Table Styles */
    .table-details {
        margin: 14px 0;
    }
    .table-summary-btn {
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        font-weight: 600;
        color: #c084fc;
        margin-bottom: 10px;
        user-select: none;
    }
    .table-summary-btn:hover {
        color: #e9d5ff;
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        background: #0b0f19;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 13px;
    }
    .custom-table th {
        background: #111827;
        color: #38bdf8;
        padding: 10px 16px;
        text-align: left;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .custom-table td {
        padding: 10px 16px;
        color: #e2e8f0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .custom-table tr:last-child td {
        border-bottom: none;
    }
    .custom-table tr:hover {
        background: rgba(255, 255, 255, 0.02);
    }

    /* Chart Box */
    .chart-card-box {
        background: #0d121f;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px 20px;
        margin: 16px 0;
    }
    .chart-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #38bdf8;
        margin-bottom: 12px;
    }

    /* SQL Query Accordion */
    .sql-details {
        margin: 14px 0;
    }
    .sql-summary-btn {
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        font-weight: 600;
        color: #38bdf8;
        user-select: none;
    }
    .sql-summary-btn:hover {
        color: #7dd3fc;
    }
    .sql-code-box {
        background: #070a12;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 18px;
        margin-top: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        color: #38bdf8;
        line-height: 1.5;
        overflow-x: auto;
    }

    /* Bottom Action Bar */
    .card-footer-actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 18px;
        padding-top: 14px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    .helpful-label {
        font-size: 12px;
        color: #94a3b8;
        margin-right: 8px;
    }

    /* Streamlit Chat Input Styling */
    div[data-testid="stChatInput"] {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 860px;
        z-index: 999;
    }
    div[data-testid="stChatInput"] > div {
        background: rgba(18, 22, 34, 0.88) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 9999px !important;
        backdrop-filter: blur(20px) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #ffffff !important;
        font-size: 14px !important;
    }

    /* Quick Suggestion Chips Row */
    .quick-chips-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 24px;
    }
    .chip-btn {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 9999px;
        padding: 6px 14px;
        font-size: 12px;
        color: #cbd5e1;
        transition: all 0.2s ease;
    }
</style>

<!-- Ambient Background Blobs -->
<div class="bg-mesh-container">
    <div class="mesh-blob blob-1"></div>
    <div class="mesh-blob blob-2"></div>
    <div class="mesh-blob blob-3"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Top Navigation Bar
# ---------------------------------------------------------
st.markdown(f"""
<div class="top-nav">
    <div class="brand-title">
        <div class="brand-logo-icon">🚗</div>
        <div>
            <div>RAMP-GPT</div>
            <div style="font-size: 10px; font-weight: 400; color: #94a3b8;">Autonomous Garage Intelligence Engine</div>
        </div>
    </div>
    <div class="status-pills-row">
        <span class="status-pill pill-green">● MySQL Connected</span>
        <span class="status-pill pill-gold">⚡ {active_engine_name}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"

# ---------------------------------------------------------
# Quick Insight Prompts (Rendered as horizontal buttons)
# ---------------------------------------------------------
quick_options = [
    "How many workshops are there in the database?",
    "What is the total service amount for Volkswagen Virtus?",
    "Compare the average service cost for Audi and Toyota."
]

cols = st.columns(len(quick_options))
for idx, q_text in enumerate(quick_options):
    with cols[idx]:
        if st.button(q_text, key=f"quick_btn_{idx}", use_container_width=True):
            st.session_state.pending_query = q_text

# ---------------------------------------------------------
# Helper Functions to Render High-Fidelity Glassmorphic Cards
# ---------------------------------------------------------
def render_user_message(query: str):
    st.markdown(f"""
    <div class="user-bubble-wrapper">
        <div class="user-bubble">{query}</div>
    </div>
    """, unsafe_allow_html=True)

def render_chart_component(chart_info: dict, chart_id: str):
    """Renders Chart.js inside a responsive iframe matching the exact UI theme."""
    chart_type = chart_info.get("type", "bar")
    title = chart_info.get("title", "Metric Visualization")
    labels = chart_info.get("labels", [])
    datasets = chart_info.get("datasets", [])
    
    chart_config = {
        "type": chart_type if chart_type != "horizontalBar" else "bar",
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "options": {
            "indexAxis": "y" if chart_type == "horizontalBar" else "x",
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "labels": {
                        "color": "#94a3b8",
                        "font": {"family": "Inter", "size": 11}
                    }
                }
            },
            "scales": {
                "x": {
                    "grid": {"color": "rgba(255, 255, 255, 0.06)"},
                    "ticks": {"color": "#94a3b8", "font": {"family": "Inter", "size": 10}}
                },
                "y": {
                    "grid": {"color": "rgba(255, 255, 255, 0.06)"},
                    "ticks": {"color": "#94a3b8", "font": {"family": "Inter", "size": 10}}
                }
            }
        }
    }
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
            .chart-wrapper {{
                background: #0d121f;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 14px 18px;
                height: 220px;
                box-sizing: border-box;
            }}
            .chart-title {{
                color: #38bdf8;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .canvas-container {{
                height: 170px;
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="chart-wrapper">
            <div class="chart-title">📊 {title}</div>
            <div class="canvas-container">
                <canvas id="chart_{chart_id}"></canvas>
            </div>
        </div>
        <script>
            const ctx = document.getElementById('chart_{chart_id}').getContext('2d');
            new Chart(ctx, {json.dumps(chart_config)});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=240)

def render_table_component(table_info: dict):
    cols = table_info.get("columns", [])
    rows = table_info.get("rows", [])
    if not cols or not rows:
        return ""
        
    th_html = "".join([f"<th>{col}</th>" for col in cols])
    tr_html = ""
    for r in rows:
        td_html = "".join([f"<td>{val}</td>" for val in r])
        tr_html += f"<tr>{td_html}</tr>"
        
    return f"""
    <details class="table-details">
        <summary class="table-summary-btn">⊟ View Structured Table ({len(rows)} rows)</summary>
        <table class="custom-table">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{tr_html}</tbody>
        </table>
    </details>
    """

# ---------------------------------------------------------
# Render Message History
# ---------------------------------------------------------
for msg_idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        render_user_message(msg["content"])
    else:
        # Determine status badge
        engine_str = msg.get("engine", "qwen/qwen3.8-27b (Groq Cloud)")
        if msg.get("cached"):
            engine_pill_html = '<span class="card-cache-pill">⚡ Semantic Cache (&lt;1ms)</span>'
        else:
            engine_pill_html = f'<span class="card-engine-pill">⚡ {engine_str}</span>'
            
        entity_pill_html = ""
        if msg.get("context_entity"):
            entity_pill_html = f'<span class="entity-tag-pill">💬 {msg["context_entity"]}</span>'

        # Render outer assistant card header & answer
        st.markdown(f"""
        <div class="assistant-card">
            <div class="card-top-row">
                <div class="card-agent-badge">
                    <div class="agent-avatar-glow">✦</div>
                    <div>
                        <span class="agent-title-text">GARAGE INTELLIGENCE</span>
                        {entity_pill_html}
                    </div>
                </div>
                <div>{engine_pill_html}</div>
            </div>
            <div class="natural-answer-text">{msg['content']}</div>
        """, unsafe_allow_html=True)
        
        # Render Structured Table (if present)
        table_data = msg.get("table_data")
        if table_data:
            st.markdown(render_table_component(table_data), unsafe_allow_html=True)
            
        # Render Chart Component (if present)
        chart_data = msg.get("chart_data")
        if chart_data and isinstance(chart_data, dict):
            render_chart_component(chart_data, f"hist_{msg_idx}")
            
        # Render Collapsible SQL
        sql_text = msg.get("sql", "").strip()
        if sql_text:
            st.markdown(f"""
            <details class="sql-details">
                <summary class="sql-summary-btn">🗔 View Executed SQL</summary>
                <div class="sql-code-box">
                    <div style="font-size: 10px; color: #94a3b8; margin-bottom: 4px; text-transform: uppercase;">MYSQL QUERY</div>
                    {sql_text}
                </div>
            </details>
            """, unsafe_allow_html=True)
            
        # Render Action Buttons (Helpful Thumbs-Up & CSV Export)
        col_act1, col_act2, col_act3 = st.columns([2, 2, 6])
        with col_act1:
            if not msg.get("cached") and sql_text:
                if st.button("👍 Helpful", key=f"th_up_{msg_idx}"):
                    save_golden_query(msg.get("user_query", ""), sql_text)
                    st.success("Saved to Golden Queries!")
                    time.sleep(1)
                    st.rerun()
        with col_act2:
            if table_data:
                df = pd.DataFrame(table_data.get("rows", []), columns=table_data.get("columns", []))
                csv_bytes = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_bytes,
                    file_name="workshop_data.csv",
                    mime="text/csv",
                    key=f"csv_btn_{msg_idx}"
                )
                
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Chat Input & Query Execution
# ---------------------------------------------------------
input_query = st.chat_input("Ask a question about workshop operations, vehicles, billing, complaints...")

# Handle pending click from quick options
if "pending_query" in st.session_state and st.session_state.pending_query:
    input_query = st.session_state.pending_query
    st.session_state.pending_query = None

if input_query:
    # Append user question
    st.session_state.messages.append({
        "role": "user",
        "content": input_query
    })
    
    # Process with spinner
    with st.spinner("Analyzing schema & executing live query..."):
        start_time = time.time()
        try:
            res = process_sql_query(
                user_query=input_query,
                session_id=st.session_state.session_id,
                return_details=True
            )
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            
            if isinstance(res, dict):
                ans = res.get("answer", "No answer generated.")
                sql_q = res.get("sql", "")
                cached_hit = res.get("cached", False)
                chart_d = res.get("chart_data")
                table_d = res.get("table_data")
                pii_flag = res.get("pii_masked", False)
                engine_used = res.get("engine", active_engine_name)
                ctx_ent = res.get("context_entity")
            else:
                ans = str(res)
                sql_q = ""
                cached_hit = False
                chart_d = None
                table_d = None
                pii_flag = False
                engine_used = active_engine_name
                ctx_ent = None
                
            assistant_payload = {
                "role": "assistant",
                "content": ans,
                "sql": sql_q,
                "cached": cached_hit,
                "chart_data": chart_d,
                "table_data": table_d,
                "pii_masked": pii_flag,
                "engine": engine_used,
                "context_entity": ctx_ent,
                "execution_time_ms": elapsed_ms,
                "user_query": input_query
            }
            st.session_state.messages.append(assistant_payload)
            
            # Log audit event
            try:
                log_audit_event(
                    client_ip="127.0.0.1",
                    session_id=st.session_state.session_id,
                    user_query=input_query,
                    resolved_query=res.get("resolved_query") if isinstance(res, dict) else None,
                    generated_sql=sql_q,
                    execution_latency_ms=elapsed_ms,
                    pii_masked=pii_flag,
                    cache_hit=cached_hit,
                    row_count=table_d.get("total_rows", 1) if table_d else 1,
                    status_code=200,
                    engine=engine_used
                )
            except Exception:
                pass
                
            st.rerun()

        except Exception as err:
            st.error(f"Error processing query: {str(err)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Error: {str(err)}",
                "sql": ""
            })
            st.rerun()
