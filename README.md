# 🚚 Welyft Assistant — Agentic RAG Chatbot

A production-styled, agentic Retrieval-Augmented Generation (RAG) assistant built for **Welyft**, a Singapore-based electric-fleet logistics company. The assistant answers questions about Welyft's business, sustainability story, and delivery services by combining instant FAQ lookups with a full LLM-backed retrieval pipeline — complete with reasoning traces, source citations, guardrails, and observability baked in.

This repository contains the **Streamlit frontend** and **processed knowledge base** for the assistant. The UI is designed to talk to a FastAPI backend exposing a `/query` endpoint (see [Architecture](#-architecture) below for the expected contract).

> **Note on scope:** This bundle includes the chat UI (`ui/`) and the pre-processed document chunks (`processed_data/`) that make up the assistant's knowledge base. The backend agent/orchestration code (LangGraph pipeline, retriever, guardrails, ingestion scripts) is inferred from `requirements.txt` and the API calls the UI makes, but is not included in this particular export — see [What's Included](#-whats-included) for the exact file list.

---

## ✨ Features

- **Instant FAQ layer** — Common questions (about Welyft, sustainability, services, careers, policies) are answered immediately from a local dictionary, with zero LLM calls or latency.
- **Agentic fallback** — Anything outside the FAQ set is routed to a backend RAG agent for a full retrieval + generation cycle.
- **Transparent reasoning** — The UI streams the agent's intermediate "thought process" steps live, so users can see what the assistant is doing (retrieving, reranking, synthesizing).
- **Cited sources** — Retrieved context chunks are shown in collapsible panels beneath each answer, so responses are auditable rather than opaque.
- **Session memory** — Each browser session gets a UUID `thread_id` so the backend can maintain conversational context, with a one-click "Clear History & Memory" reset.
- **Full observability** — Every chat turn is wrapped in [Pydantic Logfire](https://pydantic.dev/logfire) spans for distributed tracing between the UI and backend.
- **Two deployment targets** — `ui/app.py` for local development (reads `.env` directly) and `ui/st_cloud_ui.py` for Streamlit Community Cloud (reads `st.secrets`).
- **Branded dark theme** — Custom Streamlit theme (`.streamlit/config.toml`) plus CSS overrides for chat bubbles, expanders, and buttons.

---

## 🗂 What's Included

```
agentic-RAG-main/
├── ui/
│   ├── app.py              # Local/dev UI — loads secrets from a root .env file
│   └── st_cloud_ui.py      # Cloud UI — loads secrets from st.secrets
├── processed_data/
│   └── true/                # Pre-chunked source documents (ready for vector indexing)
│       ├── B2B Model.pdf.json
│       ├── B2C Model.pdf.json
│       ├── C2C Model.pdf.json
│       └── Welyft-Green-Logistics-Press-Release.pdf.json
├── .streamlit/
│   └── config.toml          # Dark theme + brand accent color
├── .vscode/
│   └── tasks.json
├── ADVANCED RAG.code-workspace
├── requirements.txt
└── .gitignore
```

Each file under `processed_data/true/` is a JSON document with the shape:

```json
{
  "filename": "B2B Model.pdf",
  "source_type": "true",
  "chunks": ["... chunk text ..."]
}
```

These represent the ingested source material (Welyft's B2B, B2C, and C2C service model documents, plus a press release) that the retrieval backend is expected to embed and index.

---

## 🏗 Architecture

```
┌─────────────┐        POST /query           ┌──────────────────────┐
│  Streamlit  │  { q, thread_id }             │   FastAPI Backend     │
│     UI      │ ─────────────────────────────▶│  (LangGraph agent)    │
│ (this repo) │                                │                       │
│             │◀───────────────────────────── │  Retrieve → Rerank →  │
└─────────────┘  { answer, sources,            │  Guardrail → Generate │
                    thought_process }           └──────────────────────┘
```

Based on `requirements.txt`, the intended backend stack is:

| Layer | Library | Purpose |
|---|---|---|
| API | FastAPI + Uvicorn | Serves the `/query` endpoint the UI calls |
| Orchestration | LangGraph + LangChain | Cyclic agentic control flow |
| LLM | `langchain-groq` (Llama 3.3) | Fast generation |
| Embeddings | Gemini (`text-embedding-004` / `gemini-embedding-001`) | Document + query embeddings |
| Vector store | Qdrant | Semantic search over `processed_data` |
| Reranking | FlashRank | Local cross-encoder reranking of retrieved chunks |
| Guardrails | NeMo Guardrails | Input/output safety rails |
| LLM Gateway | Portkey | Unified routing, fallbacks, observability |
| Ingestion | `unstructured`, `pypdf`, `pdfplumber`, `python-docx`, `python-pptx` | Parsing source documents (DOCX/PPTX/PDF/HTML) into `processed_data`-style chunks |
| Evaluation | RAGAS, DeepEval, Langfuse | Faithfulness/relevancy scoring and live production monitoring |
| Tracing | Logfire, LangSmith | Distributed tracing across UI ↔ backend |

**Expected `/query` contract:**

Request:
```json
{ "q": "What is Welyft?", "thread_id": "session-uuid" }
```

Response:
```json
{
  "answer": "Welyft is a Singapore-based logistics company...",
  "sources": ["<retrieved chunk 1>", "<retrieved chunk 2>"],
  "thought_process": ["Classified query intent", "Retrieved 4 chunks", "Reranked top 3", "Synthesized answer"]
}
```

---

## 🚀 Getting Started

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd agentic-RAG-main
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root (used by `ui/app.py`):

```bash
# Observability
LOGFIRE_TOKEN=your_logfire_token

# Backend
BACKEND_URL=http://localhost:8000   # defaults to this if unset

# Backend-side keys you will likely need once the RAG backend is running
GROQ_API_KEY=...
GOOGLE_API_KEY=...        # Gemini embeddings
QDRANT_URL=...
QDRANT_API_KEY=...
PORTKEY_API_KEY=...
LANGSMITH_API_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
NVIDIA_API_KEY=...        # NeMo Guardrails / NVIDIA AI Endpoints
```

For Streamlit Community Cloud deployment, set the equivalent values in **Settings → Secrets**, which `ui/st_cloud_ui.py` reads via `st.secrets`.

### 3. Run the backend

The backend (FastAPI app exposing `/query`) isn't part of this bundle — stand it up separately (or point `BACKEND_URL` at wherever it's hosted) before starting the UI, or the assistant will report "Backend Offline" for any question outside the FAQ set.

### 4. Run the UI

**Local development:**
```bash
streamlit run ui/app.py
```

**Cloud-style (reads `st.secrets`, defaults `BACKEND_URL` to `localhost:8000`):**
```bash
streamlit run ui/st_cloud_ui.py
```

Then open the local Streamlit URL (typically `http://localhost:8501`) in your browser.

---

## 💬 Using the Assistant

- Expand any FAQ category (**About Welyft**, **Sustainability**, **Services**, **Business enquiries**, **Careers**, **Policies**, **Contact**) and click a question for an instant, pre-written answer — no backend round-trip.
- For anything else, type into the chat box. The assistant will:
  1. Send your question and session `thread_id` to the backend.
  2. Stream its reasoning steps in a live status panel.
  3. Type out the final answer character-by-character.
  4. Show retrieved source chunks in an expandable panel underneath, if any were used.
- Use **🗑️ Clear History & Memory** in the sidebar to reset the conversation and start a fresh session ID.

---

## 🧠 Knowledge Base

The assistant's retrieval corpus (`processed_data/true/`) currently covers:

- **B2B Model** — enterprise account management, bulk shipments, dedicated fleets, multi-stop routing
- **B2C Model** — individual/consumer delivery flows
- **C2C Model** — peer-to-peer delivery
- **Green Logistics Press Release** — Welyft's sustainability positioning and electric fleet impact

To extend the knowledge base, add new source documents, run them through an ingestion pipeline (parsing + chunking, per the libraries listed in `requirements.txt`), and drop the resulting `<filename>.json` chunk files into `processed_data/true/` (or wherever your backend's indexer reads from) before re-embedding into Qdrant.

---

## 🛠 Tech Stack

`Streamlit` · `FastAPI` · `LangChain` / `LangGraph` · `Groq (Llama 3.3)` · `Gemini Embeddings` · `Qdrant` · `FlashRank` · `NeMo Guardrails` · `Portkey` · `RAGAS` / `DeepEval` · `Langfuse` · `Logfire` / `LangSmith`

---

## 📄 License

Add your license of choice here (e.g., MIT, Apache 2.0).
