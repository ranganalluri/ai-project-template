"""File processor for encoding files as base64 data URLs for LLM."""

import base64
import logging
from typing import Any

from common.services.chat_store import ChatStore
from common.services.file_storage import FileStorage

logger = logging.getLogger(__name__)


class FileProcessor:
    """Process files for LLM integration."""

    @staticmethod
    def process_file(
        file_id: str, file_storage: FileStorage, chat_store: ChatStore
    ) -> dict[str, Any] | None:
        """Process a file and return content item for Responses API.

        Args:
            file_id: File ID
            file_storage: File storage service
            chat_store: Chat store service

        Returns:
            Dictionary with file content item or None if processing failed
        """
        try:
            # Get file metadata
            file_metadata = chat_store.get_file(file_id)
            if not file_metadata:
                logger.warning("File metadata not found for file_id: %s", file_id)
                return None

            # Download file content
            try:
                file_content = file_storage.download_file(file_id)
            except FileNotFoundError:
                logger.error("File not found in storage: %s", file_id)
                return None

            # Determine file type and process accordingly
            content_type = file_metadata.content_type.lower()
            filename = file_metadata.filename.lower()

            if FileProcessor._is_image(content_type):
                return FileProcessor._process_image(file_content, content_type)
            elif FileProcessor._is_pdf(content_type, filename):
                return FileProcessor._process_pdf(file_content, content_type, file_metadata.filename)
            else:
                logger.warning(
                    "Unsupported file type: %s (file_id: %s), skipping", content_type, file_id
                )
                return None

        except Exception as e:
            logger.error("Error processing file %s: %s", file_id, e, exc_info=True)
            return None

    @staticmethod
    def _is_image(content_type: str) -> bool:
        """Check if file is an image type.

        Args:
            content_type: MIME content type

        Returns:
            True if image, False otherwise
        """
        image_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"]
        return content_type in image_types

    @staticmethod
    def _is_pdf(content_type: str, filename: str) -> bool:
        """Check if file is a PDF.

        Args:
            content_type: MIME content type
            filename: File name

        Returns:
            True if PDF, False otherwise
        """
        return content_type == "application/pdf" or filename.endswith(".pdf")

    @staticmethod
    def _process_image(content: bytes, content_type: str) -> dict[str, Any]:
        """Process image file and return content item.

        Args:
            content: File content bytes
            content_type: MIME content type

        Returns:
            Dictionary with input_image content item
        """
        data_url = FileProcessor._encode_to_base64_data_url(content, content_type)
        return {"type": "input_image", "image_url": data_url}

    @staticmethod
    def _process_pdf(content: bytes, content_type: str, filename: str) -> dict[str, Any]:
        """Process PDF file and return content item.

        Args:
            content: File content bytes
            content_type: MIME content type
            filename: Original filename

        Returns:
            Dictionary with input_file content item using file_data with data URL format
        """
        # Encode PDF as base64 data URL (data:application/pdf;base64,{base64_string})
        data_url = FileProcessor._encode_to_base64_data_url(content, content_type)
        # Use input_file format with file_data containing data URL and filename
        return {
            "type": "input_file",
            "filename": filename,
            "file_data": data_url,
        }

    @staticmethod
    def _encode_to_base64_data_url(content: bytes, content_type: str) -> str:
        """Encode file content as base64 data URL.

        Args:
            content: File content bytes
            content_type: MIME content type

        Returns:
            Base64 data URL string
        """
        base64_encoded = base64.b64encode(content).decode("utf-8")
        return f"data:{content_type};base64,{base64_encoded}"

