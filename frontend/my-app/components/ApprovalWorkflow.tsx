"use client";

import { useState, useEffect } from "react";
import axios from "axios";

type Stage = "recommendation" | "review" | "edit" | "published";

interface Props {
  planId: string;
  onPlanUpdated: () => void;
  modules?: any[];
  curriculumPlans?: Record<string, any>;
  activeRole?: string;
  onPlanApproved?: (approvedRoles: string[]) => void;
}

interface Notification {
  type: "success" | "error" | "info";
  message: string;
}

const REVISION_STAGES = [
  { label: "Analysing your feedback",         match: "Analysing"  },
  { label: "Searching EU AMLR regulations",   match: "Searching"  },
  { label: "Rebuilding compliance modules",   match: "Rebuilding" },
  { label: "Finalising revised training plan",match: "Finalising" },
];

export default function ApprovalWorkflow({ planId, onPlanUpdated, modules = [], curriculumPlans = {}, activeRole = "", onPlanApproved }: Props) {
  const [stage, setStage]               = useState<Stage>("recommendation");
  const [notes, setNotes]               = useState("");
  const [isApprovingOne, setIsApprovingOne] = useState(false);
  const [isApprovingAll, setIsApprovingAll] = useState(false);
  const [isRevising, setIsRevising] = useState(false);
  const isProcessing = isApprovingOne || isApprovingAll || isRevising;
  const [loadingStage, setLoadingStage] = useState("");
  const [showEditBox, setShowEditBox]   = useState(false);
  const [notification, setNotification] = useState<Notification | null>(null);

  // Auto-dismiss notification after 4 seconds
  useEffect(() => {
    if (!notification) return;
    const t = setTimeout(() => setNotification(null), 4000);
    return () => clearTimeout(t);
  }, [notification]);

  const notify = (type: Notification["type"], message: string) =>
    setNotification({ type, message });

  const handleEdit = () => {
    setShowEditBox(true);
    setNotification(null);
  };

  const handleRevise = async () => {
    if (!notes.trim()) {
      notify("error", "Please enter your feedback before submitting.");
      return;
    }

    setIsRevising(true);
    setLoadingStage("Analysing your feedback");
    setNotification(null);

    // Cycle through loading stage labels while the API call runs
    const stageTimers = [
      setTimeout(() => setLoadingStage("Searching EU AMLR regulations"),    4000),
      setTimeout(() => setLoadingStage("Rebuilding compliance modules"),     10000),
      setTimeout(() => setLoadingStage("Finalising revised training plan"),  18000),
    ];

    try {
      await axios.post(`http://127.0.0.1:8000/workflow/revise/${planId}`, {
        feedback: notes,
      });
      stageTimers.forEach(clearTimeout);
      setLoadingStage("");
      setIsRevising(false);
      notify("success", "Training plan revised successfully!");
      setNotes("");
      setShowEditBox(false);
      onPlanUpdated();
      setStage("recommendation");
    } catch (err: any) {
      stageTimers.forEach(clearTimeout);
      setLoadingStage("");
      setIsRevising(false);
      notify(
        "error",
        "Error revising plan: " + (err.response?.data?.detail || err.message)
      );
    }
  };

  const handleApprove = async () => {
    setIsApprovingOne(true);
    setNotification(null);
    try {
      await axios.patch(`http://127.0.0.1:8000/training/plans/${planId}`, {
        status: "approved",
        reviewer_notes: "Approved",
      });
      // Skip local setStage, instantly notify the parent
      if (onPlanApproved) {
        onPlanApproved([activeRole || "unknown"]);
      }
    } catch (err: any) {
      notify(
        "error",
        "Error approving plan: " + (err.response?.data?.detail || err.message)
      );
      setIsApprovingOne(false);
    }
  };

  const handleApproveAllCurriculum = async () => {
    setIsApprovingAll(true);
    setNotification(null);
    try {
      const planIds = Object.values(curriculumPlans).map((p: any) => p.planId).filter(Boolean);
      const roles = Object.keys(curriculumPlans);
      
      await Promise.all(
        planIds.map(id => 
          axios.patch(`http://127.0.0.1:8000/training/plans/${id}`, {
            status: "approved",
            reviewer_notes: "Approved (Bulk Curriculum)",
          })
        )
      );

      if (onPlanApproved) {
        onPlanApproved(roles);
      }
    } catch (err: any) {
      notify(
        "error",
        "Error approving curriculum: " + (err.response?.data?.detail || err.message)
      );
      setIsApprovingAll(false);
    }
  };

  const notificationColors = {
    success: "bg-emerald-50 border-emerald-300 text-emerald-800",
    error:   "bg-red-50 border-red-300 text-red-800",
    info:    "bg-blue-50 border-blue-300 text-blue-800",
  };

  const notificationIcons = {
    success: "✅",
    error:   "❌",
    info:    "ℹ️",
  };

  return (
    <div className="w-full rounded-lg border bg-card p-6 shadow-sm space-y-4">

      {/* ── Full-screen revision loader ────────────────────────────────────── */}
      {isProcessing && loadingStage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-zinc-900 rounded-lg p-8 shadow-2xl max-w-md w-full mx-4">
            <div className="flex flex-col items-center space-y-4">

              {/* Spinner */}
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 border-4 border-blue-200 rounded-full animate-pulse" />
                <div className="absolute inset-0 border-4 border-t-blue-600 rounded-full animate-spin" />
              </div>

              {/* Stage text */}
              <div className="text-center">
                <p className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {loadingStage}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Revising your training plan — this may take 20–40 seconds
                </p>
              </div>

              {/* Progress steps */}
              <div className="w-full mt-4 space-y-2">
                {REVISION_STAGES.map(({ label, match }) => (
                  <div
                    key={label}
                    className={`flex items-center gap-2 text-sm transition-colors ${
                      loadingStage.includes(match)
                        ? "text-blue-600 font-medium"
                        : "text-gray-400"
                    }`}
                  >
                    <div
                      className={`w-2 h-2 rounded-full shrink-0 transition-colors ${
                        loadingStage.includes(match)
                          ? "bg-blue-600 animate-pulse"
                          : "bg-gray-300"
                      }`}
                    />
                    <span>{label}</span>
                  </div>
                ))}
              </div>

            </div>
          </div>
        </div>
      )}

      {/* Inline notification */}
      {notification && (
        <div
          className={`flex items-start gap-3 rounded-md border px-4 py-3 text-sm font-medium
            transition-all duration-300 ${notificationColors[notification.type]}`}
        >
          <span className="mt-0.5 text-base leading-none">
            {notificationIcons[notification.type]}
          </span>
          <span className="flex-1">{notification.message}</span>
          <button
            className="ml-2 opacity-60 hover:opacity-100"
            onClick={() => setNotification(null)}
          >
            ✕
          </button>
        </div>
      )}

      {stage === "published" && !onPlanApproved ? (
        <div className="text-center py-8 space-y-4 max-w-2xl mx-auto">
          <div className="text-5xl mb-3">🎉</div>
          <div className="text-emerald-700 font-semibold text-2xl">
            Training Plan Approved!
          </div>
          <p className="text-muted-foreground text-sm max-w-md mx-auto">
            The plan has been saved to the database and is ready for LMS export.
          </p>
          <div className="pt-4 flex justify-center gap-3">
             <button onClick={() => window.open(`http://127.0.0.1:8000/training/plans/${planId}/export`, '_blank')} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-sm transition-colors text-sm">
               ⬇️ Download LMS JSON
             </button>
             <button onClick={() => window.location.reload()} className="px-5 py-2.5 bg-white hover:bg-zinc-50 border rounded-lg font-medium shadow-sm transition-colors text-sm">
               Generate New Path
             </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Edit feedback box */}
          {showEditBox && (
            <div className="space-y-2">
              <label className="block text-sm font-medium">
                Your Feedback
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Describe what you'd like changed in the training plan…"
                className="w-full rounded-md border p-3 bg-background min-h-[120px] text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                autoFocus
              />
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 justify-center">
            {!showEditBox ? (
              <>
                {Object.keys(curriculumPlans).length > 1 ? (
                  // Bulk Curriculum Approval UI
                  <div className="flex gap-2 bg-primary/5 p-1 rounded-lg border border-primary/20">
                    <button
                      className="rounded-md bg-white border border-primary/20 px-4 py-2.5 text-primary font-medium hover:bg-primary/5 disabled:opacity-50 transition-colors shadow-sm"
                      onClick={handleApprove}
                      disabled={isProcessing}
                    >
                      {isApprovingOne ? "Approving…" : "Approve"}
                    </button>
                    <button
                      className="rounded-md bg-primary px-6 py-2.5 text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors shadow-sm"
                      onClick={handleApproveAllCurriculum}
                      disabled={isProcessing}
                    >
                      {isApprovingAll ? "Approving…" : "Approve All"}
                    </button>
                  </div>
                ) : (
                  // Single Plan Approval UI
                  <button
                    className="rounded-md bg-primary px-6 py-2.5 text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    onClick={handleApprove}
                    disabled={isProcessing}
                  >
                    {isApprovingOne ? "Approving…" : "Approve"}
                  </button>
                )}

                <button
                  className="rounded-md border-2 border-primary px-6 py-2.5 text-primary font-medium hover:bg-primary/10 disabled:opacity-50 transition-colors"
                  onClick={handleEdit}
                  disabled={isProcessing}
                >
                  Edit
                </button>
              </>
            ) : (
              <>
                <button
                  className="rounded-md bg-primary px-6 py-2.5 text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                  onClick={handleRevise}
                  disabled={isProcessing}
                >
                  {isRevising ? "Revising…" : "Submit Changes"}
                </button>
                <button
                  className="rounded-md border px-6 py-2.5 font-medium hover:bg-muted disabled:opacity-50 transition-colors"
                  onClick={() => { setShowEditBox(false); setNotes(""); }}
                  disabled={isProcessing}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
