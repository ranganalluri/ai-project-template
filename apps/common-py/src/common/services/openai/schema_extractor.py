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
        cu_normalized: CuNormalizedDocument,
        doc_type: str,
        image_content_items: list[dict[str, Any]] | None = None,
        schema_definition: dict[str, Any] | None = None,
    ) -> tuple[ExtractedSchema, dict[str, Any]]:
        """Extract schema from normalized CU document using OpenAI Responses API.

        Args:
            cu_normalized: Normalized CU document (for reference, not used in API call if images provided)
            doc_type: Document type identifier
            image_content_items: Optional list of pre-converted image content items for LLM API.
                                 Format: [{"type": "input_image", "image_url": "data:..."}, ...]
                                 If provided, uses images instead of text
            schema_definition: Optional JSON schema definition for structured outputs

        Returns:
            Tuple of (ExtractedSchema, evidence_json)
        """
        try:
            openai_client = self.client.get_client()

            # Prepare input messages in Responses API format
            if image_content_items:
                # Use pre-converted image content items
                # Responses API expects content array with "input_text" and "input_image" types
                content_items = [
                    {
                        "type": "input_text",
                        "text": f"Extract structured data from these document pages (type: {doc_type}). For each extracted field, provide the page number and approximate bounding box coordinates where the field appears.",
                    }
                ]
                content_items.extend(image_content_items)
            else:
                # Fallback to text representation
                cu_text = self._cu_to_text(cu_normalized)
                content_items = [
                    {
                        "type": "input_text",
                        "text": f"Extract structured data from this document (type: {doc_type}).\n\n{cu_text}",
                    }
                ]

            # Responses API expects messages as a list of message objects with role and content
            messages = [
                {
                    "role": "user",
                    "content": content_items,
                }
            ]

            # Prepare JSON schema config for structured outputs (Responses text.format)
            text_config: dict[str, Any] | None = None
            if schema_definition:
                # If caller provided a full text.format config, use it directly
                text_config = schema_definition
            elif doc_type.lower() == "invoice":
                # Use Invoice Pydantic model to generate JSON Schema format config
                text_config = {"format": Invoice.get_json_schema_definition()}

            # Call Responses API
            logger.info("Calling OpenAI Responses API for schema extraction (doc_type: %s)", doc_type)
            try:
                if text_config is not None:
                    response = openai_client.responses.create(
                        model=self.model,
                        input=messages,
                        store=False,  # Don't store conversation
                        text=text_config,  # ResponseTextConfigParam
                        top_logprobs=5,
                        include=["message.output_text.logprobs"],
                    )
                else:
                    # No structured output config – just call with basic params
                    response = openai_client.responses.create(
                        model=self.model,
                        input=messages,
                        store=False,
                    )
            except Exception as e:
                logger.error("OpenAI Responses API call failed: %s", e)
                raise

            # Extract response text from ResponseOutputMessage objects
            output_text = ""
            if hasattr(response, "output") and response.output:
                output = response.output
                
                # Handle ResponseOutputMessage objects (list of messages)
                if isinstance(output, list):
                    text_parts = []
                    for item in output:
                        # Check if it's a ResponseOutputMessage object
                        if hasattr(item, "content") and item.content:
                            for content_item in item.content:
                                # Check if it's a ResponseOutputText object
                                if hasattr(content_item, "text"):
                                    text_parts.append(content_item.text)
                                elif isinstance(content_item, dict) and "text" in content_item:
                                    text_parts.append(content_item["text"])
                    output_text = "".join(text_parts)
                # Handle dict format
                elif isinstance(output, dict):
                    output_text = output.get("text", "")
                # Handle string format
                elif isinstance(output, str):
                    output_text = output
                # Fallback to string conversion
                else:
                    output_text = str(output)
            
            # Strip markdown code blocks if present (```json ... ```)
            if output_text:
                output_text = output_text.strip()
                if output_text.startswith("```json"):
                    output_text = output_text[7:]  # Remove ```json
                elif output_text.startswith("```"):
                    output_text = output_text[3:]  # Remove ```
                if output_text.endswith("```"):
                    output_text = output_text[:-3]  # Remove closing ```
                output_text = output_text.strip()

            # Extract log probabilities if available
            # Note: Responses API may return logprobs automatically in the response object
            # Check multiple possible locations for logprobs data
            logprobs_data = None
            if hasattr(response, "logprobs") and response.logprobs:
                logprobs_data = response.logprobs
                logger.debug("Received log probabilities from response.logprobs")
            elif hasattr(response, "output") and isinstance(response.output, dict):
                # Check if logprobs are in output metadata
                if "logprobs" in response.output:
                    logprobs_data = response.output["logprobs"]
                    logger.debug("Received log probabilities from response.output.logprobs")
                elif "metadata" in response.output and isinstance(response.output["metadata"], dict):
                    if "logprobs" in response.output["metadata"]:
                        logprobs_data = response.output["metadata"]["logprobs"]
                        logger.debug("Received log probabilities from response.output.metadata.logprobs")
            
            # Log available response attributes for debugging
            if not logprobs_data:
                logger.debug("Log probabilities not found in response. Available attributes: %s", dir(response))
                if hasattr(response, "output") and isinstance(response.output, dict):
                    logger.debug("Response output keys: %s", list(response.output.keys()))

            # Parse JSON response
            try:
                extracted_data = json.loads(output_text) if output_text else {}
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from response: %s", output_text)
                extracted_data = {}

            # Calculate average confidence from log probabilities if available
            avg_confidence = self._calculate_confidence_from_logprobs(logprobs_data) if logprobs_data else None
            if avg_confidence is not None:
                logger.info("Calculated average confidence from logprobs: %.3f", avg_confidence)

            # Build ExtractedSchema
            fields = []
            evidence_json = {"fields": []}

            if "fields" in extracted_data:
                for field_data in extracted_data["fields"]:
                    field_path = field_data.get("fieldPath", "")
                    value = field_data.get("value")
                    evidence_spans = []

                    # Extract evidence if present
                    if "evidence" in field_data:
                        for ev_data in field_data["evidence"]:
                            # Use confidence from evidence, or fall back to average logprobs confidence
                            evidence_confidence = ev_data.get("confidence")
                            if evidence_confidence is None and avg_confidence is not None:
                                evidence_confidence = avg_confidence
                            elif evidence_confidence is None:
                                evidence_confidence = 0.0

                            evidence_spans.append(
                                EvidenceSpan(
                                    page=ev_data.get("page", 1),
                                    polygon=[
                                        Point(x=p["x"], y=p["y"]) for p in ev_data.get("polygon", [])
                                    ],
                                    sourceText=ev_data.get("sourceText", ""),
                                    confidence=float(evidence_confidence),
                                )
                            )

                    fields.append(
                        ExtractedField(
                            fieldPath=field_path,
                            value=value,
                            evidence=evidence_spans,
                        )
                    )

                    # Add to evidence JSON
                    evidence_json["fields"].append(
                        {
                            "fieldPath": field_path,
                            "evidence": [
                                {
                                    "page": ev.page,
                                    "polygon": [{"x": p.x, "y": p.y} for p in ev.polygon],
                                    "sourceText": ev.sourceText,
                                    "confidence": ev.confidence,
                                }
                                for ev in evidence_spans
                            ],
                        }
                    )

            extracted_schema = ExtractedSchema(
                docType=doc_type,
                fields=fields,
                rawModelOutput=extracted_data,
            )

            logger.info("Extracted schema with %d fields for doc_type %s", len(fields), doc_type)
            return extracted_schema, evidence_json

        except Exception as e:
            logger.error("Failed to extract schema for doc_type %s: %s", doc_type, e)
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

