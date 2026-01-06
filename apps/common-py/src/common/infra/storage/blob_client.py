"""Azure Blob Storage client wrapper for document processing."""

import json
import logging
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
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

        if not config.azure_storage_connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required")

        # Initialize blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            config.azure_storage_connection_string
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
            container_client = self.blob_service_client.get_container_client(container)
            blob_client = container_client.get_blob_client(blob_path)

            blob_data = blob_client.download_blob().readall()
            json_data = json.loads(blob_data.decode("utf-8"))
            logger.info(f"Downloaded JSON from {container}/{blob_path}")
            return json_data
        except ResourceNotFoundError:
            logger.error(f"Blob not found: {container}/{blob_path}")
            raise FileNotFoundError(f"Blob not found: {container}/{blob_path}")
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

