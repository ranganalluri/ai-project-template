"""Service layer: Business logic for Content Understanding extraction."""

import logging

from common.infra.http.cu_client import AzureContentUnderstandingClient
from common.models.document import CuNormalizedDocument

logger = logging.getLogger(__name__)


class CuExtractor:
    """Service layer: Business logic for Content Understanding extraction."""

    def __init__(self, client: AzureContentUnderstandingClient | None = None) -> None:
        """Initialize CU extractor.

        Args:
            client: Azure Content Understanding client. If None, creates a new one.
        """
        self.client = client or AzureContentUnderstandingClient()

    def extract_to_raw(self, input_blob_url: str, analyzer_id: str, source_type: str | None = None) -> dict:
        """Extract raw JSON from Content Understanding.

        Args:
            input_blob_url: Blob URL of the input document
            analyzer_id: Analyzer ID to use
            source_type: Optional source type (for future use)

        Returns:
            Raw CU JSON output
        """
        try:
            logger.info(f"Starting CU extraction for {input_blob_url} with analyzer {analyzer_id}")
            response = self.client.begin_analyze(analyzer_id=analyzer_id, file_location=input_blob_url)
            result = self.client.poll_result(response, timeout_seconds=300)
            logger.info(f"CU extraction completed for {input_blob_url}")
            return result
        except Exception as e:
            logger.error(f"Failed to extract CU data from {input_blob_url}: {e}")
            raise

    def normalize(self, cu_raw_json: dict) -> CuNormalizedDocument:
        """Normalize CU raw JSON output to structured format.

        Args:
            cu_raw_json: Raw CU JSON output

        Returns:
            Normalized CU document
        """
        try:
            # Extract pages
            pages = []
            if "pages" in cu_raw_json:
                for page_data in cu_raw_json["pages"]:
                    pages.append(
                        {
                            "pageNumber": page_data.get("pageNumber", 0),
                            "width": page_data.get("width"),
                            "height": page_data.get("height"),
                            "lines": page_data.get("lines", []),
                            "words": page_data.get("words", []),
                        }
                    )

            # Extract lines
            lines = cu_raw_json.get("lines", [])

            # Extract tables
            tables = []
            if "tables" in cu_raw_json:
                for table_data in cu_raw_json["tables"]:
                    tables.append(
                        {
                            "rowCount": table_data.get("rowCount", 0),
                            "columnCount": table_data.get("columnCount", 0),
                            "cells": table_data.get("cells", []),
                            "boundingRegions": table_data.get("boundingRegions", []),
                        }
                    )

            # Create normalized document
            normalized = CuNormalizedDocument(
                pages=pages,  # type: ignore
                lines=lines,
                tables=tables,  # type: ignore
                rawContent=cu_raw_json,
            )

            logger.info(f"Normalized CU document with {len(pages)} pages, {len(lines)} lines, {len(tables)} tables")
            return normalized
        except Exception as e:
            logger.error(f"Failed to normalize CU output: {e}")
            raise

