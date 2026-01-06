"""Integration tests for Azure Content Understanding client.

These tests make real API calls to the CU service.
Set environment variables:
- CU_ENDPOINT: https://rr-eu1-dev-ai-02.services.ai.azure.com/
- CU_KEY: Your API key

Run with: pytest tests/test_cu_client_integration.py -v -m integration
"""

import pytest

from common.config.document_config import get_document_config
from common.infra.http.cu_client import AzureContentUnderstandingClient


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def cu_client():
    """Create a CU client using environment variables."""
    config = get_document_config()
    config.cu_endpoint = "https://rr-eu1-dev-ai-02.services.ai.azure.com/"
    config.cu_key = "ef8f17ba6c6644d68be1d19b3ee344cc"
    if not config.cu_endpoint:
        pytest.skip("CU_ENDPOINT environment variable not set")
    if not config.cu_key:
        pytest.skip("CU_KEY environment variable not set")
    
    return AzureContentUnderstandingClient(config=config)


@pytest.fixture
def test_invoice_url():
    """Test invoice URL from Azure samples."""
    return "https://github.com/Azure-Samples/azure-ai-content-understanding-python/raw/refs/heads/main/data/invoice.pdf"

class TestAzureContentUnderstandingClientIntegration:
    """Integration tests for AzureContentUnderstandingClient with real API calls."""

    @pytest.mark.slow
    def test_begin_analyze_with_url(self, cu_client, test_invoice_url):
        """Test begin_analyze with a real URL."""
        response = cu_client.begin_analyze("prebuilt-invoice", test_invoice_url)
        
        # Verify response
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        assert "operation-location" in response.headers, "Missing operation-location header"
        
        # Verify response body
        response_data = response.json()
        assert "id" in response_data
        assert response_data.get("status") == "Running"
        assert "result" in response_data

    def test_poll_result_complete_flow(self, cu_client, test_invoice_url):
        """Test complete flow: begin_analyze -> poll_result."""
        # Start analysis
        response = cu_client.begin_analyze("prebuilt-invoice", test_invoice_url)
        
        assert response.status_code == 202
        operation_location = response.headers.get("operation-location")
        assert operation_location is not None
        
        # Poll for result (with longer timeout for real API)
        result = cu_client.poll_result(response, timeout_seconds=300, polling_interval_seconds=3)
        
        # Verify final result
        assert result.get("status") == "succeeded", f"Expected succeeded, got: {result.get('status')}"
        assert "result" in result
        assert "contents" in result["result"] or "analyzerId" in result["result"]

    def test_get_analyze_url_format(self, cu_client):
        """Test that analyze URL is correctly formatted."""
        url = cu_client._get_analyze_url("prebuilt-invoice")
        
        assert cu_client.config.cu_endpoint in url
        assert "prebuilt-invoice" in url
        assert ":analyze" in url
        assert "api-version=2025-11-01" in url

    def test_headers_include_api_key(self, cu_client):
        """Test that headers include the API key."""
        headers = cu_client._headers
        
        assert "Ocp-Apim-Subscription-Key" in headers
        assert headers["Ocp-Apim-Subscription-Key"] == cu_client.config.cu_key
        assert "x-ms-useragent" in headers

    def test_begin_analyze_invalid_analyzer(self, cu_client, test_invoice_url):
        """Test begin_analyze with invalid analyzer ID."""
        with pytest.raises(Exception):  # Should raise HTTPError or similar
            cu_client.begin_analyze("invalid-analyzer-id", test_invoice_url)

    def test_begin_analyze_invalid_url(self, cu_client):
        """Test begin_analyze with invalid URL."""
        with pytest.raises(Exception):  # Should raise HTTPError or similar
            cu_client.begin_analyze("prebuilt-invoice", "https://invalid-url-that-does-not-exist.com/file.pdf")

    def test_poll_result_with_real_operation(self, cu_client, test_invoice_url):
        """Test poll_result with a real operation that may take time."""
        # Start analysis
        response = cu_client.begin_analyze("prebuilt-invoice", test_invoice_url)
        
        # Get operation location
        operation_location = response.headers.get("operation-location")
        assert operation_location is not None
        
        # Poll with reasonable timeout
        result = cu_client.poll_result(
            response,
            timeout_seconds=300,  # 5 minutes for real processing
            polling_interval_seconds=2
        )
        
        # Verify we got a result
        assert result is not None
        assert "status" in result
        assert result["status"] in ["succeeded", "failed"]  # Should be terminal state

    @pytest.mark.slow
    def test_multiple_analyses_sequential(self, cu_client, test_invoice_url):
        """Test multiple analyses in sequence."""
        analyzer_id = "prebuilt-invoice"
        
        # Run first analysis
        response1 = cu_client.begin_analyze(analyzer_id, test_invoice_url)
        result1 = cu_client.poll_result(response1, timeout_seconds=300, polling_interval_seconds=2)
        assert result1.get("status") == "succeeded"
        
        # Run second analysis
        response2 = cu_client.begin_analyze(analyzer_id, test_invoice_url)
        result2 = cu_client.poll_result(response2, timeout_seconds=300, polling_interval_seconds=2)
        assert result2.get("status") == "succeeded"

