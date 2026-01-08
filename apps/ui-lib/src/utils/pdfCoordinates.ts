/** Coordinate transformation utilities for converting CU coordinates to SVG/canvas coordinates */

import type { RefObject } from 'react';

export interface CUPoint {
  x: number;
  y: number;
}

export interface FieldEvidence {
  fieldPath: string;
  value: any;
  confidence: number;
  evidence: Array<{
    page: number; // 1-indexed
    polygon: CUPoint[]; // CU coordinates in points
    boundingBox?: { x: number; y: number; width: number; height: number };
    sourceText: string;
    confidence: number;
  }>;
}

/**
 * Transform CU polygon coordinates to SVG/canvas coordinates.
 * 
 * CU coordinates use points (1/72 inch) with top-left origin and downward Y-axis.
 * SVG/canvas use pixels with top-left origin and downward Y-axis (no flip needed).
 * 
 * @param cuPolygon - Array of CU coordinate points
 * @param cuPageWidth - CU page width in points
 * @param cuPageHeight - CU page height in points
 * @param canvasWidth - Canvas width in pixels
 * @param canvasHeight - Canvas height in pixels
 * @returns Array of [x, y] coordinate pairs for SVG/canvas
 */
export function transformCUPolygonToSVG(
  cuPolygon: CUPoint[],
  cuPageWidth: number,
  cuPageHeight: number,
  canvasWidth: number,
  canvasHeight: number
): Array<[number, number]> {
  if (!cuPolygon || cuPolygon.length === 0) {
    throw new Error('Polygon must contain at least one point');
  }
  if (cuPageWidth <= 0 || cuPageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${cuPageWidth}x${cuPageHeight}`);
  }
  if (canvasWidth <= 0 || canvasHeight <= 0) {
    throw new Error(`Invalid canvas dimensions: ${canvasWidth}x${canvasHeight}`);
  }

  const scaleX = canvasWidth / cuPageWidth;
  const scaleY = canvasHeight / cuPageHeight;

  if (!isFinite(scaleX) || !isFinite(scaleY) || scaleX <= 0 || scaleY <= 0) {
    throw new Error(`Invalid scale factors: scaleX=${scaleX}, scaleY=${scaleY}`);
  }

  return cuPolygon.map((p) => {
    if (typeof p.x !== 'number' || typeof p.y !== 'number' || !isFinite(p.x) || !isFinite(p.y)) {
      throw new Error(`Invalid polygon point: ${JSON.stringify(p)}`);
    }
    return [
      p.x * scaleX,
      p.y * scaleY, // No Y-axis flip needed for SVG/canvas (both use top-down)
    ] as [number, number];
  });
}

/**
 * Transform CU bounding box to SVG/canvas coordinates.
 * 
 * @param boundingBox - CU bounding box
 * @param cuPageWidth - CU page width in points
 * @param cuPageHeight - CU page height in points
 * @param canvasWidth - Canvas width in pixels
 * @param canvasHeight - Canvas height in pixels
 * @returns Object with x, y, width, height for SVG rectangle
 */
export function transformCUBoundingBoxToSVG(
  boundingBox: { x: number; y: number; width: number; height: number },
  cuPageWidth: number,
  cuPageHeight: number,
  canvasWidth: number,
  canvasHeight: number
): { x: number; y: number; width: number; height: number } {
  if (!boundingBox || typeof boundingBox.x !== 'number' || typeof boundingBox.y !== 'number' ||
      typeof boundingBox.width !== 'number' || typeof boundingBox.height !== 'number') {
    throw new Error('Invalid bounding box: must have x, y, width, and height properties');
  }
  if (boundingBox.width <= 0 || boundingBox.height <= 0) {
    throw new Error(`Invalid bounding box dimensions: ${boundingBox.width}x${boundingBox.height}`);
  }
  if (cuPageWidth <= 0 || cuPageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${cuPageWidth}x${cuPageHeight}`);
  }
  if (canvasWidth <= 0 || canvasHeight <= 0) {
    throw new Error(`Invalid canvas dimensions: ${canvasWidth}x${canvasHeight}`);
  }

  const scaleX = canvasWidth / cuPageWidth;
  const scaleY = canvasHeight / cuPageHeight;

  if (!isFinite(scaleX) || !isFinite(scaleY) || scaleX <= 0 || scaleY <= 0) {
    throw new Error(`Invalid scale factors: scaleX=${scaleX}, scaleY=${scaleY}`);
  }

  return {
    x: boundingBox.x * scaleX,
    y: boundingBox.y * scaleY, // No Y-axis flip needed
    width: boundingBox.width * scaleX,
    height: boundingBox.height * scaleY,
  };
}

/**
 * Get color for confidence level.
 * 
 * @param confidence - Confidence value (0-1)
 * @returns RGB color string
 */
export function getColorForConfidence(confidence: number): string {
  if (typeof confidence !== 'number' || !isFinite(confidence)) {
    return '255, 0, 0'; // Red for invalid
  }
  
  const clampedConfidence = Math.max(0, Math.min(1, confidence));
  
  if (clampedConfidence > 0.8) {
    return '0, 200, 0'; // Green
  } else if (clampedConfidence >= 0.5) {
    return '255, 200, 0'; // Yellow
  } else {
    return '255, 0, 0'; // Red
  }
}

// Style constants
export const SELECTED_FILL = 'rgba(147, 51, 234, 0.5)';
export const SELECTED_STROKE = 'rgb(147, 51, 234)';
export const UNSELECTED_FILL_OPACITY = 0.25;
export const UNSELECTED_STROKE_OPACITY = 0.8;
export const SELECTED_STROKE_WIDTH = 4;
export const UNSELECTED_STROKE_WIDTH = 2;

// Legacy OpenLayers functions (kept for backward compatibility if needed)
import { Polygon } from 'ol/geom';
import Feature from 'ol/Feature';
import VectorSource from 'ol/source/Vector';
import { Style, Fill, Stroke } from 'ol/style';
import type { FeatureLike } from 'ol/Feature';

/**
 * Transform CU polygon coordinates to OpenLayers map coordinates.
 * 
 * @deprecated Use transformCUPolygonToSVG instead
 */
export function transformCUPolygonToOL(
  cuPolygon: CUPoint[],
  cuPageWidth: number,
  cuPageHeight: number,
  bitmapWidth: number,
  bitmapHeight: number
): Array<[number, number]> {
  if (!cuPolygon || cuPolygon.length === 0) {
    throw new Error('Polygon must contain at least one point');
  }
  if (cuPageWidth <= 0 || cuPageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${cuPageWidth}x${cuPageHeight}`);
  }
  if (bitmapWidth <= 0 || bitmapHeight <= 0) {
    throw new Error(`Invalid bitmap dimensions: ${bitmapWidth}x${bitmapHeight}`);
  }

  const scaleX = bitmapWidth / cuPageWidth;
  const scaleY = bitmapHeight / cuPageHeight;

  if (!isFinite(scaleX) || !isFinite(scaleY) || scaleX <= 0 || scaleY <= 0) {
    throw new Error(`Invalid scale factors: scaleX=${scaleX}, scaleY=${scaleY}`);
  }

  return cuPolygon.map((p) => {
    if (typeof p.x !== 'number' || typeof p.y !== 'number' || !isFinite(p.x) || !isFinite(p.y)) {
      throw new Error(`Invalid polygon point: ${JSON.stringify(p)}`);
    }
    return [
      p.x * scaleX,
      bitmapHeight - p.y * scaleY, // Flip Y-axis (CU: top-down, OL: bottom-up)
    ];
  });
}

/**
 * Transform CU bounding box to OpenLayers polygon coordinates.
 * 
 * @deprecated Use transformCUBoundingBoxToSVG instead
 */
export function transformCUBoundingBoxToOL(
  boundingBox: { x: number; y: number; width: number; height: number },
  cuPageWidth: number,
  cuPageHeight: number,
  bitmapWidth: number,
  bitmapHeight: number
): Array<[number, number]> {
  if (!boundingBox || typeof boundingBox.x !== 'number' || typeof boundingBox.y !== 'number' ||
      typeof boundingBox.width !== 'number' || typeof boundingBox.height !== 'number') {
    throw new Error('Invalid bounding box: must have x, y, width, and height properties');
  }
  if (boundingBox.width <= 0 || boundingBox.height <= 0) {
    throw new Error(`Invalid bounding box dimensions: ${boundingBox.width}x${boundingBox.height}`);
  }
  if (cuPageWidth <= 0 || cuPageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${cuPageWidth}x${cuPageHeight}`);
  }
  if (bitmapWidth <= 0 || bitmapHeight <= 0) {
    throw new Error(`Invalid bitmap dimensions: ${bitmapWidth}x${bitmapHeight}`);
  }

  const scaleX = bitmapWidth / cuPageWidth;
  const scaleY = bitmapHeight / cuPageHeight;

  if (!isFinite(scaleX) || !isFinite(scaleY) || scaleX <= 0 || scaleY <= 0) {
    throw new Error(`Invalid scale factors: scaleX=${scaleX}, scaleY=${scaleY}`);
  }

  // Convert bounding box to polygon (rectangle)
  const x1 = boundingBox.x * scaleX;
  const y1 = bitmapHeight - boundingBox.y * scaleY; // Top-left (flipped)
  const x2 = (boundingBox.x + boundingBox.width) * scaleX;
  const y2 = bitmapHeight - (boundingBox.y + boundingBox.height) * scaleY; // Bottom-right (flipped)

  // Return rectangle as polygon coordinates (clockwise from top-left)
  return [
    [x1, y1], // Top-left
    [x2, y1], // Top-right
    [x2, y2], // Bottom-right
    [x1, y2], // Bottom-left
    [x1, y1], // Close polygon
  ];
}

/**
 * Add polygons from field evidence to OpenLayers vector source.
 * 
 * @deprecated This function is for OpenLayers compatibility only
 */
export function addPolygonsToMap(
  vectorSource: VectorSource,
  fields: FieldEvidence[],
  pageNumber: number,
  bitmap: ImageBitmap,
  cuPageWidth: number,
  cuPageHeight: number
): void {
  if (!vectorSource) {
    throw new Error('VectorSource is required');
  }
  if (!Array.isArray(fields)) {
    throw new Error('Fields must be an array');
  }
  if (!Number.isInteger(pageNumber) || pageNumber < 1) {
    throw new Error(`Invalid page number: ${pageNumber}`);
  }
  if (!bitmap || bitmap.width <= 0 || bitmap.height <= 0) {
    throw new Error(`Invalid bitmap: ${bitmap ? `${bitmap.width}x${bitmap.height}` : 'null'}`);
  }
  if (cuPageWidth <= 0 || cuPageHeight <= 0) {
    throw new Error(`Invalid page dimensions: ${cuPageWidth}x${cuPageHeight}`);
  }

  // Filter fields that have evidence on this page
  const pageFields = fields.filter((f) => {
    if (!f || !f.evidence || !Array.isArray(f.evidence)) {
      return false;
    }
    return f.evidence.some((e) => e && e.page === pageNumber);
  });

  pageFields.forEach((field) => {
    if (!field.fieldPath) {
      return;
    }

    field.evidence
      .filter((e) => e && e.page === pageNumber)
      .forEach((evidence) => {
        try {
          let coords: Array<[number, number]>;

          // Prefer polygon over bounding box
          if (evidence.polygon && Array.isArray(evidence.polygon) && evidence.polygon.length > 0) {
            // Ensure polygon is closed (first point = last point)
            const { polygon } = evidence;
            const closedPolygon = polygon.length > 0 && 
              polygon[0].x === polygon[polygon.length - 1].x &&
              polygon[0].y === polygon[polygon.length - 1].y
              ? polygon
              : [...polygon, polygon[0]]; // Close polygon if not already closed

            coords = transformCUPolygonToOL(
              closedPolygon,
              cuPageWidth,
              cuPageHeight,
              bitmap.width,
              bitmap.height
            );
          } else if (evidence.boundingBox) {
            coords = transformCUBoundingBoxToOL(
              evidence.boundingBox,
              cuPageWidth,
              cuPageHeight,
              bitmap.width,
              bitmap.height
            );
          } else {
            // Skip if no geometry available
            return;
          }

          // Validate transformed coordinates
          if (!coords || coords.length < 3) {
            console.warn(`Invalid coordinates for field ${field.fieldPath}:`, coords);
            return;
          }

          const polygon = new Polygon([coords]);
          const feature = new Feature({
            geometry: polygon,
            fieldEvidence: field,
            confidence: typeof evidence.confidence === 'number' ? evidence.confidence : 0,
            fieldPath: field.fieldPath,
            value: field.value,
            sourceText: evidence.sourceText || '',
          });

          vectorSource.addFeature(feature);
        } catch (err) {
          console.error(`Failed to add polygon for field ${field.fieldPath}:`, err);
        }
      });
  });
}

/**
 * Create a style function for polygon features that reads from a ref.
 * 
 * @deprecated This function is for OpenLayers compatibility only
 */
export function createPolygonStyleFunction(
  selectedFieldRef: RefObject<FieldEvidence | null | undefined>
): (feature: FeatureLike) => Style {
  return (feature: FeatureLike) => {
    const confidence = feature.get('confidence') as number;
    const fieldPath = feature.get('fieldPath') as string;
    const currentSelected = selectedFieldRef.current;
    const isSelected = currentSelected?.fieldPath === fieldPath;
    
    const color = getColorForConfidence(confidence);
    
    return new Style({
      fill: new Fill({
        color: isSelected 
          ? SELECTED_FILL
          : `rgba(${color}, ${UNSELECTED_FILL_OPACITY})`
      }),
      stroke: new Stroke({
        color: isSelected 
          ? SELECTED_STROKE
          : `rgba(${color}, ${UNSELECTED_STROKE_OPACITY})`,
        width: isSelected ? SELECTED_STROKE_WIDTH : UNSELECTED_STROKE_WIDTH
      }),
    });
  };
}
