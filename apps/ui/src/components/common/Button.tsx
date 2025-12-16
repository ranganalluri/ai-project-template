import React from 'react'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}) => {
  const baseStyles = 'font-semibold rounded transition-colors'
  
  const variantStyles = {
    primary: 'bg-primary-500 text-white hover:bg-blue-600',
    secondary: 'bg-gray-300 text-gray-900 hover:bg-gray-400',
    danger: 'bg-red-500 text-white hover:bg-red-600',
  }
  
  const sizeStyles = {
    sm: 'px-3 py-1 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  }
  
  const finalClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`
  
  return (
    <button className={finalClassName} {...props}>
      {children}
    </button>
  )
}
