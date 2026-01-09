"""Service layer: Business logic for schema extraction using OpenAI Responses API."""

import json
import logging
import math
from typing import Any

from common.infra.openai.openai_client import OpenAIClient
from common.models.document import CuNormalizedDocument, EvidenceSpan, ExtractedField, ExtractedSchema, Point
from common.schemas.invoice_schema import Invoice

logger = logging.getLogger(__name__)


class SchemaExtractor:
    """Service layer: Business logic for schema extraction using OpenAI Responses API."""

    def __init__(self, client: OpenAIClient | None = None, model: str | None = None) -> None:
        """Initialize schema extractor.

        Args:
            client: OpenAI client. If None, creates a new one.
            model: Model deployment name. If None, uses config default.
        """
        self.client = client or OpenAIClient()
        if model is None:
            from common.config.document_config import get_document_config

            config = get_document_config()
            model = config.foundry_deployment_name
        self.model = model

    def extract_schema(
        self,
        image_content_items: list[dict[str, Any]] | None = None,
        schema_definition: dict[str, Any] | None = None,
    ) -> tuple[ExtractedSchema, dict[str, Any], list[Any] | None, str, Any]:
        """Extract schema from normalized CU document using OpenAI Responses API.

        Args:
            cu_normalized: Normalized CU document (for reference, not used in API call if images provided)
            doc_type: Document type identifier
            image_content_items: Optional list of pre-converted image content items for LLM API.
                                 Format: [{"type": "input_image", "image_url": "data:..."}, ...]
                                 If provided, uses images instead of text
            schema_definition: Optional JSON schema definition for structured outputs

        Returns:
            Tuple of (ExtractedSchema, evidence_json, logprobs_list, response_text, response)
            - logprobs_list: List of logprob dictionaries/objects, or None if not available
            - response_text: Raw response text before JSON parsing
            - response: Full response object for extracting usage information
        """
        try:
            openai_client = self.client.get_client()

            # Responses API expects messages as a list of message objects with role and content
            messages = [
                {
                    "role": "user",
                    "content": image_content_items,
                }
            ]

            # Prepare JSON schema config for structured outputs (Responses text.format)
            text_config: dict[str, Any] | None = None
            if schema_definition:
                # If caller provided a full text.format config, use it directly
                text_config = schema_definition

            # Call Responses API
            try:
                if text_config is not None:
                    response = openai_client.responses.create(
                        model=self.model,
                        input=messages,
                        store=False,  # Don't store conversation
                        text=text_config,  # ResponseTextConfigParam
                        top_logprobs=1,
                        include=["message.output_text.logprobs"],
                    )
                else:
                    # No structured output config - just call with basic params
                    response = openai_client.responses.create(
                        model=self.model,
                        input=messages,
                        store=False,
                    )
            except Exception as e:
                logger.error("OpenAI Responses API call failed: %s", e)
                raise

            # Extract response text and logprobs following test pattern (test_foundry_responses_api.py:422-523)
            return response

        except Exception as e:
            logger.error("Failed to extract schema: %s", e)
            raise

    def _cu_to_text(self, cu_normalized: CuNormalizedDocument) -> str:
        """Convert CU normalized document to text representation.

        Args:
            cu_normalized: Normalized CU document

        Returns:
            Text representation
        """
        text_parts = []

        # Add pages content
        for page in cu_normalized.pages:
            text_parts.append(f"Page {page.pageNumber}:")
            for line in page.lines:
                if isinstance(line, dict) and "content" in line:
                    text_parts.append(line["content"])

        # Add tables
        for table in cu_normalized.tables:
            text_parts.append(f"\nTable ({table.rowCount}x{table.columnCount}):")
            for cell in table.cells:
                if isinstance(cell, dict) and "content" in cell:
                    text_parts.append(cell["content"])

        return "\n".join(text_parts)

    def _normalize_logprobs_data(self, logprobs_data: Any) -> list[Any]:
        """Normalize logprobs data to a list format.
        
        Handles different logprobs structures (list, dict with "content" key, etc.)
        following the pattern from test_responses_api_direct_call().
        
        Args:
            logprobs_data: Logprobs data in various formats
            
        Returns:
            List of logprob dictionaries/objects, or empty list if structure is unexpected
        """
        if isinstance(logprobs_data, list):
            return logprobs_data
        elif isinstance(logprobs_data, dict):
            # Check for "content" key
            if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                return logprobs_data["content"]
            else:
                logger.warning("Unexpected logprobs dict structure: %s", type(logprobs_data))
                return []
        else:
            logger.warning("Unexpected logprobs type: %s", type(logprobs_data))
            return []

    def _extract_logprobs_list(self, response: Any) -> list[Any] | None:
        """Extract logprobs list from OpenAI Responses API response.
        
        Follows the pattern from test_responses_api_direct_call() to handle
        different logprobs structures and locations in the response.
        
        Args:
            response: OpenAI Responses API response object
            
        Returns:
            List of logprob dictionaries/objects, or None if not available
        """
        logprobs_list: list[Any] = []
        logprobs_found = False
        
        # First, check content items in output messages
        if hasattr(response, "output") and response.output:
            output = response.output
            if isinstance(output, list):
                for message in output:
                    if hasattr(message, "content") and message.content:
                        for content_item in message.content:
                            if hasattr(content_item, "logprobs") and content_item.logprobs:
                                logprobs_found = True
                                logger.debug("Found logprobs in content item")
                                
                                # Get logprobs as list - handle different structures
                                logprobs_data = content_item.logprobs
                                logprobs_list = self._normalize_logprobs_data(logprobs_data)
                                
                                # Ensure logprobs_list is a list
                                if not isinstance(logprobs_list, list):
                                    logprobs_list = []
                                
                                logger.debug("Extracted %d token logprobs from content item", len(logprobs_list))
                                break
                        if logprobs_found:
                            break
        
        # Check for logprobs at response level if not found in content items
        if not logprobs_found and hasattr(response, "logprobs") and response.logprobs:
            logprobs_found = True
            logger.debug("Found logprobs at response level")
            logprobs_data = response.logprobs
            logprobs_list = self._normalize_logprobs_data(logprobs_data)
        
        # Also check response.output if it's a dict (fallback)
        if not logprobs_found and hasattr(response, "output") and isinstance(response.output, dict):
            if "logprobs" in response.output:
                logprobs_data = response.output["logprobs"]
                logger.debug("Found logprobs in response.output.logprobs")
                logprobs_list = self._normalize_logprobs_data(logprobs_data)
            elif "metadata" in response.output and isinstance(response.output["metadata"], dict):
                if "logprobs" in response.output["metadata"]:
                    logprobs_data = response.output["metadata"]["logprobs"]
                    logger.debug("Found logprobs in response.output.metadata.logprobs")
                    logprobs_list = self._normalize_logprobs_data(logprobs_data)
        
        if not logprobs_list:
            logger.debug("Log probabilities not found in response. Available attributes: %s", dir(response))
            if hasattr(response, "output") and isinstance(response.output, dict):
                logger.debug("Response output keys: %s", list(response.output.keys()))
            return None
        
        return logprobs_list

    def _calculate_confidence_from_logprobs(self, logprobs: Any) -> float | None:
        """Calculate average confidence score from log probabilities.

        Args:
            logprobs: Log probabilities data from OpenAI response

        Returns:
            Average confidence score (0.0 to 1.0) or None if not available
        """
        try:
            if not logprobs:
                return None

            # Extract token log probabilities
            # Logprobs structure varies, but typically contains:
            # - content: list of token logprobs
            # - Each token has: token, logprob, top_logprobs
            total_logprob = 0.0
            token_count = 0

            # Handle different logprobs structures
            if isinstance(logprobs, dict):
                # Check for content array
                if "content" in logprobs and isinstance(logprobs["content"], list):
                    for item in logprobs["content"]:
                        if isinstance(item, dict) and "logprob" in item:
                            # Convert log probability to probability (exp(logprob))
                            # Then normalize to 0-1 confidence
                            logprob = item.get("logprob", 0.0)
                            if logprob is not None:
                                # Logprob is negative, higher (less negative) = more confident
                                # Convert to confidence: exp(logprob) gives probability
                                prob = math.exp(logprob) if logprob > -100 else 0.0
                                total_logprob += prob
                                token_count += 1
                # Check if it's a direct list
                elif isinstance(logprobs, list):
                    for item in logprobs:
                        if isinstance(item, dict) and "logprob" in item:
                            logprob = item.get("logprob", 0.0)
                            if logprob is not None:
                                prob = math.exp(logprob) if logprob > -100 else 0.0
                                total_logprob += prob
                                token_count += 1

            if token_count == 0:
                return None

            # Calculate average confidence
            avg_confidence = total_logprob / token_count
            # Ensure it's in valid range
            return max(0.0, min(1.0, avg_confidence))

        except Exception as e:
            logger.warning("Failed to calculate confidence from logprobs: %s", e)
            return None

    def _format_schema_instruction(self, json_schema: dict[str, Any]) -> str:
        """Format JSON schema as instruction text for the model.

        Args:
            json_schema: JSON schema definition

        Returns:
            Formatted instruction string
        """
        schema_str = json.dumps(json_schema.get("schema", json_schema), indent=2)
        return (
            "IMPORTANT: You must respond with valid JSON that matches the following schema exactly:\n"
            f"```json\n{schema_str}\n```\n"
            "Ensure your response is valid JSON and conforms to this schema structure."
        )

    def _get_default_schema(self, doc_type: str) -> dict[str, Any]:
        """Get default JSON schema for structured outputs (generic schema).

        Args:
            doc_type: Document type

        Returns:
            JSON schema definition
        """
        return {
            "name": f"{doc_type}_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fieldPath": {"type": "string"},
                                "value": {},
                                "evidence": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "page": {"type": "integer"},
                                            "polygon": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "x": {"type": "number"},
                                                        "y": {"type": "number"},
                                                    },
                                                },
                                            },
                                            "sourceText": {"type": "string"},
                                            "confidence": {"type": "number"},
                                        },
                                    },
                                },
                            },
                        },
                    }
                },
            },
        }

