from typing import Any, List, Optional

import pandas as pd
from pydantic import BaseModel

from common.utils.utils import flatten_dict


class ExtractionComparisonItem(BaseModel):
    Field: Optional[str]
    Extracted: Optional[Any]
    Confidence: Optional[str]
    IsAboveThreshold: Optional[bool]
    Polygon: Optional[Any] = None
    PageNumber: Optional[int] = None

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


class ExtractionComparisonData(BaseModel):
    items: List[ExtractionComparisonItem]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


def get_extraction_comparison_data(
    actual: dict, confidence: dict, threads_hold: float
) -> ExtractionComparisonData:
    """
    Generate a JSON object comparing the extracted fields with the expected fields.

    Args:
        actual: The extracted fields.
        confidence: The confidence values for the extracted fields.
        threads_hold: Confidence threshold for filtering.

    Returns:
        ExtractionComparisonData: The JSON object comparing the extracted fields with the expected fields.
    """

    # expected_flat = flatten_dict(expected)
    extracted_flat = flatten_dict(actual)
    confidence_flat = flatten_dict(confidence)
    # accuracy_flat = flatten_dict(accuracy)

    all_keys = sorted(set(extracted_flat.keys()))

    items = []
    for key in all_keys:
        # Extract polygon information and page number from confidence data
        polygon, page_number = _extract_polygon_and_page_for_field(confidence, key)
        
        items.append(
            ExtractionComparisonItem(
                Field=key,
                Extracted=extracted_flat.get(key),
                Confidence=f"{confidence_flat.get(f'{key}_confidence', 0.0) * 100:.2f}%",
                IsAboveThreshold=f"{True if confidence_flat.get(f'{key}_confidence', 0.0) > threads_hold else False}",
                Polygon=polygon,
                PageNumber=page_number,
            )
        )

    return ExtractionComparisonData(items=items)


def _extract_polygon_and_page_for_field(confidence: dict, field_key: str) -> tuple[Optional[Any], Optional[int]]:
    """
    Extract polygon data and page number for a specific field from Content Understanding confidence data.
    
    Navigates the confidence structure to find polygon information (combined_polygon, word_polygons, 
    word_details) and page number information from CU data.
    
    Converts flattened field keys (e.g., "customer_address_city") to nested path lookups and 
    handles both nested dictionaries and list items (e.g., "items.0.description").

    Args:
        confidence: The confidence dictionary from Content Understanding containing polygon and page information.
        field_key: The field key to extract polygon/page for. Can be:
                   - Flattened nested key: "customer_address_city" (becomes customer.address.city)
                   - List indices: "items.0.field"

    Returns:
        Tuple of (polygon_data, page_number) where:
        - polygon_data is a dict with keys: combined_polygon, word_polygons, word_details (if available)
        - page_number is an int extracted from CU data (if available)
        Returns (None, None) if neither polygon nor page data is found.
    """
    import re
    
    # Convert flattened key to path parts
    # "customer_address_city" -> try ["customer", "address", "city"]
    # Also handle list indices: "items.0.field" -> ["items", "0", "field"]
    
    # First, try splitting by underscores for flattened nested objects
    parts = field_key.replace('.', '_').split('_')
    
    # For each possible split point, try to navigate the nested structure
    def navigate_path(confidence, parts):
        """Try to navigate through confidence using the given path parts."""
        current = confidence
        for part in parts:
            if isinstance(current, dict):
                # Try the part as-is
                if part in current:
                    current = current[part]
                else:
                    return None
            elif isinstance(current, list):
                # Try parsing as list index
                try:
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                except (ValueError, TypeError):
                    return None
            else:
                return None
        return current
    
    # Try different combinations to find the nested value
    # For "customer_address_city", try: [c,a,c], [ca,a,c], [c,aa,c], [ca,ac], etc.
    current = None
    
    # First try the full path as-is (for case like "items.0.field")
    if '.' in field_key or '[' in field_key:
        parts_direct = re.split(r'[\.\[\]]', field_key)
        parts_direct = [p for p in parts_direct if p]
        current = navigate_path(confidence, parts_direct)
    
    # If not found, try splitting by underscores (for flattened names like "customer_address_city")
    if current is None:
        # Try all possible split combinations
        for i in range(1, len(parts)):
            test_parts = parts[:i] + ['_'.join(parts[i:])]
            current = navigate_path(confidence, test_parts)
            if current is not None:
                break
        
        # If still not found, try other combinations
        if current is None:
            for i in range(1, len(parts)):
                test_parts = ['_'.join(parts[:i])] + parts[i:]
                current = navigate_path(confidence, test_parts)
                if current is not None:
                    break
    
    # If still not found, just try the parts as-is
    if current is None:
        current = navigate_path(confidence, parts)
    
    # Extract polygon and page data from the final location in confidence structure
    if isinstance(current, dict):
        polygon_data = {}
        page_number = None
        
        # Extract all polygon-related fields from CU data
        polygon_fields = ["combined_polygon", "word_polygons", "word_details"]
        for poly_field in polygon_fields:
            if poly_field in current:
                polygon_data[poly_field] = current.get(poly_field)
        
        # Extract page number directly from confidence data
        # evaluate_confidence stores page_number at the field level
        if "page_number" in current:
            page_number = current.get("page_number")
        elif "pageNumber" in current:
            page_number = current.get("pageNumber")
        
        # Return results if either polygon or page data was found
        if polygon_data or page_number is not None:
            return polygon_data if polygon_data else None, page_number
    
    return None, None


def get_extraction_comparison(
    expected: dict, actual: dict, confidence: dict, accuracy: dict
):
    """
    Generate a pandas DataFrame comparing the extracted fields with the expected fields.
    If a match is found, the row is highlighted in green. If a mismatch is found, the row is highlighted in red.

    Args:
        expected: The expected fields.
        actual: The extracted fields.
        confidence: The confidence values for the extracted fields.
        accuracy: The accuracy values for the extracted fields.

    Returns:
        pd.DataFrame: The DataFrame comparing the extracted fields with the expected fields.
    """

    expected_flat = flatten_dict(expected)
    extracted_flat = flatten_dict(actual)
    confidence_flat = flatten_dict(confidence)
    accuracy_flat = flatten_dict(accuracy)

    all_keys = sorted(set(expected_flat.keys()) | set(extracted_flat.keys()))

    rows = []
    for key in all_keys:
        rows.append(
            {
                "Field": key,
                "Expected": expected_flat.get(key),
                "Extracted": extracted_flat.get(key),
                "Confidence": f"{confidence_flat.get(f'{key}_confidence', 0.0) * 100:.2f}%",
                "Accuracy": f"{'Match' if accuracy_flat.get(f'accuracy_{key}', 0.0) == 1.0 else 'Mismatch'}",
            }
        )
    df = pd.DataFrame(rows)

    def highlight_row(row):
        return [
            "background-color: #66ff33"
            if row.Accuracy == "Match"
            else "background-color: #ff9999"
        ] * len(row)

    df = df.style.apply(highlight_row, axis=1)
    return df
