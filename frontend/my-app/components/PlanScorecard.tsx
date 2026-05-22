"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { DimensionCategory } from "./DimensionCategory";
import { StrengthsWeaknesses } from "./StrengthsWeaknesses";

interface Dimension {
  name: string;
  score: number;
  message: string;
  weight: number;
  contribution?: number;
}

interface Category {
  name: string;
  weight: number;
  score: number;
  dimensions: Dimension[];
}

interface Scorecard {
  plan_id: string;
  role: string;
  overall: number;
  dimensions: Dimension[];
  categories: Category[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

interface Props {
  planId: string;
}

function scoreColor(s: number) {
  if (s >= 85) return { bar: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" };
  if (s >= 65) return { bar: "bg-amber-400",   text: "text-amber-700",   bg: "bg-amber-50"   };
  return            { bar: "bg-red-400",        text: "text-red-700",     bg: "bg-red-50"     };
}

function scoreLabel(s: number) {
  if (s >= 90) return "Excellent";
  if (s >= 75) return "Good";
  if (s >= 60) return "Fair";
  return "Needs work";
}

function CircleScore({ score }: { score: number }) {
  const { text } = scoreColor(score);
  const r = 38;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <div className="relative w-28 h-28 mx-auto">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r={r} fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle
          cx="48" cy="48" r={r} fill="none"
          stroke={score >= 85 ? "#10b981" : score >= 65 ? "#f59e0b" : "#f87171"}
          strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${text}`}>{score}</span>
        <span className="text-xs text-muted-foreground">/100</span>
      </div>
    </div>
  );
}

export default function PlanScorecard({ planId }: Props) {
  const [data, setData] = useState<Scorecard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (!planId) return;
    setLoading(true);
    setError(null);
    axios
      .get(`http://127.0.0.1:8000/workflow/plan/${planId}/evaluate`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Could not load scorecard"))
      .finally(() => setLoading(false));
  }, [planId]);

  if (loading) {
    return (
      <div className="w-full rounded-xl border bg-card shadow-sm p-5 flex items-center gap-3 text-sm text-muted-foreground">
        <span className="animate-spin text-lg">⏳</span> Evaluating plan quality…
      </div>
    );
  }

  if (error || !data) {
    return null; // silently hide if plan not yet in DB
  }

  const overall = data.overall;
  const { text: overallText, bg: overallBg } = scoreColor(overall);
  const categories = data.categories || [];

  return (
    <div className="w-full rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-5 py-4 border-b bg-muted/30 hover:bg-muted/50 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📊</span>
          <h2 className="font-semibold text-base">Plan Quality Scorecard (10 Dimensions)</h2>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold border ${overallText} ${overallBg}`}>
            {scoreLabel(overall)}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xl font-bold ${overallText}`}>{overall}/100</span>
          <span className="text-muted-foreground text-sm">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {open && (
        <div className="p-5 space-y-5">
          {/* Overall ring */}
          <div className="flex flex-col items-center gap-1">
            <CircleScore score={overall} />
            <p className="text-sm text-muted-foreground mt-1">Overall Quality Score</p>
          </div>

          {/* Category-based dimension bars with collapsible sections */}
          <div className="space-y-3">
            {categories.map((category) => (
              <DimensionCategory
                key={category.name}
                name={category.name}
                weight={category.weight}
                score={category.score}
                dimensions={category.dimensions}
                collapsedByDefault={true}
              />
            ))}
          </div>

          {/* Strengths & Weaknesses with Recommendations */}
          {(data.strengths.length > 0 || data.weaknesses.length > 0 || data.recommendations.length > 0) && (
            <StrengthsWeaknesses
              strengths={data.strengths}
              weaknesses={data.weaknesses}
              recommendations={data.recommendations}
            />
          )}

          {/* Legend */}
          <div className="flex gap-4 text-xs text-muted-foreground pt-1 border-t">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> ≥80 Excellent</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> 65–79 Good</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> &lt;65 Needs work</span>
          </div>

          {/* Debug: Show all dimensions flat (can be removed) */}
          <details className="text-xs text-muted-foreground cursor-pointer">
            <summary className="font-semibold">All Dimensions (Raw View)</summary>
            <div className="mt-2 space-y-1 max-h-48 overflow-auto">
              {data.dimensions.map((dim) => (
                <div key={dim.name} className="p-1 bg-muted/20 rounded">
                  <span className="font-mono">{dim.name}</span>: <strong>{dim.score}</strong>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
