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
  partitionKey?: string,
): Promise<void> {
  const requestBody: { approved: boolean; partitionKey?: string } = { approved };
  if (partitionKey) {
    requestBody.partitionKey = partitionKey;
  }
  
  const response = await fetch(`${getApiUrl()}/v1/runs/${runId}/toolcalls/${toolCallId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new Error(`Failed to approve tool call: ${response.status}`);
  }
}

/**
 * Provide parameters for a tool call.
 */
export async function provideParameters(
  runId: string,
  toolCallId: string,
  parameters: Record<string, unknown>,
): Promise<void> {
  const response = await fetch(
    `${getApiUrl()}/v1/runs/${runId}/toolcalls/${toolCallId}/parameters`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ parameters }),
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to provide parameters: ${response.status}`);
  }
}
