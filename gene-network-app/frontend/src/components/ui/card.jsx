// src/components/ui/card.jsx
import React from 'react';

export const Card = React.forwardRef(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`rounded-lg border bg-white shadow-sm ${className}`} {...props} />
));

export const CardHeader = React.forwardRef(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`flex flex-col space-y-1.5 p-6 ${className}`} {...props} />
));

export const CardTitle = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <h3 ref={ref} className={`text-2xl font-semibold leading-none tracking-tight ${className}`} {...props}>
    {children}
  </h3>
));

export const CardContent = React.forwardRef(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`p-6 pt-0 ${className}`} {...props} />
));
