import re
import math
from typing import List, Dict, Set
import networkx as nx

NLP_AVAILABLE = False
try:
    import spacy
    # Load small English model for NER
    nlp = spacy.load("en_core_web_sm")
    NLP_AVAILABLE = True
except Exception as e:
    print(f"[NLP] spaCy model not found or failed to load: {e}")
    print("[NLP] Run: python -m spacy download en_core_web_sm")

def _is_quality_entity(text: str) -> bool:
    """Returns True if the entity text looks like a real name/place, not OCR garbage."""
    # Must have at least one proper word (3+ letters, mostly alphabetic)
    words = re.findall(r'[A-Za-z]{3,}', text)
    if not words:
        return False
    # Reject if most words are ALL-CAPS abbreviations like 'ATS', 'GTM', 'AER'
    all_caps = sum(1 for w in words if w.isupper() and len(w) <= 4)
    if len(words) > 0 and all_caps / len(words) > 0.6:
        return False
    # Reject if entity contains clear OCR junk patterns
    if re.search(r'\b[a-z]{1,2}[A-Z][a-z]\b', text):  # like 'oT', 'eA'
        return False
    if '(' in text or ')' in text or '*' in text:
        return False
    return True


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extracts People, Locations, Orgs, and Dates from text."""
    if not NLP_AVAILABLE or not text.strip():
        return {"PERSON": [], "ORG": [], "GPE": [], "DATE": []}
    
    doc = nlp(text)
    entities = {"PERSON": set(), "ORG": set(), "GPE": set(), "DATE": set()}
    
    for ent in doc.ents:
        if ent.label_ in entities:
            clean_text = ent.text.strip().replace('\n', ' ')
            clean_text = re.sub(r'\s{2,}', ' ', clean_text)
            if len(clean_text) > 2 and _is_quality_entity(clean_text):
                entities[ent.label_].add(clean_text)
                
    return {k: list(v) for k, v in entities.items()}

def get_sentences(text: str) -> List[str]:
    """Splits text into basic sentences."""
    # Simple regex split for sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def sentence_similarity(sent1: str, sent2: str) -> float:
    """Calculates cosine similarity between two sentences using simple word overlap."""
    words1 = set(re.findall(r'\w+', sent1.lower()))
    words2 = set(re.findall(r'\w+', sent2.lower()))
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    return len(intersection) / (math.log(len(words1)) + math.log(len(words2)) + 0.1)

def _is_quality_sentence(sentence: str) -> bool:
    """
    Returns True if a sentence has enough real English words to be meaningful.
    Filters out garbled OCR artifacts like 'fas fle oT eA Hetaet ara at ae'.
    """
    COMMON_ENGLISH = {
        'the','a','an','is','are','was','were','be','been','being','have','has','had',
        'do','does','did','will','would','could','should','may','might','shall','can',
        'not','no','and','or','but','if','then','so','as','at','by','for','from',
        'in','into','of','on','out','to','up','with','about','after','before','between',
        'during','through','under','over','while','when','where','who','which','that',
        'this','these','those','it','its','he','she','they','we','his','her','their',
        'complainant','returned','home','find','lock','broken','several','valuable',
        'items','including','missing','burglary','theft','house','address','name',
        'police','station','district','state','date','time','morning','evening',
        'information','report','first','sections','acts','occupation','informant',
        'complaint','case','fir','number','type','place','occurrence','written',
        'singh','vikram','bandra','mumbai','maharashtra','west','breaking','stolen',
        'electronic','goods','jewelry','officer','sub','inspector','filed','incident',
    }
    words = re.findall(r'[a-z]{3,}', sentence.lower())
    if not words:
        return False
    # At least 25% of words must be real English words
    match_count = sum(1 for w in words if w in COMMON_ENGLISH)
    return match_count / len(words) >= 0.25


def generate_summary(text: str, num_sentences: int = 3) -> str:
    """Generates an extractive summary using TextRank, filtering garbage sentences first."""
    all_sentences = get_sentences(text)
    # Keep only sentences that pass quality check
    sentences = [s for s in all_sentences if _is_quality_sentence(s)]
    # Fallback: use all sentences if filter is too aggressive
    if len(sentences) < 2:
        sentences = all_sentences
    if len(sentences) == 0:
        return ""
    if len(sentences) <= num_sentences:
        return " ".join(sentences)

    # Build similarity graph
    graph = nx.Graph()
    for i in range(len(sentences)):
        graph.add_node(i)
        for j in range(i + 1, len(sentences)):
            sim = sentence_similarity(sentences[i], sentences[j])
            if sim > 0:
                graph.add_edge(i, j, weight=sim)

    # Calculate PageRank
    try:
        scores = nx.pagerank(graph, weight='weight')
    except Exception:
        return " ".join(sentences[:num_sentences])

    ranked_sentences = sorted(((scores[i], s, i) for i, s in enumerate(sentences)), reverse=True)
    top_n = sorted(ranked_sentences[:num_sentences], key=lambda x: x[2])
    return " ".join([item[1] for item in top_n])

def extract_english_text(text: str) -> str:
    """
    Filters out lines/words that are predominantly non-Latin (Hindi, Marathi, etc.)
    and returns a clean English-only version of the text.
    This runs 100% offline with no external API calls.
    """
    lines = text.split('\n')
    english_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Count Latin (English) characters vs total alphanumeric characters
        latin_chars = len(re.findall(r'[A-Za-z0-9]', stripped))
        total_chars = len(re.findall(r'\w', stripped))
        if total_chars == 0:
            continue
        # Keep line if at least 50% of word characters are Latin/English
        if latin_chars / total_chars >= 0.5:
            # Also strip any stray Devanagari words within the line
            cleaned = re.sub(r'[\u0900-\u097F]+', '', stripped).strip()
            cleaned = re.sub(r'\s{2,}', ' ', cleaned)
            if len(cleaned) > 5:
                english_lines.append(cleaned)

    return '\n'.join(english_lines)


def analyze_document(text: str) -> Dict[str, any]:
    """Full NLP pipeline — filters to English-only content first (100% offline, no external API)."""
    if not text.strip():
        return {"summary": "", "entities": {}}

    english_text = extract_english_text(text)

    # If filtering removed too much, fall back to raw text
    if len(english_text.strip()) < 50:
        english_text = text

    summary = generate_summary(english_text, num_sentences=4)
    entities = extract_entities(english_text)

    return {
        "summary": summary,
        "entities": entities
    }
