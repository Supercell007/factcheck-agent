# 🔍 FactCheck Agent

An AI-powered web app that automatically fact-checks PDF documents by cross-referencing claims against live web data.

## What It Does

1. **Extract** — Reads your PDF and identifies specific verifiable claims (stats, dates, financial figures, technical facts)
2. **Search** — Uses Serper API to search the live web for evidence on each claim
3. **Verify** — Uses Google Gemini to compare the claim against web evidence
4. **Report** — Labels each claim as:
   - ✅ **Verified** — matches current data
   - ⚠️ **Inaccurate** — outdated or wrong numbers
   - ❌ **False** — contradicted by evidence or fabricated
   - 🔘 **Unverified** — insufficient evidence

## Live Demo

👉 [Your deployed app link here]

## Setup & Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/factcheck-agent.git
cd factcheck-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Enter API keys in the sidebar
- **Gemini API key** → [aistudio.google.com](https://aistudio.google.com) (free)
- **Serper API key** → [serper.dev](https://serper.dev) (2,500 free searches)

## Deployment (Streamlit Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → select your repo → set main file as `app.py`
4. Click **Deploy**

## Tech Stack

| Component | Tool |
|-----------|------|
| Frontend | Streamlit |
| PDF Parsing | PyMuPDF (fitz) |
| Claim Extraction | Google Gemini 2.0 Flash |
| Web Search | Serper API |
| Claim Verification | Google Gemini 2.0 Flash |

## Project Structure

```
factcheck-agent/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```
# 🔍 FactCheck Agent

An AI-powered web app that automatically fact-checks PDF documents by cross-referencing claims against live web data.

## What It Does

1. **Extract** — Reads your PDF and identifies specific verifiable claims (stats, dates, financial figures, technical facts)
2. **Search** — Uses Serper API to search the live web for evidence on each claim
3. **Verify** — Uses Google Gemini to compare the claim against web evidence
4. **Report** — Labels each claim as:
   - ✅ **Verified** — matches current data
   - ⚠️ **Inaccurate** — outdated or wrong numbers
   - ❌ **False** — contradicted by evidence or fabricated
   - 🔘 **Unverified** — insufficient evidence

## Live Demo

👉 [Your deployed app link here]

## Setup & Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/factcheck-agent.git
cd factcheck-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

### 4. Enter API keys in the sidebar
- **Gemini API key** → [aistudio.google.com](https://aistudio.google.com) (free)
- **Serper API key** → [serper.dev](https://serper.dev) (2,500 free searches)

## Deployment (Streamlit Cloud)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → select your repo → set main file as `app.py`
4. Click **Deploy**

## Tech Stack

| Component | Tool |
|-----------|------|
| Frontend | Streamlit |
| PDF Parsing | PyMuPDF (fitz) |
| Claim Extraction | Google Gemini 2.0 Flash |
| Web Search | Serper API |
| Claim Verification | Google Gemini 2.0 Flash |

## Project Structure

```
factcheck-agent/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```
