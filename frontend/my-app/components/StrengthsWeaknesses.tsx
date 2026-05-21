'use client';

import React from 'react';
import { CheckCircleIcon, ExclamationTriangleIcon, LightBulbIcon } from '@heroicons/react/24/outline';

interface StrengthsWeaknessesProps {
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export const StrengthsWeaknesses: React.FC<StrengthsWeaknessesProps> = ({
  strengths,
  weaknesses,
  recommendations
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
      {/* Strengths */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <CheckCircleIcon className="w-5 h-5 text-green-600" />
          <h4 className="font-bold text-green-900">Strengths</h4>
        </div>
        {strengths.length > 0 ? (
          <ul className="space-y-2">
            {strengths.map((strength, idx) => (
              <li key={idx} className="text-sm text-green-800">
                <span className="font-semibold">✓</span> {strength}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-green-700 italic">No dimensions scoring above 80</p>
        )}
      </div>

      {/* Weaknesses */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <ExclamationTriangleIcon className="w-5 h-5 text-red-600" />
          <h4 className="font-bold text-red-900">Weaknesses</h4>
        </div>
        {weaknesses.length > 0 ? (
          <ul className="space-y-2">
            {weaknesses.map((weakness, idx) => (
              <li key={idx} className="text-sm text-red-800">
                <span className="font-semibold">✗</span> {weakness}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-red-700 italic">No dimensions scoring below 65</p>
        )}
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="md:col-span-2 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <LightBulbIcon className="w-5 h-5 text-blue-600" />
            <h4 className="font-bold text-blue-900">Recommendations</h4>
          </div>
          <ul className="space-y-2">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="text-sm text-blue-800">
                <span className="font-semibold">→</span> {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
