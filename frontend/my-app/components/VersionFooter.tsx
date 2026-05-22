"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const FRONTEND_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || "1.0.0";

export default function VersionFooter() {
  const [backendVersion, setBackendVersion] = useState<string>("connecting...");
  const [dbVersion, setDbVersion] = useState<string>("connecting...");

  useEffect(() => {
    fetch(`${API}/health/detailed`)
      .then((res) => res.json())
      .then((data) => {
        setBackendVersion(data.version || "unknown");
        setDbVersion(data.db_version || "unknown");
      })
      .catch(() => {
        setBackendVersion("offline");
        setDbVersion("offline");
      });
  }, []);

  return (
    <footer className="w-full py-4 text-center text-xs text-muted-foreground bg-muted/20 border-t mt-auto">
      <div className="flex items-center justify-center gap-4">
        <span>UI: v{FRONTEND_VERSION}</span>
        <span>•</span>
        <span>Engine: v{backendVersion}</span>
        <span>•</span>
        <span>DB Schema: v{dbVersion}</span>
      </div>
    </footer>
  );
}
