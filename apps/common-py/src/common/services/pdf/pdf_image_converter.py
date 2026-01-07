"""Service layer: Convert PDF pages to images and store in blob storage."""

import io
import logging

import fitz  # PyMuPDF
from PIL import Image

from common.infra.storage.blob_client import BlobClientWrapper

logger = logging.getLogger(__name__)


class PdfImageConverter:
    """Service layer: Convert PDF pages to images and store in blob storage."""

    def __init__(self, blob_client: BlobClientWrapper | None = None, content_container: str = "content") -> None:
        """Initialize PDF image converter.

        Args:
            blob_client: Blob client wrapper. If None, creates a new one.
            content_container: Container name for content storage (default: "content")
        """
        self.blob_client = blob_client or BlobClientWrapper()
        self.content_container = content_container

    def convert_pdf_to_images(
        self, pdf_blob_url: str, document_id: str, tenant_id: str, user_id: str, dpi: int = 200
    ) -> list[dict]:
        """Convert PDF pages to images and store in blob storage.

        Args:
            pdf_blob_url: Blob URL of the PDF file
            document_id: Document ID
            tenant_id: Tenant ID
            user_id: User ID
            dpi: DPI for image conversion (default: 200)

        Returns:
            List of image metadata: [{"page": 1, "blobUrl": "...", "width": 800, "height": 1200}, ...]
        """
        try:
            # Download PDF from blob
            pdf_bytes = self._download_blob_bytes(pdf_blob_url)

            # Open PDF with PyMuPDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            image_metadata = []

            try:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    # Render page to pixmap
                    pix = page.get_pixmap(dpi=dpi)
                    
                    # Convert to PNG bytes
                    image_bytes = pix.tobytes("png")
                    
                    # Upload to blob storage
                    image_blob_path = f"{tenant_id}/{user_id}/{document_id}/images/page_{page_num + 1}.png"
                    image_blob_url = self.blob_client.upload_bytes(
                        container=self.content_container,
                        blob_path=image_blob_path,
                        data=image_bytes,
                        content_type="image/png",
                    )
                    
                    # Get image dimensions
                    width = pix.width
                    height = pix.height
                    
                    image_metadata.append(
                        {
                            "page": page_num + 1,  # 1-indexed
                            "blobUrl": image_blob_url,
                            "width": width,
                            "height": height,
                        }
                    )
                    
                    logger.info("Converted page %d to image: %s (%dx%d)", page_num + 1, image_blob_url, width, height)
            finally:
                doc.close()

            logger.info("Converted %d pages from PDF to images", len(image_metadata))
            return image_metadata

        except Exception as e:
            logger.error("Failed to convert PDF to images: %s", e)
            raise

    def _extract_blob_path_from_url(self, blob_url: str) -> tuple[str, str]:
        """Extract container and blob path from blob URL.

        Args:
            blob_url: Full blob URL

        Returns:
            Tuple of (container, blob_path)
        """
        # Extract path after domain
        # Example: https://account.blob.core.windows.net/container/path -> (container, path)
        try:
            # Remove query parameters if any
            url_without_query = blob_url.split("?")[0]
            # Extract path after .net/
            if ".net/" in url_without_query:
                full_path = url_without_query.split(".net/")[1]
                # Split into container and path
                if "/" in full_path:
                    parts = full_path.split("/", 1)
                    return (parts[0], parts[1])
                return (full_path, "")
            # Fallback: try to extract from URL
            parts = url_without_query.split("/")
            if len(parts) >= 5:
                # Assume format: https://account.blob.core.windows.net/container/path
                container = parts[4]
                path = "/".join(parts[5:]) if len(parts) > 5 else ""
                return (container, path)
            # If extraction fails, assume it's just a path in default container
            return (self.content_container, blob_url)
        except Exception:
            # If extraction fails, assume it's just a path in default container
            return (self.content_container, blob_url)

    def _download_blob_bytes(self, blob_url: str) -> bytes:
        """Download blob as bytes from blob URL.

        Args:
            blob_url: Full blob URL

        Returns:
            Blob content as bytes
        """
        container, blob_path = self._extract_blob_path_from_url(blob_url)
        return self.blob_client.download_bytes(container, blob_path)

