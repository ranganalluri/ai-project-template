/** Content Processing API client for document extraction operations. */

import { getApiUrl } from './config';

export interface ContentProcessingRequest {
  tenantId?: string;
  userId?: string;
  docType?: string;
  analyzerId?: string;
  force?: boolean;
}

export interface PageDimension {
  page: number;
  width: number;
  height: number;
}

// Re-export FieldEvidence from utils
export type { FieldEvidence } from '../utils/pdfCoordinates';

export interface ContentProcessingResponse {
  documentId: string;
  status: string;
  originalBlobUrl?: string | null;
  schemaBlobUrl?: string | null;
  imageBlobUrls?: string[] | null;
  evidence?: {
    fields: Array<{
      fieldPath: string;
      evidence: Array<{
        page: number;
        polygon: Array<{ x: number; y: number }>;
        sourceText: string;
        confidence: number;
      }>;
    }>;
  } | null;
  pageDimensions?: PageDimension[] | null;
  error?: Record<string, unknown> | null;
}

/**
 * Process uploaded content (PDF, image, or audio) through the content processing pipeline.
 */
export async function processContent(
  file: File,
  options: ContentProcessingRequest = {}
): Promise<ContentProcessingResponse> {
  const formData = new FormData();
  formData.append('file', file);

  // Build query parameters
  const params = new URLSearchParams();
  if (options.tenantId) params.append('tenant_id', options.tenantId);
  if (options.userId) params.append('user_id', options.userId);
  if (options.docType) params.append('doc_type', options.docType);
  if (options.analyzerId) params.append('analyzer_id', options.analyzerId);
  if (options.force !== undefined) params.append('force', String(options.force));

  const url = `${getApiUrl()}/v1/content-processing/process${params.toString() ? `?${params.toString()}` : ''}`;

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to process content: ${response.status} - ${errorText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Get content processing status for a document.
 */
export async function getProcessingStatus(
  documentId: string,
  tenantId: string = 'default'
): Promise<ContentProcessingResponse> {
  const params = new URLSearchParams();
  params.append('tenant_id', tenantId);

  const response = await fetch(
    `${getApiUrl()}/v1/content-processing/${documentId}?${params.toString()}`,
    {
      method: 'GET',
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to get processing status: ${response.status} - ${errorText}`);
  }

  const data = await response.json();
  return data;
}

