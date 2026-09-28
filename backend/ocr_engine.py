"""
OCR Engine using EasyOCR with PyTorch.
Extracts text from screenshots, headlines, newspaper clippings, or social media images.
Provides clean error handling, bounding-box text stitching, and confidence reporting.
"""

import io
import re
from PIL import Image
import numpy as np

# Lazy load EasyOCR reader to ensure swift server startup
_OCR_READER = None


def get_ocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        try:
            import easyocr
            # CPU mode by default for broad portability
            _OCR_READER = easyocr.Reader(["en"], gpu=False)
            print("[OCR Engine] EasyOCR PyTorch reader initialized successfully.")
        except Exception as e:
            print(f"[OCR Engine] Initialization warning: {e}")
            _OCR_READER = None
    return _OCR_READER


def extract_text_from_image_bytes(image_bytes: bytes) -> dict:
    """
    Extracts text from raw image bytes.
    Returns:
    - extracted_text: Full clean extracted text
    - ocr_used: True
    - confidence: Float confidence percentage (0-100%)
    - word_count: Number of extracted words
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(image)

        reader = get_ocr_reader()
        if reader is None:
            return {
                "extracted_text": "",
                "ocr_used": True,
                "confidence": 0.0,
                "word_count": 0,
                "error": "OCR engine reader not available"
            }

        results = reader.readtext(img_np)
        if not results:
            return {
                "extracted_text": "",
                "ocr_used": True,
                "confidence": 0.0,
                "word_count": 0,
                "message": "No discernible text detected in the uploaded image."
            }

        extracted_lines = []
        confidences = []
        for bbox, text, conf in results:
            clean = text.strip()
            if clean:
                extracted_lines.append(clean)
                confidences.append(float(conf))

        full_text = " ".join(extracted_lines)
        # Normalize spaces
        full_text = re.sub(r"\s+", " ", full_text).strip()
        avg_conf = (sum(confidences) / len(confidences)) * 100 if confidences else 0.0

        return {
            "extracted_text": full_text,
            "ocr_used": True,
            "confidence": round(avg_conf, 1),
            "word_count": len(full_text.split()),
            "lines_detected": len(extracted_lines)
        }

    except Exception as e:
        print(f"[OCR Engine] Processing error: {e}")
        return {
            "extracted_text": "",
            "ocr_used": True,
            "confidence": 0.0,
            "word_count": 0,
            "error": str(e)
        }
