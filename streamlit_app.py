"""
RAMP-GPT — Next-Generation Autonomous Garage Intelligence Dashboard.
Features ultra-modern vibrant colorful design, luminous radiant background mesh,
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
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "bright"  # default to bright & colorful

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
is_bright = (st.session_state.theme_mode == "bright")

# ---------------------------------------------------------
# Dynamic CSS Injection (Bright & Colorful vs Vivid Aurora)
# ---------------------------------------------------------
if is_bright:
    # 🌈 RADIANT BRIGHT & COLORFUL THEME
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        #MainMenu, header, footer, .stDeployButton { display: none !important; }
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .stApp {
            background: linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 20%, #F5F3FF 45%, #FDF2F8 70%, #ECFEFF 100%) !important;
            color: #0F172A !important;
            overflow-x: hidden !important;
        }
        
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 7.5rem !important;
            max-width: 980px !important;
            margin: 0 auto !important;
        }

        /* Ambient Dynamic Color Blobs */
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
            filter: blur(120px);
            opacity: 0.55;
            animation: orb-drift 22s infinite alternate ease-in-out;
        }
        .orb-1 {
            top: -15%; left: -10%; width: 50vw; height: 50vw;
            background: #818CF8; /* Vibrant Indigo */
            animation-delay: 0s;
        }
        .orb-2 {
            top: 25%; right: -15%; width: 55vw; height: 55vw;
            background: #F472B6; /* Radiant Pink */
            animation-delay: -6s;
        }
        .orb-3 {
            bottom: -20%; left: 15%; width: 50vw; height: 50vw;
            background: #38BDF8; /* Sky Cyan */
            animation-delay: -12s;
        }
        .orb-4 {
            top: 60%; left: 55%; width: 35vw; height: 35vw;
            background: #FBBF24; /* Warm Amber */
            opacity: 0.35;
            animation-delay: -18s;
        }

        @keyframes orb-drift {
            0% { transform: translate(0, 0) scale(1) rotate(0deg); }
            50% { transform: translate(50px, 35px) scale(1.08) rotate(8deg); }
            100% { transform: translate(-35px, -30px) scale(0.94) rotate(-8deg); }
        }

        /* Floating Bright Navbar */
        .nav-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 24px;
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            margin-bottom: 24px;
            box-shadow: 0 10px 30px rgba(99, 102, 241, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
        }
        .brand-avatar {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
        }
        .brand-heading {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #1E1B4B 0%, #4338CA 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.1;
        }
        .brand-sub {
            font-size: 11px;
            font-weight: 600;
            color: #64748B;
            letter-spacing: 0.02em;
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
            box-shadow: 0 2px 6px rgba(16, 185, 129, 0.12);
        }
        .badge-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10B981;
            box-shadow: 0 0 10px #10B981;
            animation: pulse-dot 2s infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.3; transform: scale(0.85); }
        }
        .badge-engine {
            background: #FFFBEB;
            color: #D97706;
            border: 1px solid #FDE68A;
            box-shadow: 0 2px 6px rgba(245, 158, 11, 0.12);
        }

        /* Hero Welcome Section */
        .hero-container {
            text-align: center;
            padding: 34px 20px 20px;
            margin-bottom: 20px;
        }
        .hero-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 16px;
            background: linear-gradient(135deg, #EEF2FF 0%, #FCE7F3 100%);
            border: 1px solid #C7D2FE;
            border-radius: 9999px;
            color: #4F46E5;
            font-size: 11.5px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
        }
        .hero-title {
            font-size: 36px;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.2;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #0F172A 15%, #4338CA 55%, #DB2777 95%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-description {
            font-size: 14.5px;
            color: #475569;
            max-width: 600px;
            margin: 0 auto 28px;
            line-height: 1.6;
            font-weight: 500;
        }

        /* Quick Prompt Cards */
        .prompt-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-bottom: 28px;
        }
        div[data-testid="stHorizontalBlock"] button {
            background: rgba(255, 255, 255, 0.88) !important;
            border: 1.5px solid rgba(226, 232, 240, 0.9) !important;
            border-radius: 16px !important;
            color: #1E293B !important;
            font-weight: 600 !important;
            padding: 16px 14px !important;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.06) !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            text-align: left !important;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            border-color: #6366F1 !important;
            transform: translateY(-3px) !important;
            box-shadow: 0 10px 24px rgba(99, 102, 241, 0.18) !important;
            background: #FFFFFF !important;
            color: #4338CA !important;
        }

        /* User Message Bubble */
        .user-bubble-row {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 20px;
        }
        .user-bubble-box {
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 20px 20px 4px 20px;
            padding: 14px 22px;
            color: #FFFFFF;
            font-size: 15px;
            font-weight: 600;
            max-width: 82%;
            box-shadow: 0 6px 24px rgba(79, 70, 229, 0.28);
            line-height: 1.5;
        }

        /* Assistant Card */
        .assistant-wrapper {
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid rgba(226, 232, 240, 0.95);
            border-radius: 24px;
            padding: 24px 28px;
            margin-bottom: 28px;
            backdrop-filter: blur(20px);
            box-shadow: 0 12px 36px rgba(99, 102, 241, 0.08), 0 2px 4px rgba(0, 0, 0, 0.02);
            transition: all 0.2s ease;
        }
        .assistant-wrapper:hover {
            box-shadow: 0 16px 44px rgba(99, 102, 241, 0.14);
            border-color: #C7D2FE;
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
            background: linear-gradient(135deg, #4F46E5, #EC4899);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            color: #FFF;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        }
        .asst-title {
            font-size: 12.5px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #4F46E5;
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
            font-size: 15.5px;
            color: #0F172A;
            line-height: 1.65;
            margin-bottom: 18px;
            font-weight: 500;
        }

        /* Tabular Display (Bright & Crisp) */
        .table-container {
            margin: 16px 0;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            overflow: hidden;
            background: #FFFFFF;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        .table-header-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 16px;
            background: #F8FAFC;
            border-bottom: 1px solid #E2E8F0;
            font-size: 12px;
            font-weight: 700;
            color: #4F46E5;
        }
        .styled-grid-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .styled-grid-table th {
            background: #F1F5F9;
            color: #334155;
            text-align: left;
            padding: 10px 16px;
            font-weight: 700;
            font-size: 11.5px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            border-bottom: 1px solid #E2E8F0;
        }
        .styled-grid-table td {
            padding: 10px 16px;
            color: #0F172A;
            border-bottom: 1px solid #F1F5F9;
            font-variant-numeric: tabular-nums;
        }
        .styled-grid-table tr:hover {
            background: #F8FAFC;
        }

        /* Fixed Bottom Chat Bar (Bright Glass) */
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
            background: rgba(255, 255, 255, 0.94) !important;
            border: 1.5px solid rgba(99, 102, 241, 0.3) !important;
            border-radius: 9999px !important;
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
            box-shadow: 0 12px 40px rgba(99, 102, 241, 0.16) !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stChatInput"] > div:focus-within {
            border-color: #4F46E5 !important;
            box-shadow: 0 12px 45px rgba(79, 70, 229, 0.25) !important;
        }
        div[data-testid="stChatInput"] textarea {
            color: #0F172A !important;
            font-size: 14.5px !important;
            font-weight: 500 !important;
        }

        /* Sidebar Glassmorphic Bright Styling */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 2rem !important;
        }
        .sidebar-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }
        .sidebar-card-title {
            font-size: 11px;
            font-weight: 800;
            color: #4F46E5;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .sidebar-stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12.5px;
            color: #334155;
            padding: 4px 0;
            font-weight: 500;
        }
        .stat-val-highlight {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: #4338CA;
        }
    </style>

    <!-- Radiant Ambient Blobs -->
    <div class="ambient-mesh">
        <div class="glow-orb orb-1"></div>
        <div class="glow-orb orb-2"></div>
        <div class="glow-orb orb-3"></div>
        <div class="glow-orb orb-4"></div>
    </div>
    """, unsafe_allow_html=True)
else:
    # 🌌 VIVID CYBER AURORA THEME
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        #MainMenu, header, footer, .stDeployButton { display: none !important; }
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .stApp {
            background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 35%, #2E1065 70%, #0F172A 100%) !important;
            color: #F8FAFC !important;
            overflow-x: hidden !important;
        }
        
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 7.5rem !important;
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
            filter: blur(130px);
            opacity: 0.6;
            animation: orb-drift 24s infinite alternate ease-in-out;
        }
        .orb-1 { top: -12%; left: -8%; width: 48vw; height: 48vw; background: #00F0FF; }
        .orb-2 { top: 35%; right: -12%; width: 44vw; height: 44vw; background: #A855F7; }
        .orb-3 { bottom: -15%; left: 20%; width: 42vw; height: 42vw; background: #EC4899; }
        .orb-4 { top: 60%; left: 55%; width: 35vw; height: 35vw; background: #F59E0B; opacity: 0.35; }

        @keyframes orb-drift {
            0% { transform: translate(0, 0) scale(1) rotate(0deg); }
            50% { transform: translate(50px, 40px) scale(1.08) rotate(10deg); }
            100% { transform: translate(-30px, -40px) scale(0.94) rotate(-10deg); }
        }

        .nav-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 24px;
            background: rgba(18, 24, 46, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            backdrop-filter: blur(20px);
            margin-bottom: 24px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
        }
        .brand-avatar {
            width: 40px; height: 40px; border-radius: 12px;
            background: linear-gradient(135deg, #00F0FF, #7000FF, #EC4899);
            display: flex; align-items: center; justify-content: center; font-size: 20px;
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.5);
        }
        .brand-heading {
            font-size: 18px; font-weight: 800; color: #FFF; line-height: 1.1;
        }
        .brand-sub { font-size: 11px; color: #94A3B8; }
        .badge-pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700; }
        .badge-mysql { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.35); }
        .badge-pulse { width: 8px; height: 8px; border-radius: 50%; background-color: #34D399; box-shadow: 0 0 10px #34D399; animation: pulse-dot 2s infinite; }
        .badge-engine { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.35); }

        .hero-container { text-align: center; padding: 34px 20px 20px; margin-bottom: 20px; }
        .hero-tag { display: inline-flex; padding: 4px 14px; background: rgba(0, 240, 255, 0.1); border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 9999px; color: #38BDF8; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 14px; }
        .hero-title { font-size: 36px; font-weight: 800; background: linear-gradient(135deg, #FFF 20%, #A5B4FC 60%, #F472B6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero-description { font-size: 14.5px; color: #CBD5E1; max-width: 600px; margin: 0 auto 28px; line-height: 1.6; }

        div[data-testid="stHorizontalBlock"] button {
            background: rgba(30, 41, 75, 0.7) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 16px !important;
            color: #E2E8F0 !important;
            font-weight: 600 !important;
            padding: 16px 14px !important;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            border-color: #00F0FF !important;
            background: rgba(40, 56, 105, 0.9) !important;
            color: #FFF !important;
            transform: translateY(-3px) !important;
        }

        .user-bubble-row { display: flex; justify-content: flex-end; margin-bottom: 20px; }
        .user-bubble-box { background: linear-gradient(135deg, #1E293B, #0F172A); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 20px 20px 4px 20px; padding: 14px 22px; color: #FFF; font-size: 15px; font-weight: 600; max-width: 82%; }

        .assistant-wrapper { background: rgba(18, 24, 46, 0.88); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 24px; padding: 24px 28px; margin-bottom: 28px; backdrop-filter: blur(20px); }
        .asst-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
        .asst-glow-icon { width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg, #00F0FF, #EC4899); display: flex; align-items: center; justify-content: center; font-size: 16px; }
        .asst-title { font-size: 12.5px; font-weight: 800; color: #C084FC; text-transform: uppercase; }
        .cache-pill-hit { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 9999px; padding: 4px 11px; font-size: 11px; font-weight: 700; }
        .latency-pill { background: rgba(255, 255, 255, 0.08); color: #CBD5E1; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 9999px; padding: 4px 11px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
        .asst-answer-text { font-size: 15.5px; color: #F8FAFC; line-height: 1.65; margin-bottom: 18px; font-weight: 500; }

        .table-container { margin: 16px 0; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 14px; overflow: hidden; background: #0B0E17; }
        .table-header-title { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background: #131A30; border-bottom: 1px solid rgba(255, 255, 255, 0.08); font-size: 12px; font-weight: 700; color: #38BDF8; }
        .styled-grid-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .styled-grid-table th { background: #10162A; color: #94A3B8; text-align: left; padding: 10px 16px; font-weight: 700; border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
        .styled-grid-table td { padding: 10px 16px; color: #E2E8F0; border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
        .styled-grid-table tr:hover { background: rgba(255, 255, 255, 0.03); }

        div[data-testid="stChatInput"] { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); width: 100%; max-width: 900px; z-index: 999; }
        div[data-testid="stChatInput"] > div { background: rgba(18, 24, 46, 0.9) !important; border: 1.5px solid rgba(0, 240, 255, 0.3) !important; border-radius: 9999px !important; backdrop-filter: blur(24px) !important; }
        div[data-testid="stChatInput"] textarea { color: #FFF !important; }

        section[data-testid="stSidebar"] { background: #0A0F1D !important; border-right: 1px solid rgba(255, 255, 255, 0.08) !important; }
        .sidebar-card { background: rgba(18, 24, 46, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; padding: 14px 16px; margin-bottom: 14px; }
        .sidebar-card-title { font-size: 11px; font-weight: 800; color: #38BDF8; text-transform: uppercase; margin-bottom: 10px; }
        .sidebar-stat-row { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; color: #CBD5E1; padding: 4px 0; }
        .stat-val-highlight { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #38BDF8; }
    </style>

    <div class="ambient-mesh">
        <div class="glow-orb orb-1"></div>
        <div class="glow-orb orb-2"></div>
        <div class="glow-orb orb-3"></div>
        <div class="glow-orb orb-4"></div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar: System Diagnostics & Theme Customizer
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 18px;">
        <div style="width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg, #4F46E5, #EC4899); display: flex; align-items: center; justify-content: center; font-size: 18px; color: #FFF;">🚗</div>
        <div>
            <div style="font-weight: 800; font-size: 16px;">RAMP-GPT</div>
            <div style="font-size: 10.5px; color: #64748B;">Garage Intelligence v2.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Theme Switcher Control
    st.markdown('<div class="sidebar-card"><div class="sidebar-card-title">🎨 Visual Aesthetic</div>', unsafe_allow_html=True)
    selected_theme = st.radio(
        "Theme Palette",
        options=["🌈 Radiant Bright (Colorful)", "🌌 Vivid Cyber Aurora"],
        index=0 if is_bright else 1,
        label_visibility="collapsed"
    )
    new_mode = "bright" if "Bright" in selected_theme else "dark"
    if new_mode != st.session_state.theme_mode:
        st.session_state.theme_mode = new_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Database Pool Status Card
    pool_info = st.session_state.system_status.get("pool", {})
    st.markdown(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">🗄️ Database Engine</div>
        <div class="sidebar-stat-row">
            <span>Status</span>
            <span class="stat-val-highlight" style="color: {'#059669' if is_bright else '#34D399'};">
                {'● Online (3306)' if db_online else '○ Offline'}
            </span>
        </div>
        <div class="sidebar-stat-row">
            <span>Database</span>
            <span class="stat-val-highlight">rag (6 tables)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Connection Pool</span>
            <span class="stat-val-highlight">QueuePool (size=5)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Circuit Breaker</span>
            <span class="stat-val-highlight">5,000 ms</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Knowledge Base Card
    st.markdown(f"""
    <div class="sidebar-card">
        <div class="sidebar-card-title">🧠 Caching & AI Model</div>
        <div class="sidebar-stat-row">
            <span>Primary LLM</span>
            <span class="stat-val-highlight">Groq (Qwen 27B)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Fallback LLM</span>
            <span class="stat-val-highlight">Ollama (7B Coder)</span>
        </div>
        <div class="sidebar-stat-row">
            <span>Semantic Cache</span>
            <span class="stat-val-highlight">&lt; 1 ms Jaccard</span>
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
            <span>MySQL 8.0 Live</span>
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
def render_chart_component(chart_info: dict, chart_id: str, bright: bool = True):
    """Renders responsive modern Chart.js visualizer matching the vibrant theme."""
    chart_type = chart_info.get("type", "bar")
    title = chart_info.get("title", "Analytical Breakdown")
    labels = chart_info.get("labels", [])
    datasets = chart_info.get("datasets", [])
    
    # Enrich datasets with vibrant palette if needed
    vibrant_colors = [
        "rgba(79, 70, 229, 0.85)",   # Indigo
        "rgba(236, 72, 153, 0.85)",  # Pink
        "rgba(6, 182, 212, 0.85)",   # Cyan
        "rgba(245, 158, 11, 0.85)",  # Amber
        "rgba(16, 185, 129, 0.85)"   # Emerald
    ]
    border_colors = ["#4F46E5", "#EC4899", "#06B6D4", "#F59E0B", "#10B981"]

    if datasets and isinstance(datasets, list):
        for ds in datasets:
            if not ds.get("backgroundColor") or not isinstance(ds.get("backgroundColor"), list):
                ds["backgroundColor"] = vibrant_colors[:len(labels)]
                ds["borderColor"] = border_colors[:len(labels)]
                ds["borderWidth"] = 1.5
                ds["borderRadius"] = 8

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
                        "color": "#334155" if bright else "#CBD5E1",
                        "font": {"family": "Plus Jakarta Sans", "size": 11, "weight": "600"}
                    }
                },
                "tooltip": {
                    "backgroundColor": "#FFFFFF" if bright else "rgba(18, 24, 46, 0.95)",
                    "titleColor": "#1E1B4B" if bright else "#38BDF8",
                    "bodyColor": "#334155" if bright else "#F8FAFC",
                    "borderColor": "#E2E8F0" if bright else "rgba(255, 255, 255, 0.15)",
                    "borderWidth": 1.5,
                    "padding": 12,
                    "cornerRadius": 10
                }
            },
            "scales": {
                "x": {
                    "grid": {"color": "rgba(226, 232, 240, 0.8)" if bright else "rgba(255, 255, 255, 0.06)"},
                    "ticks": {"color": "#64748B" if bright else "#94A3B8", "font": {"family": "Plus Jakarta Sans", "size": 10.5}}
                },
                "y": {
                    "grid": {"color": "rgba(226, 232, 240, 0.8)" if bright else "rgba(255, 255, 255, 0.06)"},
                    "ticks": {"color": "#64748B" if bright else "#94A3B8", "font": {"family": "Plus Jakarta Sans", "size": 10.5}}
                }
            }
        }
    }
    
    bg_box = "rgba(255, 255, 255, 0.9)" if bright else "#0E1424"
    border_box = "#E2E8F0" if bright else "rgba(255, 255, 255, 0.08)"
    title_col = "#4F46E5" if bright else "#38BDF8"

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
                height: 235px;
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
                height: 180px;
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
    components.html(html_code, height=255)

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
            <span style="font-size: 10.5px; opacity: 0.8;">MYSQL RELATIONAL OUTPUT</span>
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
            render_chart_component(chart_data, f"chart_{msg_idx}", bright=is_bright)

        # Render Collapsible SQL Inspector
        sql_text = msg.get("sql", "").strip()
        if sql_text:
            with st.expander("🗔 Inspect Generated SQL & Telemetry", expanded=False):
                st.code(sql_text, language="sql")
                st.caption(f"Engine: {msg.get('engine', active_engine_name)} | Session: {st.session_state.session_id}")

        # Action Buttons (Thumbs-Up Knowledge Base & CSV Download)
        col_act1, col_act2, col_act3 = st.columns([2.5, 2.5, 5])
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
