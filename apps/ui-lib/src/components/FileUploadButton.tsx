/** File upload button component. */

import React, { useRef } from 'react';
import './FileUploadButton.css';

export interface FileUploadButtonProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}

export const FileUploadButton: React.FC<FileUploadButtonProps> = ({
  onFileSelect,
  accept = '.pdf,.txt,.png,.jpg,.jpeg',
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
      // Reset input so same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <>
      <button
        type="button"
        className="file-upload-button"
        onClick={handleClick}
        disabled={disabled}
        title="Upload file"
      >
        📎
      </button>
      <input
        title="Upload file"
        ref={fileInputRef}
        type="file"
        className="file-upload-input"
        accept={accept}
        onChange={handleFileChange}
      />
    </>
  );
};

