/** PDF Viewer component using SVG overlay for field evidence highlights */

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { getPDFPageInfo } from '../utils/pdfRenderer';
import * as pdfjsLib from 'pdfjs-dist';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import {
  transformCUPolygonToSVG,
  transformCUBoundingBoxToSVG,
  getColorForConfidence,
  SELECTED_FILL,
  SELECTED_STROKE,
  UNSELECTED_FILL_OPACITY,
  UNSELECTED_STROKE_OPACITY,
  SELECTED_STROKE_WIDTH,
  UNSELECTED_STROKE_WIDTH,
  type FieldEvidence,
} from '../utils/pdfCoordinates';
import { PageControls } from './PageControls';
import './PDFViewer.css';

// Set up PDF.js worker
(pdfjsLib as any).GlobalWorkerOptions.workerSrc = pdfWorker;

export interface PDFViewerProps {
  pdfUrl: string | null;
  fields?: FieldEvidence[];
  pageDimensions?: Array<{ page: number; width: number; height: number }>;
  selectedField?: FieldEvidence | null;
  onFieldSelect?: (field: FieldEvidence) => void;
  className?: string;
}

interface FieldHighlight {
  field: FieldEvidence;
  evidence: FieldEvidence['evidence'][0];
  path: string; // SVG path string
  x?: number; // For rectangles
  y?: number;
  width?: number;
  height?: number;
  isPolygon: boolean;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({
  pdfUrl,
  fields = [],
  pageDimensions = [],
  selectedField,
  onFieldSelect,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const pdfRef = useRef<any>(null); // Cache PDF document
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [canvasSize, setCanvasSize] = useState<{ width: number; height: number } | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  // Navigate to the page where selected field is located
  useEffect(() => {
    if (selectedField && selectedField.evidence && selectedField.evidence.length > 0) {
      const firstEvidence = selectedField.evidence[0];
      if (firstEvidence && firstEvidence.page && firstEvidence.page !== currentPage) {
        setCurrentPage(firstEvidence.page);
      }
    }
  }, [selectedField, currentPage]);

  // Get PDF page info on mount
  useEffect(() => {
    if (!pdfUrl) {
      setError(null);
      setLoading(false);
      setTotalPages(0);
      setCanvasSize(null);
      return;
    }

    setLoading(true);
    setError(null);

    getPDFPageInfo(pdfUrl)
      .then((info) => {
        if (!info || info.length === 0) {
          throw new Error('PDF has no pages');
        }
        setTotalPages(info.length);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(`Failed to load PDF: ${errorMsg}`);
        setLoading(false);
        setTotalPages(0);
      });
  }, [pdfUrl]);

  // Render PDF page to canvas
  useEffect(() => {
    if (!pdfUrl || currentPage < 1 || !canvasRef.current) {
      return;
    }

    // Don't check totalPages here - it might not be set yet, but we'll validate against pdf.numPages
    let cancelled = false;
    setLoading(true);
    setError(null);

    const renderPage = async () => {
      try {
        // Load PDF document (cache it for reuse)
        let pdf = pdfRef.current;
        if (!pdf || pdf.url !== pdfUrl) {
          const loadingTask = pdfjsLib.getDocument({
            url: pdfUrl,
            verbosity: 0,
          });
          pdf = await loadingTask.promise;
          pdf.url = pdfUrl; // Store URL for comparison
          pdfRef.current = pdf;
          
          // Update totalPages if it changed
          if (pdf.numPages !== totalPages) {
            setTotalPages(pdf.numPages);
          }
        }

        if (currentPage < 1 || currentPage > pdf.numPages) {
          throw new Error(`Page ${currentPage} is out of range. PDF has ${pdf.numPages} pages.`);
        }

        const page = await pdf.getPage(currentPage);
        if (cancelled) return;

        const viewport = page.getViewport({ scale: 2.0 });
        const canvas = canvasRef.current;
        if (!canvas) return;

        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);

        const ctx = canvas.getContext('2d', { alpha: false });
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

        setCanvasSize({ width: canvas.width, height: canvas.height });
        setLoading(false);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(`Failed to render page ${currentPage}: ${errorMsg}`);
        setLoading(false);
        setCanvasSize(null);
      }
    };

    renderPage();

    return () => {
      cancelled = true;
    };
  }, [pdfUrl, currentPage, totalPages]);

  // Clear PDF cache when URL changes
  useEffect(() => {
    return () => {
      pdfRef.current = null;
    };
  }, [pdfUrl]);

  // Compute field highlights for current page
  const highlights = useMemo<FieldHighlight[]>(() => {
    if (!canvasSize || fields.length === 0) {
      return [];
    }

    const pageFields = fields.filter((f) =>
      f.evidence && f.evidence.some((e) => e && e.page === currentPage)
    );

    if (pageFields.length === 0) {
      return [];
    }

    const pageDim = pageDimensions.find((d) => d.page === currentPage) || {
      page: currentPage,
      width: 612,
      height: 792,
    };

    const result: FieldHighlight[] = [];

    pageFields.forEach((field) => {
      if (!field.fieldPath) return;

      field.evidence
        .filter((e) => e && e.page === currentPage)
        .forEach((evidence) => {
          try {
            if (evidence.polygon && Array.isArray(evidence.polygon) && evidence.polygon.length > 0) {
              // Ensure polygon is closed
              const polygon = evidence.polygon;
              const closedPolygon =
                polygon.length > 0 &&
                polygon[0].x === polygon[polygon.length - 1].x &&
                polygon[0].y === polygon[polygon.length - 1].y
                  ? polygon
                  : [...polygon, polygon[0]];

              const coords = transformCUPolygonToSVG(
                closedPolygon,
                pageDim.width,
                pageDim.height,
                canvasSize.width,
                canvasSize.height
              );

              if (coords && coords.length >= 3) {
                const pathString = coords
                  .map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x} ${y}`)
                  .join(' ') + ' Z';

                result.push({
                  field,
                  evidence,
                  path: pathString,
                  isPolygon: true,
                });
              }
            } else if (evidence.boundingBox) {
              const rect = transformCUBoundingBoxToSVG(
                evidence.boundingBox,
                pageDim.width,
                pageDim.height,
                canvasSize.width,
                canvasSize.height
              );

              result.push({
                field,
                evidence,
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                path: '',
                isPolygon: false,
              });
            }
          } catch (err) {
            console.error(`Failed to transform field ${field.fieldPath}:`, err);
          }
        });
    });

    return result;
  }, [fields, currentPage, canvasSize, pageDimensions]);

  // Handle mouse move for tooltips
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!containerRef.current || !tooltipRef.current) return;

    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if mouse is over any highlight
    const element = document.elementFromPoint(e.clientX, e.clientY);
    if (element && element.getAttribute('data-field-path')) {
      const fieldPath = element.getAttribute('data-field-path');
      if (fieldPath) {
        setTooltip({ x: e.clientX, y: e.clientY, text: fieldPath });
        return;
      }
    }

    setTooltip(null);
  };

  // Handle mouse leave
  const handleMouseLeave = () => {
    setTooltip(null);
  };

  // Handle click on highlight
  const handleHighlightClick = (field: FieldEvidence) => {
    if (onFieldSelect) {
      onFieldSelect(field);
    }
  };

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  if (!pdfUrl) {
    return (
      <div className={`pdf-viewer-container ${className}`}>
        <div className="pdf-viewer-error">
          <p className="text-gray-500">No PDF URL provided</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`pdf-viewer-container ${className}`}>
        <div className={`pdf-viewer-error ${className}`}>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  const isFieldSelected = (field: FieldEvidence) => {
    return selectedField?.fieldPath === field.fieldPath;
  };

  return (
    <div className={`pdf-viewer-container ${className}`}>
      {totalPages > 1 && (
        <PageControls
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          disabled={loading}
        />
      )}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          display: 'inline-block',
        }}
      >
        {/* PDF Canvas */}
        <canvas
          ref={canvasRef}
          style={{
            display: 'block',
            width: '100%',
            height: 'auto',
            maxWidth: '100%',
          }}
        />
        {/* SVG Overlay for field highlights */}
        {canvasSize && highlights.length > 0 && (
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'auto',
              zIndex: 1,
            }}
            viewBox={`0 0 ${canvasSize.width} ${canvasSize.height}`}
            preserveAspectRatio="xMidYMid meet"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            {highlights.map((highlight, index) => {
              const isSelected = isFieldSelected(highlight.field);
              const confidence = highlight.evidence.confidence ?? 0;
              const color = getColorForConfidence(confidence);

              const fillColor = isSelected
                ? SELECTED_FILL
                : `rgba(${color}, ${UNSELECTED_FILL_OPACITY})`;
              const strokeColor = isSelected
                ? SELECTED_STROKE
                : `rgba(${color}, ${UNSELECTED_STROKE_OPACITY})`;
              const strokeWidth = isSelected
                ? SELECTED_STROKE_WIDTH
                : UNSELECTED_STROKE_WIDTH;

              const commonProps = {
                fill: fillColor,
                stroke: strokeColor,
                strokeWidth: strokeWidth,
                style: { cursor: 'pointer' },
                onClick: () => handleHighlightClick(highlight.field),
                'data-field-path': highlight.field.fieldPath,
              };

              if (highlight.isPolygon) {
                return (
                  <path
                    key={`${highlight.field.fieldPath}-${index}`}
                    d={highlight.path}
                    {...commonProps}
                  />
                );
              } else {
                return (
                  <rect
                    key={`${highlight.field.fieldPath}-${index}`}
                    x={highlight.x}
                    y={highlight.y}
                    width={highlight.width}
                    height={highlight.height}
                    {...commonProps}
                  />
                );
              }
            })}
          </svg>
        )}
      </div>
      {/* Tooltip */}
      {tooltip && tooltipRef.current && (
        <div
          ref={tooltipRef}
          className="pdf-viewer-tooltip"
          style={{
            position: 'fixed',
            left: tooltip.x,
            top: tooltip.y - 30,
            pointerEvents: 'none',
          }}
        >
          {tooltip.text}
        </div>
      )}
      {loading && (
        <div className="pdf-viewer-loading">
          <p>Loading page {currentPage}...</p>
        </div>
      )}
    </div>
  );
};
