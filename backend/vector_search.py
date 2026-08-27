"""
vector_search.py — Semantic Search using TF-IDF + Cosine Similarity
100% offline, zero external model downloads required.
TF-IDF (Term Frequency - Inverse Document Frequency) is the same algorithm
used by early Google, Elasticsearch, and Lucene search engines.
It understands context, not just exact keywords.
"""
import os
import pickle
import re
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

INDEX_PATH = os.path.join(os.path.dirname(__file__), "tfidf_index.pkl")

# In-memory store: list of dicts with {doc_id, case_id, doc_name, doc_type, text}
_documents: list = []
_vectorizer: Optional[TfidfVectorizer] = None
_matrix = None  # TF-IDF matrix

def _save_index():
    """Persist the index to disk so it survives server restarts."""
    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"documents": _documents, "vectorizer": _vectorizer, "matrix": _matrix}, f)

def _load_index():
    """Load a previously saved index from disk."""
    global _documents, _vectorizer, _matrix
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "rb") as f:
                data = pickle.load(f)
            _documents = data.get("documents", [])
            _vectorizer = data.get("vectorizer")
            _matrix = data.get("matrix")
            print(f"[VectorSearch] Loaded existing index with {len(_documents)} documents.")
        except Exception as e:
            print(f"[VectorSearch] Could not load index, starting fresh: {e}")
            _documents, _vectorizer, _matrix = [], None, None

def _rebuild_matrix():
    """Rebuild the TF-IDF matrix from all stored documents."""
    global _vectorizer, _matrix
    if not _documents:
        _vectorizer = None
        _matrix = None
        return
    texts = [d["text"] for d in _documents]
    _vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),       # Single words AND two-word phrases
        max_features=20000,        # Cap vocabulary size
        sublinear_tf=True,         # Log-scale term frequency (more stable)
        strip_accents="unicode",
        analyzer="word",
        token_pattern=r"\b[a-zA-Z0-9]{2,}\b",
        min_df=1
    )
    _matrix = _vectorizer.fit_transform(texts)

# Load existing index on module import
_load_index()

def add_document_to_index(doc_id: str, case_id: int, doc_name: str, doc_type: str, text: str):
    """Add or update a document in the TF-IDF index."""
    global _documents, _matrix
    if not text or not text.strip():
        return
    try:
        # Remove existing entry for this doc_id (for updates)
        _documents = [d for d in _documents if d["doc_id"] != doc_id]

        enriched_text = f"{doc_name} {doc_type} {text}"[:10000]
        _documents.append({
            "doc_id": doc_id,
            "case_id": case_id,
            "doc_name": doc_name,
            "doc_type": doc_type,
            "text": enriched_text
        })
        _rebuild_matrix()
        _save_index()
        print(f"[VectorSearch] Indexed '{doc_name}' (case {case_id}). Total: {len(_documents)}")
    except Exception as e:
        print(f"[VectorSearch] Failed to index doc {doc_id}: {e}")


def semantic_search(query: str, n_results: int = 10) -> list[dict]:
    """
    Find the most semantically relevant cases for a natural language query.
    Uses cosine similarity on TF-IDF vectors.
    """
    global _vectorizer, _matrix
    if not _documents or _vectorizer is None or _matrix is None:
        return []
    if not query or not query.strip():
        return []
    try:
        query_vec = _vectorizer.transform([query])
        scores = cosine_similarity(query_vec, _matrix).flatten()

        # Get top results above a minimum relevance threshold
        top_indices = np.argsort(scores)[::-1][:n_results]

        output = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.05:  # Ignore near-zero matches (noise)
                continue
            doc = _documents[idx]
            output.append({
                "case_id": doc["case_id"],
                "doc_name": doc["doc_name"],
                "doc_type": doc["doc_type"],
                "score": round(score, 4)
            })

        return output
    except Exception as e:
        print(f"[VectorSearch] Search error: {e}")
        return []


def get_indexed_count() -> int:
    """Returns how many documents are in the index."""
    return len(_documents)
