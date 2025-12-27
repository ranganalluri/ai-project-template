/** Run API client for managing chat runs and tool calls. */

import { getApiUrl } from './config';

/**
 * Stop a running chat.
 */
export async function stopRun(runId: string): Promise<void> {
  const response = await fetch(`${getApiUrl()}/v1/runs/${runId}/stop`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to stop run: ${response.status}`);
  }
}

/**
 * Approve or reject a tool call.
 */
export async function approveToolCall(
  runId: string,
  toolCallId: string,
  approved: boolean,
): Promise<void> {
  const response = await fetch(`${getApiUrl()}/v1/runs/${runId}/toolcalls/${toolCallId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ approved }),
  });

  if (!response.ok) {
    throw new Error(`Failed to approve tool call: ${response.status}`);
  }
}

