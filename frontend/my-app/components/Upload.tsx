"use client";

import { useState } from "react";
import { Button } from "./ui/button";

const API = "http://127.0.0.1:8000";

interface Props {
  onProcess: (data: { type: "structured"; payload: StructuredInput }) => void;
  isLoading: boolean;
  onLoadingStart: () => void;  // called immediately on click — shows overlay before API
}

export interface StructuredInput {
  role: string;
  responsibilities: string[];
  inherent_risks: string[];
}

export default function InputSection({ onProcess, isLoading, onLoadingStart }: Props) {
  const [text, setText]   = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy]   = useState(false);

  const handleGenerate = async () => {
    const trimmed = text.trim();
    if (!trimmed) {
      setError("Please paste your role description before generating.");
      return;
    }
    setError("");
    setBusy(true);

    // Show the overlay immediately — before any network call
    onLoadingStart();

    try {
      const res = await fetch(`${API}/extract-role`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      onProcess({
        type: "structured",
        payload: {
          role:            data.role            ?? "Compliance Analyst",
          responsibilities: data.responsibilities ?? [],
          inherent_risks:   data.risks            ?? [],
        },
      });
    } catch (e: any) {
      setError("Failed to extract role info: " + (e.message ?? "Unknown error"));
    } finally {
      setBusy(false);
    }
  };

  const processing = isLoading || busy;
  const canSubmit  = !processing && text.trim().length > 0;

  return (
    <div className="w-full max-w-2xl space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          Paste your role description
        </label>
        <p className="text-xs text-muted-foreground">
          Include the job title, key responsibilities, and any known compliance risks.
        </p>
        <textarea
          value={text}
          onChange={(e) => { setText(e.target.value); setError(""); }}
          placeholder={`Example:\n\nKYC Analyst responsible for customer onboarding, identity verification, beneficial ownership checks, PEP screening, and ongoing CDD reviews. Key risks include identity fraud, shell company money laundering, and sanctions evasion.`}
          className="w-full min-h-[200px] rounded-lg border border-input bg-background p-4 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 resize-none disabled:opacity-50"
          disabled={processing}
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex justify-end">
        <Button onClick={handleGenerate} disabled={!canSubmit} size="lg">
          {processing ? "Generating…" : "Generate Training Plan"}
        </Button>
      </div>
    </div>
  );
}
