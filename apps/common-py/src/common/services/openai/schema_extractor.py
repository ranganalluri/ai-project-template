"""Service layer: Business logic for schema extraction using OpenAI Responses API."""

import json
import logging
from typing import Any

from common.infra.openai.openai_client import OpenAIClient
from common.models.document import CuNormalizedDocument, EvidenceSpan, ExtractedField, ExtractedSchema, Point

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
        self, cu_normalized: CuNormalizedDocument, doc_type: str, schema_definition: dict[str, Any] | None = None
    ) -> tuple[ExtractedSchema, dict[str, Any]]:
        """Extract schema from normalized CU document using OpenAI Responses API.

        Args:
            cu_normalized: Normalized CU document
            doc_type: Document type identifier
            schema_definition: Optional JSON schema definition for structured outputs

        Returns:
            Tuple of (ExtractedSchema, evidence_json)
        """
        try:
            openai_client = self.client.get_client()

            # Prepare input messages with CU document content
            # Convert CU normalized document to text representation for LLM
            cu_text = self._cu_to_text(cu_normalized)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract structured data from this document (type: {doc_type}).\n\n{cu_text}",
                        }
                    ],
                }
            ]

            # Prepare response format (JSON schema for structured outputs)
            response_format = schema_definition or self._get_default_schema(doc_type)

            # Call Responses API
            logger.info(f"Calling OpenAI Responses API for schema extraction (doc_type: {doc_type})")
            response = openai_client.responses.create(
                model=self.model,
                input=messages,
                response_format={"type": "json_schema", "json_schema": response_format},
                store=False,  # Don't store conversation
            )

            # Extract response
            if hasattr(response, "output") and response.output:
                output_text = response.output.get("text", "") if isinstance(response.output, dict) else str(response.output)
            else:
                output_text = ""

            # Parse JSON response
            try:
                extracted_data = json.loads(output_text) if output_text else {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {output_text}")
                extracted_data = {}

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
                            evidence_spans.append(
                                EvidenceSpan(
                                    page=ev_data.get("page", 1),
                                    polygon=[
                                        Point(x=p["x"], y=p["y"]) for p in ev_data.get("polygon", [])
                                    ],
                                    sourceText=ev_data.get("sourceText", ""),
                                    confidence=ev_data.get("confidence", 0.0),
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

            logger.info(f"Extracted schema with {len(fields)} fields for doc_type {doc_type}")
            return extracted_schema, evidence_json

        except Exception as e:
            logger.error(f"Failed to extract schema for doc_type {doc_type}: {e}")
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

    def _get_default_schema(self, doc_type: str) -> dict[str, Any]:
        """Get default JSON schema for structured outputs.

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

