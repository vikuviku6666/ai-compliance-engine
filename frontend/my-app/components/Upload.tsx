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
    setRoleName("Custom Role");
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
        <div className="space-y-6 animate-fadeIn">
          <div className="text-center space-y-1.5">
            <h3 className="text-xl font-bold tracking-tight">Step 1: Choose or Create a Compliance Role</h3>
            <p className="text-sm text-muted-foreground">
              Select an AML governance role seeded from Neo4j, write a custom one, or extract one from a text description.
            </p>
          </div>

          {/* Core options grid */}
          <div className="grid grid-cols-2 gap-4">
            <div 
              onClick={handleCreateCustom}
              className="flex flex-col items-center justify-center p-6 bg-white dark:bg-zinc-900 border rounded-2xl cursor-pointer hover:border-blue-500 hover:shadow-md transition-all group text-center space-y-2 h-[140px]"
            >
              <div className="text-2xl group-hover:scale-110 transition-transform">➕</div>
              <div>
                <h4 className="font-semibold text-sm group-hover:text-blue-500 transition-colors">Create Custom Role</h4>
                <p className="text-xs text-muted-foreground mt-1">Define responsibilities and risks manually</p>
              </div>
            </div>

            <div 
              onClick={() => setMode("extract")}
              className="flex flex-col items-center justify-center p-6 bg-white dark:bg-zinc-900 border rounded-2xl cursor-pointer hover:border-blue-500 hover:shadow-md transition-all group text-center space-y-2 h-[140px]"
            >
              <div className="text-2xl group-hover:scale-110 transition-transform">📄</div>
              <div>
                <h4 className="font-semibold text-sm group-hover:text-blue-500 transition-colors">Extract From Job Description</h4>
                <p className="text-xs text-muted-foreground mt-1">Paste description and edit the extracted outline</p>
              </div>
            </div>
          </div>

          {/* Seeded Roles section */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Preset EU AMLR Roles (Neo4j Seeded)</h4>
            
            {presetsLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {presets.map((p) => (
                  <div
                    key={p.role}
                    onClick={() => handleSelectPreset(p)}
                    className="p-4 bg-white dark:bg-zinc-900 border rounded-xl cursor-pointer hover:border-primary hover:bg-muted/10 transition-all space-y-2"
                  >
                    <div className="font-medium text-xs truncate text-primary uppercase tracking-wide">AMLR Role</div>
                    <div className="font-semibold text-sm text-foreground">{p.role}</div>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1.5 border-t">
                      <span>Resp: {p.responsibilities.length}</span>
                      <span>Risks: {p.risks.length}</span>
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
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Extract Role from Description</h3>
              <p className="text-xs text-muted-foreground">Paste custom responsibilities/risks and review them inside our editor.</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setMode("select")}>
              ← Back to Roles
            </Button>
          </div>

          <textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setExtractionError(""); }}
            placeholder={`Paste job description here...\n\nExample:\nWe are looking for a KYC Analyst to handle high-risk client onboarding, verification of UBO registries, and politically exposed persons (PEPs) checks. Primary risks are nominee ownership structures, PEP corruption, and sanctions avoidance.`}
            className="w-full min-h-[180px] rounded-lg border border-input bg-background p-4 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 resize-none disabled:opacity-50"
            disabled={isBusy}
          />

          {extractionError && <p className="text-sm text-destructive">{extractionError}</p>}

          <div className="flex justify-between items-center pt-2">
            <Button variant="outline" onClick={() => setMode("select")} disabled={isBusy}>
              Cancel
            </Button>
            <Button onClick={handleExtractText} disabled={isBusy || !text.trim()}>
              {extractionBusy ? "Extracting..." : "Parse & Edit Role Details →"}
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
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-sm">Key Responsibilities ({responsibilities.length})</h4>
                  <p className="text-[10px] text-muted-foreground">What actions does this role perform?</p>
                </div>
              </div>

              {/* Add field */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newResponsibility}
                  onChange={(e) => setNewResponsibility(e.target.value)}
                  placeholder="e.g. Conduct enhanced due diligence on PEPs"
                  className="flex-1 rounded-md border border-input bg-transparent px-3 py-1.5 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  onKeyDown={(e) => e.key === "Enter" && addResponsibility()}
                  disabled={isBusy}
                />
                <Button size="sm" variant="secondary" onClick={addResponsibility} disabled={isBusy}>
                  Add
                </Button>
              </div>

              {/* Responsibilities List */}
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {responsibilities.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic text-center py-4">No responsibilities added. Add one above.</p>
                ) : (
                  responsibilities.map((resp, idx) => (
                    <div key={idx} className="group flex items-start gap-2 bg-white dark:bg-zinc-900 border rounded-lg p-2.5 shadow-sm">
                      <input
                        type="text"
                        value={resp}
                        onChange={(e) => editResponsibility(idx, e.target.value)}
                        className="flex-1 text-xs bg-transparent border-none focus:outline-none focus:ring-0 leading-relaxed resize-none p-0 font-medium"
                        disabled={isBusy}
                      />
                      <button
                        onClick={() => removeResponsibility(idx)}
                        className="text-muted-foreground hover:text-destructive opacity-40 group-hover:opacity-100 transition-opacity text-xs"
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
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-sm text-amber-600 dark:text-amber-500">Inherent AML Risks ({risks.length})</h4>
                  <p className="text-[10px] text-muted-foreground">What money laundering/compliance risks apply?</p>
                </div>
              </div>

              {/* Add field */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newRisk}
                  onChange={(e) => setNewRisk(e.target.value)}
                  placeholder="e.g. Sanctions evasion or PEP corruption"
                  className="flex-1 rounded-md border border-input bg-transparent px-3 py-1.5 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  onKeyDown={(e) => e.key === "Enter" && addRisk()}
                  disabled={isBusy}
                />
                <Button size="sm" variant="secondary" onClick={addRisk} disabled={isBusy}>
                  Add
                </Button>
              </div>

              {/* Risks List */}
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {risks.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic text-center py-4">No inherent risks added. Add one above.</p>
                ) : (
                  risks.map((risk, idx) => (
                    <div key={idx} className="group flex items-start gap-2 bg-amber-50/20 dark:bg-amber-950/10 border border-amber-100/60 dark:border-amber-900/30 rounded-lg p-2.5 shadow-sm animate-fadeIn">
                      <input
                        type="text"
                        value={risk}
                        onChange={(e) => editRisk(idx, e.target.value)}
                        className="flex-1 text-xs bg-transparent border-none focus:outline-none focus:ring-0 leading-relaxed text-foreground"
                        disabled={isBusy}
                      />
                      <button
                        onClick={() => removeRisk(idx)}
                        className="text-amber-600/40 hover:text-destructive group-hover:opacity-100 transition-opacity text-xs"
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
              ← Start Over
            </Button>
            <Button onClick={handleFinalSubmit} disabled={isBusy} size="lg">
              {isLoading ? "Generating Training Plan..." : "Generate Training Plan 🚀"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}