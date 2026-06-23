"""
image_utils.py

Utility functions for pre-processing uploaded images before sending them
to the OCR API. Ensures images are always within the free-tier size limit
(~1MB) by resizing and compressing them using Pillow.

Strategy:
  1. Resize so the longest dimension is at most MAX_DIMENSION pixels.
  2. Convert the image to RGB JPEG (removes transparency / palette modes).
  3. Save to an in-memory BytesIO buffer at INITIAL_QUALITY.
  4. If the buffer still exceeds TARGET_SIZE_BYTES, reduce quality by
     QUALITY_STEP and retry, down to MIN_QUALITY.
  5. If still too large at MIN_QUALITY, shrink MAX_DIMENSION to FALLBACK_DIMENSION
     and repeat the quality loop once more.
"""

import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# ── Tuneable constants ────────────────────────────────────────────────────────
TARGET_SIZE_BYTES  = 900_000   # 900 KB  — safely below the 1 MB API limit
MAX_DIMENSION      = 1500      # longest side in pixels for the first pass
FALLBACK_DIMENSION = 1000      # longest side if quality loop alone is not enough
INITIAL_QUALITY    = 85        # starting JPEG quality
QUALITY_STEP       = 10        # quality reduction per iteration
MIN_QUALITY        = 30        # never go below this quality
# ─────────────────────────────────────────────────────────────────────────────


def _resize_image(img: Image.Image, max_dimension: int) -> Image.Image:
    """
    Resize *img* so that its longest side is at most *max_dimension* pixels,
    preserving the original aspect ratio.  Returns the image unchanged if it
    is already small enough.
    """
    width, height = img.size
    longest = max(width, height)

    if longest <= max_dimension:
        return img

    scale  = max_dimension / longest
    new_w  = int(width  * scale)
    new_h  = int(height * scale)

    logger.debug("Resizing image from %dx%d → %dx%d", width, height, new_w, new_h)
    return img.resize((new_w, new_h), Image.LANCZOS)


def _compress_to_buffer(img: Image.Image, max_dimension: int) -> tuple[io.BytesIO, int]:
    """
    Resize *img* to *max_dimension* and then compress it iteratively until
    the JPEG buffer is within TARGET_SIZE_BYTES.

    Returns:
        (buffer, final_quality) – a BytesIO buffer ready to be read from
        position 0, and the JPEG quality that was used.
    """
    img = _resize_image(img, max_dimension)

    quality = INITIAL_QUALITY
    buffer  = io.BytesIO()

    while quality >= MIN_QUALITY:
        buffer.seek(0)
        buffer.truncate(0)
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        size = buffer.tell()

        logger.debug(
            "Compressed at quality=%d → %d bytes (limit %d)",
            quality, size, TARGET_SIZE_BYTES,
        )

        if size <= TARGET_SIZE_BYTES:
            break

        quality -= QUALITY_STEP

    buffer.seek(0)
    return buffer, quality


def compress_image(file_storage) -> tuple[io.BytesIO, str]:
    """
    Accept a Flask FileStorage object, compress / resize it so it fits
    within the OCR API's free-tier size limit, and return an in-memory
    buffer ready to be uploaded.

    The returned buffer is always a JPEG regardless of the original format,
    because JPEG gives the best size/quality trade-off for photographs and
    scanned documents.

    Args:
        file_storage: A Flask ``werkzeug.datastructures.FileStorage`` object
                      received from ``request.files``.

    Returns:
        (buffer, filename) where *buffer* is a ``BytesIO`` positioned at 0
        and *filename* is the sanitised upload filename (with ``.jpg`` extension).

    Raises:
        ValueError: If Pillow cannot identify the image format.
    """
    # Read the raw bytes so we can report the original size
    raw_bytes    = file_storage.read()
    original_size = len(raw_bytes)
    logger.info(
        "Received image '%s' — original size: %d bytes",
        file_storage.filename, original_size,
    )

    # Open with Pillow
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()          # force full decode now, not lazily later
    except Exception as exc:
        raise ValueError(f"Cannot open image with Pillow: {exc}") from exc

    # Convert to RGB (required for JPEG — strips alpha channel / palette)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # --- First pass: resize to MAX_DIMENSION + progressive quality loop ------
    buffer, quality = _compress_to_buffer(img, MAX_DIMENSION)

    # --- Fallback pass: further shrink if still too large --------------------
    if buffer.getbuffer().nbytes > TARGET_SIZE_BYTES:
        logger.warning(
            "Image still too large after quality=%d; shrinking to %dpx and retrying.",
            MIN_QUALITY, FALLBACK_DIMENSION,
        )
        img_resized         = _resize_image(img, FALLBACK_DIMENSION)
        buffer, quality     = _compress_to_buffer(img_resized, FALLBACK_DIMENSION)

    final_size = buffer.getbuffer().nbytes
    logger.info(
        "Compression complete — original: %d bytes → final: %d bytes (quality=%d)",
        original_size, final_size, quality,
    )

    # Build a safe output filename with .jpg extension
    base_name = file_storage.filename.rsplit(".", 1)[0] if "." in file_storage.filename else file_storage.filename
    out_filename = f"{base_name}.jpg"

    return buffer, out_filename
