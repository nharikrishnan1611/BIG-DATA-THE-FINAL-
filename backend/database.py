"""
SQLite Database module for Verification History.
Stores submitted claims, predictions, evidence statuses, retrieved source cards, and metadata.
Enables instant reopening and inspection of previous verifications.
"""

import os
import json
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes verification history table and populates initial sample benchmark records."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            input_type TEXT NOT NULL,
            original_input TEXT NOT NULL,
            extracted_claim TEXT NOT NULL,
            prediction TEXT NOT NULL,
            model_confidence TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            evidence_status TEXT NOT NULL,
            sources_count INTEGER NOT NULL,
            primary_sources_count INTEGER NOT NULL,
            human_verification TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            stylistic_markers_json TEXT NOT NULL,
            explanation TEXT NOT NULL,
            burst_detected INTEGER DEFAULT 0,
            mentions_velocity INTEGER DEFAULT 0,
            ocr_used INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    # Pre-seed with benchmark verification examples if empty
    cursor.execute("SELECT COUNT(*) FROM verifications")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_samples = [
            {
                "timestamp": "2026-09-24 18:30:00 UTC",
                "input_type": "text",
                "original_input": "URGENT: Drinking boiled garlic water completely immunizes you against viral respiratory infections.",
                "extracted_claim": "Drinking boiled garlic water completely immunizes against viral respiratory infections.",
                "prediction": "MISLEADING",
                "model_confidence": "High",
                "confidence_score": 88.5,
                "evidence_status": "Contradicted by available evidence",
                "sources_count": 3,
                "primary_sources_count": 2,
                "human_verification": "Strongly recommended",
                "sources_json": json.dumps([
                    {
                        "title": "WHO Fact Sheet: Mythbusters on Respiratory Illness Remedies",
                        "source_type": "Official Organization",
                        "source_name": "World Health Organization",
                        "evidence_snippet": "There is no scientific evidence that eating garlic or drinking garlic water protects people from the novel coronavirus or respiratory infections.",
                        "relationship": "CONTRADICTS CLAIM",
                        "relationship_code": "CONTRADICTS",
                        "badge_class": "badge-contradicts",
                        "url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters",
                        "publication_date": "Updated Reference Archive",
                        "retrieved_at": "2026-09-24 18:30:00 UTC",
                        "relevance_score": 94.0,
                        "is_primary": True
                    },
                    {
                        "title": "CDC Nutrition & Preventive Health Guidance",
                        "source_type": "Official Organization",
                        "source_name": "Centers for Disease Control",
                        "evidence_snippet": "Garlic is a healthy food that may have some antimicrobial properties. However, there is no evidence that it protects against viral outbreaks.",
                        "relationship": "CONTRADICTS CLAIM",
                        "relationship_code": "CONTRADICTS",
                        "badge_class": "badge-contradicts",
                        "url": "https://www.cdc.gov",
                        "publication_date": "Clinical Health Record",
                        "retrieved_at": "2026-09-24 18:30:00 UTC",
                        "relevance_score": 91.2,
                        "is_primary": True
                    }
                ]),
                "stylistic_markers_json": json.dumps(["urgent", "completely immunizes", "viral"]),
                "explanation": "The model detected sensationalist medical cure assertions and unverified absolute promises.",
                "burst_detected": 1,
                "mentions_velocity": 420,
                "ocr_used": 0
            },
            {
                "timestamp": "2026-09-25 09:15:00 UTC",
                "input_type": "headline",
                "original_input": "NASA successfully completed laser communications experiment from deep space.",
                "extracted_claim": "NASA successfully completed laser communications experiment from deep space.",
                "prediction": "GENUINE",
                "model_confidence": "High",
                "confidence_score": 79.4,
                "evidence_status": "Supported by available evidence",
                "sources_count": 3,
                "primary_sources_count": 2,
                "human_verification": "Recommended (Verify primary records)",
                "sources_json": json.dumps([
                    {
                        "title": "NASA Deep Space Optical Communications Demo Transmits First Streaming Video",
                        "source_type": "Official Government",
                        "source_name": "NASA Jet Propulsion Laboratory",
                        "evidence_snippet": "NASA's Deep Space Optical Communications experiment beamed an ultra-high definition streaming video from 19 million miles away.",
                        "relationship": "SUPPORTS CLAIM",
                        "relationship_code": "SUPPORTS",
                        "badge_class": "badge-supports",
                        "url": "https://www.nasa.gov/mission/deep-space-optical-communications-dsoc/",
                        "publication_date": "Official Release",
                        "retrieved_at": "2026-09-25 09:15:00 UTC",
                        "relevance_score": 96.5,
                        "is_primary": True
                    },
                    {
                        "title": "Reuters: Space agency achieves breakthrough in optical space communications",
                        "source_type": "News Article",
                        "source_name": "Reuters",
                        "evidence_snippet": "Scientists confirmed the high-bandwidth optical transmission benchmark across interplanetary distances.",
                        "relationship": "SUPPORTS CLAIM",
                        "relationship_code": "SUPPORTS",
                        "badge_class": "badge-supports",
                        "url": "https://www.reuters.com",
                        "publication_date": "Journalistic Report",
                        "retrieved_at": "2026-09-25 09:15:00 UTC",
                        "relevance_score": 89.0,
                        "is_primary": False
                    }
                ]),
                "stylistic_markers_json": json.dumps(["nasa", "successfully completed", "experiment"]),
                "explanation": "Text displays standard institutional scientific reporting markers with verifiable entities.",
                "burst_detected": 0,
                "mentions_velocity": 35,
                "ocr_used": 0
            }
        ]

        for s in seed_samples:
            cursor.execute("""
                INSERT INTO verifications (
                    timestamp, input_type, original_input, extracted_claim,
                    prediction, model_confidence, confidence_score, evidence_status,
                    sources_count, primary_sources_count, human_verification,
                    sources_json, stylistic_markers_json, explanation,
                    burst_detected, mentions_velocity, ocr_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["timestamp"], s["input_type"], s["original_input"], s["extracted_claim"],
                s["prediction"], s["model_confidence"], s["confidence_score"], s["evidence_status"],
                s["sources_count"], s["primary_sources_count"], s["human_verification"],
                s["sources_json"], s["stylistic_markers_json"], s["explanation"],
                s["burst_detected"], s["mentions_velocity"], s["ocr_used"]
            ))
        conn.commit()

    conn.close()


def save_verification(record: dict) -> int:
    """Saves a verification result and returns its row ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO verifications (
            timestamp, input_type, original_input, extracted_claim,
            prediction, model_confidence, confidence_score, evidence_status,
            sources_count, primary_sources_count, human_verification,
            sources_json, stylistic_markers_json, explanation,
            burst_detected, mentions_velocity, ocr_used
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
        record.get("input_type", "text"),
        record.get("original_input", ""),
        record.get("extracted_claim", ""),
        record.get("prediction", "UNCERTAIN"),
        record.get("model_confidence", "Low"),
        record.get("confidence_score", 0.0),
        record.get("evidence_status", "Insufficient evidence"),
        record.get("sources_count", 0),
        record.get("primary_sources_count", 0),
        record.get("human_verification", "Recommended"),
        json.dumps(record.get("annotated_sources", [])),
        json.dumps(record.get("stylistic_markers", [])),
        record.get("explanation", ""),
        1 if record.get("burst_detected") else 0,
        record.get("mentions_velocity", 0),
        1 if record.get("ocr_used") else 0
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_history(limit: int = 50) -> list:
    """Returns past verification history records."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM verifications
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "input_type": r["input_type"],
            "original_input": r["original_input"],
            "extracted_claim": r["extracted_claim"],
            "prediction": r["prediction"],
            "model_confidence": r["model_confidence"],
            "confidence_score": r["confidence_score"],
            "evidence_status": r["evidence_status"],
            "sources_count": r["sources_count"],
            "primary_sources_count": r["primary_sources_count"],
            "human_verification": r["human_verification"],
            "sources": json.loads(r["sources_json"]) if r["sources_json"] else [],
            "stylistic_markers": json.loads(r["stylistic_markers_json"]) if r["stylistic_markers_json"] else [],
            "explanation": r["explanation"],
            "burst_detected": bool(r["burst_detected"]),
            "mentions_velocity": r["mentions_velocity"],
            "ocr_used": bool(r["ocr_used"])
        })
    return results


def get_record(record_id: int) -> dict:
    """Retrieves full details for a specific verification row."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verifications WHERE id = ?", (record_id,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r["id"],
        "timestamp": r["timestamp"],
        "input_type": r["input_type"],
        "original_input": r["original_input"],
        "extracted_claim": r["extracted_claim"],
        "prediction": r["prediction"],
        "model_confidence": r["model_confidence"],
        "confidence_score": r["confidence_score"],
        "evidence_status": r["evidence_status"],
        "sources_count": r["sources_count"],
        "primary_sources_count": r["primary_sources_count"],
        "human_verification": r["human_verification"],
        "sources": json.loads(r["sources_json"]) if r["sources_json"] else [],
        "stylistic_markers": json.loads(r["stylistic_markers_json"]) if r["stylistic_markers_json"] else [],
        "explanation": r["explanation"],
        "burst_detected": bool(r["burst_detected"]),
        "mentions_velocity": r["mentions_velocity"],
        "ocr_used": bool(r["ocr_used"])
    }


# Auto-init on import
init_db()
