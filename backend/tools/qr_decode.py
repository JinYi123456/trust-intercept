"""QR decoding — fully local, no external call required.

Engine priority: pyzbar (wraps the zbar library) first, zxing-cpp as fallback.
The result includes every URL found in the decoded payload(s), ready for
Module 2's redirect-chain analysis.
"""
from __future__ import annotations

import io
import re
from typing import Optional

from pydantic import BaseModel

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class QrDecodeError(RuntimeError):
    """Raised when no QR engine is available or nothing could be decoded."""


class QrDecodeResult(BaseModel):
    texts: list[str] = []
    urls: list[str] = []
    engine: str = ""


def _decode_with_pyzbar(image_bytes: bytes) -> list[str]:
    from PIL import Image  # noqa: placed here so the error message stays actionable
    from pyzbar.pyzbar import decode as zbar_decode

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    results = zbar_decode(image)
    texts = []
    for result in results:
        raw = result.data
        text = raw.decode("utf-8", errors="replace").strip() if isinstance(raw, bytes) else str(raw).strip()
        if text:
            texts.append(text)
    return texts


def _decode_with_zxing(image_bytes: bytes) -> list[str]:
    from PIL import Image
    import zxingcpp

    image = Image.open(io.BytesIO(image_bytes))
    image.load()
    texts = []
    for result in zxingcpp.read_barcodes(image):
        text = str(result.text).strip()
        if text:
            texts.append(text)
    return texts


def decode_qr(image_bytes: bytes) -> QrDecodeResult:
    """Decode the first QR/barcode payload found in ``image_bytes``."""
    if not image_bytes:
        raise QrDecodeError("No image data was provided for QR decoding.")

    errors: list[str] = []
    texts: list[str] = []
    engine = ""

    try:
        texts = _decode_with_pyzbar(image_bytes)
        if texts:
            engine = "pyzbar"
    except ImportError:
        errors.append("pyzbar is not installed")
    except Exception as exc:
        errors.append(f"pyzbar failed: {type(exc).__name__}: {exc}")

    if not texts:
        try:
            texts = _decode_with_zxing(image_bytes)
            if texts:
                engine = "zxing-cpp"
        except ImportError:
            errors.append("zxing-cpp is not installed")
        except Exception as exc:
            errors.append(f"zxing-cpp failed: {type(exc).__name__}: {exc}")

    if not texts:
        detail = "; ".join(errors) if errors else "no barcode found in the image"
        raise QrDecodeError(
            f"Could not decode a QR code ({detail}). Install pyzbar (with the zbar "
            "system library) or zxing-cpp, and make sure the image contains a readable code."
        )

    urls = sorted(
        {match.group(0).rstrip(".,);'\"") for text in texts for match in URL_RE.finditer(text)}
    )
    return QrDecodeResult(texts=texts, urls=urls, engine=engine)
