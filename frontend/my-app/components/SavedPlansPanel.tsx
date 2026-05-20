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

  // Deletion Modal State
  const [planToDelete, setPlanToDelete] = useState<Plan | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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

  const handleDeleteClick = (plan: Plan, e: React.MouseEvent) => {
    e.stopPropagation(); // prevent row click from opening the plan
    setPlanToDelete(plan);
  };

  const confirmDelete = async () => {
    if (!planToDelete) return;
    setIsDeleting(true);
    
    try {
      await axios.delete(`http://127.0.0.1:8000/training/plans/${planToDelete.plan_id}`);
      setPlans((prev) => prev.filter((p) => p.plan_id !== planToDelete.plan_id));
      setPlanToDelete(null);
    } catch (err: any) {
      alert("Failed to delete plan: " + (err.response?.data?.detail || err.message));
    } finally {
      setIsDeleting(false);
    }
  };

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
              <div className="shrink-0 flex items-center gap-3">
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
                    STATUS_STYLES[p.status] ?? "bg-gray-100 text-gray-600 border-gray-200"
                  }`}
                >
                  {STATUS_ICONS[p.status] ?? "•"} {p.status}
                </span>

                <button
                  onClick={(e) => handleDeleteClick(p, e)}
                  className="p-1.5 rounded hover:bg-red-50 hover:text-red-600 text-muted-foreground transition-colors opacity-0 group-hover:opacity-100"
                  title="Delete plan"
                >
                  🗑️
                </button>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Delete Confirmation Modal Overlay */}
      {planToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-background rounded-lg shadow-xl border border-border w-full max-w-sm overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-5">
              <div className="flex items-center gap-3 text-red-600 mb-3">
                <span className="text-2xl bg-red-100 rounded-full w-10 h-10 flex items-center justify-center">🗑️</span>
                <h3 className="font-semibold text-lg text-foreground">Delete Training Plan</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-1">
                Are you sure you want to delete the plan for:
              </p>
              <p className="font-medium text-foreground bg-muted/50 p-2 rounded text-sm mb-4">
                {planToDelete.role}
              </p>
              <p className="text-xs text-muted-foreground">
                This will permanently delete the 4-quarter plan and all associated modules. This action cannot be undone.
              </p>
            </div>
            
            <div className="bg-muted/30 px-5 py-3 border-t flex justify-end gap-2">
              <button
                onClick={() => setPlanToDelete(null)}
                disabled={isDeleting}
                className="px-4 py-2 rounded-md text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={isDeleting}
                className="px-4 py-2 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting ? "Deleting..." : "Delete Plan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
