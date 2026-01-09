import React, { useCallback, useState, useMemo } from 'react';
import {
  processContent,
  getProcessingStatus,
  type ContentProcessingResponse,
  type FieldEvidence,
  getApiUrl,
} from '@agentic/ui-lib';
import { Button, PDFViewer, FieldDetailsPanel, FieldsListPanel } from '@agentic/ui-lib';
import '@/pages/Chat.css';
import './ContentProcessing.css';

export const ContentProcessing: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ContentProcessingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusCheckInterval, setStatusCheckInterval] = useState<number | null>(null);
  const [selectedField, setSelectedField] = useState<FieldEvidence | null>(null);
  const [localPdfUrl, setLocalPdfUrl] = useState<string | null>(null);

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      const validTypes = [
        'application/pdf',
        'image/png',
        'image/jpeg',
        'image/jpg',
        'image/gif',
        'image/bmp',
        'image/tiff',
        'audio/mpeg',
        'audio/mp3',
        'audio/wav',
        'audio/m4a',
        'audio/ogg',
      ];
      const validExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.mp3', '.wav', '.m4a', '.ogg'];
      
      const fileExtension = selectedFile.name.toLowerCase().substring(selectedFile.name.lastIndexOf('.'));
      const isValidType = validTypes.includes(selectedFile.type) || validExtensions.includes(fileExtension);

      if (!isValidType) {
        setError(`Invalid file type. Supported types: PDF, images (PNG, JPG, etc.), audio (MP3, WAV, etc.)`);
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError(null);
      setResult(null);
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setProcessing(true);
    setError(null);
    setResult(null);

    try {
      // Process the file
      const response = await processContent(file, {
        tenantId: 'default',
        userId: 'default',
        docType: 'invoice',
        analyzerId: 'prebuilt-read',
        force: false,
      });

      setResult(response);
      setUploading(false);

      // Get document_id from the response (API returns snake_case)
      const documentId = response.document_id;

      // If processing is in progress, poll for status
      if (response.status === 'CU_PROCESSING' || response.status === 'LLM_PROCESSING') {
        const interval = window.setInterval(async () => {
          try {
            // Use documentId from the initial response
            const statusResponse = await getProcessingStatus(documentId, 'default');
            setResult(statusResponse);

            // Stop polling if processing is complete or failed
            if (statusResponse.status === 'DONE' || statusResponse.status === 'FAILED') {
              window.clearInterval(interval);
              setStatusCheckInterval(null);
              setProcessing(false);
              
              // If processing is done, fetch full result and schema from FastAPI using documentId
              if (statusResponse.status === 'DONE') {
                console.log('Processing complete, calling fetchFullResultAndSchema for document:', documentId);
                fetchFullResultAndSchema(documentId);
              }
            }
          } catch (err) {
            console.error('Error checking status:', err);
            window.clearInterval(interval);
            setStatusCheckInterval(null);
            setProcessing(false);
          }
        }, 2000); // Poll every 2 seconds

        setStatusCheckInterval(interval);
      } else if (response.status === 'DONE') {
        // If already done, fetch full result immediately from FastAPI using documentId from response
        setProcessing(false);
        console.log('Processing already complete, calling fetchFullResultAndSchema for document:', documentId);
        fetchFullResultAndSchema(documentId);
      } else {
        setProcessing(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process content');
      setUploading(false);
      setProcessing(false);
    }
  }, [file]);

  // Cleanup interval on unmount
  React.useEffect(() => {
    return () => {
      if (statusCheckInterval) {
        window.clearInterval(statusCheckInterval);
      }
    };
  }, [statusCheckInterval]);

  // Create local file URL for immediate PDF preview
  React.useEffect(() => {
    if (file && file.type === 'application/pdf') {
      const url = URL.createObjectURL(file);
      setLocalPdfUrl(url);
      return () => {
        URL.revokeObjectURL(url);
        setLocalPdfUrl(null);
      };
    } else {
      // Clean up previous local URL if file is not a PDF
      setLocalPdfUrl((prevUrl) => {
        if (prevUrl) {
          URL.revokeObjectURL(prevUrl);
        }
        return null;
      });
    }
  }, [file]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'DONE':
        return 'text-green-600';
      case 'FAILED':
        return 'text-red-600';
      case 'CU_PROCESSING':
      case 'LLM_PROCESSING':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'RECEIVED':
        return 'Received';
      case 'CU_PROCESSING':
        return 'Processing with Content Understanding...';
      case 'CU_DONE':
        return 'Content Understanding Complete';
      case 'LLM_PROCESSING':
        return 'Extracting Schema with AI...';
      case 'DONE':
        return 'Processing Complete';
      case 'FAILED':
        return 'Processing Failed';
      default:
        return status;
    }
  };

  // Fetch full processing result when status is DONE
  const [fullResult, setFullResult] = useState<ContentProcessingResponse | null>(null);
  const [schemaData, setSchemaData] = useState<any>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [fetchedDocumentId, setFetchedDocumentId] = useState<string | null>(null);
  const [testDocumentId, setTestDocumentId] = useState<string>('386030d3-7294-49c8-963a-11285ef13c41');

  // Function to fetch full result and extracted fields from FastAPI GET endpoint
  const fetchFullResultAndSchema = useCallback(async (documentId: string) => {
    // Prevent duplicate fetches for the same document
    if (fetchedDocumentId === documentId) {
      console.log(`Skipping duplicate fetch for document ${documentId}`);
      return;
    }

    console.log(`Fetching full result and extracted fields for document ${documentId} from FastAPI...`);
    setSchemaLoading(true);
    setSchemaError(null);
    setFetchedDocumentId(documentId);
    
    try {
      // Call GET /v1/content-processing/{document_id} to get full response with evidence
      console.log(`Calling getProcessingStatus API for document ${documentId}`);
      const apiResponse = await getProcessingStatus(documentId, 'default');
      console.log('Received API response:', apiResponse);
      setFullResult(apiResponse);
      
      // Also set result state so PDF URL calculation works (uses FastAPI endpoint)
      setResult(apiResponse);
      
      // Use evidence from API response directly (contains extracted fields with polygons)
      if (apiResponse.evidence) {
        console.log('Using evidence from API response:', apiResponse.evidence);
        // Store evidence as schemaData for compatibility with existing field transformation logic
        setSchemaData(apiResponse.evidence);
      } else if (apiResponse.schema_blob_url) {
        // Fallback: fetch schema from blob URL if evidence is not available
        console.log(`Evidence not available, fetching schema from blob URL: ${apiResponse.schema_blob_url}`);
        const schemaResponse = await fetch(apiResponse.schema_blob_url);
        if (!schemaResponse.ok) {
          throw new Error(`Failed to fetch schema: ${schemaResponse.status} ${schemaResponse.statusText}`);
        }
        const schema = await schemaResponse.json();
        console.log('Schema data loaded from blob:', schema);
        setSchemaData(schema);
      } else {
        console.warn('No evidence or schema_blob_url in API response');
        setSchemaData(null);
      }
      setSchemaLoading(false);
    } catch (err) {
      console.error('Failed to fetch processing result or extracted fields:', err);
      setSchemaError(err instanceof Error ? err.message : 'Failed to fetch processing result');
      setSchemaLoading(false);
    }
  }, [fetchedDocumentId]);

  // When processing is successful, fetch full result from API
  React.useEffect(() => {
    const documentId = result?.document_id;
    if (result?.status === 'DONE' && documentId && fetchedDocumentId !== documentId) {
      fetchFullResultAndSchema(documentId);
    } else if (result?.status !== 'DONE') {
      // Reset when status changes away from DONE
      setFullResult(null);
      setSchemaData(null);
      setSchemaLoading(false);
      setSchemaError(null);
      setFetchedDocumentId(null);
    }
  }, [result?.status, result?.document_id, fetchFullResultAndSchema, fetchedDocumentId]);

  // Transform extracted fields from schema to FieldEvidence format
  const fields: FieldEvidence[] = useMemo(() => {
    // Read fields from schemaData (ExtractedSchema structure)
    if (!schemaData?.fields || !Array.isArray(schemaData.fields)) {
      return [];
    }

    return schemaData.fields
      .filter((field: any) => {
        // Validate field structure
        if (!field || typeof field !== 'object') {
          console.warn('Invalid field entry:', field);
          return false;
        }
        if (!field.fieldPath || typeof field.fieldPath !== 'string') {
          console.warn('Field missing fieldPath:', field);
          return false;
        }
        if (!Array.isArray(field.evidence)) {
          console.warn(`Field ${field.fieldPath} missing evidence array`);
          return false;
        }
        return true;
      })
      .map((field: { 
        fieldPath: string; 
        value: any;
        evidence: Array<{ 
          page: number; 
          polygon: Array<{ x: number; y: number }>; 
          sourceText: string; 
          confidence: number;
        }> 
      }) => {
        // Validate and transform evidence
        const validEvidence = field.evidence
          .filter((ev: any) => {
            if (!ev || typeof ev !== 'object') {
              return false;
            }
            // Validate page number
            if (typeof ev.page !== 'number' || ev.page < 1 || !Number.isInteger(ev.page)) {
              console.warn(`Invalid page number for field ${field.fieldPath}:`, ev.page);
              return false;
            }
            // Validate confidence
            if (typeof ev.confidence !== 'number' || ev.confidence < 0 || ev.confidence > 1) {
              console.warn(`Invalid confidence for field ${field.fieldPath}:`, ev.confidence);
              return false;
            }
            // Validate polygon if present (polygon is optional, but if present must be valid)
            if (ev.polygon !== undefined && ev.polygon !== null) {
              if (!Array.isArray(ev.polygon)) {
                console.warn(`Invalid polygon type for field ${field.fieldPath}:`, ev.polygon);
                return false;
              }
              // Allow empty polygons - they're optional
              // Only validate structure if polygon has points
              if (ev.polygon.length > 0 && ev.polygon.length < 3) {
                console.warn(`Invalid polygon (needs at least 3 points) for field ${field.fieldPath}:`, ev.polygon);
                return false;
              }
            }
            // Allow evidence entries even without polygons if they have other valid data
            return true;
          })
          .map((ev: { 
            page: number; 
            polygon: Array<{ x: number; y: number }>; 
            sourceText: string; 
            confidence: number;
          }) => ({
            page: ev.page,
            polygon: ev.polygon || [],
            sourceText: ev.sourceText || '',
            confidence: typeof ev.confidence === 'number' ? Math.max(0, Math.min(1, ev.confidence)) : 0,
          }));

        // Calculate average confidence
        const avgConfidence = validEvidence.length > 0
          ? validEvidence.reduce((sum: number, ev: { confidence: number }) => sum + ev.confidence, 0) / validEvidence.length
          : 0;
        
        return {
          fieldPath: field.fieldPath,
          value: field.value !== undefined ? field.value : null,
          confidence: avgConfidence,
          evidence: validEvidence,
        };
      })
      .filter((field: FieldEvidence) => field.evidence.length > 0); // Only include fields with valid evidence
  }, [schemaData]);

  // Determine PDF URL: use FastAPI endpoint to serve PDF, fall back to local file URL
  const pdfUrl = useMemo(() => {
    // Use FastAPI endpoint to serve PDF instead of direct blob URL
    // This avoids CORS/authentication issues with blob storage
    const documentId = fullResult?.document_id || result?.document_id;
    if (documentId) {
      // Use FastAPI endpoint: /v1/content-processing/{document_id}/original
      const apiUrl = getApiUrl();
      return `${apiUrl}/v1/content-processing/${documentId}/original?tenant_id=default`;
    }
    // Fall back to local file URL if document hasn't been processed yet
    if (file?.type === 'application/pdf' && localPdfUrl) {
      return localPdfUrl;
    }
    return null;
  }, [fullResult?.document_id, result?.document_id, file, localPdfUrl]);

  // Check if we should show the PDF viewer (PDF file selected/uploaded OR document loaded by ID)
  const shouldShowPdfViewer = (file?.type === 'application/pdf' && pdfUrl !== null) || 
                               (pdfUrl !== null && (fullResult?.document_id || result?.document_id));


  return (
    <div className="flex flex-col h-full p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Content Processing</h1>
        <p className="text-gray-600">
          Upload PDFs, images, or audio files to extract structured data using AI-powered content understanding.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        {/* Quick test: Load specific document ID */}
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <label htmlFor="test-document-id" className="block text-sm font-medium text-gray-700 mb-2">
            Quick Test: Load Document by ID
          </label>
          <div className="flex gap-2">
            <input
              id="test-document-id"
              type="text"
              value={testDocumentId}
              onChange={(e) => setTestDocumentId(e.target.value)}
              placeholder="Enter document ID"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
            <Button
              onClick={() => {
                if (testDocumentId) {
                  setFetchedDocumentId(null); // Reset to allow fetching
                  fetchFullResultAndSchema(testDocumentId);
                }
              }}
              disabled={!testDocumentId || schemaLoading}
              className="px-4"
            >
              Load Document
            </Button>
          </div>
        </div>

        <div className="mb-4">
          <label htmlFor="file-upload" className="block text-sm font-medium text-gray-700 mb-2">
            Select File (PDF, Image, or Audio)
          </label>
          <input
            id="file-upload"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.mp3,.wav,.m4a,.ogg"
            onChange={handleFileSelect}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            disabled={uploading || processing}
            aria-label="Select file for content processing"
          />
        </div>

        {file && (
          <div className="mb-4 p-3 bg-gray-50 rounded">
            <p className="text-sm text-gray-700">
              <strong>Selected:</strong> {file.name} ({(file.size / 1024).toFixed(2)} KB)
            </p>
          </div>
        )}

        <Button
          onClick={handleUpload}
          disabled={!file || uploading || processing}
          className="w-full"
        >
          {uploading ? 'Uploading...' : processing ? 'Processing...' : 'Process Content'}
        </Button>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      {(fullResult || result) && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Processing Results</h2>
          
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-600">Document ID</p>
              <p className="font-mono text-sm">{fullResult?.document_id || result?.document_id}</p>
            </div>

            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-semibold ${getStatusColor(fullResult?.status || result?.status || '')}`}>
                {getStatusLabel(fullResult?.status || result?.status || '')}
              </p>
            </div>

            {(fullResult?.original_blob_url || result?.original_blob_url) && (
              <div>
                <p className="text-sm text-gray-600">Original File</p>
                <a
                  href={fullResult?.original_blob_url || result?.original_blob_url || ''}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm break-all"
                >
                  {fullResult?.original_blob_url || result?.original_blob_url}
                </a>
              </div>
            )}

            {(fullResult?.schema_blob_url || result?.schema_blob_url) && (
              <div>
                <p className="text-sm text-gray-600">Extracted Schema</p>
                <a
                  href={fullResult?.schema_blob_url || result?.schema_blob_url || ''}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm break-all"
                >
                  {fullResult?.schema_blob_url || result?.schema_blob_url}
                </a>
              </div>
            )}

            {((fullResult?.image_blob_urls && fullResult.image_blob_urls.length > 0) || 
              (result?.image_blob_urls && result.image_blob_urls.length > 0)) && (
              <div>
                <p className="text-sm text-gray-600">Page Images ({(fullResult?.image_blob_urls || result?.image_blob_urls || []).length})</p>
                <div className="mt-2 space-y-1">
                  {(fullResult?.image_blob_urls || result?.image_blob_urls || []).map((url, index) => (
                    <a
                      key={index}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-blue-600 hover:underline text-sm break-all"
                    >
                      Page {index + 1}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {(fullResult?.error || result?.error) && (
              <div className="p-3 bg-red-50 border border-red-200 rounded">
                <p className="text-sm font-semibold text-red-700 mb-1">Error</p>
                <pre className="text-xs text-red-600 whitespace-pre-wrap">
                  {JSON.stringify(fullResult?.error || result?.error, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* PDF Viewer with Field Highlighting - Show immediately for PDFs */}
      {shouldShowPdfViewer && (
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Document Viewer</h2>
          {processing && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
              Processing document... Field highlights will appear when processing completes.
            </div>
          )}
          {schemaLoading && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
              Loading extracted fields from schema...
            </div>
          )}
          {schemaError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              Failed to load schema: {schemaError}
            </div>
          )}
          {result?.status === 'DONE' && !schemaLoading && !schemaError && fields.length === 0 && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm">
              No extracted fields found. The document may not contain extractable data, or processing may not have completed successfully.
            </div>
          )}
          {result?.status === 'DONE' && !schemaLoading && !schemaError && fields.length > 0 && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
              Found {fields.length} extracted field{fields.length !== 1 ? 's' : ''} with evidence.
            </div>
          )}
          {result?.status === 'DONE' && !fullResult?.page_dimensions && !result?.page_dimensions && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm">
              Warning: Page dimensions not available. Field highlights may not align correctly. Using default dimensions.
            </div>
          )}
          <div className="pdf-viewer-layout">
            {/* PDF Viewer - 70% width */}
            <div className="pdf-viewer-section">
              {pdfUrl ? (
                <PDFViewer
                  pdfUrl={pdfUrl}
                  fields={fields}
                  pageDimensions={fullResult?.page_dimensions || result?.page_dimensions || [{ page: 1, width: 612, height: 792 }]}
                  selectedField={selectedField}
                  onFieldSelect={setSelectedField}
                />
              ) : (
                <div className="flex items-center justify-center h-full p-8 text-gray-500">
                  <p>PDF URL not available. Please select a PDF file.</p>
                </div>
              )}
            </div>
            {/* Fields List Panel - 30% width */}
            <div className="fields-panel-section">
              <FieldsListPanel
                fields={fields}
                selectedField={selectedField}
                onFieldSelect={setSelectedField}
              />
              {/* Field Details Panel - Show below field list when field is selected */}
              {selectedField && (
                <div className="mt-4">
                  <FieldDetailsPanel
                    field={selectedField}
                    onClose={() => setSelectedField(null)}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

