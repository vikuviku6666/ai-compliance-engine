'use client';

import React, { useState } from 'react';
import { DimensionBar } from './DimensionBar';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface Dimension {
  name: string;
  score: number;
  message?: string;
  weight?: number;
}

interface DimensionCategoryProps {
  name: string;
  weight: number;
  score: number;
  dimensions: Dimension[];
  collapsedByDefault?: boolean;
}

export const DimensionCategory: React.FC<DimensionCategoryProps> = ({
  name,
  weight,
  score,
  dimensions,
  collapsedByDefault = true
}) => {
  const [isExpanded, setIsExpanded] = useState(!collapsedByDefault);

  const getCategoryColor = (score: number) => {
    if (score >= 80) return 'border-l-4 border-l-green-500';
    if (score >= 65) return 'border-l-4 border-l-yellow-500';
    return 'border-l-4 border-l-red-500';
  };

  return (
    <div className={`mb-4 bg-white rounded-lg p-4 shadow-sm ${getCategoryColor(score)}`}>
      {/* Category Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex justify-between items-center hover:bg-gray-50 p-2 rounded transition"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-gray-600" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-600" />
          )}
          <div className="text-left">
            <h3 className="font-bold text-base text-gray-800">{name}</h3>
            <p className="text-xs text-gray-500">Weight: {(weight * 100).toFixed(0)}%</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="font-bold text-lg text-gray-800">{score}</p>
            <p className="text-xs text-gray-500">{dimensions.length} dimensions</p>
          </div>
        </div>
      </button>

      {/* Category Dimensions (Collapsible) */}
      {isExpanded && (
        <div className="mt-4 pl-4 pt-4 border-t border-gray-200">
          {dimensions.map((dim, idx) => (
            <DimensionBar
              key={idx}
              name={dim.name}
              score={dim.score}
              message={dim.message}
              weight={dim.weight}
            />
          ))}
        </div>
      )}
    </div>
  );
};
