"""
FastAPI Server for AI Fake News Verification Dashboard.
Integrates:
- Baseline TF-IDF + Logistic Regression ML Classifier
- Factual Claim Extraction Engine
- Multi-Source Live Evidence Retrieval (Google News RSS + Wikipedia)
- Stance & Relationship Classifier (SUPPORTS / CONTRADICTS / CONTEXT / UNCLEAR)
- Big Data Apache Spark / HDFS Simulation & Burst Detection
- EasyOCR Screenshot Extraction
- Verification History Database (SQLite)
"""

import os
import sys

# Ensure backend directory is in python search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

# Internal modules
from ml_baseline import classify_text
from claim_extractor import extract_claim
from evidence_retriever import retrieve_evidence
from stance_classifier import synthesize_verification
from ocr_engine import extract_text_from_image_bytes
from url_extractor import extract_from_url
from database import save_verification, get_history, get_record, init_db
from pyspark_pipeline import big_data_engine, get_spark_architecture_details
from source_spread_verifier import perform_source_and_spread_verification

app = FastAPI(
    title="AI Fake News Detection with Evidence & Source Verification",
    description="Full-stack AI Verification Dashboard with traceable external source retrieval",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


class VerifyRequest(BaseModel):
    text: str
    input_type: str = "text"  # 'text', 'headline', 'url', 'image'
    source_url: Optional[str] = None
    ocr_used: bool = False
    ocr_confidence: Optional[float] = None


@app.on_event("startup")
def startup_event():
    init_db()
    print("[Server] Initialized verification database and pipeline dependencies.")


@app.post("/api/verify")
async def verify_endpoint(req: VerifyRequest):
    """
    Main Verification Pipeline:
    1. Extract central factual claim and search query.
    2. Run ML baseline (TF-IDF + Logistic Regression) for stylistic risk markers.
    3. Retrieve external evidence from Google News RSS & Wikipedia.
    4. Classify stance relationship for each source (SUPPORTS / CONTRADICTS / CONTEXT / UNCLEAR).
    5. Synthesize final Evidence Status.
    6. Compute time-window burst metrics (Big Data stream simulation).
    7. Save to verification history.
    """
    input_text = req.text.strip()
    if not input_text:
        raise HTTPException(status_code=400, detail="No content provided for verification.")

    # 1. Claim Extraction
    claim_info = extract_claim(input_text)
    extracted_claim = claim_info["extracted_claim"]
    search_query = claim_info["search_query"]
    detected_language = claim_info["detected_language"]

    # 2. ML Baseline Classification
    ml_result = classify_text(input_text)

    # 3. Evidence Retrieval
    retrieved_sources = retrieve_evidence(extracted_claim, search_query)

    # 4. Stance & Relationship Classification
    evidence_synthesis = synthesize_verification(extracted_claim, ml_result, retrieved_sources)

    # 5. Source & Spread Verification (YouTube, News, Social Media, Platform Breakdown)
    source_and_spread = perform_source_and_spread_verification(extracted_claim, search_query, req.source_url or "")

    # 6. Big Data Burst Detection
    burst_info = big_data_engine.analyze_burst_velocity(extracted_claim, ml_result["prediction"])

    # 7. Build Consolidated Record
    timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    record = {
        "timestamp": timestamp_str,
        "input_type": req.input_type,
        "original_input": input_text,
        "source_url": req.source_url or "",
        "extracted_claim": extracted_claim,
        "search_query": search_query,
        "detected_language": detected_language,
        "prediction": ml_result["prediction"],
        "prediction_label": ml_result["prediction_label"],
        "model_confidence": ml_result["model_confidence"],
        "confidence_score": ml_result["confidence_score"],
        "misleading_probability": ml_result["misleading_probability"],
        "genuine_probability": ml_result["genuine_probability"],
        "stylistic_markers": ml_result["stylistic_markers"],
        "explanation": ml_result["explanation"],
        "ml_disclaimer": "Model prediction is not factual proof.",
        "evidence_status": evidence_synthesis["evidence_status"],
        "status_code": evidence_synthesis["status_code"],
        "status_description": evidence_synthesis["status_description"],
        "human_verification": evidence_synthesis["human_verification"],
        "sources_count": source_and_spread["sources_found_count"],
        "primary_sources_count": evidence_synthesis["primary_sources_count"],
        "supports_count": evidence_synthesis["supports_count"],
        "contradicts_count": evidence_synthesis["contradicts_count"],
        "context_count": evidence_synthesis["context_count"],
        "unclear_count": evidence_synthesis["unclear_count"],
        "annotated_sources": evidence_synthesis.get("annotated_sources", []),
        "source_and_spread": source_and_spread,
        "evidence_disclaimer": evidence_synthesis["disclaimer"],
        "burst_detected": burst_info["burst_detected"],
        "mentions_velocity": burst_info["current_velocity_per_10min"],
        "burst_info": burst_info,
        "ocr_used": req.ocr_used,
        "ocr_confidence": req.ocr_confidence
    }

    # Save to history database
    record_id = save_verification(record)
    record["id"] = record_id

    return record


@app.post("/api/extract-url")
async def extract_url_endpoint(payload: dict):
    """Fetches article headline and body text from a provided news URL."""
    url = payload.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL.")
    result = extract_from_url(url)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to extract from URL."))
    return result


@app.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    """Extracts text from an uploaded screenshot or image using EasyOCR."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty image file received.")
    result = extract_text_from_image_bytes(contents)
    return result


@app.get("/api/history")
async def history_endpoint(limit: int = 50):
    """Retrieves verification history records."""
    records = get_history(limit=limit)
    return {"history": records, "count": len(records)}


@app.get("/api/history/{record_id}")
async def history_item_endpoint(record_id: int):
    """Fetches a specific verification record to reload into the UI."""
    rec = get_record(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found.")
    return rec


@app.get("/api/bigdata-stats")
async def bigdata_stats_endpoint():
    """Returns Apache Spark / HDFS architecture details and pipeline specifications."""
    return get_spark_architecture_details()


@app.get("/download-paper")
async def download_paper_endpoint():
    """Serves the generated Microsoft Word research paper (.docx) for direct browser download."""
    docx_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Research_Paper_Real_Time_Multimodal_Trend_and_Sentiment_Tracking.docx")
    if os.path.exists(docx_file):
        return FileResponse(
            docx_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="Research_Paper_Real_Time_Multimodal_Trend_and_Sentiment_Tracking.docx"
        )
    raise HTTPException(status_code=404, detail="Research paper document not found.")


# Mount frontend static assets
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root_endpoint():
    """Serves the main application dashboard."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI Fake News Verification Backend Running. UI under construction."}
