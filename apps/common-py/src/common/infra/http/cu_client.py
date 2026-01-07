"""Azure AI Content Understanding REST API client."""

import logging
import time
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential
from requests.models import Response

from common.config.document_config import DocumentConfig

logger = logging.getLogger(__name__)

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


class AzureContentUnderstandingClient:
    """Infrastructure layer: REST API client for Azure AI Content Understanding."""

    def __init__(
        self,
        api_version: str = "2025-11-01",
        x_ms_useragent: str = "agentic-common-py/cu-client",
        config: DocumentConfig | None = None,
    ) -> None:
        """Initialize Content Understanding client.

        Args:
            api_version: API version (default: 2025-11-01)
            x_ms_useragent: User agent string
            config: Document configuration. If None, will load from environment.
        """
        if config is None:
            from common.config.document_config import get_document_config

            config = get_document_config()

        self.config = config
        self._api_version = api_version
        self._x_ms_useragent = x_ms_useragent

        if not config.cu_endpoint:
            raise ValueError("CU_ENDPOINT is required")

        self._endpoint = config.cu_endpoint.rstrip("/")

        # Initialize credential
        if config.cu_key:
            # Use key-based authentication (store key for token generation if needed)
            # For now, we'll use managed identity as primary
            self._credential = None
            self._api_key = config.cu_key
        else:
            # Use managed identity
            self._credential = DefaultAzureCredential()
            self._api_key = None

        self._headers = self._get_headers()

    def _get_headers(self) -> dict[str, str]:
        """Get headers for HTTP requests.

        Returns:
            Dictionary containing headers
        """
        headers: dict[str, str] = {}
        if self._credential:
            token = self._credential.get_token(COGNITIVE_SERVICES_SCOPE).token
            headers["Authorization"] = f"Bearer {token}"
        elif self._api_key:
            headers["Ocp-Apim-Subscription-Key"] = self._api_key
        else:
            raise ValueError("Either CU_KEY or managed identity must be configured")

        headers["x-ms-useragent"] = self._x_ms_useragent
        return headers

    def _get_analyze_url(self, analyzer_id: str) -> str:
        """Get analyze URL for analyzer (for URL-based requests).

        Args:
            analyzer_id: Analyzer ID

        Returns:
            Analyze URL
        """
        return f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={self._api_version}"

    def _get_analyze_binary_url(self, analyzer_id: str) -> str:
        """Get analyzeBinary URL for analyzer (for binary data requests).

        Args:
            analyzer_id: Analyzer ID

        Returns:
            AnalyzeBinary URL
        """
        return f"{self._endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyzeBinary?api-version={self._api_version}"

    def begin_analyze(self, analyzer_id: str, file_location: str | None = None, file_bytes: bytes | None = None, source_type: str | None = None) -> Response:
        """Begin analysis of a file, URL, or bytes.

        Args:
            analyzer_id: Analyzer ID to use
            file_location: Path to file or URL to analyze (optional if file_bytes is provided)
            file_bytes: File content as bytes (optional if file_location is provided)
            source_type: Source type hint (e.g., "pdf", "image") to determine Content-Type

        Returns:
            Response object with operation-location header

        Raises:
            ValueError: If neither file_location nor file_bytes is provided
        """
        data = None
        headers = {}
        
        if file_bytes is not None:
            # Use analyzeBinary endpoint for binary data (per Microsoft API documentation)
            # Determine content type from source_type or default to application/octet-stream
            content_type = "application/octet-stream"
            if source_type:
                source_lower = source_type.lower()
                if source_lower == "pdf":
                    content_type = "application/pdf"
                elif source_lower == "image":
                    # Default to image/png if we can't determine specific image type
                    content_type = "image/png"
                elif source_lower in ("png", "jpg", "jpeg", "gif", "bmp", "tiff"):
                    content_type = f"image/{source_lower}"
            
            # Send raw binary data with Content-Type header (per API spec: Media Types: "*/*")
            headers = self._headers.copy()
            headers["Content-Type"] = content_type
            data = file_bytes
            url = self._get_analyze_binary_url(analyzer_id)
        elif file_location:
            if Path(file_location).exists():
                # Local file path - read and send as binary using analyzeBinary endpoint
                file_path = Path(file_location)
                with open(file_location, "rb") as file:
                    file_content = file.read()
                # Try to determine content type from extension
                content_type = "application/octet-stream"
                suffix_lower = file_path.suffix.lower()
                if suffix_lower == ".pdf":
                    content_type = "application/pdf"
                elif suffix_lower in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}:
                    content_type = f"image/{suffix_lower.lstrip('.')}"
                
                headers = self._headers.copy()
                headers["Content-Type"] = content_type
                data = file_content
                url = self._get_analyze_binary_url(analyzer_id)
            elif file_location.startswith("https://") or file_location.startswith("http://"):
                # URL - use analyze endpoint with JSON format
                data = {"inputs": [{"url": file_location}]}
                headers = self._headers.copy()
                headers["Content-Type"] = "application/json"
                url = self._get_analyze_url(analyzer_id)
            else:
                raise ValueError("File location must be a valid path or URL.")
        else:
            raise ValueError("Either file_location or file_bytes must be provided.")

        try:
            if isinstance(data, dict):
                response = requests.post(url=url, headers=headers, json=data, timeout=30)
            else:
                # Send raw binary data
                response = requests.post(url=url, headers=headers, data=data, timeout=30)

            response.raise_for_status()
            input_source = "bytes" if file_bytes is not None else file_location or "unknown"
            logger.info("Started analysis with analyzer %s for %s", analyzer_id, input_source)
            return response
        except requests.exceptions.HTTPError as e:
            # Log detailed error information
            response = e.response
            error_msg = f"HTTP {response.status_code} error"
            try:
                error_body = response.text
                logger.error("API error response: %s", error_body)
                error_msg += f": {error_body}"
            except Exception:
                pass
            logger.error("Request URL: %s", url)
            logger.error("Request headers: %s", {k: v for k, v in headers.items() if k not in ("Authorization", "Ocp-Apim-Subscription-Key")})
            raise

    def poll_result(
        self,
        response: Response,
        timeout_seconds: int = 120,
        polling_interval_seconds: int = 2,
    ) -> dict:
        """Poll the result of an asynchronous operation until it completes or times out.

        Args:
            response: Initial response object containing the operation location
            timeout_seconds: Maximum seconds to wait (default: 120)
            polling_interval_seconds: Seconds between polling attempts (default: 2)

        Returns:
            JSON response of the completed operation

        Raises:
            ValueError: If operation location is not found
            TimeoutError: If operation times out
            RuntimeError: If operation fails
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers.")

        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"Operation timed out after {timeout_seconds:.2f} seconds.")

            poll_response = requests.get(operation_location, headers=self._headers, timeout=30)
            poll_response.raise_for_status()
            status = poll_response.json().get("status", "").lower()

            if status == "succeeded":
                logger.info("Request result is ready after %.2f seconds.", elapsed_time)
                return poll_response.json()
            elif status == "failed":
                logger.error("Request failed. Reason: %s", poll_response.json())
                raise RuntimeError("Request failed.")
            else:
                logger.info("Request %s in progress...", operation_location.split("/")[-1].split("?")[0])

            time.sleep(polling_interval_seconds)

