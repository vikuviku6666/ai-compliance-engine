'use client';

import React from 'react';

interface DimensionBarProps {
  name: string;
  score: number;
  message?: string;
  weight?: number;
}

export const DimensionBar: React.FC<DimensionBarProps> = ({ name, score, message, weight }) => {
  const getColorClass = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 65) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getTextColor = (score: number) => {
    if (score >= 80) return 'text-green-700';
    if (score >= 65) return 'text-yellow-700';
    return 'text-red-700';
  };

  return (
    <div className="mb-4">
      <div className="flex justify-between items-start mb-1">
        <div>
          <h4 className="font-semibold text-sm text-gray-800">{name}</h4>
          {message && <p className="text-xs text-gray-600 italic">{message}</p>}
        </div>
        <span className={`font-bold text-lg ${getTextColor(score)}`}>{score}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${getColorClass(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
      {weight && (
        <p className="text-xs text-gray-500 mt-1">Weight: {(weight * 100).toFixed(0)}%</p>
      )}
    </div>
  );
};
