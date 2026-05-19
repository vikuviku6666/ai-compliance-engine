"use client";

import { useState } from "react";
import Image from "next/image";
import axios from "axios";
import InputSection, { StructuredInput } from "../components/Upload";
import ApprovalWorkflow from "../components/ApprovalWorkflow";
import SavedPlansPanel from "../components/SavedPlansPanel";
import PlanScorecard from "../components/PlanScorecard";
import { Button } from "../components/ui/button";

const API = "http://127.0.0.1:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Module {
  id: string;
  title: string;
  roleResponsibility: string;
  amlrArticle: string;
  riskTheme: string;
  competency: string;
  behaviouralOutcomes: string[];
  quarter: "Q1" | "Q2" | "Q3" | "Q4";
  description?: string;
  evidence?: string;
  explainabilityTrace?: Record<string, any>;
}

interface WorkflowData {
  planId: string;           // normalised — always set
  role: string;
  responsibilities: string[];
  risks: string[];
  modules: Module[];
  auditSummary?: Record<string, any>;
}

// ─── Normaliser ───────────────────────────────────────────────────────────────
// Accepts ANY response shape from the backend and returns a clean WorkflowData.

function normalise(raw: any): WorkflowData {
  // ── New /compliance/generate-plan shape ───────────────────────────────────
  // { plan_id, role, plan[], roadmap{}, audit_summary, created_at }
  if (raw.plan && Array.isArray(raw.plan)) {
    const modules: Module[] = raw.plan.map((m: any, idx: number) => {
      const qKey = (m.quarter?.match(/Q[1-4]/)?.[0] ?? `Q${(idx % 4) + 1}`) as Module["quarter"];
      const articleRef =
        m.regulation_ref?.match(/(Article|Recital)\s+\d+/i)?.[0] ??
        (m.article_num ? `Article ${m.article_num}` : "");
      return {
        id: `m${idx}`,
        title: m.module ?? m.title ?? "Module",
        roleResponsibility: m.responsibility ?? m.role_reference ?? "",
        amlrArticle: articleRef,
        riskTheme: m.risk ?? m.risk_reference ?? "",
        competency: m.competency ?? m.competency_reference ?? "Foundational",
        behaviouralOutcomes: [m.description ?? m.behavioural_outcome ?? ""],
        quarter: qKey,
        description: m.description ?? m.behavioural_outcome ?? "",
        evidence: m.evidence ?? "",
        explainabilityTrace: m.explainability_trace ?? null,
      };
    });
    return {
      planId: raw.plan_id ?? raw.training_plan_id ?? "",
      role: raw.role ?? raw.role_data?.role ?? "",
      responsibilities: raw.responsibilities ?? raw.role_data?.responsibilities ?? [],
      risks: raw.inherent_risks ?? raw.risks ?? raw.role_data?.risks ?? [],
      modules,
      auditSummary: raw.audit_summary ?? null,
    };
  }

  // ── Old /workflow/run or /workflow/plan/{id} shape ────────────────────────
  // { training_plan_id, role_data{role,responsibilities,risks}, recommendations[] }
  if (raw.recommendations && Array.isArray(raw.recommendations)) {
    const modules: Module[] = raw.recommendations.map((rec: any, idx: number) => {
      const qKey = (rec.quarter?.match(/Q[1-4]/)?.[0] ?? `Q${(idx % 4) + 1}`) as Module["quarter"];
      const articleRef =
        rec.regulation_reference?.match(/(Article|Recital)\s+\d+/i)?.[0] ?? "";
      return {
        id: `m${idx}`,
        title: rec.module ?? "",
        roleResponsibility: rec.role_reference ?? "",
        amlrArticle: articleRef,
        riskTheme: rec.risk_reference ?? "",
        competency: rec.competency_reference ?? "Foundational",
        behaviouralOutcomes: [rec.behavioural_outcome ?? ""],
        quarter: qKey,
        description: rec.behavioural_outcome ?? "",
      };
    });
    return {
      planId: raw.training_plan_id ?? raw.plan_id ?? "",
      role: raw.role_data?.role ?? raw.role ?? "",
      responsibilities: raw.role_data?.responsibilities ?? [],
      risks: raw.role_data?.risks ?? [],
      modules,
    };
  }

  // Fallback — return empty
  return {
    planId: raw.plan_id ?? raw.training_plan_id ?? "",
    role: raw.role ?? "",
    responsibilities: [],
    risks: [],
    modules: [],
  };
}

// ─── Quarters config ──────────────────────────────────────────────────────────

const QUARTERS = [
  { key: "Q1" as const, label: "Q1: Foundation",  sub: "Months 1–3",   color: "bg-amber-100 dark:bg-amber-900 border-amber-300 dark:border-amber-700" },
  { key: "Q2" as const, label: "Q2: Application", sub: "Months 4–6",   color: "bg-teal-100  dark:bg-teal-900  border-teal-300  dark:border-teal-700"  },
  { key: "Q3" as const, label: "Q3: Deepening",   sub: "Months 7–9",   color: "bg-blue-100  dark:bg-blue-900  border-blue-300  dark:border-blue-700"  },
  { key: "Q4" as const, label: "Q4: Embedding",   sub: "Months 10–12", color: "bg-purple-100 dark:bg-purple-900 border-purple-300 dark:border-purple-700" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Home() {
  const [isLoading, setIsLoading]       = useState(false);
  const [loadingStage, setLoadingStage] = useState("");
  const [plan, setPlan]                 = useState<WorkflowData | null>(null);
  const [error, setError]               = useState<string | null>(null);
  const [planRefresh, setPlanRefresh]   = useState(0);

  // ── Load a saved plan by id ──────────────────────────────────────────────
  const loadPlan = async (planId: string) => {
    setError(null);
    try {
      const res = await axios.get(`${API}/workflow/plan/${planId}`);
      setPlan(normalise(res.data));
    } catch (err: any) {
      setError("Failed to load plan: " + (err.response?.data?.detail ?? err.message));
    }
  };

  // ── Generate a new plan from structured input ────────────────────────────
  const handleProcess = async (data: { type: "structured"; payload: StructuredInput }) => {
    setIsLoading(true);
    setError(null);
    setPlan(null);
    // Stage already set by onLoadingStart — update to next stage
    setLoadingStage("Traversing governance graph…");

    try {
      const { role, responsibilities, inherent_risks } = data.payload;

      setTimeout(() => setLoadingStage("Matching EU AMLR regulations…"),    2000);
      setTimeout(() => setLoadingStage("Building 4-quarter training plan…"), 6000);
      setTimeout(() => setLoadingStage("Generating module descriptions…"),   12000);

      const planRes = await axios.post(`${API}/compliance/generate-plan`, {
        role,
        responsibilities,
        inherent_risks,
      });

      setPlan(normalise(planRes.data));
      setLoadingStage("");
      setPlanRefresh((r) => r + 1);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail ?? err.message ?? "An error occurred.");
      setLoadingStage("");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => { setPlan(null); setError(null); };

  // ── Derived ──────────────────────────────────────────────────────────────
  const modulesByQuarter = (qKey: "Q1" | "Q2" | "Q3" | "Q4") =>
    plan?.modules.filter((m) => m.quarter === qKey) ?? [];

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col flex-1 items-center justify-start bg-zinc-50 font-sans dark:bg-black py-8 px-6 min-h-screen">
      <main className="flex flex-1 w-full max-w-5xl flex-col items-stretch gap-8">

        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Image src="/next.svg" alt="logo" width={80} height={18} className="dark:invert" />
            <h1 className="text-2xl font-semibold">Vidda — Training builder</h1>
          </div>
          {plan && (
            <Button variant="outline" onClick={handleReset}>
              Start Over
            </Button>
          )}
        </header>

        {/* Error banner */}
        {error && (
          <div className="bg-destructive/10 border-l-4 border-destructive text-destructive p-4 rounded-md">
            <p className="font-medium">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* ── Input screen ─────────────────────────────────────────────────── */}
        {!plan ? (
          <section className="flex flex-col items-center gap-6 mt-8 w-full max-w-2xl mx-auto">
            <InputSection
              onProcess={handleProcess}
              isLoading={isLoading}
              onLoadingStart={() => {
                setIsLoading(true);
                setLoadingStage("Analysing role description…");
              }}
            />

            <SavedPlansPanel
              refreshTrigger={planRefresh}
              onSelect={(planId) => loadPlan(planId)}
            />

            {/* Loading overlay */}
            {isLoading && loadingStage && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white dark:bg-zinc-900 rounded-lg p-8 shadow-2xl max-w-md w-full mx-4">
                  <div className="flex flex-col items-center space-y-4">
                    <div className="relative w-16 h-16">
                      <div className="absolute inset-0 border-4 border-blue-200 rounded-full animate-pulse" />
                      <div className="absolute inset-0 border-4 border-t-blue-600 rounded-full animate-spin" />
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        {loadingStage}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        This may take 20–40 seconds
                      </p>
                    </div>
                    <div className="w-full mt-4 space-y-2">
                      {[
                        { label: "Analysing role description",       match: "Analysing"   },
                        { label: "Traversing governance graph",       match: "Traversing"  },
                        { label: "Matching EU AMLR regulations",      match: "Matching"    },
                        { label: "Building 4-quarter training plan",  match: "Building"    },
                        { label: "Generating module descriptions",    match: "Generating"  },
                      ].map(({ label, match }) => (
                        <div key={label} className={`flex items-center gap-2 text-sm ${loadingStage.includes(match) ? "text-blue-600 font-medium" : "text-gray-400"}`}>
                          <div className={`w-2 h-2 rounded-full ${loadingStage.includes(match) ? "bg-blue-600 animate-pulse" : "bg-gray-300"}`} />
                          <span>{label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

        ) : (
        /* ── Plan view ────────────────────────────────────────────────────── */
          <section className="flex flex-col items-center justify-center py-8">
            <div className="w-full max-w-6xl space-y-6">

              {/* Title */}
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold mb-2">Training Path – Year 1</h2>
                <p className="text-lg text-muted-foreground mb-1">
                  Building knowledge to embedded behaviour
                </p>
                <p className="text-md font-semibold text-primary">
                  Role: {plan.role}
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Total modules: {plan.modules.length} |{" "}
                  {QUARTERS.map((q) => `${q.key}: ${modulesByQuarter(q.key).length}`).join(" | ")}
                </p>
              </div>

              {/* 4-Quarter Grid */}
              <div className="bg-card border rounded-lg p-6 shadow-sm">
                <div className="grid grid-cols-4 gap-4">
                  {QUARTERS.map((q) => (
                    <div key={q.key} className="space-y-3">
                      <div className={`rounded-lg p-3 text-center border-b-4 ${q.color}`}>
                        <h3 className="font-bold text-base text-foreground">{q.label}</h3>
                        <p className="text-xs mt-1 text-muted-foreground">{q.sub}</p>
                      </div>
                      <ul className="space-y-3 list-none">
                        {modulesByQuarter(q.key).length > 0 ? (
                          modulesByQuarter(q.key).map((mod, idx) => (
                            <li key={idx} className="rounded-md border bg-background p-3 text-sm shadow-sm">
                              {/* Module title + article */}
                              <p className="font-semibold leading-tight">
                                {mod.title}
                                {mod.amlrArticle && (
                                  <span className="ml-1 text-xs font-mono text-primary">
                                    ({mod.amlrArticle})
                                  </span>
                                )}
                              </p>

                              {/* Responsibility */}
                              {mod.roleResponsibility && (
                                <p className="text-xs text-muted-foreground mt-1.5">
                                  <span className="font-medium text-foreground">Resp:</span>{" "}
                                  {mod.roleResponsibility}
                                </p>
                              )}

                              {/* Risk */}
                              {mod.riskTheme && (
                                <p className="text-xs text-muted-foreground mt-0.5">
                                  <span className="font-medium text-foreground">Risk:</span>{" "}
                                  {mod.riskTheme}
                                </p>
                              )}

                              {/* Description — live from LLM grounded in evidence */}
                              {mod.description && (
                                <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed line-clamp-3">
                                  {mod.description}
                                </p>
                              )}
                            </li>
                          ))
                        ) : (
                          <li className="text-sm text-muted-foreground italic">No modules assigned</li>
                        )}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>

              {/* Audit summary — only for new-engine plans */}
              {plan.auditSummary && (
                <div className="bg-card border rounded-lg p-5 shadow-sm space-y-3">
                  <h3 className="font-semibold text-base">Audit Summary</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground text-xs uppercase tracking-wide mb-1">Regulations Cited</p>
                      <ul className="space-y-0.5">
                        {plan.auditSummary.regulations_cited?.map((r: string) => (
                          <li key={r} className="font-mono text-xs bg-muted px-2 py-0.5 rounded">{r}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs uppercase tracking-wide mb-1">Controls Applied</p>
                      <ul className="space-y-0.5">
                        {plan.auditSummary.controls_applied?.map((c: string) => (
                          <li key={c} className="text-xs bg-muted px-2 py-0.5 rounded">{c}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Sources: {plan.auditSummary.sources?.join(", ")} —{" "}
                    Risks covered: {plan.auditSummary.risks_covered?.length ?? 0}
                  </p>
                </div>
              )}

              {/* Explainability traces */}
              {plan.modules.some((m) => m.explainabilityTrace) && (
                <div className="bg-card border rounded-lg p-5 shadow-sm space-y-3">
                  <h3 className="font-semibold text-base">Explainability Traces</h3>
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {plan.modules.filter((m) => m.explainabilityTrace).map((mod, idx) => {
                      const t = mod.explainabilityTrace!;
                      return (
                        <div key={idx} className="text-xs border rounded p-2 bg-muted/30">
                          <span className="font-medium">{mod.title}</span>
                          <span className="text-muted-foreground ml-2">
                            {t.role} → {t.responsibility} → {t.risk} → {t.control} →{" "}
                            <span className="font-mono text-primary">{t.regulation_ref}</span>
                            <span className="ml-1 opacity-60">[{t.source}]</span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Plan Quality Scorecard */}
              {plan.planId && <PlanScorecard planId={plan.planId} />}

              {/* Approval / Edit Workflow */}
              {plan.planId && (
                <ApprovalWorkflow
                  planId={plan.planId}
                  onPlanUpdated={() => loadPlan(plan.planId)}
                />
              )}

            </div>
          </section>
        )}
      </main>
    </div>
  );
}
