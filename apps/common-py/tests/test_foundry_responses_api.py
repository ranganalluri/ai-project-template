"""Simple integration test for OpenAI Responses API.

This test makes a direct call to the Responses API with a static prompt.
Set environment variables:
- FOUNDRY_ENDPOINT: Your Foundry endpoint
- FOUNDRY_DEPLOYMENT_NAME: Your deployment name (defaults to gpt-4.1)

Run with: pytest tests/test_foundry_responses_api.py -v -m integration
"""

import json
import math
from typing import Any, Iterable
import os
import sys
import pathlib
import pytest

from common.config.document_config import get_document_config
from common.infra.openai.openai_client import OpenAIClient
from common.schemas.invoice_schema import Invoice, InvoiceItem
from common.services.openai.confidence_evaluator import OpenAIConfidenceEvaluator
from common.infra.http.cu_client import AzureContentUnderstandingClient
from common.models.content_understanding import AnalyzedResult
from common.services.image.image_utils import convert_image_to_base64
from common.services.cu.content_understanding_confidence_evaluator import evaluate_confidence
from common.services.confidence import merge_confidence_values
from common.models.comparison import get_extraction_comparison_data
from common.models.model import DataExtractionResult
# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(name="openai_client")
def _openai_client():
    """Create OpenAI client using Foundry."""
    config = get_document_config()
    if not config.foundry_endpoint:
        pytest.skip("FOUNDRY_ENDPOINT environment variable not set")
    
    return OpenAIClient(config=config)


@pytest.fixture(name="cu_client")
def _cu_client():
    """Create CU client using environment variables."""
    config = get_document_config()
    if not config.cu_endpoint:
        pytest.skip("CU_ENDPOINT environment variable not set")
    if not config.cu_key:
        pytest.skip("CU_KEY environment variable not set")
    
    return AzureContentUnderstandingClient(config=config)

def calculate_confidence_from_logprobs(logprobs_data: Any) -> float | None:
    """Calculate average confidence score from log probabilities.
    
    Args:
        logprobs_data: Log probabilities data from OpenAI response
        
    Returns:
        Average confidence score (0.0 to 1.0) or None if not available
    """
    try:
        if not logprobs_data:
            return None

        total_logprob = 0.0
        token_count = 0

        # Handle different logprobs structures
        if isinstance(logprobs_data, list):
            # logprobs_data is a list directly
            for item in logprobs_data:
                if isinstance(item, dict) and "logprob" in item:
                    logprob = item.get("logprob", 0.0)
                    if logprob is not None:
                        # Convert log probability to probability (exp(logprob))
                        prob = math.exp(logprob) if logprob > -100 else 0.0
                        total_logprob += prob
                        token_count += 1
        elif isinstance(logprobs_data, dict):
            # Check for content array
            if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                for item in logprobs_data["content"]:
                    if isinstance(item, dict) and "logprob" in item:
                        logprob = item.get("logprob", 0.0)
                        if logprob is not None:
                            # Convert log probability to probability (exp(logprob))
                            prob = math.exp(logprob) if logprob > -100 else 0.0
                            total_logprob += prob
                            token_count += 1

        if token_count == 0:
            return None

        # Calculate average confidence
        avg_confidence = total_logprob / token_count
        # Ensure it's in valid range
        return max(0.0, min(1.0, avg_confidence))
    except Exception:
        return None


def extract_token_logprobs(logprobs_data: Any) -> list[dict[str, Any]]:
    """Extract token-level logprobs from response.
    
    Args:
        logprobs_data: Log probabilities data from OpenAI response
        
    Returns:
        List of token logprob dictionaries with token, logprob, and probability
    """
    tokens = []
    
    if not logprobs_data:
        return tokens
    
    try:
        if isinstance(logprobs_data, list):
            # logprobs_data is a list directly
            for item in logprobs_data:
                if isinstance(item, dict):
                    token = item.get("token", "")
                    logprob = item.get("logprob")
                    if logprob is not None:
                        prob = math.exp(logprob) if logprob > -100 else 0.0
                        tokens.append({
                            "token": token,
                            "logprob": logprob,
                            "probability": prob,
                            "confidence": prob
                        })
        elif isinstance(logprobs_data, dict):
            # Check for content array
            if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                for item in logprobs_data["content"]:
                    if isinstance(item, dict):
                        token = item.get("token", "")
                        logprob = item.get("logprob")
                        if logprob is not None:
                            prob = math.exp(logprob) if logprob > -100 else 0.0
                            tokens.append({
                                "token": token,
                                "logprob": logprob,
                                "probability": prob,
                                "confidence": prob  # Same as probability for single token
                            })
    except Exception:
        pass
    
    return tokens

def _enrich_merged_confidence_with_polygons(merged_conf: dict, cu_confidence: dict) -> dict:
    """Enrich merged confidence score with polygon data and page numbers from Content Understanding.
    
    Ensures that polygon information (combined_polygon, word_polygons, word_details)
    and page numbers from Content Understanding confidence are preserved in the merged result 
    for all fields including nested fields and list items.
    
    Args:
        merged_conf: The merged confidence dictionary from GPT and CU
        cu_confidence: The original Content Understanding confidence with polygon data
        
    Returns:
        Enriched merged confidence dictionary with polygon information and page numbers
    """
    import copy
    
    def _merge_with_polygons(merged: dict, cu: dict) -> dict:
        """Recursively merge polygon data and page numbers from CU confidence into merged confidence."""
        for key, cu_value in cu.items():
            if key == "_overall":
                continue
            
            # Ensure key exists in merged
            if key not in merged:
                if isinstance(cu_value, dict):
                    merged[key] = {}
                elif isinstance(cu_value, list):
                    merged[key] = []
                else:
                    merged[key] = cu_value
                    continue
            
            merged_value = merged[key]
            
            # Handle dictionary values
            if isinstance(cu_value, dict) and isinstance(merged_value, dict):
                # Check if this is a leaf node with polygon or page data
                polygon_fields = ["combined_polygon", "word_polygons", "word_details", "value", "confidence"]
                page_fields = ["page_number", "pageNumber"]
                has_polygon = any(field in cu_value for field in polygon_fields[:3])
                has_page = any(field in cu_value for field in page_fields)
                
                if has_polygon or has_page:
                    # This is a leaf node - copy polygon and page fields from CU
                    for poly_field in polygon_fields[:3]:
                        if poly_field in cu_value and poly_field not in merged_value:
                            merged_value[poly_field] = cu_value[poly_field]
                    
                    for page_field in page_fields:
                        if page_field in cu_value and page_field not in merged_value:
                            merged_value[page_field] = cu_value[page_field]
                else:
                    # This is a nested structure - recurse
                    _merge_with_polygons(merged_value, cu_value)
            
            # Handle list values (e.g., invoice items)
            elif isinstance(cu_value, list) and isinstance(merged_value, list):
                for idx, cu_item in enumerate(cu_value):
                    if idx < len(merged_value):
                        if isinstance(cu_item, dict) and isinstance(merged_value[idx], dict):
                            # Check if item has polygon or page data
                            polygon_fields = ["combined_polygon", "word_polygons", "word_details"]
                            page_fields = ["page_number", "pageNumber"]
                            has_polygon = any(field in cu_item for field in polygon_fields)
                            has_page = any(field in cu_item for field in page_fields)
                            
                            if has_polygon or has_page:
                                # Copy polygon and page fields
                                for poly_field in polygon_fields:
                                    if poly_field in cu_item and poly_field not in merged_value[idx]:
                                        merged_value[idx][poly_field] = cu_item[poly_field]
                                
                                for page_field in page_fields:
                                    if page_field in cu_item and page_field not in merged_value[idx]:
                                        merged_value[idx][page_field] = cu_item[page_field]
                            else:
                                # Recurse into the item
                                _merge_with_polygons(merged_value[idx], cu_item)
        
        return merged
    
    # Create a deep copy to avoid modifying originals
    enriched = copy.deepcopy(merged_conf)
    enriched = _merge_with_polygons(enriched, cu_confidence)
    return enriched

def extract_cu_data(cu_client: AzureContentUnderstandingClient):
    """Extract CU data from a document."""
    current_dir = pathlib.Path(__file__).parent.absolute()
    with open(os.path.join(current_dir, "data", "Invoice-94129C5E-0020.pdf"), "rb") as file:
        file_bytes = file.read()
        response = cu_client.begin_analyze(analyzer_id="prebuilt-read", file_bytes=file_bytes)
        result = cu_client.poll_result(response, timeout_seconds=300)
        return AnalyzedResult(**result), file_bytes


def convert_pdf_page_to_image_base64(pdf_bytes: bytes, page_num: int = 0, dpi: int = 200) -> str | None:
    """Convert a PDF page to a base64-encoded image.
    
    Uses the same approach as PdfImageConverter but returns base64 directly
    instead of uploading to blob storage.
    
    Args:
        pdf_bytes: PDF file bytes
        page_num: Page number (0-indexed, default: 0 for first page)
        dpi: DPI for rendering (default: 200)
        
    Returns:
        Base64 data URL string (e.g., "data:image/png;base64,...") or None if conversion fails
    """
    try:
        import fitz  # PyMuPDF
        
        # Open PDF from bytes (same as PdfImageConverter.convert_pdf_to_images)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if page_num >= len(doc):
            doc.close()
            return None
        
        try:
            # Get the page
            page = doc[page_num]
            
            # Render page to pixmap (same as PdfImageConverter)
            pix = page.get_pixmap(dpi=dpi)
            
            # Convert to PNG bytes (same as PdfImageConverter)
            image_bytes = pix.tobytes("png")
            
            # Convert to base64 data URL
            return convert_image_to_base64(image_bytes, content_type="image/png")
        finally:
            doc.close()
        
    except ImportError:
        print("⚠️  Warning: PyMuPDF (fitz) not available. Install with: pip install pymupdf")
        return None
    except Exception as e:
        print(f"⚠️  Warning: Failed to convert PDF page to image: {e}")
        return None

# def combine_pages_to_markdown(pages: Iterable[Page]) -> str:
#     """Combine pages to markdown."""
#     parts: list[str] = [f"# Extracted OCR (Azure Content Understanding)\n"]
#     for i, page in enumerate(pages, start=1):
#         parts.append(f"\n---\n## Page {page.pageNumber}\n")
#         parts.append(f"{page.markdown.strip() if page. else ""}\n")
#         parts.append("\n")
#     return "".join(parts)

@pytest.mark.slow
def test_extract_cu_data(cu_client: AzureContentUnderstandingClient):
    """Test extracting CU data from a document."""
    # Get CU data from a document
    extracted_data, file_bytes = extract_cu_data(cu_client)
    assert extracted_data is not None
    assert file_bytes is not None
    assert len(file_bytes) > 0
    assert extracted_data.result.contents is not None
    assert len(extracted_data.result.contents) > 0
    assert extracted_data.result.contents[0].kind is not None
    


@pytest.mark.slow
def test_responses_api_direct_call(openai_client: OpenAIClient, cu_client: AzureContentUnderstandingClient):
    """Test direct Responses API call with invoice text and schema extraction.
    
    This test demonstrates:
    - Extracting logprobs for each token
    - Calculating confidence for extracted field values
    - Handling duplicate items (e.g., "Software License" appearing multiple times)
    """
    client = openai_client.get_client()
    config = openai_client.config
    
    # Invoice text with all required fields (note: "Software License" appears twice)
    invoice_text = (
        "INVOICE\n"
        "Invoice Number: INV-2024-001\n"
        "Invoice Date: January 15, 2024\n"
        "Due Date: February 14, 2024\n\n"
        "BILL TO:\n"
        "Acme Corporation\n"
        "123 Business Street\n"
        "New York, NY 10001\n"
        "United States\n"
        "Phone: +1-555-123-4567\n"
        "Tax ID: 12-3456789\n\n"
        "FROM:\n"
        "Tech Solutions Inc.\n"
        "456 Vendor Avenue\n"
        "San Francisco, CA 94102\n"
        "United States\n"
        "Phone: +1-555-987-6543\n"
        "Tax ID: 98-7654321\n\n"
        "ITEMS:\n"
        "1. Software License - Qty: 5, Unit Price: $200.00, Total: $1,000.00\n"
        "2. Support Services - Qty: 1, Unit Price: $250.75, Total: $250.75\n"
        "3. Software License - Qty: 10, Unit Price: $150.00, Total: $1,500.00\n\n"
        "SUBTOTAL: $2,750.75\n"
        "TAX (8%): $220.06\n"
        "DISCOUNT: $100.00\n"
        "TOTAL: $2,870.81\n\n"
        "Payment Terms: Net 30\n"
        "Contact Email: billing@acme.com\n"
        "Remittance Address: 456 Vendor Avenue, San Francisco, CA 94102"
    )
    
    # Prepare messages with invoice text
    # You can also add image content items here:
    # {
    #     "type": "input_image",
    #     "image_url": "data:image/jpeg;base64,..."
    # }
    cu_extracted_data: AnalyzedResult
    file_bytes: bytes
    cu_extracted_data, file_bytes = extract_cu_data(cu_client)
    markdown = cu_extracted_data.result.contents[0].markdown
    
    # Convert PDF first page to image (PDFs are not images, need to render them)
    # Uses the same approach as PdfImageConverter.convert_pdf_to_images
    image_url = convert_pdf_page_to_image_base64(file_bytes, page_num=0, dpi=200)
    
    if not image_url:
        pytest.skip("Failed to convert PDF page to image. PyMuPDF may not be installed.")
    content_items: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": markdown
        },
        {
            "type": "input_image",
            "image_url": image_url
        }
    ]
    
    messages = [
        {
            "role": "user",
            "content": content_items
        }
    ]
    
    # Get Invoice schema definition
    schema_definition = {"format": Invoice.get_json_schema_definition()}
    
    # Make direct Responses API call with schema and logprobs
    response = client.responses.create(
        model=config.foundry_deployment_name,
        input=messages,
        store=False,
        text=schema_definition,
        top_logprobs=1,
        include=["message.output_text.logprobs"],
    )
    
    # Verify response
    assert response is not None
    assert hasattr(response, "output")
    
    # Extract and parse the response
    extracted_data = None
    response_text = ""
    logprobs_list: list[dict[str, Any]] = []
    logprobs_found = False
    
    if hasattr(response, "output") and response.output:
        output = response.output
        if isinstance(output, list):
            for message in output:
                if hasattr(message, "content") and message.content:
                    for content_item in message.content:
                        if hasattr(content_item, "text"):
                            response_text = content_item.text
                            assert response_text is not None
                            assert len(response_text) > 0
                            print(f"\nResponse Text: {response_text}")
                            
                            # Try to parse as JSON
                            try:
                                # Strip markdown code blocks if present
                                cleaned_text = response_text.strip()
                                # if cleaned_text.startswith("```json"):
                                #     cleaned_text = cleaned_text[7:]
                                # elif cleaned_text.startswith("```"):
                                #     cleaned_text = cleaned_text[3:]
                                # if cleaned_text.endswith("```"):
                                #     cleaned_text = cleaned_text[:-3]
                                # cleaned_text = cleaned_text.strip()
                                
                                extracted_data = json.loads(cleaned_text)
                                print("\n✅ Successfully parsed JSON response")
                                print(f"Extracted data: {json.dumps(extracted_data, indent=2)}")
                                
                                # Validate against Invoice schema
                                try:
                                    invoice = Invoice.model_validate(extracted_data)
                                    print("\n✅ Successfully validated against Invoice schema")
                                    print(f"Invoice ID: {invoice.invoice_id}")
                                    print(f"Customer: {invoice.customer_name}")
                                    print(f"Vendor: {invoice.vendor_name}")
                                    print(f"Total: ${invoice.invoice_total}")
                                    print(f"Date: {invoice.invoice_date}")
                                    print(f"Payment Terms: {invoice.payment_terms}")
                                    
                                    # Handle duplicate items - show each item separately
                                    if invoice.items:
                                        print(f"\nItems extracted ({len(invoice.items)}):")
                                        for idx, item in enumerate[InvoiceItem](invoice.items, 1):
                                            desc = item.description or "N/A"
                                            qty = item.quantity or 0
                                            total = item.total or 0.0
                                            print(f"  Item {idx}: {desc} - Qty: {qty}, Total: ${total}")
                                    
                                except Exception as e:
                                    print(f"\n⚠️  Warning: Could not validate as Invoice: {e}")
                                    
                            except json.JSONDecodeError as e:
                                print(f"\n⚠️  Warning: Could not parse response as JSON: {e}")
                        
                        # Extract logprobs from content item
                        if hasattr(content_item, "logprobs") and content_item.logprobs:
                            logprobs_found = True
                            print("\n✅ Logprobs found in content item!")
                            
                            # Get logprobs as list - handle different structures
                            logprobs_data = content_item.logprobs
                            
                            # Handle different logprobs structures
                            if isinstance(logprobs_data, list):
                                logprobs_list = logprobs_data
                            elif isinstance(logprobs_data, dict):
                                # Check for "content" key
                                if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                                    logprobs_list = logprobs_data["content"]
                                else:
                                    # Try to convert dict to list if it has token/logprob keys
                                    logprobs_list = []
                                    print(f"⚠️  Warning: Unexpected logprobs dict structure: {type(logprobs_data)}")
                            else:
                                logprobs_list = []
                                print(f"⚠️  Warning: Unexpected logprobs type: {type(logprobs_data)}")
                            
                            # Ensure logprobs_list is a list
                            if not isinstance(logprobs_list, list):
                                logprobs_list = []
                            
                            print(f"Extracted {len(logprobs_list)} token logprobs")
                            
    
    # Check for logprobs at response level
    if hasattr(response, "logprobs") and response.logprobs:
        logprobs_found = True
        print("\n✅ Logprobs found at response level")
        if not logprobs_list:
            logprobs_data = response.logprobs
            # Handle different logprobs structures
            if isinstance(logprobs_data, list):
                logprobs_list = logprobs_data
            elif isinstance(logprobs_data, dict):
                if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
                    logprobs_list = logprobs_data["content"]
                else:
                    logprobs_list = []
                    print("⚠️  Warning: Unexpected response logprobs dict structure")
            else:
                logprobs_list = []
                print(f"⚠️  Warning: Unexpected response logprobs type: {type(logprobs_data)}")
    
    # Calculate confidence for all extracted values using Microsoft's approach
    if extracted_data and logprobs_list and response_text:
        print("\n" + "="*60)
        print("CONFIDENCE EVALUATION FOR EXTRACTED VALUES")
        print("(Using Microsoft's content-processing-solution-accelerator approach)")
        print("="*60)
        
        # Use the OpenAIConfidenceEvaluator class
        evaluator = OpenAIConfidenceEvaluator(model=config.foundry_deployment_name)
        gpt_confidence_results = evaluator.evaluate_confidence(
            extract_result=extracted_data,
            generated_text=response_text,
            logprobs=logprobs_list
        )
        print(f"GPT Confidence Results: {gpt_confidence_results}")
         # Evaluate Confidence Score - Content Understanding
        # This evaluates confidence and includes page numbers and polygon information from CU
        content_understanding_confidence_score = evaluate_confidence(
            extracted_data,
            cu_extracted_data.result.contents[0],
        )
        
        # content_understanding_confidence_score now contains:
        # - Confidence values for each field
        # - Page numbers where fields were found in the document (from CU)
        # - Polygon coordinates for visual location of fields (from CU)
        # - Word details including matched text and confidence scores
        
        # Print word polygon information for debugging
        print("\n" + "="*60)
        print("WORD-LEVEL POLYGON INFORMATION")
        print("="*60)
        
        def print_polygon_info(data: dict, prefix: str = ""):
            """Recursively print polygon information for nested structures."""
            for field, conf_data in data.items():
                if field == "_overall":
                    continue
                
                if isinstance(conf_data, dict):
                    if "word_polygons" in conf_data:
                        # This is a leaf node with polygon data
                        word_polys = conf_data.get("word_polygons", [])
                        word_details = conf_data.get("word_details", [])
                        combined_poly = conf_data.get("combined_polygon")
                        value = conf_data.get("value", "")
                        
                        print(f"\n{prefix}{field}: '{value}'")
                        print(f"{prefix}  Word polygons: {len(word_polys)} polygon(s)")
                        
                        # Show matched words
                        if word_details:
                            print(f"{prefix}  Matched words:")
                            for idx, detail in enumerate(word_details, 1):
                                content = detail.get("content", "")
                                conf = detail.get("confidence", 0.0)
                                print(f"{prefix}    {idx}. '{content}' (confidence: {conf:.4f})")
                        
                        if combined_poly:
                            print(f"{prefix}  Combined polygon: {combined_poly}")
                    else:
                        # This is a nested structure
                        print(f"\n{prefix}{field}:")
                        print_polygon_info(conf_data, prefix + "  ")
                elif isinstance(conf_data, list):
                    # Handle list of items
                    print(f"\n{prefix}{field} ({len(conf_data)} items):")
                    for idx, item in enumerate(conf_data, 1):
                        if isinstance(item, dict):
                            print(f"{prefix}  Item {idx}:")
                            print_polygon_info({f"": item}, prefix + "    ")
        
        print_polygon_info(content_understanding_confidence_score)
        
        # Merge the confidence scores - Content Understanding and GPT results.
        # Ensure polygon data from Content Understanding is preserved in the merged result
        merged_confidence_score = merge_confidence_values(
            content_understanding_confidence_score, gpt_confidence_results
        )
        
        # Enhance merged confidence with polygon data and page numbers from content_understanding_confidence_score
        # Page numbers are extracted from CU data where fields were actually found in the document
        merged_confidence_score = _enrich_merged_confidence_with_polygons(
            merged_confidence_score, content_understanding_confidence_score
        )

        # Flatten extracted data and confidence score with polygons
        result_data = get_extraction_comparison_data(
            actual=extracted_data,  # Use extracted_data instead of undefined variable
            confidence=merged_confidence_score,
            threads_hold=0.8,  # TODO: Get this from config
        )

        # Extract usage information from response if available
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage"):
            usage = response.usage
            if hasattr(usage, "prompt_tokens"):
                prompt_tokens = usage.prompt_tokens or 0
            if hasattr(usage, "completion_tokens"):
                completion_tokens = usage.completion_tokens or 0
        elif hasattr(response, "usage") and isinstance(response.usage, dict):
            prompt_tokens = response.usage.get("prompt_tokens", 0)
            completion_tokens = response.usage.get("completion_tokens", 0)

        # Put all results in a single object
        # Note: Page numbers and polygons are already included in comparison_result items
        # via ExtractionComparisonItem.PageNumber and ExtractionComparisonItem.Polygon
        # which are extracted from content_understanding_confidence_score
        all_results = DataExtractionResult(
            extracted_result=extracted_data,
            confidence=merged_confidence_score,
            comparison_result=result_data,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            execution_time=0,
        )
        
        
        # Display confidence results
        print(f"\nOverall Confidence: {gpt_confidence_results.get('_overall', 0.0):.4f} ({gpt_confidence_results.get('_overall', 0.0)*100:.2f}%)")
        
        def print_confidence_recursive(conf_dict: dict[str, Any], prefix: str = ""):
            """Recursively print confidence values."""
            for key, value in conf_dict.items():
                if key == "_overall":
                    continue
                if isinstance(value, dict):
                    if "confidence" in value and "value" in value:
                        conf = value["confidence"]
                        val = value["value"]
                        print(f"{prefix}{key}: '{val}'")
                        print(f"{prefix}  Confidence: {conf:.4f} ({conf*100:.2f}%)")
                    else:
                        print(f"{prefix}{key}:")
                        print_confidence_recursive(value, prefix + "  ")
                elif isinstance(value, list):
                    print(f"{prefix}{key} ({len(value)} items):")
                    for idx, item in enumerate(value, 1):
                        if isinstance(item, dict):
                            if "confidence" in item and "value" in item:
                                conf = item["confidence"]
                                val = item["value"]
                                print(f"{prefix}  Item {idx}: '{val}'")
                                print(f"{prefix}    Confidence: {conf:.4f} ({conf*100:.2f}%)")
                            else:
                                print(f"{prefix}  Item {idx}:")
                                print_confidence_recursive(item, prefix + "    ")
        
        print_confidence_recursive(gpt_confidence_results)
    
    # Verify extracted data contains expected fields
    if extracted_data:
        expected_fields = ["invoice_id", "customer_name", "vendor_name", "invoice_total", "invoice_date", "payment_terms"]
        found_fields = [field for field in expected_fields if field in extracted_data and extracted_data.get(field)]
        print(f"\nExtracted fields: {found_fields}")
        assert found_fields, "No invoice fields were extracted"
    
    if not logprobs_found:
        print("\n⚠️  Warning: Logprobs not found in response. Check include parameter and API version.")
    else:
        print("\n✅ Logprobs successfully retrieved and processed!")
