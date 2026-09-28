"""
Claim Extraction Engine.
Extracts the core factual assertion from headlines, paragraphs, social media posts, or OCR text.
Removes viral prefixes/clickbait noise and produces an optimized search query.
"""

import re
import string


CLICKBAIT_PREFIXES = [
    r"^breaking(\s+news)?\s*[:!\-—]+",
    r"^shocking(\s+revelation)?\s*[:!\-—]+",
    r"^urgent(\s+alert)?\s*[:!\-—]+",
    r"^forwarded\s+as\s+received\s*[:!\-—]+",
    r"^warning\s*[:!\-—]+",
    r"^confirmed\s*[:!\-—]+",
    r"^must\s+watch\s*[:!\-—]+",
    r"^exposed\s*[:!\-—]+",
    r"^did\s+you\s+know\s+(that\s+)?",
    r"^you\s+won'?t\s+believe\s+(that\s+)?",
    r"^they\s+don'?t\s+want\s+you\s+to\s+know\s+(that\s+)?",
    r"^unbelievable\s*[:!\-—]+",
    r"^bombshell\s*[:!\-—]+"
]


def clean_prefix(text: str) -> str:
    """Removes sensationalist clickbait wrappers and attention-grabbing prefixes."""
    cleaned = text.strip()
    for pattern in CLICKBAIT_PREFIXES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def extract_claim(raw_text: str) -> dict:
    """
    Extracts the central factual assertion from input text.
    Returns:
    - extracted_claim: Cleaned, representative claim sentence.
    - search_query: High-relevance query tailored for live news and Wikipedia search.
    - detected_language: Detected language (defaults to 'English (en)').
    """
    if not raw_text or not raw_text.strip():
        return {
            "extracted_claim": "No content provided",
            "search_query": "",
            "detected_language": "Unknown"
        }

    # Normalize whitespace
    normalized = re.sub(r"\s+", " ", raw_text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized)

    candidate_sentences = []
    for s in sentences:
        s_clean = clean_prefix(s).strip()
        if len(s_clean.split()) >= 4:
            candidate_sentences.append(s_clean)

    if not candidate_sentences:
        candidate_sentences = [clean_prefix(normalized)]

    # Score sentences to find the primary factual assertion
    # Factual assertions typically contain proper nouns, numbers, policy verbs, or factual subjects
    def score_sentence(sent: str) -> float:
        score = 0.0
        words = sent.split()
        # Ideal claim length: 6 to 25 words
        if 6 <= len(words) <= 25:
            score += 2.0
        elif len(words) < 5:
            score -= 1.0

        # Numbers, dates, years, or currency indicators
        if re.search(r"\b(\d+|first|second|billion|million|percent|%|\$)\b", sent, re.I):
            score += 1.5

        # Declarative and policy action verbs
        if re.search(r"\b(announces?|declared?|passed?|banned?|approved?|confirmed?|closed?|discovered?|signed?|ordered?|investigating|cured?|died|launched?)\b", sent, re.I):
            score += 2.0

        # Institutional or entity indicators
        if re.search(r"\b(government|president|minister|court|police|fda|cdc|who|nasa|state|bank|union|board|scientists?)\b", sent, re.I):
            score += 1.5

        # Penalize questions (rhetorical headlines)
        if sent.endswith("?"):
            score -= 1.5

        return score

    best_sentence = max(candidate_sentences, key=score_sentence)
    best_sentence = clean_prefix(best_sentence)

    # Ensure clean ending punctuation
    if not best_sentence.endswith((".", "!", "?")):
        best_sentence = best_sentence + "."

    # Produce concise search query (top keywords, entities, numbers)
    # Remove punctuation
    query_words = re.sub(r"[^\w\s]", "", best_sentence).split()
    # Remove common conversational stop words for search query
    stopwords = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "about", "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "from", "up", "down", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "can", "could", "should", "would",
        "that", "this", "these", "those", "it", "its", "they", "them", "their", "we", "us",
        "our", "you", "your", "he", "him", "his", "she", "her", "share", "before", "deleted",
        "urgent", "shocking", "breaking", "secretly"
    }

    filtered_keywords = [w for w in query_words if w.lower() not in stopwords]
    # Keep up to 6 most salient terms for tight search precision
    search_query = " ".join(filtered_keywords[:6]) if filtered_keywords else best_sentence[:60]

    return {
        "extracted_claim": best_sentence,
        "search_query": search_query,
        "detected_language": "English (en)",
        "original_length": len(normalized)
    }


if __name__ == "__main__":
    t = "SHOCKING: Government secretly announces that all public schools will remain indefinitely closed for three months. Share before deleted!"
    print(extract_claim(t))
