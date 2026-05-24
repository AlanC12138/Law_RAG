"""Root conftest.py — runs before any test or app imports.

Stubs out heavy ML / external-service libraries so the test suite can run
without installing PyTorch, Qdrant, sentence-transformers, etc.  Only the
modules that would otherwise prevent the FastAPI app from being *imported*
need to be stubbed here; the actual ML functionality is mocked per-test
inside tests/.
"""
from __future__ import annotations

import sys
import types


def _stub(name: str, **attrs) -> types.ModuleType:
    """Create and register a minimal stub module."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------------
# qdrant_client  — used by QdrantVectorStore
# ---------------------------------------------------------------------------

def _make_qdrant_stubs() -> None:
    class _FakeQdrantClient:
        def __init__(self, *args, **kwargs): pass
        def get_collections(self): return types.SimpleNamespace(collections=[])
        def create_collection(self, *args, **kwargs): pass
        def collection_exists(self, *args, **kwargs): return False
        def upsert(self, *args, **kwargs): pass
        def search(self, *args, **kwargs): return []
        def delete(self, *args, **kwargs): pass
        def scroll(self, *args, **kwargs): return ([], None)

    class _VectorParams:
        def __init__(self, *args, **kwargs): pass

    class _Distance:
        COSINE = "Cosine"

    class _PointStruct:
        def __init__(self, *args, **kwargs): pass

    class _Filter:
        def __init__(self, *args, **kwargs): pass

    class _FieldCondition:
        def __init__(self, *args, **kwargs): pass

    class _MatchValue:
        def __init__(self, *args, **kwargs): pass

    qdrant = _stub("qdrant_client", QdrantClient=_FakeQdrantClient)
    qdrant_models = _stub(
        "qdrant_client.models",
        VectorParams=_VectorParams,
        Distance=_Distance,
        PointStruct=_PointStruct,
        Filter=_Filter,
        FieldCondition=_FieldCondition,
        MatchValue=_MatchValue,
    )
    qdrant.models = qdrant_models
    # Some imports use qdrant_client.http.models
    qdrant_http = _stub("qdrant_client.http")
    qdrant_http_models = _stub(
        "qdrant_client.http.models",
        VectorParams=_VectorParams,
        Distance=_Distance,
        PointStruct=_PointStruct,
        Filter=_Filter,
        FieldCondition=_FieldCondition,
        MatchValue=_MatchValue,
    )
    qdrant_http.models = qdrant_http_models


_make_qdrant_stubs()


# ---------------------------------------------------------------------------
# sentence_transformers — used by CrossEncoderReranker
# ---------------------------------------------------------------------------

def _make_sentence_transformer_stubs() -> None:
    class _FakeCrossEncoder:
        def __init__(self, *args, **kwargs): pass
        def predict(self, pairs): return [0.5] * len(pairs)

    _stub("sentence_transformers", CrossEncoder=_FakeCrossEncoder)
    _stub("sentence_transformers.cross_encoder", CrossEncoder=_FakeCrossEncoder)


_make_sentence_transformer_stubs()


# ---------------------------------------------------------------------------
# rank_bm25
# ---------------------------------------------------------------------------

class _FakeBM25Okapi:
    def __init__(self, corpus, *args, **kwargs): pass
    def get_scores(self, query): return []

_stub("rank_bm25", BM25Okapi=_FakeBM25Okapi)


# ---------------------------------------------------------------------------
# pdfplumber, pytesseract, fitz (PyMuPDF), python-docx
# ---------------------------------------------------------------------------

_stub("pdfplumber")
_stub("pytesseract")

# fitz (PyMuPDF)
class _FakePage:
    def get_text(self, *a, **kw): return ""
    def get_pixmap(self, *a, **kw): return types.SimpleNamespace(tobytes=lambda *a, **kw: b"")

class _FakeDocument:
    def __iter__(self): return iter([])
    def __len__(self): return 0
    def __enter__(self): return self
    def __exit__(self, *a): pass

_stub("fitz", open=lambda *a, **kw: _FakeDocument())

# python-docx
class _FakeDocx:
    paragraphs = []
    tables = []

_stub("docx", Document=lambda *a, **kw: _FakeDocx())

# openai (async client used by OpenAIProvider and OpenAIEmbeddingProvider)
class _FakeAsyncOpenAI:
    def __init__(self, *args, **kwargs):
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=None  # patched per-test if needed
            )
        )
        self.embeddings = types.SimpleNamespace(
            create=None  # patched per-test if needed
        )

_stub("openai", AsyncOpenAI=_FakeAsyncOpenAI)
