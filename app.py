import streamlit as st
import pypdf
import requests
import json
import re
import time

st.set_page_config(page_title="FactCheck Agent", page_icon="🔍", layout="wide")

st.markdown("""
<style>
.stApp { background: #0f172a; color: #e2e8f0; }
.hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
    border: 1px solid #00d4aa33; border-radius: 16px;
    padding: 2rem 2.5rem; margin-bottom: 2rem; text-align: center;
}
.hero h1 { font-size: 2.4rem; color: #00d4aa; margin: 0; }
.hero p { color: #94a3b8; font-size: 1.05rem; margin-top: 0.5rem; }
.card { background: #1e293b; border-radius: 12px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; border-left: 4px solid #334155; }
.card-verified { border-left-color: #22c55e; }
.card-inaccurate { border-left-color: #f59e0b; }
.card-false { border-left-color: #ef4444; }
.card-unverified { border-left-color: #64748b; }
.badge { display: inline-block; padding: 2px 12px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.5rem; }
.badge-verified { background:#14532d; color:#4ade80; }
.badge-inaccurate { background:#451a03; color:#fbbf24; }
.badge-false { background:#450a0a; color:#f87171; }
.badge-unverified { background:#1e293b; color:#94a3b8; border:1px solid #475569; }
.claim-text { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.4rem; }
.explanation { font-size: 0.9rem; color: #94a3b8; }
.real-fact { font-size: 0.9rem; color: #34d399; margin-top: 0.4rem; }
.stat-box { background: #1e293b; border-radius: 10px; padding: 1rem; text-align: center; }
.stat-num { font-size: 2rem; font-weight: 800; }
.stat-label { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }
.stButton > button { background: #00d4aa; color: #0f172a; font-weight: 700; border: none; border-radius: 8px; padding: 0.6rem 2rem; font-size: 1rem; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🔍 FactCheck Agent</h1>
  <p>Upload any PDF — we extract claims, search the live web, and flag what's <b>True</b>, <b>Outdated</b>, or <b>False</b>.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
    serper_key = st.text_input("Serper API Key", type="password", placeholder="your-serper-key")
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


def extract_text_from_pdf(file):
    reader = pypdf.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def call_gemini(prompt, gemini_key):
    # UPDATED MODEL NAME TO 3.1-FLASH
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + gemini_key
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}
    }
    
    # Retry logic for 429 errors
    for attempt in range(5):
        r = requests.post(url, json=body, timeout=60)
        if r.status_code == 429:
            # Wait longer after each failed attempt (30s, 60s, etc.)
            st.warning(f"Rate limited. Retrying in {30 * (attempt + 1)} seconds...")
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    
    st.error("Too many requests. Please wait a few minutes before trying again.")
    return None


def extract_claims(text, gemini_key):
    prompt = (
        "You are a fact-checking assistant. Extract all specific, verifiable factual claims from the text below.\n\n"
        "Focus ONLY on:\n"
        "- Statistics and percentages\n"
        "- Dates and years\n"
        "- Financial figures\n"
        "- Named facts with numbers\n"
        "- Technical specifications\n\n"
        "Return a JSON array of objects. Each object must have:\n"
        '"claim": the exact claim as stated\n'
        '"context": one sentence of surrounding context\n'
        '"search_query": a good Google search query to verify this (5-8 words)\n\n'
        "Return ONLY valid JSON. No markdown, no explanation, no code fences.\n\n"
        "TEXT:\n" + text[:8000]
    )
    raw = call_gemini(prompt, gemini_key)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw)
    return json.loads(raw.strip())


def web_search(query, serper_key):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"q": query, "num": 5}, timeout=30)
    r.raise_for_status()
    data = r.json()
    snippets = []
    if "answerBox" in data:
        ab = data["answerBox"]
        snippets.append(ab.get("answer") or ab.get("snippet", ""))
    for res in data.get("organic", [])[:4]:
        snippets.append(res.get("title", "") + " - " + res.get("snippet", ""))
    return " | ".join(snippets)[:3000]


def verify_claim(claim, evidence, gemini_key):
    prompt = (
        "You are a strict fact-checker. Given a claim and web evidence, return a verdict.\n\n"
        "CLAIM: " + claim["claim"] + "\n"
        "CONTEXT: " + claim.get("context", "") + "\n\n"
        "WEB EVIDENCE:\n" + evidence + "\n\n"
        "Return a JSON object with EXACTLY these keys:\n"
        "verdict: one of Verified, Inaccurate, False, Unverified\n"
        "explanation: 1-2 sentences explaining your verdict\n"
        "real_fact: if Inaccurate or False, state the correct fact. Otherwise null.\n"
        "confidence: High, Medium, or Low\n\n"
        "Rules:\n"
        "Verified means evidence clearly supports the claim\n"
        "Inaccurate means claim has wrong numbers or dates but topic exists\n"
        "False means evidence contradicts the claim\n"
        "Unverified means insufficient evidence\n\n"
        "Return ONLY valid JSON. No markdown, no code fences."
    )
    raw = call_gemini(prompt, gemini_key)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw)
    result = json.loads(raw.strip())
    result["claim"] = claim["claim"]
    result["context"] = claim.get("context", "")
    return result


def verdict_badge(v):
    icons = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌", "Unverified": "🔘"}
    css = {"Verified": "verified", "Inaccurate": "inaccurate", "False": "false", "Unverified": "unverified"}
    return '<span class="badge badge-' + css.get(v, "unverified") + '">' + icons.get(v, "🔘") + " " + v + "</span>"


uploaded = st.file_uploader("📄 Upload a PDF to fact-check", type=["pdf"])

if uploaded:
    if not gemini_key or not serper_key:
        st.warning("⚠️ Please enter both API keys in the sidebar.")
        st.stop()

    if st.button("🚀 Run Fact-Check"):
        results = []

        with st.spinner("📄 Extracting text from PDF..."):
            text = extract_text_from_pdf(uploaded)
            if len(text.strip()) < 50:
                st.error("Could not extract readable text from this PDF.")
                st.stop()
            st.success("✅ Extracted " + str(len(text)) + " characters from PDF")

        with st.spinner("🧠 Identifying claims with Gemini..."):
            try:
                claims = extract_claims(text, gemini_key)
                if not claims:
                    st.warning("No verifiable claims found in this document.")
                    st.stop()
                st.success("✅ Found " + str(len(claims)) + " claims to verify")
            except Exception as e:
                st.error("Gemini error during claim extraction: " + str(e))
                st.stop()

        progress = st.progress(0, text="Verifying claims...")
        status = st.empty()

        for i, claim in enumerate(claims):
            status.markdown("🔍 Verifying claim " + str(i + 1) + "/" + str(len(claims)))
            try:
                evidence = web_search(claim.get("search_query", claim["claim"]), serper_key)
                time.sleep(3)
                verdict = verify_claim(claim, evidence, gemini_key)
                results.append(verdict)
            except Exception as e:
                results.append({
                    "claim": claim["claim"],
                    "context": claim.get("context", ""),
                    "verdict": "Unverified",
                    "explanation": "Error: " + str(e),
                    "real_fact": None,
                    "confidence": "Low",
                })
            progress.progress((i + 1) / len(claims))

        status.empty()
        progress.empty()

        st.markdown("---")
        st.markdown("## 📊 Fact-Check Report")

        counts = {v: sum(1 for r in results if r["verdict"] == v)
                  for v in ["Verified", "Inaccurate", "False", "Unverified"]}

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="stat-box"><div class="stat-num" style="color:#22c55e">' + str(counts["Verified"]) + '</div><div class="stat-label">✅ Verified</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="stat-box"><div class="stat-num" style="color:#f59e0b">' + str(counts["Inaccurate"]) + '</div><div class="stat-label">⚠️ Inaccurate</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="stat-box"><div class="stat-num" style="color:#ef4444">' + str(counts["False"]) + '</div><div class="stat-label">❌ False</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="stat-box"><div class="stat-num" style="color:#64748b">' + str(counts["Unverified"]) + '</div><div class="stat-label">🔘 Unverified</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        filter_opt = st.selectbox("Filter by verdict:", ["All", "Verified", "Inaccurate", "False", "Unverified"])
        filtered = results if filter_opt == "All" else [r for r in results if r["verdict"] == filter_opt]

        for r in filtered:
            v = r.get("verdict", "Unverified")
            css = {"Verified": "verified", "Inaccurate": "inaccurate", "False": "false", "Unverified": "unverified"}.get(v, "unverified")
            conf_color = {"High": "#22c55e", "Medium": "#f59e0b", "Low": "#ef4444"}.get(r.get("confidence", ""), "#64748b")
            real_fact_html = ""
            if r.get("real_fact"):
                real_fact_html = '<div class="real-fact">💡 <b>Real fact:</b> ' + str(r["real_fact"]) + "</div>"
            st.markdown(
                '<div class="card card-' + css + '">'
                + verdict_badge(v)
                + '<span style="font-size:0.75rem;color:' + conf_color + ';margin-left:8px;">● ' + r.get("confidence", "?") + ' confidence</span>'
                + '<div class="claim-text">"' + r["claim"] + '"</div>'
                + '<div class="explanation">' + r.get("explanation", "") + "</div>"
                + real_fact_html + "</div>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.download_button(
            label="⬇️ Download Full Report (JSON)",
            data=json.dumps(results, indent=2),
            file_name="factcheck_report.json",
            mime="application/json",
        )
