/** Simple PDF Viewer component using pdf.js - renders directly to canvas without OpenLayers */

import React, { useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

// Set up PDF.js worker
(pdfjsLib as any).GlobalWorkerOptions.workerSrc = pdfWorker;

export interface SimplePdfViewerProps {
  pdfUrl: string;
  pageNumber?: number;
  scale?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function SimplePdfViewer({
  pdfUrl,
  pageNumber = 1,
  scale = 2.0,
  className = '',
  style,
}: SimplePdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const pdfRef = useRef<any>(null); // Cache PDF document

  useEffect(() => {
    let cancelled = false;

    const renderPage = async () => {
      if (!canvasRef.current || !pdfUrl) return;

      try {
        // Load PDF document (cache it for reuse)
        let pdf = pdfRef.current;
        if (!pdf || pdf.url !== pdfUrl) {
          const loadingTask = pdfjsLib.getDocument({ 
            url: pdfUrl,
            verbosity: 0, // Suppress warnings like PdfViewer
          });
          pdf = await loadingTask.promise;
          pdf.url = pdfUrl; // Store URL for comparison
          pdfRef.current = pdf;
        }

        // Validate page number
        if (pageNumber < 1 || pageNumber > pdf.numPages) {
          throw new Error(`Page ${pageNumber} is out of range. PDF has ${pdf.numPages} pages.`);
        }

        // Get the page
        const page = await pdf.getPage(pageNumber);
        if (cancelled) return;

        // Get viewport with scale
        const viewport = page.getViewport({ scale });

        // Validate viewport dimensions
        if (viewport.width <= 0 || viewport.height <= 0 || !isFinite(viewport.width) || !isFinite(viewport.height)) {
          throw new Error(`Invalid viewport dimensions: ${viewport.width}x${viewport.height}`);
        }

        // Set canvas dimensions
        const canvas = canvasRef.current;
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);

        // Get canvas context with alpha: false for better performance (like PdfViewer)
        const ctx = canvas.getContext('2d', {
          alpha: false, // Opaque background for better performance
        });
        if (!ctx) {
          throw new Error('Failed to get canvas 2D context');
        }

        // Set white background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Render PDF page to canvas
        const renderContext = {
          canvasContext: ctx,
          viewport: viewport,
          canvas: canvas,
        };

        await page.render(renderContext as any).promise;
        if (cancelled) return;

        // Don't set fixed container size - let CSS handle responsiveness
        // The canvas will scale via maxWidth: 100% in the style
      } catch (error) {
        console.error('Failed to render PDF page:', error);
        if (canvasRef.current) {
          const ctx = canvasRef.current.getContext('2d');
          if (ctx) {
            // Set default dimensions if canvas is empty
            if (canvasRef.current.width === 0 || canvasRef.current.height === 0) {
              canvasRef.current.width = 400;
              canvasRef.current.height = 600;
            }
            ctx.fillStyle = '#f0f0f0';
            ctx.fillRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(
              error instanceof Error ? error.message : 'Failed to load PDF',
              canvasRef.current.width / 2,
              canvasRef.current.height / 2
            );
          }
        }
      }
    };

    renderPage();

    return () => {
      cancelled = true;
    };
  }, [pdfUrl, pageNumber, scale]);

  // Clear PDF cache when URL changes
  useEffect(() => {
    return () => {
      pdfRef.current = null;
    };
  }, [pdfUrl]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        display: 'inline-block',
        ...style,
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          maxWidth: '100%',
          height: 'auto',
        }}
      />
    </div>
  );
}

