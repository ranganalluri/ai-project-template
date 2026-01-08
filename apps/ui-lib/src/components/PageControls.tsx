/** Page navigation controls for multi-page PDF viewer */

import React from 'react';
import { Button } from './Button';
import './PageControls.css';

export interface PageControlsProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
  className?: string;
}

export const PageControls: React.FC<PageControlsProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  disabled = false,
  className = '',
}) => {
  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handleFirst = () => {
    onPageChange(1);
  };

  const handleLast = () => {
    onPageChange(totalPages);
  };

  return (
    <div className={`page-controls ${className}`}>
      <Button onClick={handleFirst} disabled={disabled || currentPage === 1}>
        First
      </Button>
      <Button onClick={handlePrevious} disabled={disabled || currentPage === 1}>
        Previous
      </Button>
      <span className="page-controls-info">
        Page {currentPage} of {totalPages}
      </span>
      <Button onClick={handleNext} disabled={disabled || currentPage === totalPages}>
        Next
      </Button>
      <Button onClick={handleLast} disabled={disabled || currentPage === totalPages}>
        Last
      </Button>
    </div>
  );
};

