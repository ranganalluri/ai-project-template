/** Health API client for checking backend status. */

import { getApiUrl } from './config';

/**
 * Check backend health and Foundry connection.
 */
export async function checkHealth(): Promise<{ status: string; foundryConfigured: boolean }> {
  const response = await fetch(`${getApiUrl()}/api/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  const data = await response.json();
  return {
    status: data.status || 'unknown',
    foundryConfigured: data.foundry_configured || false,
  };
}

