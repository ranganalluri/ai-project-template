/** PDF.js worker setup for Vite */

import * as pdfjsLib from 'pdfjs-dist';

// Import worker using Vite's ?url syntax
// This ensures Vite bundles the worker correctly and resolves it at build time
// The ?url suffix tells Vite to treat this as a URL asset
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

// Initialize PDF.js worker with the bundled worker URL
export function setupPDFWorker(): void {
  if (typeof window !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
  }
}

// Auto-setup when this module is imported
setupPDFWorker();

