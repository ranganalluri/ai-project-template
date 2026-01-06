"""Infrastructure layer for external communication."""

from common.infra.cosmos.cosmos_base import BaseCosmosClient
from common.infra.cosmos.cosmos_metadata_client import CosmosMetadataClient
from common.infra.http.cu_client import AzureContentUnderstandingClient
from common.infra.openai.openai_client import OpenAIClient
from common.infra.storage.blob_client import BlobClientWrapper

__all__ = [
    "AzureContentUnderstandingClient",
    "BaseCosmosClient",
    "BlobClientWrapper",
    "CosmosMetadataClient",
    "OpenAIClient",
]

