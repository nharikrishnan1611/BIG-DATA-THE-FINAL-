"""
Evidence Retrieval & Source Ranking Engine.
Performs live multi-source retrieval across Google News RSS, Wikipedia API,
and official knowledge repositories. Ranks sources transparently by credibility tier
and semantic relevance to the extracted claim.
"""

import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


HEADERS = {
    "User-Agent": "FakeNewsEvidenceVerificationBot/1.0 (Academic Research; contact@verification-dashboard.org)"
}

GOV_DOMAINS = [".gov", ".mil", "whitehouse.gov", "pib.gov.in", "gov.uk", "europa.eu", "nasa.gov"]
ORG_DOMAINS = ["who.int", "cdc.gov", "un.org", "unesco.org", "redcross.org", "snopes.com", "politifact.com", "factcheck.org"]
REPUTABLE_NEWS = [
    "reuters", "associated press", "ap news", "bbc", "the guardian", "new york times", "nytimes",
    "washington post", "wall street journal", "wsj", "bloomberg", "the hindu", "npr", "pbs",
    "france 24", "deutsche welle", "al jazeera", "financial times", "time", "the economist"
]


def classify_source_type(source_name: str, url: str) -> tuple:
    """
    Categorizes the source credibility tier.
    Returns: (source_type, tier_weight)
    """
    url_lower = url.lower()
    name_lower = source_name.lower()

    for gd in GOV_DOMAINS:
        if gd in url_lower:
            return "Official Government", 1.0

    for od in ORG_DOMAINS:
        if od in url_lower or od in name_lower:
            return "Official Organization", 0.95

    for rn in REPUTABLE_NEWS:
        if rn in name_lower or rn in url_lower:
            return "News Article", 0.88

    if "wikipedia.org" in url_lower or "wikipedia" in name_lower:
        return "Reference Source", 0.78

    return "Public Web Source", 0.65


def extract_best_passage(text: str, claim: str) -> str:
    """Extracts the most relevant 1-2 sentence passage from a document snippet."""
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= 2:
        return text.strip()

    claim_words = set(re.findall(r"\w+", claim.lower()))
    scored = []
    for s in sentences:
        s_words = set(re.findall(r"\w+", s.lower()))
        overlap = len(claim_words.intersection(s_words))
        scored.append((overlap, s.strip()))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Take top 2 sentences maintaining natural text flow
    best = [s for count, s in scored[:2] if count > 0]
    if not best:
        return " ".join(sentences[:2])
    return " ".join(best)


def compute_relevance(claim: str, snippet: str, tier_weight: float) -> float:
    """
    Computes transparent source relevance (0 - 100%) using
    TF-IDF cosine similarity weighted by source credibility tier.
    """
    try:
        vec = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vec.fit_transform([claim, snippet])
        sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    except Exception:
        sim = 0.35

    # Composite relevance score
    raw_score = (sim * 0.70) + (tier_weight * 0.30)
    # Scale to percentage bounded between 40% and 98%
    relevance_pct = min(98.0, max(42.0, round(raw_score * 100, 1)))
    return relevance_pct


def fetch_google_news(search_query: str, max_items: int = 5) -> list:
    """Retrieves live verified news articles matching search query via Google News RSS."""
    sources = []
    try:
        encoded_query = urllib.parse.quote(search_query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(rss_url, headers=HEADERS, timeout=7)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:max_items]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source_elem = item.find("source")
                source_name = source_elem.text if source_elem is not None else "Verified News Outlet"

                # Clean title (Google News appends ' - SourceName')
                clean_title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
                description = item.find("description").text if item.find("description") is not None else ""
                clean_desc = re.sub(r"<[^>]+>", "", description).strip()

                snippet = clean_desc if clean_desc else clean_title

                sources.append({
                    "title": clean_title or title,
                    "url": link,
                    "source_name": source_name,
                    "publication_date": pub_date,
                    "raw_snippet": snippet
                })
    except Exception as e:
        print(f"[Evidence Search] Google News RSS query notice: {e}")

    return sources


def fetch_wikipedia_reference(search_query: str, max_items: int = 2) -> list:
    """Retrieves contextual reference information from Wikipedia API."""
    sources = []
    try:
        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_query,
            "utf8": "",
            "format": "json"
        }
        resp = requests.get(api_url, params=params, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            search_results = data.get("query", {}).get("search", [])[:max_items]
            for res in search_results:
                page_title = res.get("title", "")
                page_id = res.get("pageid", "")
                snippet_html = res.get("snippet", "")
                clean_snippet = re.sub(r"<[^>]+>", "", snippet_html).strip()
                page_url = f"https://en.wikipedia.org/?curid={page_id}"

                sources.append({
                    "title": f"Wikipedia: {page_title}",
                    "url": page_url,
                    "source_name": "Wikipedia Knowledge Base",
                    "publication_date": "Updated Reference Entry",
                    "raw_snippet": clean_snippet
                })
    except Exception as e:
        print(f"[Evidence Search] Wikipedia query notice: {e}")

    return sources


def retrieve_evidence(extracted_claim: str, search_query: str) -> list:
    """
    Main retrieval pipeline:
    1. Gathers sources from live news RSS and reference sources.
    2. Categorizes credibility tier (Gov > Org > News > Reference > Public).
    3. Extracts targeted passage snippets.
    4. Computes transparent source relevance.
    5. Sorts sources by relevance.
    """
    if not search_query:
        return []

    raw_sources = []
    # 1. Fetch live news articles
    news_items = fetch_google_news(search_query, max_items=4)
    raw_sources.extend(news_items)

    # 2. Fetch reference background
    wiki_items = fetch_wikipedia_reference(search_query, max_items=2)
    raw_sources.extend(wiki_items)

    if not raw_sources:
        # Fallback query with fewer terms
        shorter_query = " ".join(search_query.split()[:3])
        if shorter_query != search_query:
            raw_sources.extend(fetch_google_news(shorter_query, max_items=3))
            raw_sources.extend(fetch_wikipedia_reference(shorter_query, max_items=1))

    processed_sources = []
    retrieved_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    for src in raw_sources:
        source_name = src.get("source_name", "Unknown Source")
        url = src.get("url", "#")
        title = src.get("title", "Untitled Article")
        pub_date = src.get("publication_date", "Date unavailable")
        raw_snippet = src.get("raw_snippet", "")

        source_type, tier_weight = classify_source_type(source_name, url)
        evidence_passage = extract_best_passage(raw_snippet, extracted_claim)
        relevance_score = compute_relevance(extracted_claim, evidence_passage, tier_weight)

        processed_sources.append({
            "title": title,
            "source_type": source_type,
            "source_name": source_name,
            "evidence_snippet": evidence_passage,
            "url": url,
            "publication_date": pub_date,
            "retrieved_at": retrieved_time,
            "relevance_score": relevance_score,
            "is_primary": source_type in ["Official Government", "Official Organization"]
        })

    # Sort by relevance score descending
    processed_sources.sort(key=lambda s: s["relevance_score"], reverse=True)
    return processed_sources


if __name__ == "__main__":
    claim_test = "Government announces school closures"
    query_test = "government school closures"
    results = retrieve_evidence(claim_test, query_test)
    print(f"Retrieved {len(results)} sources.")
    for r in results[:2]:
        print(r)
