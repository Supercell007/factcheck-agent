import streamlit as st
import fitz  # PyMuPDF
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
  .card-false     { border-left-color: #ef4444; }
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
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    return json.loads(raw)


def web_search(query: str, serper_key: str) -> str:
    """Search web via Serper, return a condensed text snippet."""
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
    body = {"q": query, "num": 5}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()

    snippets = []
    # Answer box
    if "answerBox" in data:
        ab = data["answerBox"]
        snippets.append(ab.get("answer") or ab.get("snippet", ""))
    # Organic results
    for res in data.get("organic", [])[:4]:
        snippets.append(f"{res.get('title','')} — {res.get('snippet','')}")
    return " | ".join(snippets)[:3000]


def verify_claim(claim: dict, web_evidence: str, gemini_key: str) -> dict:
    """Ask Gemini to verdict the claim given web evidence."""
    prompt = f"""You are a strict fact-checker. Given a claim and web search evidence, return a verdict.

CLAIM: {claim['claim']}
CONTEXT: {claim.get('context', '')}

WEB EVIDENCE:
{web_evidence}

Return a JSON object with EXACTLY these keys:
- "verdict": one of "Verified", "Inaccurate", "False", "Unverified"
- "explanation": 1-2 sentences explaining your verdict
- "real_fact": if Inaccurate or False, state the correct fact based on evidence. Otherwise null.
- "confidence": "High", "Medium", or "Low"

Rules:
- "Verified": evidence clearly supports the claim
- "Inaccurate": claim has wrong numbers/dates but the topic exists (e.g. outdated stat)
- "False": evidence contradicts the claim or claim is fabricated
- "Unverified": insufficient evidence to confirm or deny

Return ONLY valid JSON, no markdown.
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512}}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    result = json.loads(raw)
    result["claim"]   = claim["claim"]
    result["context"] = claim.get("context", "")
    return result


def verdict_badge(v: str) -> str:
    icons = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "🔘"}
    css   = {"Verified": "verified", "Inaccurate": "inaccurate", "False": "false", "Unverified": "unverified"}
    icon  = icons.get(v, "🔘")
    cls   = css.get(v, "unverified")
    return f'<span class="badge badge-{cls}">{icon} {v}</span>'


# ── Main UI ────────────────────────────────────────────────────────────────────

uploaded = st.file_uploader("📄 Upload a PDF to fact-check", type=["pdf"])

if uploaded:
    if not gemini_key or not serper_key:
        st.warning("⚠️ Please enter both API keys in the sidebar to continue.")
        st.stop()

    if st.button("🚀 Run Fact-Check"):
        results = []

        # Step 1: Extract text
        with st.spinner("📄 Extracting text from PDF..."):
            text = extract_text_from_pdf(uploaded)
            if len(text.strip()) < 50:
                st.error("Could not extract readable text from this PDF.")
                st.stop()
            st.success(f"✅ Extracted {len(text):,} characters from PDF")

        # Step 2: Extract claims
        with st.spinner("🧠 Identifying verifiable claims with Gemini..."):
            try:
                claims = extract_claims(text, gemini_key)
                if not claims:
                    st.warning("No specific verifiable claims found in this document.")
                    st.stop()
                st.success(f"✅ Found {len(claims)} claims to verify")
            except Exception as e:
                st.error(f"Gemini error during claim extraction: {e}")
                st.stop()

        # Step 3+4: Search + Verify each claim
        progress = st.progress(0, text="Verifying claims...")
        status   = st.empty()

        for i, claim in enumerate(claims):
            status.markdown(f"🔍 Verifying claim {i+1}/{len(claims)}: *{claim['claim'][:80]}...*")
            try:
                evidence = web_search(claim.get("search_query", claim["claim"]), serper_key)
                time.sleep(0.3)  # be polite to APIs
                verdict  = verify_claim(claim, evidence, gemini_key)
                results.append(verdict)
            except Exception as e:
                results.append({
                    "claim": claim["claim"],
                    "context": claim.get("context", ""),
                    "verdict": "Unverified",
                    "explanation": f"Error during verification: {str(e)}",
                    "real_fact": None,
                    "confidence": "Low",
                })
            progress.progress((i + 1) / len(claims))

        status.empty()
        progress.empty()

        # ── Results ────────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📊 Fact-Check Report")

        # Summary stats
        counts = {v: sum(1 for r in results if r["verdict"] == v)
                  for v in ["Verified", "Inaccurate", "False", "Unverified"]}

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#22c55e">{counts["Verified"]}</div><div class="stat-label">✅ Verified</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#f59e0b">{counts["Inaccurate"]}</div><div class="stat-label">⚠️ Inaccurate</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#ef4444">{counts["False"]}</div><div class="stat-label">❌ False</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#64748b">{counts["Unverified"]}</div><div class="stat-label">🔘 Unverified</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Filter
        filter_opt = st.selectbox("Filter by verdict:", ["All", "Verified", "Inaccurate", "False", "Unverified"])
        filtered = results if filter_opt == "All" else [r for r in results if r["verdict"] == filter_opt]

        # Claim cards
        for r in filtered:
            v   = r.get("verdict", "Unverified")
            css = {"Verified": "verified", "Inaccurate": "inaccurate", "False": "false", "Unverified": "unverified"}.get(v, "unverified")

            real_fact_html = ""
            if r.get("real_fact"):
                real_fact_html = f'<div class="real-fact">💡 <b>Real fact:</b> {r["real_fact"]}</div>'

            conf_color = {"High": "#22c55e", "Medium": "#f59e0b", "Low": "#ef4444"}.get(r.get("confidence",""), "#64748b")

            st.markdown(f"""
<div class="card card-{css}">
  {verdict_badge(v)}
  <span style="font-size:0.75rem;color:{conf_color};margin-left:8px;">● {r.get('confidence','?')} confidence</span>
  <div class="claim-text">"{r['claim']}"</div>
  <div class="explanation">{r.get('explanation','')}</div>
  {real_fact_html}
</div>
""", unsafe_allow_html=True)

        # Download JSON report
        st.markdown("---")
        st.download_button(
            label="⬇️ Download Full Report (JSON)",
            data=json.dumps(results, indent=2),
            file_name="factcheck_report.json",
            mime="application/json",
        )
