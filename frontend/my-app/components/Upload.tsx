"use client";

import { useState, useEffect } from "react";
import { Button } from "./ui/button";

const API = "http://127.0.0.1:8000";

interface Props {
  onProcess: (data: { type: "structured"; payload: StructuredInput }) => void; // fallback
  onProcessMulti?: (data: { domain: string; roles: ExtractedRole[] }) => void; // for enterprise multi-role curriculum
  isLoading: boolean;
  onLoadingStart: (stage?: string) => void;
  onLoadingEnd: () => void;
}

export interface StructuredInput {
  role: string;
  responsibilities: string[];
  inherent_risks: string[];
  domain: string;
}

export interface ExtractedRole {
  role: string;
  responsibilities: string[];
  risks: string[];
  isEnabled: boolean;
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

export default function InputSection({ onProcess, onProcessMulti, isLoading, onLoadingStart, onLoadingEnd }: Props) {
  // Modes: "select" (selection screen), "editor" (structured editing), "extract" (paste text screen)
  const [mode, setMode] = useState<"select" | "editor" | "extract">("select");
  
  // Preset roles loaded from the backend
  const [presets, setPresets] = useState<PresetRole[]>([]);
  const [presetsLoading, setPresetsLoading] = useState(true);
  
  // Text extraction states
  const [text, setText] = useState("");
  const [extractionError, setExtractionError] = useState("");
  const [extractionBusy, setExtractionErrorBusy] = useState(false);

  // File upload states
  const [uploadError, setUploadError] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);

  // Active list of roles inside our Multi-Role Curriculum Dashboard
  const [rolesList, setRolesList] = useState<ExtractedRole[]>([]);
  const [activeRoleIndex, setActiveRoleIndex] = useState<number>(0);
  const [domain, setDomain] = useState("Banking & Payments");
  
  // Add input states for the current active role
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
    setRolesList([{
      role: p.role,
      responsibilities: [...p.responsibilities],
      risks: [...p.risks],
      isEnabled: true
    }]);
    setActiveRoleIndex(0);
    setMode("editor");
  };

  // Handler for starting a custom role from scratch
  const handleCreateCustom = () => {
    setRolesList([{
      role: "Custom Compliance Role",
      responsibilities: ["Establish internal AML controls"],
      risks: ["Money Laundering Risk"],
      isEnabled: true
    }]);
    setActiveRoleIndex(0);
    setMode("editor");
  };

  // Append a brand new empty role inside the editor
  const handleAddNewRole = () => {
    const newRole: ExtractedRole = {
      role: `Custom Role #${rolesList.length + 1}`,
      responsibilities: ["Establish internal AML controls"],
      risks: ["Money Laundering Risk"],
      isEnabled: true
    };
    setRolesList([...rolesList, newRole]);
    setActiveRoleIndex(rolesList.length);
  };

  // Delete a role from the list
  const handleDeleteRole = (idx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (rolesList.length <= 1) {
      alert("You must keep at least one role in your curriculum.");
      return;
    }
    const updated = rolesList.filter((_, i) => i !== idx);
    setRolesList(updated);
    setActiveRoleIndex(Math.max(0, idx - 1));
  };

  // Extract multiple roles from text / job descriptions
  const processExtractionText = async (rawText: string) => {
    try {
      const res = await fetch(`${API}/extract-multiple-roles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: rawText, domain: domain }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      if (data && Array.isArray(data.roles) && data.roles.length > 0) {
        const loaded = data.roles.map((r: any) => ({
          role: r.role ?? "Extracted Role",
          responsibilities: r.responsibilities ?? ["Analyze risk alerts"],
          risks: r.inherent_risks ?? r.risks ?? ["AML Risk"],
          isEnabled: true
        }));
        setRolesList(loaded);
        setActiveRoleIndex(0);
        setMode("editor");
      } else {
        throw new Error("No roles could be identified in the description.");
      }
    } catch (e: any) {
      throw e;
    }
  };

  // Handlers for free-text extractor
  const handleExtractText = async () => {
    const trimmed = text.trim();
    if (!trimmed) {
      setExtractionError("Please paste your role description before extracting.");
      return;
    }
    setExtractionError("");
    setExtractionErrorBusy(true);

    try {
      await processExtractionText(trimmed);
    } catch (e: any) {
      setExtractionError("Failed to extract roles: " + (e.message ?? "Unknown error"));
    } finally {
      setExtractionErrorBusy(false);
    }
  };

  // Handlers for PDF File Uploader
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError("");
    setUploadBusy(true);
    onLoadingStart("Parsing corporate PDF file…");

    try {
      const formData = new FormData();
      formData.append("file", file);

      // 1. Upload to extract text
      const uploadRes = await fetch(`${API}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) throw new Error(await uploadRes.text());
      const uploadData = await uploadRes.json();
      const extractedText = uploadData.text;

      if (!extractedText || !extractedText.trim()) {
        throw new Error("PDF file appears to be empty or unscannable.");
      }

      onLoadingStart("Analyzing text and extracting compliance roles…");

      // 2. Call multi-role extractor
      await processExtractionText(extractedText);
    } catch (err: any) {
      console.error(err);
      setUploadError(err.message ?? "Failed to parse PDF file.");
    } finally {
      setUploadBusy(false);
      // Turn off overall loading since we loaded into editor mode (or errored)
      onLoadingEnd();
    }
  };

  // Dynamic Responsibility Add
  const addResponsibility = () => {
    const r = newResponsibility.trim();
    if (!r) return;
    const currentRole = rolesList[activeRoleIndex];
    if (currentRole && !currentRole.responsibilities.includes(r)) {
      const updated = [...rolesList];
      updated[activeRoleIndex].responsibilities = [...currentRole.responsibilities, r];
      setRolesList(updated);
      setNewResponsibility("");
    }
  };

  // Dynamic Responsibility Edit
  const editResponsibility = (idx: number, newVal: string) => {
    const updated = [...rolesList];
    updated[activeRoleIndex].responsibilities[idx] = newVal;
    setRolesList(updated);
  };

  // Dynamic Responsibility Delete
  const removeResponsibility = (idx: number) => {
    const updated = [...rolesList];
    updated[activeRoleIndex].responsibilities = updated[activeRoleIndex].responsibilities.filter((_, i) => i !== idx);
    setRolesList(updated);
  };

  // Dynamic Risk Add
  const addRisk = () => {
    const r = newRisk.trim();
    if (!r) return;
    const currentRole = rolesList[activeRoleIndex];
    if (currentRole && !currentRole.risks.includes(r)) {
      const updated = [...rolesList];
      updated[activeRoleIndex].risks = [...currentRole.risks, r];
      setRolesList(updated);
      setNewRisk("");
    }
  };

  // Dynamic Risk Edit
  const editRisk = (idx: number, newVal: string) => {
    const updated = [...rolesList];
    updated[activeRoleIndex].risks[idx] = newVal;
    setRolesList(updated);
  };

  // Dynamic Risk Delete
  const removeRisk = (idx: number) => {
    const updated = [...rolesList];
    updated[activeRoleIndex].risks = updated[activeRoleIndex].risks.filter((_, i) => i !== idx);
    setRolesList(updated);
  };

  // In-line change of active role name
  const handleRoleNameChange = (val: string) => {
    const updated = [...rolesList];
    updated[activeRoleIndex].role = val;
    setRolesList(updated);
  };

  // Final Action: Process the dynamic structured curriculum
  const handleFinalSubmit = () => {
    const enabledRoles = rolesList.filter(r => r.isEnabled);
    if (enabledRoles.length === 0) {
      alert("Please select/enable at least one role to generate a curriculum.");
      return;
    }

    // Verify all enabled roles are structured correctly
    for (const r of enabledRoles) {
      if (!r.role.trim()) {
        alert("Role job titles cannot be empty.");
        return;
      }
      if (r.responsibilities.length === 0) {
        alert(`Please add at least one responsibility for ${r.role}.`);
        return;
      }
      if (r.risks.length === 0) {
        alert(`Please add at least one inherent risk for ${r.role}.`);
        return;
      }
    }

    onLoadingStart();
    if (onProcessMulti) {
      // Trigger bulk multi-role curriculum generation!
      onProcessMulti({
        domain: domain,
        roles: enabledRoles
      });
    } else {
      // Fallback to single-role logic
      const active = enabledRoles[0];
      onProcess({
        type: "structured",
        payload: {
          role: active.role.trim(),
          responsibilities: active.responsibilities.map(r => r.trim()).filter(Boolean),
          inherent_risks: active.risks.map(r => r.trim()).filter(Boolean),
          domain: domain,
        }
      });
    }
  };

  const isBusy = isLoading || extractionBusy || uploadBusy;
  const currentActiveRole = rolesList[activeRoleIndex];

  return (
    <div className="w-full space-y-6">
      {/* ── MODE 1: SELECTION SCREEN ────────────────────────────────────────── */}
      {mode === "select" && (
        <div className="space-y-8 animate-fadeIn">
          <div className="text-center space-y-2 max-w-xl mx-auto">
            <h3 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">Step 1: Define Your Compliance Roles</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Create training paths mapped to real EU AMLR regulations. Upload a corporate PDF, select a seeded role, or write custom ones.
            </p>
          </div>

          {/* Three core options grid */}
          <div className="grid grid-cols-3 gap-4">
            
            {/* 1. Upload PDF */}
            <label className="flex flex-col items-center justify-center p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl cursor-pointer hover:border-emerald-500 hover:shadow-lg hover:shadow-emerald-500/5 transition-all group text-center space-y-2 h-[150px] relative">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
                disabled={isBusy}
              />
              <div className="text-3xl bg-emerald-50 dark:bg-emerald-950/40 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">📂</div>
              <div className="space-y-0.5">
                <h4 className="font-bold text-sm text-zinc-800 dark:text-zinc-100 group-hover:text-emerald-500 transition-colors">Upload Corporate PDF</h4>
                <p className="text-[10px] text-muted-foreground">Extracts multiple roles & risks automatically</p>
              </div>
            </label>

            {/* 2. Custom Role */}
            <div 
              onClick={handleCreateCustom}
              className="flex flex-col items-center justify-center p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl cursor-pointer hover:border-blue-500 hover:shadow-lg hover:shadow-blue-500/5 transition-all group text-center space-y-2 h-[150px]"
            >
              <div className="text-3xl bg-blue-50 dark:bg-blue-950/40 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">➕</div>
              <div className="space-y-0.5">
                <h4 className="font-bold text-sm text-zinc-800 dark:text-zinc-100 group-hover:text-blue-500 transition-colors">Create Custom Role</h4>
                <p className="text-[10px] text-muted-foreground">Define responsibilities & risks manually</p>
              </div>
            </div>

            {/* 3. Paste Description */}
            <div 
              onClick={() => setMode("extract")}
              className="flex flex-col items-center justify-center p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl cursor-pointer hover:border-violet-500 hover:shadow-lg hover:shadow-violet-500/5 transition-all group text-center space-y-2 h-[150px]"
            >
              <div className="text-3xl bg-violet-50 dark:bg-violet-950/40 w-12 h-12 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform shrink-0">📄</div>
              <div className="space-y-0.5">
                <h4 className="font-bold text-sm text-zinc-800 dark:text-zinc-100 group-hover:text-violet-500 transition-colors">Extract From Job Text</h4>
                <p className="text-[10px] text-muted-foreground">Paste plain job description/responsibilities</p>
              </div>
            </div>

          </div>

          {uploadError && <p className="text-sm text-destructive text-center">{uploadError}</p>}

          {/* Seeded Roles section */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between border-b pb-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Seeded EU AMLR Roles (Live from Neo4j)</h4>
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
              <h3 className="text-lg font-bold">Extract Role Outlines</h3>
              <p className="text-xs text-muted-foreground">Paste text describing one or more roles. AI extracts duties and risks for each.</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setMode("select")} className="text-xs">
              ← Back to Roles
            </Button>
          </div>

          <div className="space-y-2">
            <textarea
              value={text}
              onChange={(e) => { setText(e.target.value); setExtractionError(""); }}
              placeholder="Paste job description here..."
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
      {mode === "editor" && currentActiveRole && (
        <div className="space-y-6 animate-fadeIn w-full">
          {/* Header */}
          <div className="flex items-center justify-between border-b pb-4">
            <div className="flex-1 min-w-0 mr-4 flex gap-4">
              <div className="flex-1 min-w-0">
                <span className="text-[10px] font-bold text-primary uppercase tracking-wider font-mono">Curriculum Job Title / Role</span>
                <input
                  type="text"
                  value={currentActiveRole.role}
                  onChange={(e) => handleRoleNameChange(e.target.value)}
                  placeholder="Job Title"
                  className="w-full text-xl font-bold bg-transparent border-b border-transparent hover:border-zinc-300 focus:border-primary focus:outline-none py-0.5"
                  disabled={isBusy}
                />
              </div>
              <div className="w-[200px] shrink-0">
                <span className="text-[10px] font-bold text-primary uppercase tracking-wider font-mono">Curriculum Domain / Sector</span>
                <select
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  className="w-full text-xs font-semibold bg-zinc-100 dark:bg-zinc-800 border rounded-lg p-1.5 focus:outline-none focus:ring-1 focus:ring-primary mt-1"
                  disabled={isBusy}
                >
                  <option value="Banking & Payments">🏦 Banking & Payments</option>
                  <option value="Crypto & Virtual Assets">🪙 Crypto & Virtual Assets</option>
                  <option value="FinTech & Payments">💳 FinTech & Payments</option>
                  <option value="Wealth Management">📈 Wealth Management</option>
                  <option value="Real Estate">🏠 Real Estate</option>
                  <option value="Gaming & Casinos">🎰 Gaming & Casinos</option>
                </select>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => setMode("select")} disabled={isBusy}>
              ← Back to Roles
            </Button>
          </div>

          {/* Two Columns: Left Sidebar (Roles List) + Right Panel (Active Role Details) */}
          <div className="grid grid-cols-12 gap-6 items-stretch">
            
            {/* LEFT SIDEBAR: Active Curriculum Roles List (4 cols) */}
            <div className="col-span-3 bg-zinc-100/50 dark:bg-zinc-900/30 border border-zinc-200 dark:border-zinc-800 p-4 rounded-2xl flex flex-col space-y-4">
              <div className="space-y-1">
                <h4 className="font-bold text-xs uppercase tracking-wider text-muted-foreground">Curriculum Roles ({rolesList.length})</h4>
                <p className="text-[9px] text-muted-foreground leading-normal">Configure and select roles to include in the bulk generation.</p>
              </div>

              {/* Roles Selector List */}
              <div className="flex-1 overflow-y-auto space-y-2 max-h-[400px] pr-1">
                {rolesList.map((r, idx) => (
                  <div
                    key={idx}
                    onClick={() => setActiveRoleIndex(idx)}
                    className={`group flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all duration-200 ${activeRoleIndex === idx ? "bg-white dark:bg-zinc-900 border-primary shadow-sm" : "bg-transparent border-zinc-200/60 dark:border-zinc-800/60 hover:bg-white/40 dark:hover:bg-zinc-900/20"}`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {/* Checkbox to enable/disable role in generation */}
                      <input
                        type="checkbox"
                        checked={r.isEnabled}
                        onChange={(e) => {
                          const updated = [...rolesList];
                          updated[idx].isEnabled = e.target.checked;
                          setRolesList(updated);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-zinc-300 text-primary focus:ring-primary w-3.5 h-3.5"
                        disabled={isBusy}
                        title="Include in training curriculum"
                      />
                      <div className="min-w-0 space-y-0.5">
                        <p className={`text-xs font-bold truncate leading-snug ${activeRoleIndex === idx ? "text-primary" : "text-zinc-700 dark:text-zinc-300"}`}>
                          {r.role || "Job Title Empty"}
                        </p>
                        <p className="text-[9px] text-muted-foreground">
                          {r.responsibilities.length} Resp | {r.risks.length} Risks
                        </p>
                      </div>
                    </div>
                    
                    {/* Delete Role Button */}
                    <button
                      onClick={(e) => handleDeleteRole(idx, e)}
                      className="text-zinc-400 hover:text-destructive opacity-35 group-hover:opacity-100 transition-opacity text-xs pr-1 shrink-0"
                      disabled={isBusy}
                      title="Remove Role"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>

              {/* Add New Role Button */}
              <Button variant="outline" size="sm" onClick={handleAddNewRole} disabled={isBusy} className="w-full text-xs font-semibold">
                ➕ Add Another Role
              </Button>
            </div>

            {/* RIGHT PANEL: Edit Active Role Responsibilities + Risks (9 cols) */}
            <div className="col-span-9 grid grid-cols-2 gap-6 h-[540px] items-stretch">
              
              {/* 1. Responsibilities Section */}
              <div className="space-y-4 bg-white dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-200/80 dark:border-zinc-800/40 shadow-sm flex flex-col h-full">
                <div className="flex items-center gap-2 border-b pb-3">
                  <span className="text-xl">📋</span>
                  <div>
                    <h4 className="font-bold text-sm">Key Responsibilities ({currentActiveRole.responsibilities.length})</h4>
                    <p className="text-[10px] text-muted-foreground">What compliance duties does this role perform?</p>
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
                  {currentActiveRole.responsibilities.length === 0 ? (
                    <p className="text-xs text-muted-foreground italic text-center py-12">No responsibilities added. Write one above to start.</p>
                  ) : (
                    currentActiveRole.responsibilities.map((resp, idx) => (
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
              <div className="space-y-4 bg-white dark:bg-zinc-950 p-5 rounded-2xl border border-zinc-200/80 dark:border-zinc-800/40 shadow-sm flex flex-col h-full">
                <div className="flex items-center gap-2 border-b pb-3">
                  <span className="text-xl">🚨</span>
                  <div>
                    <h4 className="font-bold text-sm text-amber-600 dark:text-amber-500">Inherent AML Risks ({currentActiveRole.risks.length})</h4>
                    <p className="text-[10px] text-muted-foreground">What compliance risks must be managed?</p>
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
                  {currentActiveRole.risks.length === 0 ? (
                    <p className="text-xs text-muted-foreground italic text-center py-12">No inherent risks added. Write one above to start.</p>
                  ) : (
                    currentActiveRole.risks.map((risk, idx) => (
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

          </div>

          {/* Action buttons at bottom */}
          <div className="flex justify-between items-center pt-4 border-t">
            <Button variant="outline" onClick={() => setMode("select")} disabled={isBusy}>
              ← Cancel & Choose Role
            </Button>
            <Button onClick={handleFinalSubmit} disabled={isBusy} size="lg" className="shadow-lg shadow-primary/10">
              {isLoading ? "Assembling Widescreen Curriculum..." : `Generate Training Paths for ${rolesList.filter(r => r.isEnabled).length} Roles 🚀`}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}