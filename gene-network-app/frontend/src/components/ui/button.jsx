// src/components/ui/button.jsx
import React from 'react';

export const Button = React.forwardRef(({ 
  className = '', 
  variant = 'default', 
  size = 'default', 
  children,
  ...props 
}, ref) => {
  const baseStyles = 'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  const variantStyles = variant === 'outline' ? 'border border-gray-300 bg-white hover:bg-gray-50' : 'bg-gray-900 text-white hover:bg-gray-800';
  const sizeStyles = size === 'sm' ? 'h-9 px-3' : 'h-10 px-4 py-2';

  return (
    <button
      ref={ref}
      className={`${baseStyles} ${variantStyles} ${sizeStyles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
});
