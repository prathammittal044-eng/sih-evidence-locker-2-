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

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extracts People, Locations, Orgs, and Dates from text."""
    if not NLP_AVAILABLE or not text.strip():
        return {"PERSON": [], "ORG": [], "GPE": [], "DATE": []}
    
    doc = nlp(text)
    entities = {"PERSON": set(), "ORG": set(), "GPE": set(), "DATE": set()}
    
    for ent in doc.ents:
        if ent.label_ in entities:
            # Clean up entity text
            clean_text = ent.text.strip().replace('\n', ' ')
            if len(clean_text) > 1:
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

def generate_summary(text: str, num_sentences: int = 3) -> str:
    """Generates an extractive summary using TextRank algorithm."""
    sentences = get_sentences(text)
    if len(sentences) <= num_sentences:
        return text.strip()
        
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
        # Fallback if convergence fails
        return " ".join(sentences[:num_sentences])
        
    # Sort sentences by score
    ranked_sentences = sorted(((scores[i], s, i) for i, s in enumerate(sentences)), reverse=True)
    
    # Pick top N sentences and sort them back to original chronological order
    top_n = sorted(ranked_sentences[:num_sentences], key=lambda x: x[2])
    
    return " ".join([item[1] for item in top_n])

def analyze_document(text: str) -> Dict[str, any]:
    """Full NLP pipeline for a document (translates to English first)."""
    if not text.strip():
        return {"summary": "", "entities": {}}
        
    # Attempt to translate text to English using deep_translator
    try:
        from deep_translator import GoogleTranslator
        # GoogleTranslator has a max char limit of 5000 per request, so we chunk if needed
        translator = GoogleTranslator(source='auto', target='en')
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        translated_chunks = []
        for chunk in chunks:
            translated_chunks.append(translator.translate(chunk))
        english_text = " ".join(translated_chunks)
    except Exception as e:
        print(f"[NLP] Translation failed: {e}")
        english_text = text  # Fallback to original text
        
    summary = generate_summary(english_text, num_sentences=4)
    entities = extract_entities(english_text)
    
    return {
        "summary": summary,
        "entities": entities
    }
