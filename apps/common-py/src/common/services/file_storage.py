"""Azure Blob Storage file service."""

import logging
from abc import ABC, abstractmethod
from datetime import timedelta

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)

from common.models.chat import FileUploadResponse

logger = logging.getLogger(__name__)


class FileStorage(ABC):
    """Abstract interface for file storage."""

    @abstractmethod
    def upload_file(self, file_id: str, content: bytes, metadata: FileUploadResponse) -> str:
        """Upload a file."""
        pass

    @abstractmethod
    def download_file(self, file_id: str) -> bytes:
        """Download a file."""
        pass

    @abstractmethod
    def delete_file(self, file_id: str) -> None:
        """Delete a file."""
        pass

    @abstractmethod
    def get_file_url(self, file_id: str, expiry_minutes: int = 60) -> str:
        """Get a SAS URL for direct file access."""
        pass


class BlobFileStorage(FileStorage):
    """Azure Blob Storage implementation of FileStorage."""

    def __init__(
        self,
        account_name: str,
        account_key: str | None = None,
        container_name: str = "files",
        use_managed_identity: bool = False,
    ) -> None:
        """Initialize Blob Storage file service.

        Args:
            account_name: Storage account name
            account_key: Storage account key (if not using managed identity)
            container_name: Container name for files
            use_managed_identity: Use managed identity for authentication
        """
        self.account_name = account_name
        self.container_name = container_name

        if use_managed_identity:
            account_url = f"https://{account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            if not account_key:
                raise ValueError("account_key is required when not using managed identity")
            connection_string = (
                f"DefaultEndpointsProtocol=https;AccountName={account_name};"
                f"AccountKey={account_key};EndpointSuffix=core.windows.net"
            )
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        self.container_client = self.blob_service_client.get_container_client(container_name)

        # Ensure container exists
        try:
            self.container_client.create_container()
        except Exception:
            # Container already exists, ignore
            pass

    def upload_file(self, file_id: str, content: bytes, metadata: FileUploadResponse) -> str:
        """Upload a file."""
        blob_client = self.container_client.get_blob_client(file_id)
        blob_client.upload_blob(
            data=content,
            overwrite=True,
            metadata={
                "filename": metadata.filename,
                "content_type": metadata.content_type,
                "size": str(metadata.size),
            },
        )
        logger.info("Uploaded file %s to blob storage", file_id)
        return file_id

    def download_file(self, file_id: str) -> bytes:
        """Download a file."""
        blob_client = self.container_client.get_blob_client(file_id)
        try:
            return blob_client.download_blob().readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File {file_id} not found")

    def delete_file(self, file_id: str) -> None:
        """Delete a file."""
        blob_client = self.container_client.get_blob_client(file_id)
        try:
            blob_client.delete_blob()
            logger.info("Deleted file %s from blob storage", file_id)
        except ResourceNotFoundError:
            logger.warning("File %s not found for deletion", file_id)

    def get_file_url(self, file_id: str, expiry_minutes: int = 60) -> str:
        """Get a SAS URL for direct file access.
        Note: SAS tokens require account key. If using managed identity,
        consider using blob client's generate_sas method or returning
        a pre-signed URL from your API.
        """
        blob_client = self.container_client.get_blob_client(file_id)

        # For managed identity, we can't generate SAS tokens directly
        # Return the blob URL (access will be controlled by RBAC)
        # In production, you might want to generate SAS tokens server-side
        # or use Azure AD authentication for direct blob access
        if hasattr(self.blob_service_client.credential, "account_key"):
            account_key = self.blob_service_client.credential.account_key
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=file_id,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=timedelta(minutes=expiry_minutes),
            )
            return f"{blob_client.url}?{sas_token}"
        else:
            # Managed identity - return URL without SAS (requires RBAC)
            return blob_client.url
