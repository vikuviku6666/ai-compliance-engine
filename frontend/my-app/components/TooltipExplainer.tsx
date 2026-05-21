'use client';

import React, { useState } from 'react';

interface TooltipExplainerProps {
  title: string;
  content: string;
  children?: React.ReactNode;
}

export const TooltipExplainer: React.FC<TooltipExplainerProps> = ({ title, content, children }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        className="text-blue-600 hover:text-blue-800 underline text-xs"
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onClick={() => setIsOpen(!isOpen)}
      >
        {children || 'Why this score?'}
      </button>
      {isOpen && (
        <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 z-50 w-64 bg-gray-900 text-white text-xs p-3 rounded shadow-lg">
          <p className="font-bold mb-1">{title}</p>
          <p>{content}</p>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  );
};
