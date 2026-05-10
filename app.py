import streamlit as st
import pypdf
import requests
import json
import re
import time

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main { background: #0f172a; }
  .stApp { background: #0f172a; color: #e2e8f0; }

  .hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
    border: 1px solid #00d4aa33;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    text-align: center;
  }
  .hero h1 { font-size: 2.4rem; color: #00d4aa; margin: 0; }
  .hero p  { color: #94a3b8; font-size: 1.05rem; margin-top: 0.5rem; }

  .card {
    background: #1e293b;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid #334155;
  }
  .card-verified  { border-left-color: #22c55e; }
  .card-inaccurate{ border-left-color: #f59e0b; }
  .card-false      { border-left-color: #ef4444; }
  .card-unverified{ border-left-color: #64748b; }

  .badge {
    display: inline-block;
    padding: 2px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }
  .badge-verified  { background:#14532d; color:#4ade80; }
  .badge-inaccurate{ background:#451a03; color:#fbbf24; }
  .badge-false     { background:#450a0a; color:#f87171; }
  .badge-unverified{ background:#1e293b; color:#94a3b8; border:1px solid #475569; }

  .claim-text { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.4rem; }
  .explanation{ font-size: 0.9rem; color: #94a3b8; }
  .real-fact  { font-size: 0.9rem; color: #34d399; margin-top: 0.4rem; }
  .source-link{ font-size: 0.8rem; color: #60a5fa; }

  .stat-box {
    background: #1e293b;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
  }
  .stat-num { font-size: 2rem; font-weight: 800; }
  .stat-label { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }

  div[data-testid="stFileUploader"] {
    background: #1e293b;
    border: 2px dashed #00d4aa55;
    border-radius: 12px;
    padding: 1rem;
  }
  .stButton > button {
    background: #00d4aa;
    color: #0f172a;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 2rem;
    font-size: 1rem;
    width: 100%;
  }
  .stButton > button:hover { background: #00b894; }
</style>
""", unsafe_allow_html=True)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔍 FactCheck Agent</h1>
  <p>Upload any PDF — we extract claims, search the live web, and flag what's <b>True</b>, <b>Outdated</b>, or <b>False</b>.</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar: API Keys ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
    serper_key  = st.text_input("Serper API Key",  type="password", placeholder="your-serper-key")
    st.markdown("---")
    st.markdown("**How it works:**")
    st.markdown("1. 📄 Extract text from PDF")
    st.markdown("2. 🧠 Gemini identifies claims")
    st.markdown("3. 🌐 Serper searches the web")
    st.markdown("4. 🧠 Gemini verifies each claim")
    st.markdown("5. 📊 Report with verdicts")
    st.markdown("---")
    st.markdown("**Verdicts:**")
    st.markdown("✅ **Verified** — matches live data")
    st.markdown("⚠️ **Inaccurate** — outdated/wrong")
    st.markdown("❌ **False** — no evidence found")
    st.markdown("🔘 **Unverified** — can't confirm")

# ── Helper functions ───────────────────────────────────────────────────────────

def extract_text_from_pdf(file) -> str:
    reader = pypdf.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def extract_claims(text: str, gemini_key: str) -> list[dict]:
    """Ask Gemini to pull out verifiable factual claims."""
    prompt = f"""You are a fact-checking assistant. Extract all specific, verifiable factual claims from the text below.

Focus ONLY on:
- Statistics and percentages (e.g. "X% of people...")
- Dates and years (e.g. "Founded in 2005...")
- Financial figures (e.g. "Revenue of $5B...")
- Named facts (e.g. "Country X has population of Y...")
- Technical specifications or version numbers

Return a JSON array of objects. Each object must have:
- "claim": the exact claim as stated
- "context": one sentence of surrounding context
- "search_query": a good Google search query to verify this claim (5-8 words)

Return ONLY valid JSON, no markdown, no explanation.

TEXT:
{text[:8000]}
"""
    # FIXED MODEL NAME TO 1.5-FLASH-LATEST
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raw = re.sub(r"
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1

**Final Security Warning:** Since you mentioned your key was visible in a screenshot, please **delete that key now** at [aistudio.google.com](https://aistudio.google.com/) and create a new one. This protects you from someone else using up your credits!

Does the app work correctly now once you've pasted this in?
