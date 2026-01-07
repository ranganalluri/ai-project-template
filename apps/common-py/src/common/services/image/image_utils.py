"""Utility functions for image processing."""

import base64
import logging
from typing import Any

from common.infra.storage.blob_client import BlobClientWrapper

logger = logging.getLogger(__name__)

def convert_image_to_base64(image_bytes: bytes, content_type: str = "image/png") -> str:
    """Convert image bytes to a base64 data URL for LLM consumption.

    Args:
        image_bytes: Image bytes
        content_type: Content type of the image
    Returns:
        Base64 data URL string (e.g., "data:image/png;base64,...")
    """
    try:
        base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{content_type};base64,{base64_encoded}"
    except Exception as e:
        logger.error("Failed to convert image to base64: %s", e)
        return None

def convert_blob_url_to_base64_data_url(
    blob_url: str, blob_client: BlobClientWrapper | None = None
) -> str | None:
    """Convert a blob URL to a base64 data URL for LLM consumption.

    Args:
        blob_url: Blob storage URL
        blob_client: Blob client for downloading. If None, creates a new one.

    Returns:
        Base64 data URL string (e.g., "data:image/png;base64,...") or None if conversion fails
    """
    if not blob_url:
        logger.warning("Empty blob URL provided")
        return None

    try:
        # Use provided blob client or create a new one
        if blob_client is None:
            blob_client = BlobClientWrapper()

        # Download image bytes from blob storage
        image_bytes = blob_client.download_bytes_from_url(blob_url)

        # Determine content type from URL extension
        content_type = _get_content_type_from_url(blob_url)

        # Convert to base64 data URL
        base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{content_type};base64,{base64_encoded}"

        logger.info("Converted image %s to base64 data URL (size: %d bytes)", blob_url, len(image_bytes))
        return data_url

    except Exception as e:
        logger.error("Failed to download and convert image %s: %s", blob_url, e)
        return None


def convert_image_metadata_to_content_items(
    image_urls: list[dict[str, Any]], blob_client: BlobClientWrapper | None = None
) -> list[dict[str, Any]]:
    """Convert image metadata list to content items with base64 data URLs for LLM.

    Args:
        image_urls: List of image metadata: [{"page": 1, "blobUrl": "...", "width": 800, "height": 1200}, ...]
        blob_client: Blob client for downloading. If None, creates a new one.

    Returns:
        List of content items for LLM API: [{"type": "input_image", "image_url": "data:..."}, ...]
    """
    content_items = []

    for img_meta in sorted(image_urls, key=lambda x: x.get("page", 0)):
        blob_url = img_meta.get("blobUrl", "")
        if not blob_url:
            logger.warning("Skipping image with empty blobUrl")
            continue

        # Convert blob URL to base64 data URL
        data_url = convert_blob_url_to_base64_data_url(blob_url, blob_client)

        if data_url:
            content_items.append(
                {
                    "type": "input_image",
                    "image_url": data_url,
                }
            )
        else:
            # Fall back to using URL directly if conversion fails
            logger.warning("Falling back to blob URL for image: %s", blob_url)
            content_items.append(
                {
                    "type": "input_image",
                    "image_url": blob_url,
                }
            )

    return content_items


def _get_content_type_from_url(url: str) -> str:
    """Determine content type from URL extension.

    Args:
        url: URL string

    Returns:
        MIME content type string
    """
    url_lower = url.lower()
    if ".jpg" in url_lower or ".jpeg" in url_lower:
        return "image/jpeg"
    elif ".png" in url_lower:
        return "image/png"
    elif ".gif" in url_lower:
        return "image/gif"
    elif ".bmp" in url_lower:
        return "image/bmp"
    elif ".tiff" in url_lower or ".tif" in url_lower:
        return "image/tiff"
    else:
        # Default to PNG if extension not recognized
        return "image/png"

