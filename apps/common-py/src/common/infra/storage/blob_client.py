"""Azure Blob Storage client wrapper for document processing."""

import json
import logging
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from common.config.document_config import DocumentConfig

logger = logging.getLogger(__name__)


class BlobClientWrapper:
    """Infrastructure layer: Azure Blob Storage client wrapper."""

    def __init__(self, config: DocumentConfig | None = None) -> None:
        """Initialize Blob Storage client.

        Args:
            config: Document configuration. If None, will load from environment.
        """
        if config is None:
            from common.config.document_config import get_document_config

            config = get_document_config()

        self.config = config

        if not config.azure_storage_account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME is required")
        if not config.azure_storage_account_key:
            raise ValueError("AZURE_STORAGE_ACCOUNT_KEY is required")

        # Build account URL if not provided
        account_url = config.blob_account_url
        if not account_url:
            if config.azure_storage_account_name == "devstoreaccount1":
                account_url = "http://127.0.0.1:10000/devstoreaccount1"
            else:
                account_url = f"https://{config.azure_storage_account_name}.blob.core.windows.net"

        # Initialize blob service client using account name and key
        self.blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=config.azure_storage_account_key,
        )

    def upload_bytes(
        self, container: str, blob_path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes to blob storage.

        Args:
            container: Container name
            blob_path: Blob path within container
            data: Bytes data to upload
            content_type: Content type (MIME type)

        Returns:
            Blob URL
        """
        try:
            container_client = self.blob_service_client.get_container_client(container)
            # Ensure container exists
            try:
                container_client.create_container()
            except Exception:
                # Container already exists, ignore
                pass

            blob_client = container_client.get_blob_client(blob_path)
            blob_client.upload_blob(data=data, overwrite=True, content_type=content_type)

            blob_url = blob_client.url
            logger.info(f"Uploaded {len(data)} bytes to {container}/{blob_path}")
            return blob_url
        except Exception as e:
            logger.error(f"Failed to upload bytes to {container}/{blob_path}: {e}")
            raise

    def download_bytes(self, container: str, blob_path: str) -> bytes:
        """Download bytes from blob storage.

        Args:
            container: Container name
            blob_path: Blob path within container

        Returns:
            Blob content as bytes

        Raises:
            FileNotFoundError: If blob does not exist
        """
        try:
            container_client = self.blob_service_client.get_container_client(container)
            blob_client = container_client.get_blob_client(blob_path)

            blob_data = blob_client.download_blob().readall()
            logger.info(f"Downloaded {len(blob_data)} bytes from {container}/{blob_path}")
            return blob_data
        except ResourceNotFoundError:
            logger.error(f"Blob not found: {container}/{blob_path}")
            raise FileNotFoundError(f"Blob not found: {container}/{blob_path}")
        except Exception as e:
            logger.error(f"Failed to download bytes from {container}/{blob_path}: {e}")
            raise

    def download_json(self, container: str, blob_path: str) -> dict[str, Any]:
        """Download JSON from blob storage.

        Args:
            container: Container name
            blob_path: Blob path within container

        Returns:
            Parsed JSON as dictionary

        Raises:
            FileNotFoundError: If blob does not exist
        """
        try:
            blob_data = self.download_bytes(container, blob_path)
            json_data = json.loads(blob_data.decode("utf-8"))
            logger.info(f"Downloaded JSON from {container}/{blob_path}")
            return json_data
        except Exception as e:
            logger.error(f"Failed to download JSON from {container}/{blob_path}: {e}")
            raise

    def upload_json(self, container: str, blob_path: str, obj: Any) -> str:
        """Upload object as JSON to blob storage.

        Args:
            container: Container name
            blob_path: Blob path within container
            obj: Object to serialize as JSON

        Returns:
            Blob URL
        """
        json_data = json.dumps(obj, indent=2, default=str)
        return self.upload_bytes(
            container=container, blob_path=blob_path, data=json_data.encode("utf-8"), content_type="application/json"
        )

    def download_bytes_from_url(self, blob_url: str) -> bytes:
        """Download bytes from blob storage using a blob URL.

        Args:
            blob_url: Full blob URL

        Returns:
            Blob content as bytes

        Raises:
            ValueError: If blob URL cannot be parsed
            FileNotFoundError: If blob does not exist
        """
        container, blob_path = self._extract_blob_path_from_url(blob_url)
        return self.download_bytes(container, blob_path)

    def _extract_blob_path_from_url(self, blob_url: str) -> tuple[str, str]:
        """Extract container and blob path from blob URL.

        Args:
            blob_url: Full blob URL

        Returns:
            Tuple of (container, blob_path)
        """
        # Remove query parameters if any
        url_without_query = blob_url.split("?")[0]
        
        # Handle Azure Blob Storage URLs: https://account.blob.core.windows.net/container/path
        if ".blob.core.windows.net/" in url_without_query:
            full_path = url_without_query.split(".blob.core.windows.net/")[1]
            if "/" in full_path:
                parts = full_path.split("/", 1)
                return (parts[0], parts[1])
            return (full_path, "")
        
        # Handle local emulator URLs: http://127.0.0.1:10000/devstoreaccount1/container/path
        if "127.0.0.1:10000/" in url_without_query or "localhost:10000/" in url_without_query:
            if "127.0.0.1:10000/" in url_without_query:
                full_path = url_without_query.split("127.0.0.1:10000/")[1]
            else:
                full_path = url_without_query.split("localhost:10000/")[1]
            # Skip account name (devstoreaccount1)
            if "/" in full_path:
                parts = full_path.split("/", 2)
                if len(parts) >= 3:
                    return (parts[1], parts[2])
                elif len(parts) == 2:
                    return (parts[1], "")
            return ("content", full_path)
        
        # Fallback: try to extract from URL path
        parts = url_without_query.split("/")
        if len(parts) >= 5:
            # Assume format: https://account.blob.core.windows.net/container/path
            container = parts[4]
            path = "/".join(parts[5:]) if len(parts) > 5 else ""
            return (container, path)
        
        # If extraction fails, use default container
        logger.warning("Could not parse blob URL, using default container: %s", blob_url)
        return ("content", blob_url)

