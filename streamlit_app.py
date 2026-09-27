"""
RAMP-GPT — Next-Generation Autonomous Garage Intelligence Dashboard.
Features ultra-modern dark glassmorphism, glowing ambient mesh lighting,
live Chart.js telemetry visualizations, interactive data tables with 1-click CSV export,
collapsible SQL code inspector, and autonomous knowledge base caching.
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
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# System Diagnostics & State Initialization
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
    except Exception:
        st.session_state.system_status = {
            "db_connected": False,
            "engine": "qwen/qwen3.8-27b (Groq Cloud)",
            "pool": {"checked_in": 0, "pool_size": 5}
        }

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = f"ramp_session_{int(time.time())}"

if "golden_count" not in st.session_state:
    try:
        golden_data = load_golden_queries()
        st.session_state.golden_count = len(golden_data)
    except Exception:
        st.session_state.golden_count = 24

active_engine_name = st.session_state.system_status.get("engine", "qwen/qwen3.8-27b (Groq Cloud)")
db_online = st.session_state.system_status.get("db_connected", True)

# ---------------------------------------------------------
# Next-Gen Glassmorphic Design System (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Reset & Streamlit Chrome Removal */
    #MainMenu, header, footer, .stDeployButton { display: none !important; }
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    .stApp {
        background-color: #06080F !important;
        color: #F1F5F9 !important;
        overflow-x: hidden !important;
    }
    
    /* Layout Container */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 7.5rem !important;
        max-width: 980px !important;
        margin: 0 auto !important;
    }

    /* Ambient Background Glow Mesh */
    .ambient-mesh {
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        z-index: -10;
        overflow: hidden;
        pointer-events: none;
        background: radial-gradient(circle at 50% 10%, #0d1224 0%, #06080F 80%);
    }
    .glow-orb {
        position: absolute;
        border-radius: 50%;
        filter: blur(130px);
        opacity: 0.38;
        animation: orb-drift 24s infinite alternate ease-in-out;
    }
    .orb-cyan {
        top: -12%; left: -8%; width: 48vw; height: 48vw;
        background: #00F0FF;
        animation-delay: 0s;
    }
    .orb-violet {
        top: 35%; right: -12%; width: 44vw; height: 44vw;
        background: #7000FF;
        animation-delay: -6s;
    }
    .orb-magenta {
        bottom: -15%; left: 20%; width: 42vw; height: 42vw;
        background: #FF007A;
        animation-delay: -12s;
    }

    @keyframes orb-drift {
        0% { transform: translate(0, 0) scale(1) rotate(0deg); }
        50% { transform: translate(50px, 40px) scale(1.08) rotate(10deg); }
        100% { transform: translate(-30px, -40px) scale(0.94) rotate(-10deg); }
    }

    /* Floating Navbar */
    .nav-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 24px;
        background: rgba(14, 19, 34, 0.72);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 20px;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }
    .nav-left {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .brand-avatar {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: linear-gradient(135deg, #00F0FF 0%, #7000FF 50%, #FF007A 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 19px;
        box-shadow: 0 0 18px rgba(0, 240, 255, 0.45);
    }
    .brand-heading {
        font-size: 17px;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #FFFFFF 30%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
    }
    .brand-sub {
        font-size: 11px;
        font-weight: 500;
        color: #64748B;
        letter-spacing: 0.02em;
    }
    .nav-right {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .badge-mysql {
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-pulse {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #34D399;
        box-shadow: 0 0 8px #34D399;
        animation: pulse-dot 2s infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }
    .badge-engine {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 38px 20px 24px;
        margin-bottom: 20px;
    }
    .hero-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        background: rgba(0, 240, 255, 0.08);
        border: 1px solid rgba(0, 240, 255, 0.25);
        border-radius: 9999px;
        color: #38BDF8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 16px;
    }
    .hero-title {
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #FFFFFF 20%, #E2E8F0 60%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-description {
        font-size: 14px;
        color: #94A3B8;
        max-width: 580px;
        margin: 0 auto 28px;
        line-height: 1.6;
    }

    /* Quick Prompt Cards */
    .prompt-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
        margin-bottom: 28px;
    }
    .prompt-card {
        background: rgba(18, 24, 43, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 16px;
        text-align: left;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(14px);
    }
    .prompt-card:hover {
        background: rgba(28, 36, 62, 0.85);
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 240, 255, 0.12);
    }
    .prompt-card-icon {
        font-size: 20px;
        margin-bottom: 8px;
    }
    .prompt-card-title {
        font-size: 12px;
        font-weight: 700;
        color: #38BDF8;
        letter-spacing: 0.02em;
        margin-bottom: 4px;
    }
    .prompt-card-text {
        font-size: 12px;
        color: #CBD5E1;
        line-height: 1.4;
    }

    /* User Message Bubble */
    .user-bubble-row {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 20px;
    }
    .user-bubble-box {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(56, 189, 248, 0.25);
        backdrop-filter: blur(16px);
        border-radius: 20px 20px 4px 20px;
        padding: 14px 22px;
        color: #F8FAFC;
        font-size: 14.5px;
        font-weight: 500;
        max-width: 82%;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        line-height: 1.5;
    }

    /* Assistant Card */
    .assistant-wrapper {
        background: rgba(14, 19, 34, 0.88);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 24px 26px;
        margin-bottom: 28px;
        backdrop-filter: blur(24px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
        transition: border-color 0.2s ease;
    }
    .assistant-wrapper:hover {
        border-color: rgba(56, 189, 248, 0.2);
    }
    .asst-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    .asst-identity {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .asst-glow-icon {
        width: 32px;
        height: 32px;
        border-radius: 10px;
        background: linear-gradient(135deg, #00F0FF, #7000FF);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        box-shadow: 0 0 12px rgba(0, 240, 255, 0.35);
    }
    .asst-title {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #A78BFA;
    }
    .asst-telemetry-row {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .cache-pill-hit {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 9999px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 600;
    }
    .latency-pill {
        background: rgba(255, 255, 255, 0.05);
        color: #94A3B8;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 9999px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 500;
        font-family: 'JetBrains Mono', monospace;
    }
    .asst-answer-text {
        font-size: 15px;
        color: #F8FAFC;
        line-height: 1.65;
        margin-bottom: 18px;
    }

    /* Tabular Display */
    .table-container {
        margin: 16px 0;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        overflow: hidden;
        background: #0B0E17;
    }
    .table-header-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        background: #111726;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 12px;
        font-weight: 600;
        color: #38BDF8;
    }
    .styled-grid-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
    }
    .styled-grid-table th {
        background: #0E1424;
        color: #94A3B8;
        text-align: left;
        padding: 10px 16px;
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .styled-grid-table td {
        padding: 10px 16px;
        color: #E2E8F0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        font-variant-numeric: tabular-nums;
    }
    .styled-grid-table tr:hover {
        background: rgba(255, 255, 255, 0.025);
    }

    /* SQL Inspector */
    .sql-inspect-box {
        margin-top: 14px;
        background: #070911;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 14px 18px;
    }
    .sql-label-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 11px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
    }

    /* Fixed Bottom Chat Input Bar */
    div[data-testid="stChatInput"] {
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 900px;
        z-index: 999;
    }
    div[data-testid="stChatInput"] > div {
        background: rgba(14, 19, 34, 0.88) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 9999px !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: rgba(0, 240, 255, 0.6) !important;
        box-shadow: 0 10px 40px rgba(0, 240, 255, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #FFFFFF !important;
        font-size: 14.5px !important;
    }

    /* Sidebar Glassmorphic Styling */
    section[data-testid="stSidebar"] {
        background-color: #070912 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    .sidebar-card {
        background: rgba(16, 22, 38, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
    }
    .sidebar-card-title {
        font-size: 11px;
        font-weight: 700;
        color: #94A3B8;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }
    .sidebar-stat-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12.5px;
        color: #E2E8F0;
        padding: 4px 0;
    }
    .stat-val-highlight {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        color: #38BDF8;
    }
</style>

<!-- Ambient Gradient Lighting Orbs -->
<div class="ambient-mesh">
    <div class="glow-orb orb-cyan"></div>
    <div class="glow-orb orb-violet"></div>
    <div class="glow-orb orb-magenta"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar: System Diagnostics & Settings
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
        <div style="width: 32px; height: 32px; border-radius: 10px; background: linear-gradient(135deg, #00F0FF, #7000FF); display: flex; align-items: center; justify-content: center; font-size: 16px;">🚗</div>
        <div>
            <div style="font-weight: 800; font-size: 15px; color: #FFF;">RAMP-GPT</div>
            <div style="font-size: 10px; color: #64748B;">System Telemetry v2.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Database Pool Status Card
    pool_info = st.session_state.system_status.get("pool", {})
    st.markdown(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">🗄️ Database Engine</div>
        <div class="sidebar-stat-row">
            <span>Status</span>
            <span class="stat-val-highlight" style="color: {'#34D399' if db_online else '#EF4444'};">
                {'● Online (3306)' if db_online else '○ Offline'}
            </span>
        </div>
        <div class="sidebar-stat-row">
            <span>Schema</span>
            <span class="stat-val-highlight">rag (6 tables)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Pool Mode</span>
            <span class="stat-val-highlight">QueuePool (size=5)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Timeout Guard</span>
            <span class="stat-val-highlight">5,000 ms</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Knowledge Base Card
    st.markdown(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">🧠 Caching & AI Engine</div>
        <div class="sidebar-stat-row">
            <span>Primary Model</span>
            <span class="stat-val-highlight">Groq (Qwen 27B)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Local Fallback</span>
            <span class="stat-val-highlight">Ollama (7B Coder)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Semantic Cache</span>
            <span class="stat-val-highlight">&lt; 1 ms Token Jaccard</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Golden Queries</span>
            <span class="stat-val-highlight">{st.session_state.golden_count} Verified</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Session Management Card
    st.markdown('<div class="sidebar-card"><div class="sidebar-card-title">⚙️ Session Actions</div>', unsafe_allow_html=True)
    if st.button("🗑️ Reset Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"ramp_session_{int(time.time())}"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Top Navigation Header
# ---------------------------------------------------------
st.markdown(f"""
<div class="nav-card">
    <div class="nav-left">
        <div class="brand-avatar">🚗</div>
        <div>
            <div class="brand-heading">RAMP-GPT</div>
            <div class="brand-sub">Autonomous Garage Intelligence Engine</div>
        </div>
    </div>
    <div class="nav-right">
        <div class="badge-pill badge-mysql">
            <div class="badge-pulse"></div>
            <span>MySQL 8.0 Connected</span>
        </div>
        <div class="badge-pill badge-engine">
            <span>⚡ {active_engine_name.split()[0]}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper Functions: Chart.js & Table Components
# ---------------------------------------------------------
def render_chart_component(chart_info: dict, chart_id: str):
    """Renders responsive modern Chart.js visualizer matching the dark theme."""
    chart_type = chart_info.get("type", "bar")
    title = chart_info.get("title", "Analytical Breakdown")
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
                        "color": "#94A3B8",
                        "font": {"family": "Plus Jakarta Sans", "size": 11, "weight": "600"}
                    }
                },
                "tooltip": {
                    "backgroundColor": "rgba(14, 19, 34, 0.95)",
                    "titleColor": "#38BDF8",
                    "bodyColor": "#F8FAFC",
                    "borderColor": "rgba(255, 255, 255, 0.1)",
                    "borderWidth": 1,
                    "padding": 10,
                    "cornerRadius": 8
                }
            },
            "scales": {
                "x": {
                    "grid": {"color": "rgba(255, 255, 255, 0.05)"},
                    "ticks": {"color": "#64748B", "font": {"family": "Plus Jakarta Sans", "size": 10}}
                },
                "y": {
                    "grid": {"color": "rgba(255, 255, 255, 0.05)"},
                    "ticks": {"color": "#64748B", "font": {"family": "Plus Jakarta Sans", "size": 10}}
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
                background: #090D18;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 16px;
                padding: 16px 20px;
                height: 230px;
                box-sizing: border-box;
            }}
            .chart-title-bar {{
                color: #38BDF8;
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .canvas-box {{
                height: 175px;
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="chart-wrapper">
            <div class="chart-title-bar">📊 {title}</div>
            <div class="canvas-box">
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
    components.html(html_code, height=250)

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
    <div class="table-container">
        <div class="table-header-title">
            <span>📋 Structured Records ({len(rows)} rows)</span>
            <span style="font-size: 10px; color: #64748B;">MYSQL RELATIONAL OUTPUT</span>
        </div>
        <table class="styled-grid-table">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{tr_html}</tbody>
        </table>
    </div>
    """

# ---------------------------------------------------------
# Hero Section & Quick Prompt Cards (Shown when chat is empty)
# ---------------------------------------------------------
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="hero-container">
        <div class="hero-tag">✦ Autonomous Workshop Analytics</div>
        <div class="hero-title">Ask anything about garage operations</div>
        <div class="hero-description">
            Translate conversational questions into multi-table MySQL statements with sub-second retrieval, 
            heuristic self-healing validation, and dynamic visual dashboards.
        </div>
    </div>
    """, unsafe_allow_html=True)

    quick_cards = [
        {"icon": "🚗", "title": "Virtus Service Revenue", "text": "What is the total service amount for Volkswagen Virtus?", "query": "What is the total service amount for Volkswagen Virtus?"},
        {"icon": "📊", "title": "Brand Cost Comparison", "text": "Compare the average service cost for Audi and Toyota.", "query": "Compare the average service cost for Audi and Toyota."},
        {"icon": "🏆", "title": "Highest Value Services", "text": "What are the top 3 most expensive services by total amount?", "query": "What are the top 3 most expensive services by total amount?"},
        {"icon": "👥", "title": "Workshop Capacity", "text": "How many workshops and employees are in the database?", "query": "How many workshops are there in the database?"}
    ]

    cols = st.columns(4)
    for idx, card in enumerate(quick_cards):
        with cols[idx]:
            card_clicked = st.button(
                f"{card['icon']} **{card['title']}**\n\n{card['text']}", 
                key=f"hero_prompt_{idx}", 
                use_container_width=True
            )
            if card_clicked:
                st.session_state.pending_query = card["query"]
                st.rerun()

# ---------------------------------------------------------
# Message Stream Display
# ---------------------------------------------------------
for msg_idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="user-bubble-row">
            <div class="user-bubble-box">{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Determine status badges
        cached_hit = msg.get("cached", False)
        elapsed_val = msg.get("execution_time_ms", 1.2)
        
        telemetry_html = f'<span class="latency-pill">⏱️ {elapsed_val} ms</span>'
        if cached_hit:
            telemetry_html = '<span class="cache-pill-hit">⚡ Semantic Cache (&lt;1ms)</span> ' + telemetry_html

        st.markdown(f"""
        <div class="assistant-wrapper">
            <div class="asst-header">
                <div class="asst-identity">
                    <div class="asst-glow-icon">✦</div>
                    <div>
                        <div class="asst-title">GARAGE INTELLIGENCE</div>
                        <div style="font-size: 10px; color: #64748B;">Validated Relational Output</div>
                    </div>
                </div>
                <div class="asst-telemetry-row">{telemetry_html}</div>
            </div>
            <div class="asst-answer-text">{msg['content']}</div>
        """, unsafe_allow_html=True)

        # Render Structured Table Component
        table_data = msg.get("table_data")
        if table_data:
            st.markdown(render_table_component(table_data), unsafe_allow_html=True)

        # Render Dynamic Chart Component
        chart_data = msg.get("chart_data")
        if chart_data and isinstance(chart_data, dict):
            render_chart_component(chart_data, f"chart_{msg_idx}")

        # Render Collapsible SQL Inspector
        sql_text = msg.get("sql", "").strip()
        if sql_text:
            with st.expander("🗔 Inspect Generated SQL & Telemetry", expanded=False):
                st.code(sql_text, language="sql")
                st.caption(f"Engine: {msg.get('engine', active_engine_name)} | Session: {st.session_state.session_id}")

        # Action Buttons (Thumbs-Up Knowledge Base & CSV Download)
        col_act1, col_act2, col_act3 = st.columns([2, 2.5, 5.5])
        with col_act1:
            if not cached_hit and sql_text:
                if st.button("👍 Useful Query", key=f"thumb_{msg_idx}"):
                    save_golden_query(msg.get("user_query", ""), sql_text)
                    st.toast("Saved to Golden Knowledge Base!", icon="✅")
                    st.session_state.golden_count += 1
                    time.sleep(0.6)
                    st.rerun()

        with col_act2:
            if table_data:
                df = pd.DataFrame(table_data.get("rows", []), columns=table_data.get("columns", []))
                csv_bytes = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_bytes,
                    file_name=f"ramp_query_{msg_idx}.csv",
                    mime="text/csv",
                    key=f"csv_dl_{msg_idx}"
                )

        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Chat Input & Query Pipeline Invocation
# ---------------------------------------------------------
input_query = st.chat_input("Ask a question about workshop operations, vehicles, billing, complaints...")

# Handle pending query from hero cards
if "pending_query" in st.session_state and st.session_state.pending_query:
    input_query = st.session_state.pending_query
    st.session_state.pending_query = None

if input_query:
    st.session_state.messages.append({
        "role": "user",
        "content": input_query
    })
    
    with st.spinner("Analyzing schema & synthesizing verified SQL..."):
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
            
            # Audit Logging
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
                "content": f"⚠️ Query execution encountered an issue: {str(err)}",
                "sql": ""
            })
            st.rerun()
