"""
Stance & Relationship Classification Engine.
Compares each retrieved source passage with the extracted claim.
Classifies relationship as:
- SUPPORTS CLAIM
- CONTRADICTS CLAIM
- CONTEXT
- UNCLEAR

Synthesizes the overall Evidence Status:
- Supported by available evidence
- Contradicted by available evidence
- Mixed/Conflicting evidence
- Insufficient evidence
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


CONTRADICTION_MARKERS = [
    r"\b(false|hoax|debunk(ed|s)?|misleading|untrue|fabricated|fake|rumor|rumour)\b",
    r"\b(no\s+evidence|not\s+true|unfounded|denied|denies|refute(d|s)?|reject(ed|s)?)\b",
    r"\b(fact[\s\-]check|claim[\s\-]check|myth|misinformation|disinformation)\b",
    r"\b(did\s+not\s+(announce|pass|approve|occur|happen|say|state))\b",
    r"\b(incorrectly\s+claimed|falsely\s+asserted|no\s+record\s+of)\b",
    r"\b(contrary\s+to\s+claims|debunking\s+the|disproved)\b"
]

SUPPORT_MARKERS = [
    r"\b(confirmed|officially\s+announced|approved|verified|passed\s+into\s+law)\b",
    r"\b(authorities\s+state|spokesperson\s+confirmed|official\s+statement\s+affirms)\b",
    r"\b(documented\s+by|validated\s+by|corroborated\s+by|formal\s+decree)\b",
    r"\b(regulatory\s+clearance|effective\s+immediately|signed\s+into\s+law)\b"
]

CONTEXT_MARKERS = [
    r"\b(overview|history|background|timeline|profile|encyclopedia|wikipedia)\b",
    r"\b(general\s+guidelines|standard\s+definition|broadly\s+defined|context)\b"
]


def classify_relationship(claim: str, source: dict) -> dict:
    """
    Classifies relationship between an individual source snippet and the claim.
    Returns:
    - relationship: 'SUPPORTS', 'CONTRADICTS', 'CONTEXT', or 'UNCLEAR'
    - rationale: Brief explanation of why this stance was assigned
    """
    snippet = source.get("evidence_snippet", "")
    title = source.get("title", "")
    source_type = source.get("source_type", "")
    combined_text = f"{title} {snippet}".lower()
    claim_lower = claim.lower()

    # 1. Check for Contradiction / Debunking cues
    for pat in CONTRADICTION_MARKERS:
        if re.search(pat, combined_text):
            return {
                "relationship": "CONTRADICTS CLAIM",
                "relationship_code": "CONTRADICTS",
                "badge_class": "badge-contradicts",
                "rationale": "Source explicitly flags the assertion as debunked, refuted, or lacking evidential foundation."
            }

    # 2. Check for Context indicators (e.g. encyclopedic / reference entries)
    if source_type == "Reference Source":
        return {
            "relationship": "CONTEXT",
            "relationship_code": "CONTEXT",
            "badge_class": "badge-context",
            "rationale": "Source provides contextual encyclopedic background on the topic rather than breaking verification."
        }

    for pat in CONTEXT_MARKERS:
        if re.search(pat, combined_text):
            return {
                "relationship": "CONTEXT",
                "relationship_code": "CONTEXT",
                "badge_class": "badge-context",
                "rationale": "Source provides informational overview and related situational context."
            }

    # 3. Check for Affirmative Support cues
    for pat in SUPPORT_MARKERS:
        if re.search(pat, combined_text):
            return {
                "relationship": "SUPPORTS CLAIM",
                "relationship_code": "SUPPORTS",
                "badge_class": "badge-supports",
                "rationale": "Source directly corroborates the factual announcement or verified event."
            }

    # 4. Measure textual semantic alignment using TF-IDF similarity
    try:
        vec = TfidfVectorizer(stop_words="english")
        matrix = vec.fit_transform([claim_lower, combined_text])
        sim = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception:
        sim = 0.2

    if sim >= 0.40:
        return {
            "relationship": "SUPPORTS CLAIM",
            "relationship_code": "SUPPORTS",
            "badge_class": "badge-supports",
            "rationale": "High semantic alignment and affirmative reporting of the key claim entities."
        }
    elif sim >= 0.20:
        return {
            "relationship": "CONTEXT",
            "relationship_code": "CONTEXT",
            "badge_class": "badge-context",
            "rationale": "Source addresses related subject matter and relevant background details."
        }
    else:
        return {
            "relationship": "RELATIONSHIP UNCLEAR",
            "relationship_code": "UNCLEAR",
            "badge_class": "badge-unclear",
            "rationale": "Source mentions terms in common but the specific factual relationship remains ambiguous."
        }


def synthesize_verification(claim: str, prediction_result: dict, sources: list) -> dict:
    """
    Synthesizes overall Evidence Status and human verification guidance
    combining the ML baseline prediction with live retrieved evidence cards.
    """
    total_sources = len(sources)
    if total_sources == 0:
        return {
            "evidence_status": "Insufficient evidence",
            "status_code": "INSUFFICIENT",
            "status_description": "No sufficient external evidence found across publicly accessible news and official archives.",
            "human_verification": "Not enough evidence — Independent human verification required",
            "sources_count": 0,
            "primary_sources_count": 0,
            "supports_count": 0,
            "contradicts_count": 0,
            "context_count": 0,
            "unclear_count": 0,
            "disclaimer": "Based on retrieved sources. Human verification recommended."
        }

    # Classify each source
    supports_count = 0
    contradicts_count = 0
    context_count = 0
    unclear_count = 0
    primary_count = 0

    annotated_sources = []
    for s in sources:
        stance = classify_relationship(claim, s)
        annotated_s = {**s, **stance}
        annotated_sources.append(annotated_s)

        code = stance["relationship_code"]
        if code == "SUPPORTS":
            supports_count += 1
        elif code == "CONTRADICTS":
            contradicts_count += 1
        elif code == "CONTEXT":
            context_count += 1
        else:
            unclear_count += 1

        if s.get("is_primary"):
            primary_count += 1

    # Determine overall status
    if contradicts_count > 0 and supports_count > 0:
        evidence_status = "Mixed/Conflicting evidence"
        status_code = "MIXED"
        status_desc = "Retrieved sources present conflicting reports or differing interpretations of this claim."
        human_verdict = "Strongly recommended"
    elif contradicts_count > 0:
        evidence_status = "Contradicted by available evidence"
        status_code = "CONTRADICTED"
        status_desc = "Publicly accessible official or news reports contradict or debunk the asserted claim."
        human_verdict = "Strongly recommended"
    elif supports_count > 0:
        evidence_status = "Supported by available evidence"
        status_code = "SUPPORTED"
        status_desc = "Available verified news or reference sources corroborate the essential details of the claim."
        human_verdict = "Recommended (Verify primary records)"
    elif context_count > 0:
        evidence_status = "Contextual information available (Specific claim unverified)"
        status_code = "CONTEXT_ONLY"
        status_desc = "Background reference material located, but specific new assertions remain unverified."
        human_verdict = "Recommended"
    else:
        evidence_status = "Insufficient evidence"
        status_code = "INSUFFICIENT"
        status_desc = "No definitive corroboration or refutation found in publicly accessible records."
        human_verdict = "Not enough evidence"

    # Escalate human verification if ML model flagged Misleading
    if prediction_result.get("prediction") == "MISLEADING" and human_verdict != "Strongly recommended":
        human_verdict = "Strongly recommended"

    return {
        "evidence_status": evidence_status,
        "status_code": status_code,
        "status_description": status_desc,
        "human_verification": human_verdict,
        "sources_count": total_sources,
        "primary_sources_count": primary_count,
        "supports_count": supports_count,
        "contradicts_count": contradicts_count,
        "context_count": context_count,
        "unclear_count": unclear_count,
        "annotated_sources": annotated_sources,
        "disclaimer": "Based on retrieved sources. Human verification recommended."
    }


if __name__ == "__main__":
    dummy_claim = "Government secretly announces all schools will close for 3 months"
    dummy_src = {
        "title": "Fact check: Did the government order 3-month school closure?",
        "source_name": "Reuters Fact Check",
        "source_type": "Official Organization",
        "evidence_snippet": "This viral claim is false. Education ministry officials debunked rumors of prolonged closures.",
        "url": "https://reuters.com",
        "is_primary": True
    }
    print(classify_relationship(dummy_claim, dummy_src))
