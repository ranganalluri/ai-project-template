import React, { useCallback, useState, useMemo } from 'react';
import {
  processContent,
  getProcessingStatus,
  type ContentProcessingResponse,
  type FieldEvidence,
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

      // If processing is in progress, poll for status
      if (response.status === 'CU_PROCESSING' || response.status === 'LLM_PROCESSING') {
        const interval = window.setInterval(async () => {
          try {
            const statusResponse = await getProcessingStatus(response.documentId, 'default');
            setResult(statusResponse);

            // Stop polling if processing is complete or failed
            if (statusResponse.status === 'DONE' || statusResponse.status === 'FAILED') {
              window.clearInterval(interval);
              setStatusCheckInterval(null);
              setProcessing(false);
            }
          } catch (err) {
            console.error('Error checking status:', err);
            window.clearInterval(interval);
            setStatusCheckInterval(null);
            setProcessing(false);
          }
        }, 2000); // Poll every 2 seconds

        setStatusCheckInterval(interval);
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

  // Fetch schema data
  const [schemaData, setSchemaData] = useState<any>(null);

  React.useEffect(() => {
    if (result?.status === 'DONE' && result.schemaBlobUrl) {
      fetch(result.schemaBlobUrl)
        .then((response) => response.json())
        .then((data) => setSchemaData(data))
        .catch((err) => console.error('Failed to fetch schema:', err));
    } else {
      setSchemaData(null);
    }
  }, [result?.schemaBlobUrl, result?.status]);

  // Helper function to get value by field path
  const getValueByPath = (obj: any, path: string): any => {
    const parts = path.split('.');
    let current = obj;
    for (const part of parts) {
      if (current && typeof current === 'object' && part in current) {
        current = current[part];
      } else {
        return undefined;
      }
    }
    return current;
  };


  // Transform evidence from API to FieldEvidence format
  const fields: FieldEvidence[] = useMemo(() => {
    if (!result?.evidence?.fields) {
      return [];
    }

    if (!Array.isArray(result.evidence.fields)) {
      console.warn('Evidence fields is not an array:', result.evidence.fields);
      return [];
    }

    return result.evidence.fields
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
      .map((field: { fieldPath: string; evidence: Array<{ page: number; polygon: Array<{ x: number; y: number }>; sourceText: string; confidence: number }> }) => {
        // Get value from schema if available
        const value = schemaData ? getValueByPath(schemaData, field.fieldPath) : null;
        
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
            // Validate polygon if present
            if (ev.polygon && (!Array.isArray(ev.polygon) || ev.polygon.length < 3)) {
              console.warn(`Invalid polygon for field ${field.fieldPath}:`, ev.polygon);
              return false;
            }
            return true;
          })
          .map((ev: { page: number; polygon: Array<{ x: number; y: number }>; sourceText: string; confidence: number }) => ({
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
          value: value !== undefined ? value : null,
          confidence: avgConfidence,
          evidence: validEvidence,
        };
      })
      .filter((field: FieldEvidence) => field.evidence.length > 0); // Only include fields with valid evidence
  }, [result?.evidence, schemaData]);

  // Determine PDF URL: prefer blob URL if available, fall back to local file URL
  const pdfUrl = useMemo(() => {
    if (result?.originalBlobUrl) {
      return result.originalBlobUrl;
    }
    if (file?.type === 'application/pdf' && localPdfUrl) {
      return localPdfUrl;
    }
    return null;
  }, [result?.originalBlobUrl, file, localPdfUrl]);

  // Check if we should show the PDF viewer (PDF file selected or uploaded)
  const shouldShowPdfViewer = file?.type === 'application/pdf' && pdfUrl !== null;

  // Generate dummy fields for testing (when no real fields available)
  const dummyFields: FieldEvidence[] = useMemo(() => {
    // Only generate if we have a PDF but no real fields
    if (shouldShowPdfViewer && (!result || result.status !== 'DONE' || !result.evidence?.fields || result.evidence.fields.length === 0)) {
      // Create dummy fields with various confidence levels and shapes
      // Using standard US Letter size (612x792 points) for coordinates
      return [
        {
          fieldPath: 'invoice.total',
          value: '$1,234.56',
          confidence: 0.95,
          evidence: [
            {
              page: 1,
              polygon: [
                { x: 450, y: 100 },
                { x: 580, y: 100 },
                { x: 580, y: 130 },
                { x: 450, y: 130 },
              ],
              sourceText: '$1,234.56',
              confidence: 0.95,
            },
          ],
        },
        {
          fieldPath: 'invoice.date',
          value: '2024-01-15',
          confidence: 0.85,
          evidence: [
            {
              page: 1,
              polygon: [], // Empty polygon when using boundingBox
              boundingBox: { x: 50, y: 100, width: 150, height: 30 },
              sourceText: '2024-01-15',
              confidence: 0.85,
            },
          ],
        },
        {
          fieldPath: 'invoice.vendor',
          value: 'Acme Corporation',
          confidence: 0.75,
          evidence: [
            {
              page: 1,
              polygon: [
                { x: 50, y: 50 },
                { x: 300, y: 50 },
                { x: 300, y: 80 },
                { x: 50, y: 80 },
              ],
              sourceText: 'Acme Corporation',
              confidence: 0.75,
            },
          ],
        },
        {
          fieldPath: 'invoice.lineItems',
          value: 'Multiple items',
          confidence: 0.65,
          evidence: [
            {
              page: 1,
              polygon: [], // Empty polygon when using boundingBox
              boundingBox: { x: 50, y: 200, width: 500, height: 200 },
              sourceText: 'Item 1, Item 2, Item 3',
              confidence: 0.65,
            },
          ],
        },
        {
          fieldPath: 'invoice.invoiceNumber',
          value: 'INV-2024-001',
          confidence: 0.55,
          evidence: [
            {
              page: 1,
              polygon: [
                { x: 400, y: 50 },
                { x: 550, y: 50 },
                { x: 550, y: 75 },
                { x: 400, y: 75 },
              ],
              sourceText: 'INV-2024-001',
              confidence: 0.55,
            },
          ],
        },
      ];
    }
    return [];
  }, [shouldShowPdfViewer, result]);

  return (
    <div className="flex flex-col h-full p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Content Processing</h1>
        <p className="text-gray-600">
          Upload PDFs, images, or audio files to extract structured data using AI-powered content understanding.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
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

      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Processing Results</h2>
          
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-600">Document ID</p>
              <p className="font-mono text-sm">{result.documentId}</p>
            </div>

            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-semibold ${getStatusColor(result.status)}`}>
                {getStatusLabel(result.status)}
              </p>
            </div>

            {result.originalBlobUrl && (
              <div>
                <p className="text-sm text-gray-600">Original File</p>
                <a
                  href={result.originalBlobUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm break-all"
                >
                  {result.originalBlobUrl}
                </a>
              </div>
            )}

            {result.schemaBlobUrl && (
              <div>
                <p className="text-sm text-gray-600">Extracted Schema</p>
                <a
                  href={result.schemaBlobUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm break-all"
                >
                  {result.schemaBlobUrl}
                </a>
              </div>
            )}

            {result.imageBlobUrls && result.imageBlobUrls.length > 0 && (
              <div>
                <p className="text-sm text-gray-600">Page Images ({result.imageBlobUrls.length})</p>
                <div className="mt-2 space-y-1">
                  {result.imageBlobUrls.map((url, index) => (
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

            {result.error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded">
                <p className="text-sm font-semibold text-red-700 mb-1">Error</p>
                <pre className="text-xs text-red-600 whitespace-pre-wrap">
                  {JSON.stringify(result.error, null, 2)}
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
          {result?.status === 'DONE' && fields.length === 0 && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm">
              No extracted fields found. The document may not contain extractable data, or processing may not have completed successfully.
            </div>
          )}
          {result?.status === 'DONE' && !result.pageDimensions && (
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
                  fields={result?.status === 'DONE' ? fields : dummyFields}
                  pageDimensions={result?.pageDimensions || [{ page: 1, width: 612, height: 792 }]}
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
                fields={result?.status === 'DONE' ? fields : dummyFields}
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

