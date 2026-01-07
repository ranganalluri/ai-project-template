"""Service layer: Map extracted schema fields to CU polygons/bounding boxes."""

import logging
from typing import Any

from common.models.document import CuNormalizedDocument, EvidenceSpan, ExtractedField, ExtractedSchema, Point

logger = logging.getLogger(__name__)


class EvidenceMapper:
    """Service layer: Map extracted schema fields to CU polygons/bounding boxes."""

    def map_evidence_to_cu_polygons(
        self,
        extracted_schema: ExtractedSchema,
        cu_normalized: CuNormalizedDocument,
        image_metadata: list[dict],
    ) -> ExtractedSchema:
        """Map extracted schema fields to CU polygons from normalized CU document.

        Args:
            extracted_schema: Extracted schema with field paths and values
            cu_normalized: Normalized CU document with polygons
            image_metadata: Image metadata: [{"page": 1, "blobUrl": "...", "width": 800, "height": 1200}, ...]

        Returns:
            Updated ExtractedSchema with accurate polygon coordinates from CU
        """
        try:
            updated_fields = []

            for field in extracted_schema.fields:
                updated_evidence = []

                # For each evidence span in the field
                for evidence_span in field.evidence:
                    # Try to match sourceText to CU words/lines
                    matched_polygon = self._find_cu_polygon_for_text(
                        evidence_span.sourceText, evidence_span.page, cu_normalized
                    )

                    if matched_polygon:
                        # Use CU polygon coordinates
                        updated_evidence.append(
                            EvidenceSpan(
                                page=evidence_span.page,
                                polygon=matched_polygon,
                                sourceText=evidence_span.sourceText,
                                confidence=evidence_span.confidence,
                            )
                        )
                    else:
                        # Keep original evidence if no match found
                        updated_evidence.append(evidence_span)
                        logger.warning(
                            "Could not find CU polygon for text '%s' on page %d",
                            evidence_span.sourceText,
                            evidence_span.page,
                        )

                updated_fields.append(
                    ExtractedField(
                        fieldPath=field.fieldPath,
                        value=field.value,
                        evidence=updated_evidence,
                    )
                )

            return ExtractedSchema(
                docType=extracted_schema.docType,
                fields=updated_fields,
                rawModelOutput=extracted_schema.rawModelOutput,
            )

        except Exception as e:
            logger.error("Failed to map evidence to CU polygons: %s", e)
            # Return original schema on error
            return extracted_schema

    def _find_cu_polygon_for_text(
        self, source_text: str, page_num: int, cu_normalized: CuNormalizedDocument
    ) -> list[Point] | None:
        """Find CU polygon for given text on a specific page.

        Args:
            source_text: Text to match
            page_num: Page number (1-indexed)
            cu_normalized: Normalized CU document

        Returns:
            List of Points forming polygon, or None if not found
        """
        try:
            # Normalize source text for matching
            source_text_lower = source_text.lower().strip()

            # Find matching page
            page_data = None
            for page in cu_normalized.pages:
                if page.pageNumber == page_num:
                    page_data = page
                    break

            if not page_data:
                return None

            # Try to match in words first (more precise)
            if page_data.words:
                for word in page_data.words:
                    if isinstance(word, dict):
                        word_text = word.get("content", "").lower().strip()
                        if source_text_lower in word_text or word_text in source_text_lower:
                            # Extract polygon from word
                            polygon = self._extract_polygon_from_cu_element(word)
                            if polygon:
                                return polygon

            # Try to match in lines
            if page_data.lines:
                for line in page_data.lines:
                    if isinstance(line, dict):
                        line_text = line.get("content", "").lower().strip()
                        if source_text_lower in line_text or line_text in source_text_lower:
                            # Extract polygon from line
                            polygon = self._extract_polygon_from_cu_element(line)
                            if polygon:
                                return polygon

            # Try to match in document-level lines
            for line in cu_normalized.lines:
                if isinstance(line, dict):
                    # Check if line is on the correct page
                    bounding_regions = line.get("boundingRegions", [])
                    for region in bounding_regions:
                        if region.get("pageNumber") == page_num:
                            line_text = line.get("content", "").lower().strip()
                            if source_text_lower in line_text or line_text in source_text_lower:
                                polygon = self._extract_polygon_from_cu_element(line)
                                if polygon:
                                    return polygon

            return None

        except Exception as e:
            logger.error("Error finding CU polygon for text '%s': %s", source_text, e)
            return None

    def _extract_polygon_from_cu_element(self, element: dict) -> list[Point] | None:
        """Extract polygon coordinates from CU element.

        Args:
            element: CU element (word, line, etc.) with polygon data

        Returns:
            List of Points forming polygon, or None if not found
        """
        try:
            # Try different polygon formats from CU
            # Format 1: polygon array directly
            if "polygon" in element:
                polygon_data = element["polygon"]
                if isinstance(polygon_data, list) and len(polygon_data) > 0:
                    points = []
                    for p in polygon_data:
                        if isinstance(p, dict):
                            points.append(Point(x=p.get("x", 0.0), y=p.get("y", 0.0)))
                        elif isinstance(p, (list, tuple)) and len(p) >= 2:
                            points.append(Point(x=float(p[0]), y=float(p[1])))
                    if points:
                        return points

            # Format 2: boundingBox with polygon
            if "boundingBox" in element:
                bbox = element["boundingBox"]
                if isinstance(bbox, list) and len(bbox) >= 4:
                    # Convert bounding box [x, y, width, height] to polygon
                    x, y, width, height = bbox[0], bbox[1], bbox[2], bbox[3]
                    return [
                        Point(x=x, y=y),
                        Point(x=x + width, y=y),
                        Point(x=x + width, y=y + height),
                        Point(x=x, y=y + height),
                    ]

            # Format 3: boundingRegions
            if "boundingRegions" in element:
                regions = element["boundingRegions"]
                if isinstance(regions, list) and len(regions) > 0:
                    region = regions[0]  # Use first region
                    polygon_data = region.get("polygon")
                    if polygon_data:
                        points = []
                        for p in polygon_data:
                            if isinstance(p, dict):
                                points.append(Point(x=p.get("x", 0.0), y=p.get("y", 0.0)))
                            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                                points.append(Point(x=float(p[0]), y=float(p[1])))
                        if points:
                            return points

            return None

        except Exception as e:
            logger.error("Error extracting polygon from CU element: %s", e)
            return None

