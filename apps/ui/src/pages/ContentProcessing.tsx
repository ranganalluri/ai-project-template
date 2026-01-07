import React, { useCallback, useState } from 'react';
import { processContent, getProcessingStatus, type ContentProcessingResponse } from '@agentic/ui-lib';
import { Button } from '@agentic/ui-lib';
import '@/pages/Chat.css';

export const ContentProcessing: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ContentProcessingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusCheckInterval, setStatusCheckInterval] = useState<number | null>(null);

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
    </div>
  );
};

