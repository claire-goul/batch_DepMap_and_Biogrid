// src/components/ui/alert.jsx
import React from 'react';

export const Alert = React.forwardRef(({ children, className = '', variant = 'default', ...props }, ref) => {
  const baseStyles = 'relative w-full rounded-lg border p-4';
  const variantStyles = variant === 'destructive' ? 'border-red-500 text-red-700 bg-red-50' : 'border-gray-200 bg-white';
  
  return (
    <div ref={ref} className={`${baseStyles} ${variantStyles} ${className}`} {...props}>
      {children}
    </div>
  );
});

export const AlertDescription = React.forwardRef(({ children, className = '', ...props }, ref) => (
  <div ref={ref} className={`text-sm mt-1 ${className}`} {...props}>
    {children}
  </div>
));
