"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Sparkles, Loader2, AlertCircle } from "lucide-react";
import { API_BASE } from "@/lib/api";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("Exchanging Google Authorization Code...");
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("No authorization code provided in callback URL.");
      return;
    }

    async function processOAuth() {
      try {
        const resp = await fetch(`${API_BASE}/auth/callback?code=${encodeURIComponent(code)}`);
        if (!resp.ok) {
          throw new Error(`OAuth exchange failed with status ${resp.status}`);
        }
        const data = await resp.json();
        
        if (data?.access_token) {
          localStorage.setItem("mew_access_token", data.access_token);
        }
        if (data?.user) {
          localStorage.setItem("mew_user", JSON.stringify(data.user));
        }

        setStatus("Login Successful! Redirecting to Dashboard...");
        setTimeout(() => {
          window.location.href = "/";
        }, 1000);
      } catch (err) {
        setError(err.message || "Failed to complete Google Sign-In.");
      }
    }

    processOAuth();
  }, [searchParams]);

  return (
    <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-slate-800 text-center">
      <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 p-0.5 shadow-lg shadow-sky-500/20 flex items-center justify-center mx-auto mb-4">
        <Sparkles className="h-6 w-6 text-white" />
      </div>

      {error ? (
        <div>
          <div className="h-10 w-10 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto mb-3">
            <AlertCircle className="h-5 w-5" />
          </div>
          <h2 className="text-base font-bold text-rose-400 mb-2">Sign-In Failed</h2>
          <p className="text-xs text-slate-400 mb-6">{error}</p>
          <a
            href="/"
            className="inline-block px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 transition-colors"
          >
            Return to Home
          </a>
        </div>
      ) : (
        <div>
          <Loader2 className="h-8 w-8 text-sky-400 animate-spin mx-auto mb-4" />
          <h2 className="text-base font-bold text-slate-100 mb-1">{status}</h2>
          <p className="text-xs text-slate-400">Storing silent refresh token vault in SQLite...</p>
        </div>
      )}
    </div>
  );
}

export default function AuthCallback() {
  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center p-6 text-slate-100">
      <Suspense fallback={
        <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-slate-800 text-center">
          <Loader2 className="h-8 w-8 text-sky-400 animate-spin mx-auto mb-4" />
          <h2 className="text-base font-bold text-slate-100 mb-1">Loading Auth Callback...</h2>
        </div>
      }>
        <AuthCallbackContent />
      </Suspense>
    </main>
  );
}
