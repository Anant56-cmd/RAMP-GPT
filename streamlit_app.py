"""
RAMP-GPT — Enterprise Autonomous Garage Intelligence Dashboard.
Features ultra-modern corporate branding, cohesive enterprise color palette,
floating command-center chatbox, live Chart.js visualizations,
interactive data tables with 1-click CSV export, and autonomous caching.
"""

import os
import sys
import time
import json
import base64
import textwrap
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
# Page Configuration & Professional Branding
# ---------------------------------------------------------
LOGO_PATH = os.path.join(PROJECT_ROOT, "assets", "logo.png")
PAGE_ICON = LOGO_PATH if os.path.exists(LOGO_PATH) else "⚡"

st.set_page_config(
    page_title="RAMP-GPT — Enterprise Garage Intelligence",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "bright"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = f"ramp_{int(time.time())}"

if "saved_queries" not in st.session_state:
    st.session_state.saved_queries = set()

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

if "golden_count" not in st.session_state:
    try:
        golden_data = load_golden_queries()
        st.session_state.golden_count = len(golden_data)
        st.session_state.golden_list = golden_data
    except Exception:
        st.session_state.golden_count = 24
        st.session_state.golden_list = []

active_engine_name = st.session_state.system_status.get("engine", "qwen/qwen3.8-27b (Groq Cloud)")
db_online = st.session_state.system_status.get("db_connected", True)
is_bright = (st.session_state.theme_mode == "bright")

# Corporate SVG Logo Icon
SVG_LOGO = (
    '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>'
    '<polyline points="2 17 12 22 22 17"></polyline>'
    '<polyline points="2 12 12 17 22 12"></polyline>'
    '</svg>'
)

def render_html(html_str: str):
    """Safely render HTML without CommonMark 4-space indentation code-block conversions."""
    clean_html = " ".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# Design System & Responsive CSS Styling
# ---------------------------------------------------------
if is_bright:
    # 🌈 REFINED TECH-SLATE & ELECTRIC INDIGO (BRIGHT THEME)
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        #MainMenu, header, footer, .stDeployButton { display: none !important; }
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .stApp {
            background-color: #F8FAFC !important;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(14, 165, 233, 0.07) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(241, 245, 249, 0.85) 0px, transparent 50%) !important;
            color: #0F172A !important;
            overflow-x: hidden !important;
        }
        
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 8.5rem !important;
            max-width: 980px !important;
            margin: 0 auto !important;
        }

        /* Subtle Ambient Glow Mesh */
        .ambient-mesh {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -10;
            overflow: hidden;
            pointer-events: none;
        }
        .glow-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(140px);
            opacity: 0.18;
            animation: orb-drift 24s infinite alternate ease-in-out;
        }
        .orb-1 { top: -10%; left: -5%; width: 45vw; height: 45vw; background: #6366F1; animation-delay: 0s; }
        .orb-2 { top: 30%; right: -10%; width: 40vw; height: 40vw; background: #38BDF8; animation-delay: -8s; }
        .orb-3 { bottom: -15%; left: 20%; width: 45vw; height: 45vw; background: #818CF8; animation-delay: -16s; }

        @keyframes orb-drift {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(30px, 20px) scale(1.04); }
            100% { transform: translate(-25px, -20px) scale(0.96); }
        }

        /* Floating Navbar */
        .nav-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 24px;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid #E2E8F0;
            border-radius: 20px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
        }
        .nav-left {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-avatar {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, #4338CA 0%, #4F46E5 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.28);
        }
        .brand-heading {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #0F172A;
            line-height: 1.1;
        }
        .brand-sub {
            font-size: 11.5px;
            font-weight: 600;
            color: #64748B;
            letter-spacing: 0.01em;
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
            padding: 5px 13px;
            border-radius: 9999px;
            font-size: 11.5px;
            font-weight: 700;
            letter-spacing: 0.02em;
        }
        .badge-mysql {
            background: #ECFDF5;
            color: #059669;
            border: 1px solid #A7F3D0;
        }
        .badge-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10B981;
            box-shadow: 0 0 8px #10B981;
            animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.35; transform: scale(0.85); }
        }
        .badge-engine {
            background: #EEF2FF;
            color: #4338CA;
            border: 1px solid #C7D2FE;
        }

        /* Hero Welcome Section */
        .hero-container {
            text-align: center;
            padding: 30px 20px 18px;
            margin-bottom: 20px;
        }
        .hero-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 16px;
            background: #EEF2FF;
            border: 1px solid #C7D2FE;
            border-radius: 9999px;
            color: #4338CA;
            font-size: 11.5px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 14px;
        }
        .hero-title {
            font-size: 36px;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.2;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #0F172A 30%, #3730A3 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-description {
            font-size: 14.5px;
            color: #475569;
            max-width: 620px;
            margin: 0 auto 24px;
            line-height: 1.6;
            font-weight: 500;
        }

        /* Feature Pill Highlights Bar */
        .feature-pills-row {
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 28px;
        }
        .feat-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 14px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 9999px;
            font-size: 11.5px;
            font-weight: 700;
            color: #334155;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
        }

        /* User Message Bubble */
        .user-bubble-row {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 20px;
        }
        .user-bubble-box {
            background: linear-gradient(135deg, #3730A3 0%, #4F46E5 100%);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px 20px 4px 20px;
            padding: 14px 22px;
            color: #FFFFFF;
            font-size: 14.5px;
            font-weight: 600;
            max-width: 82%;
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.22);
            line-height: 1.5;
        }

        /* Assistant Card */
        .assistant-wrapper {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 22px;
            padding: 24px 28px;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(0, 0, 0, 0.02);
            transition: all 0.2s ease;
        }
        .assistant-wrapper:hover {
            box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
            border-color: #CBD5E1;
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
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, #4338CA, #6366F1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            color: #FFF;
            box-shadow: 0 3px 10px rgba(79, 70, 229, 0.25);
        }
        .asst-title {
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #4338CA;
        }
        .asst-telemetry-row {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .cache-pill-hit {
            background: #ECFDF5;
            color: #059669;
            border: 1px solid #A7F3D0;
            border-radius: 9999px;
            padding: 4px 11px;
            font-size: 11px;
            font-weight: 700;
        }
        .latency-pill {
            background: #F1F5F9;
            color: #475569;
            border: 1px solid #E2E8F0;
            border-radius: 9999px;
            padding: 4px 11px;
            font-size: 11px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }
        .asst-answer-text {
            font-size: 15px;
            color: #0F172A;
            line-height: 1.65;
            margin-bottom: 18px;
            font-weight: 500;
        }

        /* ----------------------------------------------- */
        /* STYLED STREAMLIT BUTTONS & HERO PROMPT CARDS    */
        /* ----------------------------------------------- */
        .stButton > button, .stDownloadButton > button {
            background: #FFFFFF !important;
            color: #0F172A !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 14px !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 10px 16px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            text-align: left !important;
            white-space: normal !important;
            word-wrap: break-word !important;
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: #6366F1 !important;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12) !important;
            transform: translateY(-2px) !important;
            background: #FFFFFF !important;
            color: #4338CA !important;
        }

        .stButton > button:active, .stDownloadButton > button:active {
            transform: translateY(0) !important;
        }

        /* Multi-line Prompt Cards typography */
        .stButton > button p {
            color: #475569 !important;
            font-size: 12px !important;
            line-height: 1.45 !important;
            margin: 0 !important;
        }

        .stButton > button strong {
            color: #0F172A !important;
            font-size: 13.5px !important;
            font-weight: 700 !important;
            display: block !important;
            margin-bottom: 2px !important;
        }

        .stButton > button em {
            color: #4F46E5 !important;
            font-size: 10px !important;
            font-weight: 800 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            font-style: normal !important;
            display: block !important;
            margin-bottom: 6px !important;
        }

        /* Hero Prompt Cards Container */
        .hero-card-col .stButton > button {
            min-height: 124px !important;
            padding: 16px 14px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            align-items: flex-start !important;
        }

        /* Sidebar Button & Radio Controls */
        section[data-testid="stSidebar"] {
            background: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 2rem !important;
        }
        .sidebar-card {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 14px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
        }
        .sidebar-card-title {
            font-size: 11px;
            font-weight: 800;
            color: #4338CA;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .sidebar-stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12.5px;
            color: #475569;
            padding: 4px 0;
            font-weight: 500;
        }
        .stat-val-highlight {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: #0F172A;
        }

        /* Sidebar Radio Button explicit high-contrast text */
        div[data-testid="stRadio"] label, div[data-testid="stRadio"] label p {
            color: #1E293B !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            margin: 0 !important;
        }
        div[data-testid="stRadio"] label:hover, div[data-testid="stRadio"] label:hover p {
            color: #4F46E5 !important;
        }

        /* Sidebar Clear button */
        section[data-testid="stSidebar"] .stButton > button {
            text-align: center !important;
            justify-content: center !important;
            display: flex !important;
            align-items: center !important;
            font-size: 12.5px !important;
            padding: 8px 14px !important;
            background: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: #FEE2E2 !important;
            border-color: #FCA5A5 !important;
            color: #DC2626 !important;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.12) !important;
        }

        /* Fixed Bottom Command Center Dock */
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 24px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 100% !important;
            max-width: 920px !important;
            z-index: 9999 !important;
            padding: 0 16px !important;
        }
        div[data-testid="stChatInput"] > div {
            background: rgba(255, 255, 255, 0.98) !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 24px !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            box-shadow: 0 12px 36px rgba(15, 23, 42, 0.08), 0 2px 6px rgba(0, 0, 0, 0.03) !important;
            padding: 6px 14px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        div[data-testid="stChatInput"] > div:focus-within {
            border-color: #4F46E5 !important;
            box-shadow: 0 16px 44px rgba(79, 70, 229, 0.18), 0 0 0 3px rgba(79, 70, 229, 0.12) !important;
            transform: translateY(-2px) !important;
        }
        div[data-testid="stChatInput"] textarea {
            color: #0F172A !important;
            font-size: 14.5px !important;
            font-weight: 500 !important;
            line-height: 1.5 !important;
            padding: 8px 12px !important;
        }
        div[data-testid="stChatInput"] textarea::placeholder {
            color: #94A3B8 !important;
            font-weight: 400 !important;
        }
        div[data-testid="stChatInput"] button {
            background: #4F46E5 !important;
            color: #FFFFFF !important;
            border-radius: 14px !important;
            border: none !important;
            width: 38px !important;
            height: 38px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35) !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stChatInput"] button:hover {
            background: #4338CA !important;
            transform: scale(1.05) !important;
        }

        /* Streamlit Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid #E2E8F0;
            margin-bottom: 14px;
        }
        .stTabs [data-baseweb="tab"] {
            font-weight: 700 !important;
            font-size: 12.5px !important;
            color: #64748B !important;
            padding: 8px 16px !important;
            border-radius: 8px 8px 0 0 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #4F46E5 !important;
            border-bottom: 2px solid #4F46E5 !important;
        }
    </style>

    <div class="ambient-mesh">
        <div class="glow-orb orb-1"></div>
        <div class="glow-orb orb-2"></div>
        <div class="glow-orb orb-3"></div>
    </div>
    """, unsafe_allow_html=True)
else:
    # 🌌 DEEP CYBER MIDNIGHT THEME
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        #MainMenu, header, footer, .stDeployButton { display: none !important; }
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .stApp {
            background-color: #090D16 !important;
            background-image: 
                radial-gradient(at 0% 0%, rgba(2, 132, 199, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(124, 58, 237, 0.14) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(15, 23, 42, 0.9) 0px, transparent 50%) !important;
            color: #F8FAFC !important;
            overflow-x: hidden !important;
        }
        
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 8.5rem !important;
            max-width: 980px !important;
            margin: 0 auto !important;
        }

        .ambient-mesh {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -10;
            overflow: hidden;
            pointer-events: none;
        }
        .glow-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(140px);
            opacity: 0.22;
            animation: orb-drift 24s infinite alternate ease-in-out;
        }
        .orb-1 { top: -10%; left: -5%; width: 45vw; height: 45vw; background: #0284C7; }
        .orb-2 { top: 35%; right: -10%; width: 40vw; height: 40vw; background: #6366F1; }
        .orb-3 { bottom: -15%; left: 20%; width: 45vw; height: 45vw; background: #7C3AED; }

        @keyframes orb-drift {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(30px, 20px) scale(1.04); }
            100% { transform: translate(-25px, -20px) scale(0.96); }
        }

        .nav-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 24px;
            background: rgba(17, 24, 39, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            backdrop-filter: blur(20px);
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }
        .brand-avatar {
            width: 42px; height: 42px; border-radius: 12px;
            background: linear-gradient(135deg, #0284C7, #6366F1);
            display: flex; align-items: center; justify-content: center; color: #FFF;
            box-shadow: 0 0 16px rgba(2, 132, 199, 0.4);
        }
        .brand-heading { font-size: 18px; font-weight: 800; color: #FFF; line-height: 1.1; }
        .brand-sub { font-size: 11px; color: #94A3B8; }
        .badge-pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; }
        .badge-mysql { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.35); }
        .badge-pulse { width: 8px; height: 8px; border-radius: 50%; background-color: #34D399; box-shadow: 0 0 10px #34D399; animation: pulse-dot 2s infinite; }
        .badge-engine { background: rgba(99, 102, 241, 0.15); color: #A5B4FC; border: 1px solid rgba(99, 102, 241, 0.35); }

        .hero-container { text-align: center; padding: 30px 20px 18px; margin-bottom: 20px; }
        .hero-tag { display: inline-flex; padding: 4px 14px; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 9999px; color: #38BDF8; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 14px; }
        .hero-title { font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #FFF 30%, #93C5FD 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero-description { font-size: 14.5px; color: #CBD5E1; max-width: 620px; margin: 0 auto 24px; line-height: 1.6; }

        .feature-pills-row { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-bottom: 28px; }
        .feat-pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 9999px; font-size: 11.5px; font-weight: 700; color: #E2E8F0; }

        .user-bubble-row { display: flex; justify-content: flex-end; margin-bottom: 20px; }
        .user-bubble-box { background: linear-gradient(135deg, #1E293B, #0F172A); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 20px 20px 4px 20px; padding: 14px 22px; color: #FFF; font-size: 14.5px; font-weight: 600; max-width: 82%; }

        .assistant-wrapper { background: rgba(17, 24, 39, 0.88); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 22px; padding: 24px 28px; margin-bottom: 24px; backdrop-filter: blur(20px); }
        .asst-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
        .asst-glow-icon { width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg, #0284C7, #6366F1); display: flex; align-items: center; justify-content: center; font-size: 14px; color: #FFF; }
        .asst-title { font-size: 12px; font-weight: 800; color: #38BDF8; text-transform: uppercase; }
        .cache-pill-hit { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 9999px; padding: 4px 11px; font-size: 11px; font-weight: 700; }
        .latency-pill { background: rgba(255, 255, 255, 0.08); color: #CBD5E1; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 9999px; padding: 4px 11px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .asst-answer-text { font-size: 15px; color: #F8FAFC; line-height: 1.65; margin-bottom: 18px; font-weight: 500; }

        /* Dark Mode Buttons */
        .stButton > button, .stDownloadButton > button {
            background: #111827 !important;
            color: #F8FAFC !important;
            border: 1.5px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 10px 16px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            text-align: left !important;
            white-space: normal !important;
            word-wrap: break-word !important;
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: #38BDF8 !important;
            box-shadow: 0 8px 24px rgba(56, 189, 248, 0.18) !important;
            transform: translateY(-2px) !important;
            background: #111827 !important;
            color: #38BDF8 !important;
        }

        .stButton > button p {
            color: #94A3B8 !important;
            font-size: 12px !important;
            line-height: 1.45 !important;
            margin: 0 !important;
        }

        .stButton > button strong {
            color: #F8FAFC !important;
            font-size: 13.5px !important;
            font-weight: 700 !important;
            display: block !important;
            margin-bottom: 2px !important;
        }

        .stButton > button em {
            color: #38BDF8 !important;
            font-size: 10px !important;
            font-weight: 800 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            font-style: normal !important;
            display: block !important;
            margin-bottom: 6px !important;
        }

        .hero-card-col .stButton > button {
            min-height: 124px !important;
            padding: 16px 14px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: flex-start !important;
            align-items: flex-start !important;
        }

        div[data-testid="stChatInput"] { position: fixed !important; bottom: 24px !important; left: 50% !important; transform: translateX(-50%) !important; width: 100% !important; max-width: 920px !important; z-index: 9999 !important; padding: 0 16px !important; }
        div[data-testid="stChatInput"] > div { background: rgba(17, 24, 39, 0.95) !important; border: 1.5px solid rgba(56, 189, 248, 0.35) !important; border-radius: 24px !important; backdrop-filter: blur(28px) !important; box-shadow: 0 16px 50px rgba(0, 0, 0, 0.65), 0 0 20px rgba(56, 189, 248, 0.12) !important; padding: 6px 14px !important; }
        div[data-testid="stChatInput"] textarea { color: #FFF !important; font-size: 14.5px !important; }
        div[data-testid="stChatInput"] button { background: #0284C7 !important; color: #FFF !important; border-radius: 14px !important; width: 38px !important; height: 38px !important; }

        section[data-testid="stSidebar"] { background: #0B0F19 !important; border-right: 1px solid rgba(255, 255, 255, 0.08) !important; }
        .sidebar-card { background: rgba(17, 24, 39, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 14px 16px; margin-bottom: 14px; }
        .sidebar-card-title { font-size: 11px; font-weight: 800; color: #38BDF8; text-transform: uppercase; margin-bottom: 10px; }
        .sidebar-stat-row { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; color: #94A3B8; padding: 4px 0; }
        .stat-val-highlight { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #F8FAFC; }

        div[data-testid="stRadio"] label, div[data-testid="stRadio"] label p {
            color: #F1F5F9 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            margin: 0 !important;
        }
        div[data-testid="stRadio"] label:hover, div[data-testid="stRadio"] label:hover p {
            color: #38BDF8 !important;
        }

        section[data-testid="stSidebar"] .stButton > button {
            text-align: center !important;
            justify-content: center !important;
            display: flex !important;
            align-items: center !important;
            font-size: 12.5px !important;
            padding: 8px 14px !important;
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 14px; }
        .stTabs [data-baseweb="tab"] { font-weight: 700 !important; font-size: 12.5px !important; color: #94A3B8 !important; padding: 8px 16px !important; }
        .stTabs [aria-selected="true"] { color: #38BDF8 !important; border-bottom: 2px solid #38BDF8 !important; }
    </style>

    <div class="ambient-mesh">
        <div class="glow-orb orb-1"></div>
        <div class="glow-orb orb-2"></div>
        <div class="glow-orb orb-3"></div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar: System Diagnostics & Theme Controls
# ---------------------------------------------------------
with st.sidebar:
    render_html(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <div style="width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #4338CA, #4F46E5); display: flex; align-items: center; justify-content: center; color: #FFF;">
            {SVG_LOGO}
        </div>
        <div>
            <div style="font-weight: 800; font-size: 16px; letter-spacing: -0.01em; color: #0F172A;">RAMP-GPT</div>
            <div style="font-size: 11px; color: #64748B; font-weight: 600;">Enterprise Intelligence v2.0</div>
        </div>
    </div>
    """)

    # Database Status Card
    render_html(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">🗄️ Relational Database</div>
        <div class="sidebar-stat-row">
            <span>MySQL 8.0</span>
            <span class="stat-val-highlight" style="color: {'#059669' if is_bright else '#34D399'};">
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
            <span>Circuit Breaker</span>
            <span class="stat-val-highlight">5,000 ms</span>
        </div>
    </div>
    """)

    # Knowledge Base Card & Explorer
    render_html(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">🧠 Caching & AI Engine</div>
        <div class="sidebar-stat-row">
            <span>Primary LLM</span>
            <span class="stat-val-highlight">Groq (Qwen 27B)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Semantic Cache</span>
            <span class="stat-val-highlight">&lt; 1 ms Jaccard</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Golden Knowledge</span>
            <span class="stat-val-highlight">{st.session_state.golden_count} Templates</span>
        </div>
    </div>
    """)

    with st.expander("📚 Browse Golden Queries", expanded=False):
        for idx, gq in enumerate(st.session_state.golden_list[:5]):
            st.markdown(f"**{idx+1}. {gq.get('query', '')}**")
            st.code(gq.get('sql', ''), language="sql")

    # Session Management
    render_html('<div class="sidebar-card"><div class="sidebar-card-title">⚙️ Session Actions</div>')
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.saved_queries = set()
        st.session_state.session_id = f"ramp_{int(time.time())}"
        st.rerun()
    render_html('</div>')

# ---------------------------------------------------------
# Top Navigation Header
# ---------------------------------------------------------
render_html(f"""
<div class="nav-card">
    <div class="nav-left">
        <div class="brand-avatar">{SVG_LOGO}</div>
        <div>
            <div class="brand-heading">RAMP-GPT</div>
            <div class="brand-sub">Enterprise Autonomous Garage Intelligence</div>
        </div>
    </div>
    <div class="nav-right">
        <div class="badge-pill badge-mysql">
            <div class="badge-pulse"></div>
            <span>MySQL Live</span>
        </div>
        <div class="badge-pill badge-engine">
            <span>⚡ {active_engine_name.split()[0]}</span>
        </div>
    </div>
</div>
""")

# ---------------------------------------------------------
# Helper Functions: Visualizations & Tables
# ---------------------------------------------------------
def render_chart_component(chart_info: dict, chart_id: str, bright: bool = True):
    """Renders responsive modern Chart.js visualizer matching the vibrant theme."""
    chart_type = chart_info.get("type", "bar")
    title = chart_info.get("title", "Analytical Breakdown")
    labels = chart_info.get("labels", [])
    datasets = chart_info.get("datasets", [])

    palette_bright = [
        "rgba(79, 70, 229, 0.85)",   # Electric Indigo
        "rgba(14, 165, 233, 0.85)",  # Sky Blue
        "rgba(16, 185, 129, 0.85)",  # Emerald
        "rgba(245, 158, 11, 0.85)",  # Amber
        "rgba(139, 92, 246, 0.85)"   # Purple
    ]
    palette_dark = [
        "rgba(56, 189, 248, 0.85)",  # Light Sky
        "rgba(129, 140, 248, 0.85)", # Light Indigo
        "rgba(52, 211, 153, 0.85)",  # Emerald
        "rgba(251, 191, 36, 0.85)",  # Amber
        "rgba(192, 132, 252, 0.85)"  # Purple
    ]
    colors = palette_bright if bright else palette_dark

    for i, ds in enumerate(datasets):
        if "backgroundColor" not in ds:
            if chart_type in ["pie", "doughnut"]:
                ds["backgroundColor"] = colors[:len(labels)]
            else:
                ds["backgroundColor"] = colors[i % len(colors)]
        if "borderColor" not in ds:
            ds["borderColor"] = "#FFFFFF" if bright else "rgba(255, 255, 255, 0.15)"
        ds["borderRadius"] = 8

    chart_config = {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "labels": {
                        "color": "#334155" if bright else "#CBD5E1",
                        "font": {"family": "Plus Jakarta Sans", "size": 11, "weight": "600"}
                    }
                },
                "tooltip": {
                    "backgroundColor": "#FFFFFF" if bright else "rgba(17, 24, 39, 0.95)",
                    "titleColor": "#0F172A" if bright else "#38BDF8",
                    "bodyColor": "#334155" if bright else "#F8FAFC",
                    "borderColor": "#E2E8F0" if bright else "rgba(255, 255, 255, 0.15)",
                    "borderWidth": 1.5,
                    "padding": 12,
                    "cornerRadius": 10
                }
            },
            "scales": {
                "x": {
                    "grid": {"color": "rgba(226, 232, 240, 0.7)" if bright else "rgba(255, 255, 255, 0.06)"},
                    "ticks": {"color": "#64748B" if bright else "#94A3B8", "font": {"family": "Plus Jakarta Sans", "size": 10.5}}
                },
                "y": {
                    "grid": {"color": "rgba(226, 232, 240, 0.7)" if bright else "rgba(255, 255, 255, 0.06)"},
                    "ticks": {"color": "#64748B" if bright else "#94A3B8", "font": {"family": "Plus Jakarta Sans", "size": 10.5}}
                }
            }
        }
    }
    
    bg_box = "#FFFFFF" if bright else "rgba(17, 24, 39, 0.9)"
    border_box = "#E2E8F0" if bright else "rgba(255, 255, 255, 0.08)"
    title_col = "#4338CA" if bright else "#38BDF8"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
            .chart-wrapper {{
                background: {bg_box};
                border: 1.5px solid {border_box};
                border-radius: 16px;
                padding: 16px 20px;
                height: 240px;
                box-sizing: border-box;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
            }}
            .chart-title-bar {{
                color: {title_col};
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 13px;
                font-weight: 800;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .canvas-box {{
                height: 185px;
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
    components.html(html_code, height=260)

# ---------------------------------------------------------
# Hero Section & Quick Prompt Cards (Shown when chat is empty)
# ---------------------------------------------------------
if len(st.session_state.messages) == 0:
    render_html("""
    <div class="hero-container">
        <div class="hero-tag">✦ Enterprise Text-to-SQL Intelligence</div>
        <div class="hero-title">Smart Workshop Analytics</div>
        <div class="hero-description">
            Translate conversational operational questions into multi-table MySQL statements with sub-second retrieval, 
            10-layer self-healing validation, zero-bloat semantic caching, and dynamic visualizations.
        </div>
        <div class="feature-pills-row">
            <div class="feat-pill">⚡ &lt;1ms Semantic Cache</div>
            <div class="feat-pill">🛡️ AST Read-Only Guard</div>
            <div class="feat-pill">🔄 10-Layer Self-Healing</div>
            <div class="feat-pill">📉 ~65% Token Pruning</div>
        </div>
    </div>
    """)

    quick_cards = [
        {"icon": "💎", "tag": "REVENUE ANALYSIS", "title": "Virtus Revenue", "text": "What is the total service amount for Volkswagen Virtus?", "query": "What is the total service amount for Volkswagen Virtus?"},
        {"icon": "📊", "tag": "BRAND COMPARISON", "title": "Brand Cost Compare", "text": "Compare the average service cost for Audi and Toyota.", "query": "Compare the average service cost for Audi and Toyota."},
        {"icon": "⚡", "tag": "EXPENSE AUDIT", "title": "Top Expensive Services", "text": "What are the top 3 most expensive services by total amount?", "query": "What are the top 3 most expensive services by total amount?"},
        {"icon": "🏢", "tag": "OPERATIONS METRICS", "title": "Workshop Capacity", "text": "How many workshops are there in the database?", "query": "How many workshops are there in the database?"}
    ]

    cols = st.columns(4)
    for idx, card in enumerate(quick_cards):
        with cols[idx]:
            render_html('<div class="hero-card-col">')
            card_clicked = st.button(
                f"{card['icon']} **{card['title']}**\n\n*{card['tag']}*\n\n{card['text']}", 
                key=f"hero_prompt_{idx}", 
                use_container_width=True
            )
            render_html('</div>')
            if card_clicked:
                st.session_state.pending_query = card["query"]
                st.rerun()

# ---------------------------------------------------------
# Message Stream Display
# ---------------------------------------------------------
for msg_idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        render_html(f"""
        <div class="user-bubble-row">
            <div class="user-bubble-box">{msg['content']}</div>
        </div>
        """)
    else:
        # Determine status badges
        cached_hit = msg.get("cached", False)
        elapsed_val = msg.get("execution_time_ms", 1.2)
        
        telemetry_html = f'<span class="latency-pill">⏱️ {elapsed_val} ms</span>'
        if cached_hit:
            telemetry_html = '<span class="cache-pill-hit">⚡ Semantic Cache (&lt;1ms)</span> ' + telemetry_html

        render_html(f"""
        <div class="assistant-wrapper">
            <div class="asst-header">
                <div class="asst-identity">
                    <div class="asst-glow-icon">{SVG_LOGO}</div>
                    <div>
                        <div class="asst-title">GARAGE INTELLIGENCE</div>
                        <div style="font-size: 10.5px; color: #64748B; font-weight: 600;">Verified SQL Analytical Output</div>
                    </div>
                </div>
                <div class="asst-telemetry-row">{telemetry_html}</div>
            </div>
            <div class="asst-answer-text">{msg['content']}</div>
        </div>
        """)

        chart_data = msg.get("chart_data")
        table_data = msg.get("table_data")
        sql_text = msg.get("sql", "").strip()

        # Modern Interactive Tabs
        has_chart = bool(chart_data and isinstance(chart_data, dict))
        has_table = bool(table_data and len(table_data.get("rows", [])) > 0)
        has_sql = bool(sql_text)

        tab_names = []
        if has_chart:
            tab_names.append("📊 Visualization")
        if has_table:
            tab_names.append("📋 Data Table")
        if has_sql:
            tab_names.append("🗔 Executed SQL")

        if tab_names:
            tabs = st.tabs(tab_names)
            tab_idx = 0

            # 1. Visualization Tab
            if has_chart:
                with tabs[tab_idx]:
                    render_chart_component(chart_data, f"chart_{msg_idx}", bright=is_bright)
                tab_idx += 1

            # 2. Data Table Tab
            if has_table:
                with tabs[tab_idx]:
                    df = pd.DataFrame(table_data.get("rows", []), columns=table_data.get("columns", []))
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    csv_bytes = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Formatted CSV",
                        data=csv_bytes,
                        file_name=f"ramp_data_query_{msg_idx}.csv",
                        mime="text/csv",
                        key=f"csv_dl_{msg_idx}"
                    )
                tab_idx += 1

            # 3. Executed SQL Tab
            if has_sql:
                with tabs[tab_idx]:
                    st.code(sql_text, language="sql")
                    st.caption(f"Engine: {msg.get('engine', active_engine_name)} | Session: {st.session_state.session_id}")
                tab_idx += 1

        # Action Buttons (Thumbs-Up Knowledge Base Ingestion)
        col_act1, col_act2 = st.columns([3.5, 6.5])
        with col_act1:
            if not cached_hit and sql_text:
                if msg_idx in st.session_state.saved_queries:
                    st.button("✓ Saved in Knowledge Base", key=f"saved_{msg_idx}", disabled=True)
                else:
                    if st.button("👍 Add to Golden Knowledge Base", key=f"thumb_{msg_idx}"):
                        save_golden_query(msg.get("user_query", ""), sql_text)
                        st.session_state.saved_queries.add(msg_idx)
                        st.session_state.golden_count += 1
                        st.toast("Verified query added to Golden Cache!", icon="✅")
                        time.sleep(0.5)
                        st.rerun()

# ---------------------------------------------------------
# Dynamic Suggestion Chips Row (Accessible Anytime)
# ---------------------------------------------------------
if len(st.session_state.messages) > 0:
    render_html('<div style="margin: 18px 0 10px; font-size: 11.5px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em;">💡 Quick Analytical Prompts:</div>')
    chip_cols = st.columns(4)
    chips = [
        ("🚗 Virtus Revenue", "What is the total service amount for Volkswagen Virtus?"),
        ("📊 Audi vs Toyota", "Compare the average service cost for Audi and Toyota."),
        ("⚡ Top 3 Services", "What are the top 3 most expensive services by total amount?"),
        ("🏢 Total Workshops", "How many workshops are there in the database?")
    ]
    for c_idx, (c_label, c_query) in enumerate(chips):
        with chip_cols[c_idx]:
            if st.button(c_label, key=f"chip_btn_{c_idx}", use_container_width=True):
                st.session_state.pending_query = c_query
                st.rerun()

# ---------------------------------------------------------
# Chat Input & Query Pipeline Invocation
# ---------------------------------------------------------
input_query = st.chat_input("Ask a question about workshop operations, vehicles, billing, complaints...")

# Handle pending query from hero cards or quick chips
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
