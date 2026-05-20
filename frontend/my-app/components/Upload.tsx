"use client";

import { useState, useEffect } from "react";
import { Button } from "./ui/button";

const API = "http://127.0.0.1:8000";

interface Props {
  onProcess: (data: { type: "structured"; payload: StructuredInput }) => void;
  isLoading: boolean;
  onLoadingStart: () => void;
}

export interface StructuredInput {
  role: string;
  responsibilities: string[];
  inherent_risks: string[];
}

interface PresetRole {
  role: string;
  responsibilities: string[];
  risks: string[];
}

// Map role names to beautiful emojis for premium cards
const getRoleIcon = (roleName: string) => {
  const name = roleName.toLowerCase();
  if (name.includes("kyc")) return "👤";
  if (name.includes("compliance")) return "🛡️";
  if (name.includes("mlro")) return "💼";
  if (name.includes("investigator")) return "🔍";
  if (name.includes("manager") || name.includes("relationship")) return "🤝";
  if (name.includes("senior") || name.includes("management")) return "🏛️";
  return "⚙️";
};

// Map role names to beautiful brand colors for card borders
const getRoleColorClass = (roleName: string) => {
  const name = roleName.toLowerCase();
  if (name.includes("kyc")) return "hover:border-emerald-500 dark:hover:border-emerald-700 hover:shadow-emerald-500/10";
  if (name.includes("compliance")) return "hover:border-blue-500 dark:hover:border-blue-700 hover:shadow-blue-500/10";
  if (name.includes("mlro")) return "hover:border-purple-500 dark:hover:border-purple-700 hover:shadow-purple-500/10";
  if (name.includes("investigator")) return "hover:border-amber-500 dark:hover:border-amber-700 hover:shadow-amber-500/10";
  if (name.includes("manager") || name.includes("relationship")) return "hover:border-teal-500 dark:hover:border-teal-700 hover:shadow-teal-500/10";
  if (name.includes("senior") || name.includes("management")) return "hover:border-rose-500 dark:hover:border-rose-700 hover:shadow-rose-500/10";
  return "hover:border-zinc-500 dark:hover:border-zinc-700 hover:shadow-zinc-500/10";
};

export default function InputSection({ onProcess, isLoading, onLoadingStart }: Props) {
  // Modes: "select" (selection screen), "editor" (structured editing), "extract" (paste text screen)
  const [mode, setMode] = useState<"select" | "editor" | "extract">("select");
  
  // Preset roles loaded from the backend
  const [presets, setPresets] = useState<PresetRole[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(true);
  
  // Text for extraction mode
  const [text, setText] = useState("");
  const [extractionError, setExtractionError] = useState("");
  const [extractionBusy, setExtractionErrorBusy] = useState(false);

  // Active structured state inside the editor
  const [roleName, setRoleName] = useState("");
  const [responsibilities, setResponsibilities] = useState<string[]>([]);
  const [risks, setRisks] = useState<string[]>([]);
  
  // Add input states
  const [newResponsibility, setNewResponsibility] = useState("");
  const [newRisk, setNewRisk] = useState("");

  // Quick Description Samples
  const SAMPLES = [
    {
      label: "👤 KYC Analyst",
      text: "KYC Analyst responsible for customer onboarding, identity verification, beneficial ownership checks, PEP screening, and ongoing CDD reviews. Key risks include identity fraud, shell company money laundering, and sanctions evasion."
    },
    {
      label: "🔍 AML Investigator",
      text: "AML Investigator tasked with suspicious transaction investigations, alert triage and review, case management, and sanctions review. Key risks include false negatives, failure to report suspicious transactions, and case documentation gaps."
    },
    {
      label: "🏛️ Senior Management",
      text: "Senior Management responsible for AML governance oversight, setting the firm's risk appetite, and training programme oversight. Key risks include regulatory breaches, lack of strategic risk alignment, and undertrained staff."
    }
  ];

  // Fetch preset roles on mount
  useEffect(() => {
    async function loadPresets() {
      try {
        const res = await fetch(`${API}/graph/roles`);
        if (res.ok) {
          const data = await res.json();
          if (data && Array.isArray(data.roles)) {
            setPresets(data.roles);
          }
        }
      } catch (err) {
        console.error("Failed to load preset roles from Neo4j:", err);
      } finally {
        setPresetsLoading(false);
      }
    }
    loadPresets();
  }, []);

  // Handler for selecting a preset role
  const handleSelectPreset = (p: PresetRole) => {
    setRoleName(p.role);
    setResponsibilities([...p.responsibilities]);
    setRisks([...p.risks]);
    setMode("editor");
  };

  // Handler for starting a custom role from scratch
  const handleCreateCustom = () => {
    setRoleName("Custom Compliance Role");
    setResponsibilities(["Establish internal AML controls"]);
    setRisks(["Money Laundering Risk"]);
    setMode("editor");
  };

  // Extract role, responsibilities, and risks from pasted text
  const handleExtractText = async () => {
    const trimmed = text.trim();
    if (!trimmed) {
      setExtractionError("Please paste your role description before extracting.");
      return;
    }
    setExtractionError("");
    setExtractionErrorBusy(true);

    try {
      const res = await fetch(`${API}/extract-role`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      // Load extracted content directly into the editor instead of submitting immediately
      setRoleName(data.role ?? "Custom Compliance Role");
      setResponsibilities(data.responsibilities ?? []);
      setRisks(data.risks ?? []);
      setMode("editor");
    } catch (e: any) {
      setExtractionError("Failed to extract role details: " + (e.message ?? "Unknown error"));
    } finally {
      setExtractionErrorBusy(false);
    }
  };

  // Dynamic Responsibility Add
  const addResponsibility = () => {
    const r = newResponsibility.trim();
    if (r && !responsibilities.includes(r)) {
      setResponsibilities([...responsibilities, r]);
      setNewResponsibility("");
    }
  };

  // Dynamic Responsibility Edit
  const editResponsibility = (idx: number, newVal: string) => {
    const updated = [...responsibilities];
    updated[idx] = newVal;
    setResponsibilities(updated);
  };

  // Dynamic Responsibility Delete
  const removeResponsibility = (idx: number) => {
    setResponsibilities(responsibilities.filter((_, i) => i !== idx));
  };

  // Dynamic Risk Add
  const addRisk = () => {
    const r = newRisk.trim();
    if (r && !risks.includes(r)) {
      setRisks([...risks, r]);
      setNewRisk("");
    }
  };

  // Dynamic Risk Edit
  const editRisk = (idx: number, newVal: string) => {
    const updated = [...risks];
    updated[idx] = newVal;
    setRisks(updated);
  };

  // Dynamic Risk Delete
  const removeRisk = (idx: number) => {
    setRisks(risks.filter((_, i) => i !== idx));
  };

  // Final Action: Process the dynamic, structured plan
  const handleFinalSubmit = () => {
    if (!roleName.trim()) {
      alert("Role Name cannot be empty.");
      return;
    }
    if (responsibilities.length === 0) {
      alert("Please add at least one responsibility.");
      return;
    }
    if (risks.length === 0) {
      alert("Please add at least one inherent risk.");
      return;
    }

    onLoadingStart();
    onProcess({
      type: "structured",
      payload: {
        role: roleName.trim(),
        responsibilities: responsibilities.map((r) => r.trim()).filter(Boolean),
        inherent_risks: risks.map((r) => r.trim()).filter(Boolean),
      },
    });
  };

  const isBusy = isLoading || extractionBusy;

  return (
    <div className="w-full space-y-6">
      {/* ── MODE 1: SELECTION SCREEN ────────────────────────────────────────── */}
      {mode === "select" && (
        <div className="space-y-8 animate-fadeIn">
          <div className="text-center space-y-2 max-w-xl mx-auto">
            <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">Step 1: Define Your Compliance Role</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Create a training plan mapped to real EU AMLR regulations. Select a seeded role, start a custom one, or paste a job description.
            </p>
          </div>

          {/* Core options grid */}
          <div className="grid grid-cols-2 gap-5">
            <div 
              onClick={handleCreateCustom}
              className="flex items-start gap-4 p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl cursor-pointer hover:border-blue-500 hover:shadow-lg hover:shadow-blue-500/5 transition-all group h-[120px]"
            >
              <div className="text-3xl bg-blue-50 dark:bg-blue-950/40 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">➕</div>
              <div className="space-y-1">
                <h4 className="font-bold text-sm text-zinc-800 dark:text-zinc-100 group-hover:text-blue-500 transition-colors">Create Custom Role</h4>
                <p className="text-xs text-muted-foreground leading-relaxed">Manually list your own specific role, responsibilities, and risk factors</p>
              </div>
            </div>

            <div 
              onClick={() => setMode("extract")}
              className="flex items-start gap-4 p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl cursor-pointer hover:border-violet-500 hover:shadow-lg hover:shadow-violet-500/5 transition-all group h-[120px]"
            >
              <div className="text-3xl bg-violet-50 dark:bg-violet-950/40 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">📄</div>
              <div className="space-y-1">
                <h4 className="font-bold text-sm text-zinc-800 dark:text-zinc-100 group-hover:text-violet-500 transition-colors">Extract From Job Description</h4>
                <p className="text-xs text-muted-foreground leading-relaxed">Paste free-form text or PDF context to extract the structure automatically</p>
              </div>
            </div>
          </div>

          {/* Seeded Roles section */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">EU AMLR Seeded Roles (Live from Neo4j)</h4>
              <span className="text-[10px] bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full font-semibold border border-emerald-100 dark:border-emerald-900/20">Idempotent Merge</span>
            </div>
            
            {presetsLoading ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                <span className="text-xs text-muted-foreground">Traversing governance graph...</span>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-4">
                {presets.map((p) => (
                  <div
                    key={p.role}
                    onClick={() => handleSelectPreset(p)}
                    className={`flex flex-col justify-between p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl cursor-pointer shadow-sm hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5 ${getRoleColorClass(p.role)}`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[28px]">{getRoleIcon(p.role)}</span>
                        <span className="text-[9px] font-mono font-bold uppercase bg-muted px-2 py-0.5 rounded text-muted-foreground">Preset</span>
                      </div>
                      <div className="space-y-0.5">
                        <h5 className="font-bold text-sm text-zinc-800 dark:text-zinc-100 leading-snug line-clamp-1">{p.role}</h5>
                        <p className="text-[10px] text-muted-foreground">EU Regulation Grounded</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-zinc-500 font-semibold pt-3 mt-4 border-t border-zinc-100 dark:border-zinc-800">
                      <span className="flex items-center gap-1">📋 {p.responsibilities.length} Resp</span>
                      <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">🚨 {p.risks.length} Risks</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── MODE 2: TEXT EXTRACTION SCREEN ──────────────────────────────────── */}
      {mode === "extract" && (
        <div className="space-y-5 animate-fadeIn">
          <div className="flex items-center justify-between border-b pb-3">
            <div>
              <h3 className="text-lg font-bold">Extract Role Outline</h3>
              <p className="text-xs text-muted-foreground">Our AI extracts the core responsibilities and risks for review.</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setMode("select")} className="text-xs">
              ← Back to Roles
            </Button>
          </div>

          <div className="space-y-2">
            <textarea
              value={text}
              onChange={(e) => { setText(e.target.value); setExtractionError(""); }}
              placeholder="Paste text description here..."
              className="w-full min-h-[220px] rounded-xl border border-zinc-200 dark:border-zinc-800 bg-background p-4 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 resize-none disabled:opacity-50 font-sans leading-relaxed"
              disabled={isBusy}
            />

            {/* Quick click samples */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Quick Test Samples:</span>
              <div className="flex items-center gap-2">
                {SAMPLES.map((s) => (
                  <button
                    key={s.label}
                    onClick={() => { setText(s.text); setExtractionError(""); }}
                    className="text-xs bg-muted hover:bg-primary hover:text-white dark:hover:text-black px-3 py-1.5 rounded-full transition-all text-zinc-600 dark:text-zinc-300 font-medium"
                    disabled={isBusy}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {extractionError && <p className="text-sm text-destructive">{extractionError}</p>}

          <div className="flex justify-between items-center pt-2 border-t">
            <Button variant="outline" onClick={() => setMode("select")} disabled={isBusy}>
              Cancel
            </Button>
            <Button 
              onClick={handleExtractText} 
              disabled={isBusy || !text.trim()} 
              className="bg-violet-600 hover:bg-violet-700 text-white dark:text-zinc-50 shadow-md shadow-violet-500/10"
            >
              {extractionBusy ? "Processing Description..." : "AI Parse & Load to Editor →"}
            </Button>
          </div>
        </div>
      )}

      {/* ── MODE 3: THE RICH INTERACTIVE ROLE EDITOR ────────────────────────── */}
      {mode === "editor" && (
        <div className="space-y-6 animate-fadeIn">
          {/* Header */}
          <div className="flex items-center justify-between border-b pb-4">
            <div className="flex-1 min-w-0 mr-4">
              <span className="text-[10px] font-bold text-primary uppercase tracking-wider font-mono">Job Title / Compliance Role</span>
              <input
                type="text"
                value={roleName}
                onChange={(e) => setRoleName(e.target.value)}
                placeholder="Job Title"
                className="w-full text-xl font-bold bg-transparent border-b border-transparent hover:border-zinc-300 focus:border-primary focus:outline-none py-0.5"
                disabled={isBusy}
              />
            </div>
            <Button variant="outline" size="sm" onClick={() => setMode("select")} disabled={isBusy}>
              ← Back to Roles
            </Button>
          </div>

          {/* Two section grids: Responsibilities + Risks */}
          <div className="grid grid-cols-2 gap-6">
            
            {/* 1. Responsibilities Section */}
            <div className="space-y-4 bg-white dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-100 dark:border-zinc-900/60 shadow-sm flex flex-col h-[520px]">
              <div className="flex items-center gap-2 border-b pb-3">
                <span className="text-xl">📋</span>
                <div>
                  <h4 className="font-bold text-sm">Key Responsibilities ({responsibilities.length})</h4>
                  <p className="text-[10px] text-muted-foreground">What compliance functions are assigned?</p>
                </div>
              </div>

              {/* Add field */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newResponsibility}
                  onChange={(e) => setNewResponsibility(e.target.value)}
                  placeholder="Add custom responsibility..."
                  className="flex-1 rounded-lg border border-input bg-transparent px-3 py-1.5 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  onKeyDown={(e) => e.key === "Enter" && addResponsibility()}
                  disabled={isBusy}
                />
                <Button size="sm" onClick={addResponsibility} disabled={isBusy}>
                  Add ➕
                </Button>
              </div>

              {/* Responsibilities List */}
              <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
                {responsibilities.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic text-center py-12">No responsibilities added. Write one above to start.</p>
                ) : (
                  responsibilities.map((resp, idx) => (
                    <div key={idx} className="group flex items-start gap-2 bg-zinc-50/50 dark:bg-zinc-900/40 border border-zinc-100 dark:border-zinc-800/40 rounded-xl p-3 shadow-sm hover:border-zinc-200 dark:hover:border-zinc-700 transition-colors animate-fadeIn">
                      <span className="mt-0.5 text-zinc-400 shrink-0 text-xs font-mono font-bold">#{idx + 1}</span>
                      <textarea
                        rows={1}
                        value={resp}
                        onChange={(e) => editResponsibility(idx, e.target.value)}
                        className="flex-1 text-xs bg-transparent border-none focus:outline-none focus:ring-0 leading-relaxed font-semibold resize-none p-0 h-auto overflow-hidden focus:text-primary transition-colors"
                        disabled={isBusy}
                      />
                      <button
                        onClick={() => removeResponsibility(idx)}
                        className="text-zinc-400 hover:text-destructive opacity-30 group-hover:opacity-100 transition-opacity text-sm leading-none shrink-0"
                        disabled={isBusy}
                        title="Delete"
                      >
                        ✕
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* 2. Inherent Risks Section */}
            <div className="space-y-4 bg-white dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-100 dark:border-zinc-900/60 shadow-sm flex flex-col h-[520px]">
              <div className="flex items-center gap-2 border-b pb-3">
                <span className="text-xl">🚨</span>
                <div>
                  <h4 className="font-bold text-sm text-amber-600 dark:text-amber-500">Inherent AML Risks ({risks.length})</h4>
                  <p className="text-[10px] text-muted-foreground">What money laundering risks must be managed?</p>
                </div>
              </div>

              {/* Add field */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newRisk}
                  onChange={(e) => setNewRisk(e.target.value)}
                  placeholder="Add custom compliance risk..."
                  className="flex-1 rounded-lg border border-input bg-transparent px-3 py-1.5 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  onKeyDown={(e) => e.key === "Enter" && addRisk()}
                  disabled={isBusy}
                />
                <Button size="sm" onClick={addRisk} disabled={isBusy}>
                  Add ➕
                </Button>
              </div>

              {/* Risks List */}
              <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
                {risks.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic text-center py-12">No inherent risks added. Write one above to start.</p>
                ) : (
                  risks.map((risk, idx) => (
                    <div key={idx} className="group flex items-start gap-2 bg-amber-50/20 dark:bg-amber-950/10 border border-amber-100/60 dark:border-amber-900/20 rounded-xl p-3 shadow-sm hover:border-amber-200 dark:hover:border-amber-800 transition-colors animate-fadeIn">
                      <span className="mt-0.5 text-amber-500/60 shrink-0 text-xs font-mono font-bold">#{idx + 1}</span>
                      <textarea
                        rows={1}
                        value={risk}
                        onChange={(e) => editRisk(idx, e.target.value)}
                        className="flex-1 text-xs bg-transparent border-none focus:outline-none focus:ring-0 leading-relaxed text-zinc-800 dark:text-zinc-200 font-semibold resize-none p-0 h-auto overflow-hidden focus:text-amber-600 transition-colors"
                        disabled={isBusy}
                      />
                      <button
                        onClick={() => removeRisk(idx)}
                        className="text-amber-600/40 hover:text-destructive opacity-30 group-hover:opacity-100 transition-opacity text-sm leading-none shrink-0"
                        disabled={isBusy}
                        title="Delete"
                      >
                        ✕
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* Action buttons at bottom */}
          <div className="flex justify-between items-center pt-4 border-t">
            <Button variant="outline" onClick={() => setMode("select")} disabled={isBusy}>
              ← Cancel & Choose Role
            </Button>
            <Button onClick={handleFinalSubmit} disabled={isBusy} size="lg" className="shadow-lg shadow-primary/10">
              {isLoading ? "Assembling Training Plan..." : "Generate Regulatory Training Plan 🚀"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}