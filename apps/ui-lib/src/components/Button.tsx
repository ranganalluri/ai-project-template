import React, { useState } from 'react';
import type { ButtonProps } from '../types/Button.types';

import './Button.css';

export const Button: React.FC<ButtonProps> = ({ children, className = '', onClick, ...props }) => {
  const [clicked, setClicked] = useState(false);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    // setClicked(true);
    if (onClick) onClick(e);
  };

  return (
    <button
      className={`button-green ${className}`.trim()}
      onClick={handleClick}
      {...props}
    >
      {clicked ? 'Clicked!' : children}
    </button>
  );
};