# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Simple in-memory vector store using Azure OpenAI embeddings."""

import logging
import math
from typing import TYPE_CHECKING

from common.services.cu.extract_chunks import Chunk
from azure.ai.inference import EmbeddingsClient
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
if TYPE_CHECKING:
    from common.infra.openai.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class InlineVectorStore:
    """Simple in-memory vector store using Azure OpenAI embeddings.
    
    Stores chunks with their embeddings in-memory and provides similarity search.
    """

    def __init__(
        self,
        openai_client: "OpenAIClient",
        embedding_model: str | None = None,
    ) -> None:
        """Initialize the vector store.

        Args:
            openai_client: OpenAI client instance for creating embeddings
            embedding_model: Embedding model deployment name to use.
                For Azure OpenAI, this MUST be the deployment name (not the model name).
                The deployment name is what you set when creating the deployment in Azure Portal.
                If None, defaults to 'text-embedding-3-small'.
                Note: The deployment name may differ from the model name (e.g., deployment 'embedding'
                for model 'text-embedding-3-small').
        """
        self.openai_client = openai_client
        # Default to text-embedding-3-small
        self.embedding_model = embedding_model or "text-embedding-3-large-249174"
        self._chunks: list[Chunk] = []
        self._embeddings: list[list[float]] = []
        self._embeddings_client = EmbeddingsClient("https://rr-eu1-dev-ai-02.services.ai.azure.com/models", credential=AzureKeyCredential("ef8f17ba6c6644d68be1d19b3ee344cc"))

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to the vector store and create embeddings.

        Args:
            chunks: List of Chunk objects to add
        """
        if not chunks:
            logger.warning("No chunks provided to add_chunks")
            return

        # Extract text from chunks
        texts = [chunk.text for chunk in chunks]

        # Batch create embeddings
        try:
            response = self._embeddings_client.embed(
                model=self.embedding_model,
                input=texts,
            )

            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]

            # Store chunks and embeddings
            self._chunks.extend(chunks)
            self._embeddings.extend(embeddings)

            logger.info("Added %d chunks to vector store", len(chunks))
        except Exception as e:
            logger.error("Failed to create embeddings: %s", e)
            raise

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """Search for similar chunks using cosine similarity.

        Args:
            query: Query text to search for
            top_k: Number of top results to return (default: 5)

        Returns:
            List of tuples (chunk, similarity_score) sorted by score descending
        """
        if not self._chunks:
            logger.warning("No chunks in vector store")
            return []

        # Create embedding for query
        try:
            response = self._embeddings_client.embed(
                model=self.embedding_model,
                input=[query],
            )
            query_embedding = response.data[0].embedding
        except Exception as e:
            logger.error("Failed to create query embedding: %s", e)
            raise

        # Compute cosine similarity with all stored embeddings
        similarities = []
        for i, stored_embedding in enumerate(self._embeddings):
            similarity = self._cosine_similarity(query_embedding, stored_embedding)
            similarities.append((self._chunks[i], similarity))

        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vectors must have same length: {len(vec1)} != {len(vec2)}")

        # Compute dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Compute magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

