/** File API client for file upload operations. */

import type { FileUpload } from '../types/chat.types';
import { getApiUrl } from './config';

/**
 * Upload a file.
 */
export async function uploadFile(file: File): Promise<FileUpload> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${getApiUrl()}/v1/files`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to upload file: ${response.status}`);
  }

  return response.json();
}

