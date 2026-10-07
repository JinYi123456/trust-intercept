"""OCR: local Tesseract by default; Google Vision only as an opt-in fallback.

Per the blueprint, screenshots of personal messages never leave the machine
unless the user explicitly enables the higher-accuracy cloud fallback
(``OCR_CLOUD_FALLBACK=true`` plus ``GOOGLE_VISION_API_KEY``).
"""
from __future__ import annotations

import base64
import io
from typing import Optional

from pydantic import BaseModel

from backend.config import get_settings


class OcrError(RuntimeError):
    """Raised when no OCR engine could extract text from the image."""


class OcrResult(BaseModel):
    text: str
    mean_confidence: Optional[float] = None  # 0-100, None if the engine cannot report it
    engine: str
    warning: str = ""


def _tesseract(image_bytes: bytes) -> OcrResult:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise OcrError(
            "Local OCR is unavailable: install the 'pytesseract' and 'Pillow' packages "
            "(and the Tesseract binary) or enable the cloud OCR fallback."
        ) from exc

    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.load()
    except Exception as exc:
        raise OcrError(f"Could not read the uploaded image: {exc}") from exc

    try:
        text = pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError(
            "The Tesseract engine is not installed on this machine. Install it "
            "(e.g. 'apt install tesseract-ocr' / 'choco install tesseract') or enable "
            "OCR_CLOUD_FALLBACK with a Google Vision key."
        ) from exc
    except Exception as exc:
        raise OcrError(f"Tesseract failed: {exc}") from exc

    mean_confidence: Optional[float] = None
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confidences = [
            int(conf)
            for conf, word in zip(data.get("conf", []), data.get("text", []))
            if str(word).strip() and int(conf) >= 0
        ]
        if confidences:
            mean_confidence = round(sum(confidences) / len(confidences), 1)
    except Exception:
        mean_confidence = None  # confidence reporting is best-effort

    if not text.strip():
        raise OcrError("Tesseract extracted no text from the image.")

    return OcrResult(text=text.strip(), mean_confidence=mean_confidence, engine="tesseract")


def _google_vision(image_bytes: bytes) -> OcrResult:
    settings = get_settings()
    if not settings.google_vision_api_key:
        raise OcrError("Google Vision fallback is enabled but GOOGLE_VISION_API_KEY is not set.")

    import httpx

    body = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }
    url = f"https://vision.googleapis.com/v1/images:annotate?key={settings.google_vision_api_key}"
    try:
        response = httpx.post(
            url, json=body, timeout=settings.outbound_timeout_seconds
        )
        response.raise_for_status()
    except Exception as exc:
        raise OcrError(f"Google Vision request failed: {exc}") from exc

    try:
        annotation = response.json()["responses"][0].get("fullTextAnnotation", {})
        text = annotation.get("text", "")
        pages = annotation.get("pages") or []
        confidence = None
        if pages and "confidence" in pages[0]:
            confidence = round(float(pages[0]["confidence"]) * 100, 1)
    except Exception as exc:
        raise OcrError(f"Could not parse the Google Vision response: {exc}") from exc

    if not text.strip():
        raise OcrError("Google Vision extracted no text from the image.")

    return OcrResult(
        text=text.strip(),
        mean_confidence=confidence,
        engine="google_vision",
    )


def extract_text(image_bytes: bytes) -> OcrResult:
    """Extract text from an image: local Tesseract first, cloud Vision if opted in."""
    if not image_bytes:
        raise OcrError("No image data was provided.")

    settings = get_settings()
    errors: list[str] = []

    try:
        return _tesseract(image_bytes)
    except OcrError as exc:
        errors.append(str(exc))

    if settings.ocr_cloud_fallback:
        try:
            return _google_vision(image_bytes)
        except OcrError as exc:
            errors.append(str(exc))

    raise OcrError(" | ".join(errors) or "No OCR engine available.")
