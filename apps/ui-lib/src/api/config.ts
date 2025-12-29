/** API configuration for managing base URL and environment variables. */

declare global {
  interface Window {
    ENV?: Record<string, string>;
  }
  
  // Extend ImportMeta for Vite env support
  interface ImportMetaEnv {
    [key: string]: string | undefined;
  }
}

/**
 * Get an environment variable with fallback priority:
 * 1. window.ENV (public env-config.js - runtime)
 * 2. import.meta.env (Vite env - build-time)
 * 3. defaultValue (if provided)
 * 
 * @param varName - The name of the environment variable
 * @param defaultValue - Optional default value if not found in env
 * @returns The environment variable value or default
 */
export function getEnvVar(varName: string, defaultValue?: string): string | undefined {
  // Check if we're in a browser environment and window.ENV exists
  if (typeof window !== 'undefined' && window.ENV?.[varName]) {
    return window.ENV[varName];
  }
  
  // Fall back to Vite env (available at build time)
  try {
    // @ts-expect-error - import.meta.env is a Vite feature, may not be available in all contexts
    if (import.meta?.env?.[varName]) {
      // @ts-expect-error
      return import.meta.env[varName];
    }
  } catch {
    // import.meta not available, skip
  }
  
  // Return default if provided
  return defaultValue;
}

let userSetApiUrl: string | null = null;
const DEFAULT_API_URL = 'http://localhost:8000';

export function setApiUrl(url: string): void {
  userSetApiUrl = url;
}

export function getApiUrl(): string {
  // If user explicitly set a URL, use that
  if (userSetApiUrl !== null) {
    return userSetApiUrl;
  }
  
  // Otherwise, check environment variables with fallback to default
  return getEnvVar('VITE_API_URL', DEFAULT_API_URL) || DEFAULT_API_URL;
}

