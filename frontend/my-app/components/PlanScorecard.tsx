"use client";

import { useEffect, useState } from "react";
import axios from "axios";

interface Dimension {
  name: string;
  score: number;
  message: string;
  weight: number;
  contribution: number;   // calculated in Python, not frontend
}

interface Scorecard {
  plan_id: string;
  role: string;
  overall: number;
  dimensions: Dimension[];
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

  return (
    <div className="w-full rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-5 py-4 border-b bg-muted/30 hover:bg-muted/50 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📊</span>
          <h2 className="font-semibold text-base">Plan Quality Scorecard</h2>
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

          {/* Dimension bars */}
          <div className="space-y-4">
            {data.dimensions.map((dim) => {
              const { bar, text } = scoreColor(dim.score);
              // contribution comes from backend Python calculation — not computed in frontend
              const contribution = dim.contribution ?? Math.round(dim.score * dim.weight / 100);
              return (
                <div key={dim.name}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{dim.name}</span>
                      <span className="text-xs text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                        weight {dim.weight}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        contributes {contribution}pts
                      </span>
                      <span className={`text-sm font-bold ${text}`}>{dim.score}/100</span>
                    </div>
                  </div>
                  {/* Bar width = actual score, not weight */}
                  <div className="h-2.5 w-full bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${bar}`}
                      style={{ width: `${dim.score}%` }}
                    />
                  </div>
                  {/* Message */}
                  <p className="text-xs text-muted-foreground mt-1">{dim.message}</p>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex gap-4 text-xs text-muted-foreground pt-1 border-t">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> ≥85 Excellent</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> 65–84 Good</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> &lt;65 Needs work</span>
          </div>
        </div>
      )}
    </div>
  );
}
