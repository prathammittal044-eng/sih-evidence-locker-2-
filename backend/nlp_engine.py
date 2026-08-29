"""
nlp_engine.py — AI Document Analysis Engine
Primary: Gemini 2.0 Flash Vision (reads document images directly, perfect for bilingual FIRs)
Fallback: Offline spaCy + TextRank (no API required)
"""
import re
import os
import io
import math
import json
from typing import List, Dict, Any
import networkx as nx
from dotenv import load_dotenv

# Load .env from the backend directory (works regardless of cwd)
_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_backend_dir, ".env"))

# -------------------------------------------------------
# Gemini Vision Setup — using new google.genai SDK
# -------------------------------------------------------
GEMINI_AVAILABLE = False
_gemini_client = None

try:
    from google import genai
    from google.genai import types
    _api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if _api_key:
        _gemini_client = genai.Client(api_key=_api_key)
        GEMINI_AVAILABLE = True
        print(f"[NLP] Gemini Vision ready (google.genai SDK, gemini-3.6-flash)")
    else:
        print("[NLP] GEMINI_API_KEY not set — falling back to offline mode")
except Exception as e:
    print(f"[NLP] Gemini init failed: {e} — falling back to offline mode")

# -------------------------------------------------------
# Offline spaCy Setup (fallback)
# -------------------------------------------------------
NLP_AVAILABLE = False
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    NLP_AVAILABLE = True
    print("[NLP] spaCy offline model loaded")
except Exception as e:
    print(f"[NLP] spaCy not available: {e}")


# -------------------------------------------------------
# Gemini Vision Analysis (Primary)
# -------------------------------------------------------
def analyze_with_gemini(text: str, image_paths: List[str] = None) -> Dict[str, Any]:
    """
    Send document images directly to Gemini Vision for analysis.
    Uses the new google.genai SDK.
    """
    from PIL import Image as PILImage
    import base64

    prompt = """You are an AI assistant analyzing an Indian government legal document (FIR - First Information Report).

This document is in a bilingual format (English + Hindi/Marathi). Please analyze it and provide:

1. EXECUTIVE SUMMARY: A clear, concise 3-4 sentence summary in English describing:
   - What crime was reported
   - Who is the complainant
   - Where and when it occurred
   - Key evidence or stolen items mentioned

2. EXTRACTED ENTITIES as JSON with these exact keys:
   - "PERSON": list of real person names mentioned
   - "GPE": list of locations/places (cities, addresses)
   - "ORG": list of organizations (police stations, courts)
   - "DATE": list of dates and times mentioned

Respond in this exact format:
SUMMARY:
<your summary here>

ENTITIES:
<valid JSON object with PERSON, GPE, ORG, DATE arrays>
"""

    contents = [prompt]

    # Attach images using the new SDK format
    images_added = 0
    if image_paths:
        for img_path in image_paths[:3]:
            if os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    # Detect mime type
                    ext = img_path.lower().rsplit('.', 1)[-1]
                    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
                    from google.genai import types
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
                    images_added += 1
                except Exception as e:
                    print(f"[NLP] Could not load image {img_path}: {e}")

    # Fallback to text if no images
    if images_added == 0 and text.strip():
        contents.append(f"\nDocument text (OCR extracted):\n{text[:3000]}")

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents
        )
        raw = response.text.strip()

        summary = ""
        entities = {"PERSON": [], "ORG": [], "GPE": [], "DATE": []}

        if "SUMMARY:" in raw and "ENTITIES:" in raw:
            summary_part = raw.split("ENTITIES:")[0].replace("SUMMARY:", "").strip()
            entities_part = raw.split("ENTITIES:")[1].strip()
            summary = summary_part
            try:
                json_match = re.search(r'\{.*\}', entities_part, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    for key in ["PERSON", "ORG", "GPE", "DATE"]:
                        if key in parsed and isinstance(parsed[key], list):
                            entities[key] = [str(v).strip() for v in parsed[key] if v]
            except Exception as je:
                print(f"[NLP] Entity JSON parse error: {je}")
        else:
            summary = raw

        return {"summary": summary, "entities": entities, "engine": "gemini-vision"}

    except Exception as e:
        print(f"[NLP] Gemini analysis failed: {e}")
        return None


# -------------------------------------------------------
# Offline Fallback: English Filter + spaCy + TextRank
# -------------------------------------------------------
def _is_quality_entity(text: str) -> bool:
    words = re.findall(r'[A-Za-z]{3,}', text)
    if not words:
        return False
    all_caps = sum(1 for w in words if w.isupper() and len(w) <= 4)
    if all_caps / len(words) > 0.6:
        return False
    if re.search(r'\b[a-z]{1,2}[A-Z][a-z]\b', text):
        return False
    if '(' in text or ')' in text or '*' in text:
        return False
    return True


def _extract_english_text(text: str) -> str:
    lines = text.split('\n')
    english_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        latin_chars = len(re.findall(r'[A-Za-z0-9]', stripped))
        total_chars = len(re.findall(r'\w', stripped))
        if total_chars == 0:
            continue
        if latin_chars / total_chars >= 0.5:
            cleaned = re.sub(r'[\u0900-\u097F]+', '', stripped).strip()
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            if len(cleaned) > 5:
                english_lines.append(cleaned)
    return '\n'.join(english_lines)


def _offline_extract_entities(text: str) -> Dict[str, List[str]]:
    if not NLP_AVAILABLE or not text.strip():
        return {"PERSON": [], "ORG": [], "GPE": [], "DATE": []}
    doc = nlp(text)
    entities = {"PERSON": set(), "ORG": set(), "GPE": set(), "DATE": set()}
    for ent in doc.ents:
        if ent.label_ in entities:
            clean_text = re.sub(r'\s{2,}', ' ', ent.text.strip().replace('\n', ' '))
            if len(clean_text) > 2 and _is_quality_entity(clean_text):
                entities[ent.label_].add(clean_text)
    return {k: list(v) for k, v in entities.items()}


def _get_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _sentence_similarity(s1: str, s2: str) -> float:
    w1 = set(re.findall(r'\w+', s1.lower()))
    w2 = set(re.findall(r'\w+', s2.lower()))
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / (math.log(len(w1)) + math.log(len(w2)) + 0.1)


def _offline_generate_summary(text: str, n: int = 3) -> str:
    sentences = _get_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= n:
        return " ".join(sentences)
    graph = nx.Graph()
    for i in range(len(sentences)):
        graph.add_node(i)
        for j in range(i + 1, len(sentences)):
            sim = _sentence_similarity(sentences[i], sentences[j])
            if sim > 0:
                graph.add_edge(i, j, weight=sim)
    try:
        scores = nx.pagerank(graph, weight='weight')
    except Exception:
        return " ".join(sentences[:n])
    ranked = sorted(((scores[i], s, i) for i, s in enumerate(sentences)), reverse=True)
    top_n = sorted(ranked[:n], key=lambda x: x[2])
    return " ".join([item[1] for item in top_n])


def _offline_analyze(text: str) -> Dict[str, Any]:
    english_text = _extract_english_text(text)
    if len(english_text.strip()) < 50:
        english_text = text
    return {
        "summary": _offline_generate_summary(english_text, n=3),
        "entities": _offline_extract_entities(english_text),
        "engine": "offline-spacy"
    }


# -------------------------------------------------------
# Main entry point
# -------------------------------------------------------
def analyze_document(text: str, image_paths: List[str] = None) -> Dict[str, Any]:
    """
    Analyze a document. Uses Gemini Vision if API key is configured,
    otherwise falls back to offline spaCy + TextRank.
    """
    if not text.strip() and not image_paths:
        return {"summary": "", "entities": {}}

    if GEMINI_AVAILABLE:
        result = analyze_with_gemini(text, image_paths)
        if result:
            return result

    # Fallback to offline
    print("[NLP] Using offline spaCy fallback")
    return _offline_analyze(text)


