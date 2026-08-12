# ─────────────────────────────────────────────────────────────────────────────
# application/app.py — Streamlit UI entry point for the Compliance Chatbot
#
# Two pages:
#   1. LLM Configuration — form to connect to the DLH on-prem inference server
#   2. Chat             — NL2SQL conversational interface with stage-pill trace
#
# Run from the project root:
#   streamlit run dlh_ai/application/app.py
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import json
import base64
from pathlib import Path
import sys

# ── PATH SETUP ────────────────────────────────────────────────────────────────
# Resolve the project root (dlh_ai/) so all internal imports work correctly
# regardless of where Streamlit is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# llm_config.json is written to the workspace root (one level above dlh_ai/)
CONFIG_FILE = _PROJECT_ROOT / "llm_config.json"

# Add the project root to sys.path so "from genai..." and "from utils..." work
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── INTERNAL IMPORTS ──────────────────────────────────────────────────────────
# These are imported after the sys.path fix above
from genai.core.model import ModelLoaderService          # LLM client wrapper
from genai.core.processor import ComplianceProcessor     # pipeline orchestrator
from genai.nl2sql_agent.graph import build_nl2sql_graph  # LangGraph factory
from utils.config import ModelSettings, get_settings     # pydantic settings
from utils.logger import get_logger                      # centralised logger

# Create a module-level logger — all log entries appear in data/logs/
LOGGER = get_logger("compliance_bot.streamlit")


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENCE HELPERS
# These two functions read/write llm_config.json so credentials survive
# Streamlit hot-reloads and server restarts.
# ─────────────────────────────────────────────────────────────────────────────

def save_config_to_disk(model_name: str, base_url: str, api_key: str) -> None:
    """Write LLM credentials to llm_config.json next to the workspace root."""
    try:
        # Build the config dict with the three user-supplied values
        config = {
            "model_name": model_name,
            "base_url":   base_url,
            "api_key":    api_key,
        }
        # Overwrite (or create) the file — no sensitive data in git
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        LOGGER.info("Configuration saved to disk successfully.")
    except Exception as e:
        # Log the error but never crash the UI — the user can retry
        LOGGER.error(f"Failed to save config to disk: {e}")


def load_config_from_disk() -> dict | None:
    """Read and return the saved LLM credentials, or None if the file is missing."""
    try:
        if CONFIG_FILE.exists():
            # Open the file and parse JSON into a plain dict
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        # If the file is corrupt or unreadable, return None gracefully
        LOGGER.error(f"Failed to load config from disk: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# FONT LOADING HELPER
# Urbanist TTF files are embedded as base64 data URIs so they work without
# any external CDN — the font is served directly inside the HTML page.
# ─────────────────────────────────────────────────────────────────────────────

def get_font_base64(font_path: Path) -> str | None:
    """Read a .ttf font file and return it as a base64 string for CSS injection."""
    try:
        with open(font_path, "rb") as f:
            data = f.read()
        # base64-encode the raw bytes and decode to a plain string
        return base64.b64encode(data).decode()
    except Exception as e:
        # Font is cosmetic — log and fall back to the system sans-serif
        LOGGER.error(f"Could not load font at {font_path}: {e}")
        return None


# Load Urbanist font weights: regular (400), medium (500), bold (700)
font_dir      = _PROJECT_ROOT / "application" / "fonts"
font_reg      = get_font_base64(font_dir / "Urbanist-Regular.ttf")
font_medium   = get_font_base64(font_dir / "Urbanist-Medium.ttf")
font_bold     = get_font_base64(font_dir / "Urbanist-Bold.ttf")
font_semibold = get_font_base64(font_dir / "Urbanist-SemiBold.ttf")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG — must be the first Streamlit call in the script
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SBI Compliance Chatbot",
    page_icon="\u2302",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Enterprise Design System
# Injects Urbanist @font-face declarations plus all component styles.
# Design tokens: deep navy primary, white cards, cool-grey background, shadows.
# ─────────────────────────────────────────────────────────────────────────────

# Build @font-face declarations — empty string when TTF file was missing
def _font_face(b64: str | None, weight: int) -> str:
    """Return a @font-face rule for Urbanist at the given weight."""
    if not b64:
        return ""
    return (
        f"@font-face {{ font-family: 'Urbanist'; "
        f"src: url(data:font/truetype;base64,{b64}) format('truetype'); "
        f"font-weight: {weight}; font-style: normal; font-display: swap; }}"
    )

font_face_css = (
    _font_face(font_reg,      400)
    + _font_face(font_medium,  500)
    + _font_face(font_semibold, 600)
    + _font_face(font_bold,    700)
)

# All CSS is injected in one st.markdown call to minimise DOM mutations.
# unsafe_allow_html is required for raw <style> injection in Streamlit.
st.markdown(f"""
<style>
    /* ── FONT DECLARATIONS ────────────────────────────────────────────── */
    {font_face_css}

    /* ── DESIGN TOKENS — light grey & white theme ─────────────────────── */
    :root {{
        --clr-bg:          #f0f0f0;          /* page background: light grey        */
        --clr-surface:     #ffffff;          /* card / widget background: white    */
        --clr-surface-alt: #f6f6f6;          /* secondary surface: near-white      */
        --clr-border:      #dedede;          /* card and input borders: soft grey  */
        --clr-border-md:   #c0c0c0;          /* medium-weight border               */
        --clr-primary:     #2c2c2c;          /* primary: dark charcoal (not black) */
        --clr-primary-mid: #4a4a4a;          /* mid-tone: medium grey              */
        --clr-primary-lt:  #6b6b6b;          /* lighter interactive grey           */
        --clr-accent:      #5a5a5a;          /* accent: charcoal                   */
        --clr-success:     #1a7a3c;          /* green success (kept functional)    */
        --clr-success-lt:  #eaf5ee;          /* green tint background              */
        --clr-error:       #b91c1c;          /* red error (kept functional)        */
        --clr-error-lt:    #fef2f2;          /* red tint background                */
        --clr-warn:        #92400e;          /* amber warning (kept functional)    */
        --clr-warn-lt:     #fffbeb;          /* amber tint background              */
        --clr-text:        #1e1e1e;          /* primary body text: dark grey       */
        --clr-text-muted:  #636363;          /* secondary / label text             */
        --clr-text-faint:  #9e9e9e;          /* placeholder / hint text            */
        --clr-code-bg:     #ffffff;          /* code block: white                  */
        --clr-code-text:   #1e1e1e;          /* code block text: dark grey         */
        --shadow-xs:   0 1px 3px rgba(0,0,0,0.07);
        --shadow-sm:   0 2px 8px rgba(0,0,0,0.09);
        --shadow-md:   0 4px 18px rgba(0,0,0,0.11);
        --shadow-lg:   0 8px 32px rgba(0,0,0,0.14);
        --radius-sm:   8px;
        --radius-md:   12px;
        --radius-lg:   16px;
        --radius-pill: 999px;
    }}

    /* ── GLOBAL TYPOGRAPHY & PAGE ─────────────────────────────────────── */
    html, body,
    [class*="css"],
    .stMarkdown, .stText,
    p, li, label, span, div,
    h1, h2, h3, h4 {{
        font-family: 'Urbanist', 'Segoe UI', system-ui, sans-serif !important;
        font-weight: 500 !important;   /* consistent medium weight everywhere */
        color: var(--clr-text);
    }}

    /* Page chrome background */
    .stApp {{
        background-color: var(--clr-bg) !important;
    }}

    /* Content width — adjust max-width to control how far content spreads
       on large monitors.  Common values:
         1280px  — compact (current default, suits 15" laptops)
         1600px  — comfortable on 18–22" screens
         1920px  — fills a standard 1080p monitor
         100%    — always full browser width                               */
    .main .block-container {{
        max-width: 1600px !important;
        margin: 0 auto !important;
        padding: 1.5rem 2.5rem 4rem !important;
    }}

    /* ── TOP HEADER BANNER ────────────────────────────────────────────── */
    /* Injected via st.markdown on every page */
    .app-header {{
        background: linear-gradient(135deg, #111111 0%, #2e2e2e 100%);
        border-radius: var(--radius-lg);
        padding: 20px 28px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: var(--shadow-md);
    }}
    .app-header-title {{
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: 0.3px;
        margin: 0;
    }}
    .app-header-sub {{
        font-size: 13px;
        color: rgba(255,255,255,0.70);
        margin: 3px 0 0;
        font-weight: 400;
    }}
    .app-header-badge {{
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: var(--radius-pill);
        padding: 5px 14px;
        font-size: 12px;
        color: #ffffff;
        font-weight: 600;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }}

    /* ── SIDEBAR — light grey / white theme ──────────────────────────── */

    /* Hide Streamlit's built-in collapse arrow, dark/light mode toggle,
       and the running/stop widget that appear inside the sidebar chrome */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[title="Close sidebar"],
    button[aria-label="Close sidebar"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu,
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
    }}

    [data-testid="stSidebar"] {{
        background: #ffffff !important;
        border-right: 1px solid #dedede !important;
        box-shadow: 2px 0 12px rgba(0,0,0,0.07) !important;
    }}
    /* All text inside sidebar — dark grey on white */
    [data-testid="stSidebar"] * {{
        color: #2c2c2c !important;
        font-family: 'Urbanist', sans-serif !important;
    }}
    /* Sidebar brand block */
    .sidebar-brand {{
        padding: 8px 0 16px;
        border-bottom: 1px solid #e4e4e4;
        margin-bottom: 16px;
    }}
    .sidebar-brand-title {{
        font-size: 17px;
        font-weight: 700;
        color: #1e1e1e !important;
        letter-spacing: 0.2px;
    }}
    .sidebar-brand-sub {{
        font-size: 11px;
        color: #808080 !important;
        margin-top: 3px;
        font-weight: 400;
    }}
    /* Sidebar dividers */
    [data-testid="stSidebar"] hr {{
        border-color: #e4e4e4 !important;
    }}
    /* Sidebar nav buttons */
    [data-testid="stSidebar"] .stButton > button {{
        background: #f6f6f6 !important;
        border: 1px solid #dedede !important;
        color: #2c2c2c !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 16px !important;
        width: 100% !important;
        text-align: left !important;
        transition: background 0.15s, border-color 0.15s !important;
        margin-bottom: 6px !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: #ebebeb !important;
        border-color: #c0c0c0 !important;
    }}
    /* Sidebar status badges — adjusted for light background */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 8px 14px;
        border-radius: var(--radius-sm);
        font-size: 13px;
        font-weight: 600;
        margin-top: 8px;
        width: 100%;
    }}
    .status-badge.online {{
        background: #edf7f1;
        border: 1px solid #a7d9b8;
        color: #1a6b36 !important;
    }}
    .status-badge.offline {{
        background: #fdf2f2;
        border: 1px solid #f0bbbb;
        color: #9b2020 !important;
    }}
    .status-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .status-dot.online  {{ background: #34a85a; box-shadow: 0 0 5px rgba(52,168,90,0.50); }}
    .status-dot.offline {{ background: #d94444; }}

    /* ── CARDS ────────────────────────────────────────────────────────── */
    /* Main card container — white surface with shadow and border */
    .card {{
        background: var(--clr-surface);
        border: 1px solid var(--clr-border);
        border-radius: var(--radius-lg);
        padding: 24px 28px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 20px;
    }}
    /* Elevated card for primary sections */
    .card-elevated {{
        background: var(--clr-surface);
        border: 1px solid var(--clr-border);
        border-radius: var(--radius-lg);
        padding: 28px 32px;
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
    }}
    /* Card with left accent stripe */
    .card-accent {{
        background: var(--clr-surface);
        border: 1px solid var(--clr-border);
        border-left: 4px solid #333333;
        border-radius: var(--radius-md);
        padding: 20px 24px;
        box-shadow: var(--shadow-xs);
        margin-bottom: 16px;
    }}
    /* Card header row inside a card */
    .card-header {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 18px;
        padding-bottom: 14px;
        border-bottom: 1px solid var(--clr-border);
    }}
    .card-icon {{
        width: 38px;
        height: 38px;
        border-radius: var(--radius-sm);
        background: linear-gradient(135deg, #3a3a3a 0%, #5e5e5e 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
    }}
    .card-title {{
        font-size: 17px;
        font-weight: 700;
        color: var(--clr-text);
        line-height: 1.3;
    }}
    .card-subtitle {{
        font-size: 12.5px;
        color: var(--clr-text-muted);
        margin-top: 2px;
        font-weight: 400;
        line-height: 1.4;
    }}

    /* ── STREAMLIT FORM INPUT OVERRIDES ──────────────────────────────── */
    /* Make all inputs look clean and consistent */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea {{
        border: 1.5px solid var(--clr-border-md) !important;
        border-radius: var(--radius-sm) !important;
        background: var(--clr-surface) !important;
        color: var(--clr-text) !important;
        font-family: 'Urbanist', sans-serif !important;
        font-size: 14px !important;
        box-shadow: var(--shadow-xs) !important;
        transition: border-color 0.15s !important;
        padding: 10px 14px !important;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: #333333 !important;
        box-shadow: 0 0 0 3px rgba(0,0,0,0.10) !important;
        outline: none !important;
    }}
    /* Input labels */
    .stTextInput label, .stSelectbox label {{
        font-size: 13px !important;
        font-weight: 600 !important;
        color: var(--clr-text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        margin-bottom: 4px !important;
    }}

    /* ── BUTTONS ──────────────────────────────────────────────────────── */
    /* Primary submit / action button */
    .stButton > button[kind="primary"],
    [data-testid="baseButton-primary"] {{
        background: linear-gradient(135deg, #2c2c2c 0%, #4a4a4a 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 11px 22px !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.15) !important;
        transition: opacity 0.15s, transform 0.1s !important;
        letter-spacing: 0.3px !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        opacity: 0.88 !important;
        transform: translateY(-1px) !important;
    }}
    /* Secondary button (form_submit_button default) */
    .stButton > button[kind="secondary"],
    [data-testid="baseButton-secondary"] {{
        background: #ffffff !important;
        color: #111111 !important;
        border: 1.5px solid #333333 !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 20px !important;
        transition: background 0.15s !important;
    }}
    .stButton > button[kind="secondary"]:hover {{
        background: #f0f0f0 !important;
    }}
    /* Download button */
    .stDownloadButton > button {{
        background: #ffffff !important;
        border: 1.5px solid #444444 !important;
        color: #222222 !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }}
    .stDownloadButton > button:hover {{
        background: #f0f0f0 !important;
    }}

    /* ── STAGE PIPELINE PILLS ─────────────────────────────────────────── */
    .pipeline-track {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: nowrap;
        overflow-x: auto;
        padding: 14px 18px;
        background: var(--clr-surface);
        border: 1px solid var(--clr-border);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-xs);
        margin-bottom: 18px;
        scrollbar-width: thin;
    }}
    .stage-pill {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 6px 14px;
        border-radius: var(--radius-pill);
        font-size: 12px;
        font-weight: 500;              /* same weight as global body text */
        background: var(--clr-surface-alt);
        color: var(--clr-text-muted);
        border: 1.5px solid var(--clr-border);
        white-space: nowrap;
        letter-spacing: 0.2px;
        transition: background 0.2s, color 0.2s, border-color 0.2s, box-shadow 0.2s;
        position: relative;
    }}
    /* No connector between pills */
    .stage-pill + .stage-pill::before {{
        content: none;
        display: none;
    }}
    .stage-pill.active {{
        background: #1d4ed8;
        color: #ffffff !important;
        border-color: transparent;
        box-shadow: 0 2px 8px rgba(29,78,216,0.35);
        font-weight: 500;              /* same weight as inactive — no jump */
    }}
    .stage-pill.active::before {{
        background: #3b82f6;
    }}

    /* ── CHAT BUBBLES ─────────────────────────────────────────────────── */
    /* Row is a flex column so bubbles are auto-width and don't stretch */
    .chat-row {{
        display: flex;
        flex-direction: column;
        margin-bottom: 14px;
        gap: 0;
    }}
    /* User bubble — right-aligned, shrinks to fit content */
    .msg-user {{
        background: linear-gradient(135deg, #2c2c2c 0%, #4a4a4a 100%);
        color: #ffffff !important;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        align-self: flex-end;       /* pushes to the right */
        display: inline-block;
        width: fit-content;         /* only as wide as the text */
        max-width: 72%;             /* but never wider than 72% */
        font-size: 14px;
        font-weight: 500;
        line-height: 1.55;
        box-shadow: var(--shadow-sm);
        word-break: break-word;
    }}
    /* Bot bubble — left-aligned, shrinks to fit content */
    .msg-bot {{
        background: var(--clr-surface);
        color: var(--clr-text) !important;
        padding: 10px 16px;
        border-radius: 4px 18px 18px 18px;
        border: 1px solid var(--clr-border);
        align-self: flex-start;     /* stays on the left */
        display: inline-block;
        width: fit-content;         /* only as wide as the text */
        max-width: 80%;             /* but never wider than 80% */
        font-size: 14px;
        line-height: 1.55;
        box-shadow: var(--shadow-xs);
        word-break: break-word;
    }}
    /* Error notice — red tint */
    .msg-notice-blocked {{
        background: var(--clr-error-lt);
        border: 1px solid #fecaca;
        border-left: 4px solid var(--clr-error);
        color: #991b1b !important;
        padding: 14px 18px;
        border-radius: var(--radius-md);
        margin-bottom: 14px;
        font-size: 14px;
        line-height: 1.65;
        clear: both;
        box-shadow: var(--shadow-xs);
        white-space: pre-line;   /* renders \n line-breaks from YAML strings */
    }}
    /* Clarification notice — light grey tint */
    .msg-notice-clarify {{
        background: #f4f4f4;
        border: 1px solid #cccccc;
        border-left: 4px solid #444444;
        color: #1a1a1a !important;
        padding: 14px 18px;
        border-radius: var(--radius-md);
        margin-bottom: 14px;
        font-size: 14px;
        line-height: 1.65;
        clear: both;
        box-shadow: var(--shadow-xs);
        white-space: pre-line;   /* renders \n line-breaks from YAML strings */
    }}

    /* ── CODE BLOCK (SQL / trace / JSON) ─────────────────────────────── */
    .code-block {{
        background: #ffffff;
        color: #1e1e1e;
        padding: 16px 18px;
        border-radius: var(--radius-md);
        font-family: 'Courier New', 'Courier', monospace;
        font-size: 12px;
        line-height: 1.70;
        margin: 8px 0 14px;
        white-space: pre-wrap;
        word-break: break-word;
        border: 1px solid #dedede;
        box-shadow: var(--shadow-xs);
        clear: both;
    }}
    /* Label row above code blocks */
    .code-label {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: var(--clr-text-muted);
        margin-bottom: 4px;
        display: block;
    }}

    /* ── RESULT TABLE ─────────────────────────────────────────────────── */
    .result-table-wrap {{
        background: var(--clr-surface);
        border: 1px solid var(--clr-border);
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        margin: 12px 0 16px;
        clear: both;
    }}
    .result-table-wrap table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    .result-table-wrap th {{
        background: #3a3a3a;
        color: #ffffff;
        padding: 10px 14px;
        text-align: left;
        font-weight: 600;
        font-size: 12px;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        white-space: nowrap;
    }}
    .result-table-wrap td {{
        padding: 9px 14px;
        border-bottom: 1px solid var(--clr-border);
        color: var(--clr-text);
        vertical-align: top;
    }}
    .result-table-wrap tr:last-child td {{
        border-bottom: none;
    }}
    .result-table-wrap tr:nth-child(even) td {{
        background: var(--clr-surface-alt);
    }}
    .result-table-wrap tr:hover td {{
        background: rgba(0,0,0,0.04);
    }}

    /* ── STREAMLIT NATIVE TABLE & DATAFRAME ──────────────────────────── */
    .stDataFrame, [data-testid="stDataFrame"] {{
        border-radius: var(--radius-md) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-sm) !important;
        border: 1px solid var(--clr-border) !important;
    }}

    /* ── METRIC CARDS (st.metric) ────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: var(--clr-surface) !important;
        border: 1px solid var(--clr-border) !important;
        border-radius: var(--radius-md) !important;
        padding: 18px 20px !important;
        box-shadow: var(--shadow-xs) !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        color: var(--clr-text-muted) !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #2c2c2c !important;
    }}

    /* ── ALERT / NOTICE BOXES ────────────────────────────────────────── */
    .stAlert {{
        border-radius: var(--radius-md) !important;
        font-size: 14px !important;
        box-shadow: var(--shadow-xs) !important;
        border-width: 1px !important;
    }}
    /* Success — green */
    [data-testid="stAlert"][data-type="success"] {{
        background: var(--clr-success-lt) !important;
        border-color: #86efac !important;
        color: #14532d !important;
    }}
    /* Error — red */
    [data-testid="stAlert"][data-type="error"] {{
        background: var(--clr-error-lt) !important;
        border-color: #fca5a5 !important;
        color: #7f1d1d !important;
    }}

    /* ── SPINNER ─────────────────────────────────────────────────────── */
    [data-testid="stSpinner"] > div {{
        border-color: var(--clr-primary-lt) !important;
    }}

    /* ── DIVIDER ─────────────────────────────────────────────────────── */
    hr {{
        border-color: var(--clr-border) !important;
        margin: 18px 0 !important;
    }}

    /* ── SCROLLBAR (webkit) ──────────────────────────────────────────── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{
        background: var(--clr-border-md);
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--clr-text-muted); }}

    /* ── SECTION LABEL ────────────────────────────────────────────────── */
    .section-label {{
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--clr-text-muted);
        margin-bottom: 10px;
        display: block;
    }}

    /* ── INFO ROW (key-value pairs on config page) ───────────────────── */
    .info-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 9px 0;
        border-bottom: 1px solid var(--clr-border);
        font-size: 13.5px;
    }}
    .info-row:last-child {{ border-bottom: none; }}
    .info-key {{
        color: var(--clr-text-muted);
        font-weight: 500;
        flex-shrink: 0;
        margin-right: 12px;
    }}
    .info-val {{
        color: var(--clr-text);
        font-weight: 600;
        font-family: 'Cascadia Code', monospace;
        font-size: 12.5px;
        word-break: break-all;
        text-align: right;
    }}

    /* ── EMPTY CHAT PLACEHOLDER ──────────────────────────────────────── */
    .chat-empty {{
        text-align: center;
        padding: 56px 24px;
        color: var(--clr-text-muted);
    }}
    .chat-empty-icon {{
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.55;
    }}
    .chat-empty-title {{
        font-size: 18px;
        font-weight: 700;
        color: var(--clr-text);
        margin-bottom: 8px;
    }}
    .chat-empty-sub {{
        font-size: 13.5px;
        color: var(--clr-text-muted);
        max-width: 420px;
        margin: 0 auto;
        line-height: 1.6;
    }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# Streamlit re-runs the whole script on every interaction; st.session_state
# persists values across those re-runs within a single browser session.
# ─────────────────────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    # Start on the config page so the user sets up the LLM before chatting
    st.session_state.page = "llm-config"

if "messages" not in st.session_state:
    # Chat history — list of dicts with role/content/meta/stages keys
    st.session_state.messages = []

if "processor" not in st.session_state:
    # ComplianceProcessor instance — None until LLM is connected
    st.session_state.processor = None

if "model_service" not in st.session_state:
    # ModelLoaderService instance — None until connection test passes
    st.session_state.model_service = None

if "last_csv" not in st.session_state:
    # Bytes of the last query result as CSV — used by the download button
    st.session_state.last_csv = None


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE INITIALISATION
# Called when the user submits the LLM config form.
# Builds the full LangGraph pipeline and tests the LLM connection.
# ─────────────────────────────────────────────────────────────────────────────

def initialize_pipeline(model_name: str, base_url: str, api_key: str):
    """
    Build and connect the full NL2SQL pipeline.

    Steps:
      1. Copy default ModelSettings and override with user-supplied values.
      2. Create a ModelLoaderService and call load() to init the HTTP client.
      3. Call test_connection() — sends a tiny "Reply with OK." request.
      4. Build the compiled LangGraph from build_nl2sql_graph().
      5. Wrap in a ComplianceProcessor and return (service, processor).
    """
    try:
        # Start from defaults defined in utils/config.py ModelSettings
        base_settings = get_settings().model.model_copy(deep=True)

        # Override only the values the user supplied in the form
        model_settings = base_settings.model_copy(update={
            "provider":       "dlh",
            "model_name":     model_name,
            "dlh_base_url":   base_url,
            "dlh_api_key":    api_key,
            "dlh_verify_ssl": True,
        })

        # Create the HTTP client wrapper for the DLH inference server
        model_service = ModelLoaderService(settings=model_settings)
        model_service.load()             # initialises the OpenAI-compatible client
        model_service.test_connection()  # sends "Reply with OK." to verify auth

        # Resolve the SQLite database path from settings
        db_path = get_settings().database.db_path

        # Build and compile the 6-node LangGraph StateGraph
        compiled_graph = build_nl2sql_graph(model_service=model_service, db_path=db_path)

        # Wrap the graph in the thin orchestrator that maps API models ↔ AgentState
        processor = ComplianceProcessor(compiled_graph=compiled_graph)

        return model_service, processor

    except Exception as e:
        # Log full traceback for debugging, then re-raise so the UI shows an error
        LOGGER.exception("Pipeline initialization failed")
        raise e


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# Always visible — shows the two page buttons and a backend status indicator.
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand block at the top of the sidebar
    st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">SBI Compliance Chatbot</div>
            <div class="sidebar-brand-sub">LangGraph &middot; NL2SQL &middot; DLH On-prem LLM</div>
        </div>
    """, unsafe_allow_html=True)

    # Page navigation buttons
    if st.button("\u2699  LLM Configuration", use_container_width=True):
        st.session_state.page = "llm-config"

    if st.button("\u203A\u203A  Chat", use_container_width=True):
        st.session_state.page = "chat"

    st.divider()

    # Backend status badge — green when pipeline is live, red when not configured
    if st.session_state.processor:
        st.markdown(
            '<div class="status-badge online">'
            '<span class="status-dot online"></span>Backend Active</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-badge offline">'
            '<span class="status-dot offline"></span>Backend Offline</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: LLM CONFIGURATION
# Lets the user enter model name, base URL, and API key, then test + save.
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.page == "llm-config":

    # Page header banner
    st.markdown("""
        <div class="app-header">
            <div>
                <div class="app-header-title">LLM Configuration</div>
                <div class="app-header-sub">Connect to the DLH on-prem OpenAI-compatible inference server</div>
            </div>
            <span class="app-header-badge">&#x2699; SETUP</span>
        </div>
    """, unsafe_allow_html=True)

    # Pre-fill input fields with whatever is already saved on disk
    saved_cfg = load_config_from_disk()
    def_model = saved_cfg.get("model_name", "google/gemma-4-31b-it") if saved_cfg else "google/gemma-4-31b-it"
    def_url   = saved_cfg.get("base_url",   "http://10.190.236.15:9000/api/v1") if saved_cfg else "http://10.190.236.15:9000/api/v1"
    def_key   = saved_cfg.get("api_key",    "") if saved_cfg else ""

    # Two-column layout: configuration form on the left, saved preview on the right
    col1, col2 = st.columns([1, 1], gap="large")

    # ── LEFT COLUMN: configuration form ──────────────────────────────────────
    with col1:
        st.markdown("""
            <div class="card-header">
                <div class="card-icon">&#x2699;</div>
                <div>
                    <div class="card-title">Model Connection</div>
                    <div class="card-subtitle">Enter DLH inference server credentials and click Test & Save.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.form("config_form", clear_on_submit=False):
            # Three credential fields — rendered inside the card
            model_name = st.text_input("Model Name",   value=def_model,
                                       placeholder="google/gemma-4-31b-it")
            base_url   = st.text_input("DLH Base URL", value=def_url,
                                       placeholder="http://host:9000/api/v1")
            api_key    = st.text_input("DLH API Key",  value=def_key,
                                       type="password", placeholder="********")

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                # Primary button: test the connection and save credentials on success
                submit = st.form_submit_button(
                    "\u25BA  Test & Save", type="primary", use_container_width=True
                )
            with btn_col2:
                # Secondary button: reload saved values from disk
                if st.form_submit_button("\u21BA  Reload Saved", use_container_width=True):
                    st.rerun()

            if submit:
                with st.spinner("Testing LLM connection..."):
                    try:
                        # Attempt to build the full pipeline (raises on auth/network failure)
                        svc, proc = initialize_pipeline(model_name, base_url, api_key)

                        # Store the live pipeline objects in session state
                        st.session_state.model_service = svc
                        st.session_state.processor     = proc

                        # Persist credentials so they survive hot-reloads
                        save_config_to_disk(model_name, base_url, api_key)

                        st.success("[OK]  LLM connection successful \u2014 credentials saved.")
                    except Exception as e:
                        st.error(f"[ERR]  Connection failed: {str(e)}")

    # ── RIGHT COLUMN: saved config preview ───────────────────────────────────
    with col2:
        st.markdown("""
            <div class="card-header">
                <div class="card-icon">&#x2261;</div>
                <div>
                    <div class="card-title">Saved Configuration</div>
                    <div class="card-subtitle">Credentials stored locally — never committed to git.</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if saved_cfg:
            # Render each credential as a structured info row
            masked_key = "********" if saved_cfg.get("api_key") else "(empty)"
            st.markdown(f"""
                <div class="card-accent">
                    <span class="section-label">Active Credentials</span>
                    <div class="info-row">
                        <span class="info-key">Provider</span>
                        <span class="info-val">dlh</span>
                    </div>
                    <div class="info-row">
                        <span class="info-key">Model</span>
                        <span class="info-val">{saved_cfg.get("model_name","-")}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-key">Base URL</span>
                        <span class="info-val">{saved_cfg.get("base_url","-")}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-key">API Key</span>
                        <span class="info-val">{masked_key}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Also show the raw JSON in the dark code block for quick copy-paste
            json_data = {
                "provider":     "dlh",
                "model_name":   saved_cfg["model_name"],
                "dlh_base_url": saved_cfg["base_url"],
                "dlh_api_key":  "********",  # never display the real key in the UI
            }
            st.markdown(
                f'<span class="code-label">JSON Preview</span>'
                f'<div class="code-block">{json.dumps(json_data, indent=4)}</div>',
                unsafe_allow_html=True,
            )
        else:
            # Nothing saved yet — prompt the user to fill in the form on the left
            st.markdown("""
                <div class="card" style="text-align:center; padding: 36px 24px;">
                    <div style="font-size:36px; margin-bottom:12px; opacity:0.4;">&#x2205;</div>
                    <div style="font-size:15px; font-weight:600; color:#374151; margin-bottom:6px;">
                        No Configuration Saved
                    </div>
                    <div style="font-size:13px; color:#6b7280; line-height:1.6;">
                        Fill in the form on the left and click<br>
                        <strong>Test &amp; Save</strong> to store your credentials.
                    </div>
                </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CHAT
# Conversational interface — renders chat history, stage pills, and the
# st.chat_input box at the bottom.
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.page == "chat":

    # Page header banner
    st.markdown("""
        <div class="app-header">
            <div>
                <div class="app-header-title">Compliance Intelligence Chat</div>
                <div class="app-header-sub">Six LangGraph nodes: Intent &#x2192; Schema &#x2192; SQL Writer &#x2192; SQL Review &#x2192; Validator &#x2192; Executor</div>
            </div>
            <span class="app-header-badge">&#x25CE; CHAT</span>
        </div>
    """, unsafe_allow_html=True)

    # ── Stage pipeline track ──────────────────────────────────────────────────
    # One pill per node; highlights active nodes from the most recent query.
    stages_list = [
        "Intent Checker",
        "Schema Checker",
        "SQL Writer",
        "SQL Review",
        "SQL Validator",
        "Executor",
    ]

    # Extract stage tags from the last bot message (or empty if no messages yet)
    last_stages = st.session_state.messages[-1].get("stages", []) if st.session_state.messages else []

    # Build the HTML pill track — label only, no icon characters
    pill_html = '<div class="pipeline-track">'
    for label in stages_list:
        # Map "SQL Writer" -> "sql_writer" to match stage tag format
        is_active = any(label.lower().replace(" ", "_") in trace.lower() for trace in last_stages)
        cls = "stage-pill active" if is_active else "stage-pill"
        pill_html += f'<span class="{cls}">{label}</span>'
    pill_html += '</div>'
    st.markdown(pill_html, unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────────
    # Re-render every stored message on each script re-run.
    if not st.session_state.messages:
        # Empty state placeholder when no conversation has started yet
        st.markdown("""
            <div class="chat-empty">
                <div class="chat-empty-icon">&#x25CE;</div>
                <div class="chat-empty-title">Start a Compliance Query</div>
                <div class="chat-empty-sub">
                    Ask a natural-language question about the compliance data.<br>
                    Example: <em>"How many senior citizen accounts have KYC flag N?"</em>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                # User bubble — right-aligned navy gradient
                st.markdown(
                    f'<div class="chat-row"><div class="msg-user">{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )
            elif msg["role"] == "bot":
                # Bot bubble — left-aligned white card
                st.markdown(
                    f'<div class="chat-row"><div class="msg-bot">{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )
            elif msg["role"] == "notice":
                # Error or clarification notice — colour depends on type
                type_cls = "msg-notice-blocked" if msg["type"] == "error" else "msg-notice-clarify"
                st.markdown(
                    f'<div class="{type_cls}">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

            # If this message has a metadata block (trace, SQL, data), render it
            if "meta" in msg:
                st.markdown(
                    f'<span class="code-label">Agent Trace &middot; SQL &middot; Results</span>'
                    f'<div class="code-block">{msg["meta"]}</div>',
                    unsafe_allow_html=True,
                )

    # ── CSV download button ───────────────────────────────────────────────────
    # Shown only when the last query produced result rows
    if st.session_state.last_csv:
        st.download_button(
            label="\u2193  Download Results as CSV",
            data=st.session_state.last_csv,
            file_name="compliance_results.csv",
            mime="text/csv",
            key="global_csv_btn",
        )

    # ── Chat input ────────────────────────────────────────────────────────────
    # st.chat_input appears fixed at the bottom of the page.
    # It returns None until the user submits a message.
    if prompt := st.chat_input("Ask a compliance question — e.g. How many accounts in Mumbai circle?"):
        if not st.session_state.processor:
            # Pipeline not ready — direct the user to the config page
            st.error("\u2699  Please configure the LLM connection first (sidebar \u2192 LLM Configuration).")
        else:
            # Add the user's message to the history immediately
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.spinner("Agents collaborating..."):
                try:
                    # Build the Pydantic request model — fixed question_id per session
                    from genai.core.schemas import ComplianceChatRequest
                    request_obj = ComplianceChatRequest(question=prompt, question_id="st_session")

                    # Run the full 6-node LangGraph pipeline and get the response
                    response = st.session_state.processor.process_query_with_orchestration(request_obj)

                    if response.needs_clarification:
                        # IntentChecker decided the question is too vague to process
                        st.session_state.messages.append({
                            "role": "notice",
                            "type": "clarify",
                            "content": response.clarification_question,
                        })
                    elif response.error:
                        # A pipeline node returned an error (e.g. max retries exceeded)
                        st.session_state.messages.append({
                            "role": "notice",
                            "type": "error",
                            "content": response.error,
                        })
                    else:
                        # Success — encode result rows as CSV for the download button
                        if response.df_output:
                            df = pd.DataFrame(response.df_output)
                            st.session_state.last_csv = df.to_csv(index=False).encode("utf-8")
                        else:
                            # No rows returned — clear any previous CSV download
                            st.session_state.last_csv = None

                        # Build the metadata block rendered in the dark code box
                        meta_content  = f"Agent Trace  :  {' > '.join(response.stages)}\n"
                        meta_content += f"Summary      :  {response.result_summary}\n\n"
                        meta_content += f"SQL\n{'-'*60}\n{response.sql_query}\n\n"
                        meta_content += f"Data (first rows)\n{'-'*60}\n{json.dumps(response.df_output, indent=2)}"

                        # Append the full bot response to session history
                        st.session_state.messages.append({
                            "role":    "bot",
                            "content": f"[OK] Query completed \u2014 {response.result_summary}",
                            "meta":    meta_content,
                            "stages":  response.stages,
                        })

                except Exception as e:
                    # Catch any unexpected error and surface it as a notice card
                    st.session_state.messages.append({
                        "role": "notice",
                        "type": "error",
                        "content": f"Unexpected error: {str(e)}",
                    })

            # Force a full re-run so the new message renders immediately
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — NEW CHAT BUTTON (chat page only)
# Clears chat history and the cached CSV so the user can start fresh.
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.page == "chat":
    with st.sidebar:
        st.divider()
        if st.button("\u2715  New Chat", use_container_width=True):
            # Wipe history and CSV cache, then re-run to show an empty chat
            st.session_state.messages = []
            st.session_state.last_csv = None
            st.rerun()
