"use client";

import { useEffect, useState, useCallback } from "react";
import axios from "axios";

interface Plan {
  plan_id: string;
  role: string;
  status: string;
  module_count: number;
  created_at: string | null;
}

interface Props {
  /** bump this to force a refresh (e.g. after a new plan is generated) */
  refreshTrigger?: number;
  onSelect?: (planId: string) => void;
}

const STATUS_STYLES: Record<string, string> = {
  draft:    "bg-amber-100 text-amber-800 border-amber-200",
  revised:  "bg-blue-100  text-blue-800  border-blue-200",
  approved: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

const STATUS_ICONS: Record<string, string> = {
  draft:    "📝",
  revised:  "🔄",
  approved: "✅",
};

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function SavedPlansPanel({ refreshTrigger, onSelect }: Props) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get("http://127.0.0.1:8000/workflow/plans");
      setPlans(res.data);
    } catch (e: any) {
      setError("Could not load saved plans.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlans(); }, [fetchPlans, refreshTrigger]);

  return (
    <div className="w-full rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-lg">🗄️</span>
          <h2 className="font-semibold text-base">Saved Training Plans</h2>
          {!loading && (
            <span className="ml-1 rounded-full bg-primary/10 text-primary text-xs font-medium px-2 py-0.5">
              {plans.length}
            </span>
          )}
        </div>
        <button
          onClick={fetchPlans}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Body */}
      <div className="divide-y max-h-[420px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-10 gap-2 text-muted-foreground text-sm">
            <span className="animate-spin">⏳</span> Loading…
          </div>
        ) : error ? (
          <div className="py-8 text-center text-sm text-red-500">{error}</div>
        ) : plans.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted-foreground">
            No training plans saved yet.
            <br />
            <span className="text-xs">Submit a role description to generate one.</span>
          </div>
        ) : (
          plans.map((p) => (
            <button
              key={p.plan_id}
              onClick={() => onSelect?.(p.plan_id)}
              className="w-full flex items-center gap-4 px-5 py-3.5 text-left hover:bg-muted/40 transition-colors group"
            >
              {/* Role avatar */}
              <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm shrink-0">
                {p.role.charAt(0).toUpperCase()}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                  {p.role}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {p.module_count} module{p.module_count !== 1 ? "s" : ""} ·{" "}
                  {timeAgo(p.created_at)}
                </p>
              </div>

              {/* Status badge */}
              <span
                className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
                  STATUS_STYLES[p.status] ?? "bg-gray-100 text-gray-600 border-gray-200"
                }`}
              >
                {STATUS_ICONS[p.status] ?? "•"} {p.status}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
