/** PDF rendering utilities using PDF.js */

import * as pdfjsLib from 'pdfjs-dist';

export interface PDFPageInfo {
  width: number;
  height: number;
  pageNumber: number;
}

/**
 * Render a PDF page to an ImageBitmap.
 * 
 * @param pdfUrl - URL or data URL of the PDF document
 * @param pageNumber - Page number (1-indexed)
 * @param scale - Scale factor for rendering (default: 2.0 for high DPI)
 * @returns Promise resolving to ImageBitmap of the rendered page
 */
export async function renderPDFPageToBitmap(
  pdfUrl: string,
  pageNumber: number,
  scale: number = 2.0
): Promise<ImageBitmap> {
  if (!pdfUrl || typeof pdfUrl !== 'string') {
    throw new Error('PDF URL is required and must be a string');
  }
  if (!Number.isInteger(pageNumber) || pageNumber < 1) {
    throw new Error(`Invalid page number: ${pageNumber}. Must be a positive integer.`);
  }
  if (typeof scale !== 'number' || scale <= 0 || !isFinite(scale)) {
    throw new Error(`Invalid scale: ${scale}. Must be a positive number.`);
  }

  try {
    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      verbosity: 0, // Suppress warnings
    });
    const pdf = await loadingTask.promise;
    
    if (pageNumber < 1 || pageNumber > pdf.numPages) {
      throw new Error(`Page ${pageNumber} is out of range. PDF has ${pdf.numPages} pages.`);
    }
    
    const page = await pdf.getPage(pageNumber);
    const viewport = page.getViewport({ scale });
    
    if (viewport.width <= 0 || viewport.height <= 0 || !isFinite(viewport.width) || !isFinite(viewport.height)) {
      throw new Error(`Invalid viewport dimensions: ${viewport.width}x${viewport.height}`);
    }

    const canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    const context = canvas.getContext('2d', {
      alpha: false, // Opaque background for better performance
    });
    if (!context) {
      throw new Error('Failed to get canvas context');
    }

    // Set white background
    context.fillStyle = 'white';
    context.fillRect(0, 0, canvas.width, canvas.height);

    // Render the PDF page
    const renderContext = {
      canvasContext: context,
      viewport: viewport,
      canvas: canvas,
    };
    
    await page.render(renderContext as any).promise;

    if (canvas.width === 0 || canvas.height === 0) {
      throw new Error(`Rendered page has invalid dimensions: ${canvas.width}x${canvas.height}`);
    }

    const bitmap = await createImageBitmap(canvas);
    
    if (!bitmap || bitmap.width <= 0 || bitmap.height <= 0) {
      throw new Error(`Failed to create valid bitmap from canvas`);
    }

    return bitmap;
  } catch (err) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error(`Failed to render PDF page ${pageNumber}: ${String(err)}`);
  }
}

/**
 * Get PDF document information including page count and dimensions.
 * 
 * @param pdfUrl - URL or data URL of the PDF document
 * @returns Promise resolving to array of page info
 */
export async function getPDFPageInfo(pdfUrl: string): Promise<PDFPageInfo[]> {
  if (!pdfUrl || typeof pdfUrl !== 'string') {
    throw new Error('PDF URL is required and must be a string');
  }

  try {
    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      verbosity: 0, // Suppress warnings
    });
    const pdf = await loadingTask.promise;
    
    if (pdf.numPages <= 0) {
      throw new Error('PDF has no pages');
    }

    const pageInfo: PDFPageInfo[] = [];

    for (let i = 1; i <= pdf.numPages; i++) {
      try {
        const page = await pdf.getPage(i);
        const viewport = page.getViewport({ scale: 1.0 });
        
        if (viewport.width <= 0 || viewport.height <= 0 || !isFinite(viewport.width) || !isFinite(viewport.height)) {
          console.warn(`Page ${i} has invalid dimensions: ${viewport.width}x${viewport.height}`);
          pageInfo.push({
            width: 612, // Default US Letter width
            height: 792, // Default US Letter height
            pageNumber: i,
          });
        } else {
          pageInfo.push({
            width: viewport.width,
            height: viewport.height,
            pageNumber: i,
          });
        }
      } catch (err) {
        console.error(`Failed to get info for page ${i}:`, err);
        pageInfo.push({
          width: 612,
          height: 792,
          pageNumber: i,
        });
      }
    }

    return pageInfo;
  } catch (err) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error(`Failed to get PDF page info: ${String(err)}`);
  }
}

