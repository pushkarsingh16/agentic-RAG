import time
import logfire
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings

BATCH_SIZE = 50
_GEMINI_DIM = 3072
_FALLBACK_DIM = 768  # all-mpnet-base-v2

# Free-tier gemini-embedding-001 is roughly 90 RPM / 950 RPD. Pace requests so we
# don't slam into the per-minute limit; the daily cap still needs to be solved
# by cutting request *count* (see filtering note in processor.py), not just spacing.
_MIN_SECONDS_BETWEEN_CALLS = 60.0 / 80  # stay a bit under 90 RPM
_last_call_ts = 0.0

_active_model = None
_model_type: str | None = None  # "gemini" or "fallback"


# ── Model initialisation ───────────────────────────────────────────────────────

def _probe_gemini():
    """
    Try to verify Gemini is reachable. Retries transient errors (rate limit /
    503) with backoff instead of bailing on the first hiccup — a single 429
    during the probe used to permanently switch the whole process over to the
    sentence-transformers fallback for the rest of its life.
    """
    model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",  # was the non-existent "gemini-embedding-2-preview"
        google_api_key=settings.GEMINI_API_KEY,
    )
    for attempt in range(4):
        try:
            model.embed_query("probe")
            logfire.info("Gemini embeddings ready (gemini-embedding-001, 3072-dim).")
            return model
        except Exception as e:
            err = str(e).lower()
            is_transient = any(x in err for x in ("429", "rate", "quota", "resource_exhausted", "503"))
            if is_transient and attempt < 3:
                wait = 2 ** attempt
                logfire.warning(f"Gemini probe transient error — retrying in {wait}s: {e}")
                time.sleep(wait)
                continue
            logfire.warning(f"Gemini probe failed: {e}. Will use sentence-transformers fallback.")
            return None
    return None


def _load_fallback():
    from sentence_transformers import SentenceTransformer
    logfire.info("Loading sentence-transformers fallback (all-mpnet-base-v2, 768-dim).")
    return SentenceTransformer("all-mpnet-base-v2")


def _init():
    """Initialise embedding model once per process. Called lazily on first use."""
    global _active_model, _model_type
    if _active_model is not None:
        return

    gemini = _probe_gemini()
    if gemini:
        _active_model = gemini
        _model_type = "gemini"
    else:
        _active_model = _load_fallback()
        _model_type = "fallback"


# ── Public helpers ─────────────────────────────────────────────────────────────

def get_embedding_dim() -> int:
    """Return the vector dimension for the active model. Call after _init()."""
    _init()
    return _GEMINI_DIM if _model_type == "gemini" else _FALLBACK_DIM


# ── Batch embedding with retry ─────────────────────────────────────────────────

def _throttle():
    """Proactively space out calls instead of only reacting to 429s after the fact."""
    global _last_call_ts
    elapsed = time.time() - _last_call_ts
    if elapsed < _MIN_SECONDS_BETWEEN_CALLS:
        time.sleep(_MIN_SECONDS_BETWEEN_CALLS - elapsed)
    _last_call_ts = time.time()


def _embed_batch(batch: list[str]) -> list[list[float]]:
    if _model_type == "gemini":
        # Exponential backoff: 1 s → 2 s → 4 s → 8 s (4 attempts total)
        for attempt in range(4):
            try:
                _throttle()
                return _active_model.embed_documents(batch)
            except Exception as e:
                err = str(e).lower()
                is_rate_limit = any(x in err for x in ("429", "rate", "quota", "resource_exhausted"))
                if is_rate_limit and attempt < 3:
                    wait = 2 ** attempt
                    logfire.warning(
                        f"Gemini rate limit hit — retrying in {wait}s "
                        f"(attempt {attempt + 1}/4)."
                    )
                    time.sleep(wait)
                else:
                    logfire.error(f"Gemini embedding failed: {e}")
                    raise
        raise RuntimeError("Gemini rate limit persisted after 4 attempts.")
    else:
        return _active_model.encode(batch, show_progress_bar=False).tolist()


# ── Public API (same signatures as before) ─────────────────────────────────────

def embed_query(query: str) -> list[float]:
    _init()
    if _model_type == "gemini":
        return _active_model.embed_query(query)
    return _active_model.encode([query])[0].tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    _init()
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        with logfire.span("Embed batch", model=_model_type, start=i, size=len(batch)):
            all_embeddings.extend(_embed_batch(batch))
    return all_embeddings
