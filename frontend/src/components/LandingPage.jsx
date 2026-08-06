"use client";

import { useState } from "react";
import { Zap, ArrowRight, ShieldCheck, Terminal, Key, Check, Layers, FileCode } from "lucide-react";

export default function LandingPage({ onGoogleLogin, onManualCodeSubmit }) {
  const [manualCode, setManualCode] = useState("");
  const [isSubmittingCode, setIsSubmittingCode] = useState(false);
  const [codeError, setCodeError] = useState(null);

  const handleCodeSubmit = async (e) => {
    e.preventDefault();
    if (!manualCode.trim()) return;
    setIsSubmittingCode(true);
    setCodeError(null);
    try {
      await onManualCodeSubmit(manualCode.trim());
    } catch (err) {
      setCodeError(err.message || "Failed to exchange authorization code.");
    } finally {
      setIsSubmittingCode(false);
    }
  };

  return (
    <div className="relative overflow-hidden bg-[#08090a] text-slate-100 min-h-screen">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-lime-400/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Hero Section */}
      <section className="relative pt-20 pb-24 px-6 max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-lime-400/10 border border-lime-400/30 text-lime-400 text-xs font-mono mb-8 backdrop-blur-md">
          <Terminal className="h-3.5 w-3.5" />
          <span>[AGENTIC_FORM_ENGINE // v2.0]</span>
        </div>

        <h1 className="text-4xl sm:text-7xl md:text-8xl font-black tracking-tighter uppercase text-white max-w-5xl mx-auto leading-[0.95] mb-8">
          TERMINATE MANUAL JOB FORMS. <span className="neon-lime-text">AUTOFILL IN 0.4s.</span>
        </h1>

        <p className="text-base sm:text-xl text-slate-400 max-w-2xl mx-auto mb-12 font-mono">
          MEW overrides cross-origin iframe security boundaries, parses PDF resumes via Gemini AI, and auto-fills Greenhouse & Workday forms seamlessly.
        </p>

        {/* Primary Auth Actions */}
        <div className="max-w-xl mx-auto mb-16 space-y-4">
          <button
            onClick={onGoogleLogin}
            className="w-full flex items-center justify-center gap-3 px-8 py-5 rounded-2xl bg-lime-400 text-slate-950 font-black text-sm tracking-wider uppercase shadow-2xl shadow-lime-400/30 hover:bg-lime-300 hover:scale-[1.01] transition-all"
          >
            <Zap className="h-5 w-5 fill-slate-950" />
            <span>1-Click Authenticate with Google</span>
            <ArrowRight className="h-4 w-4" />
          </button>

          {/* 1-Click Code Paste Drawer (Fix for screenshot 3) */}
          <form onSubmit={handleCodeSubmit} className="cyber-panel p-4 rounded-2xl border border-lime-400/20 text-left">
            <label className="text-[11px] font-mono text-lime-400 block mb-1 flex items-center gap-1.5">
              <Key className="h-3.5 w-3.5" />
              <span>PASTE GOOGLE AUTHORIZATION CODE BELOW:</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={manualCode}
                onChange={(e) => setManualCode(e.target.value)}
                placeholder="e.g. 4/1AXEQxIde_Eu8v2qM72ng-..."
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
              />
              <button
                type="submit"
                disabled={isSubmittingCode}
                className="px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs font-bold transition-all"
              >
                {isSubmittingCode ? "VERIFYING..." : "SUBMIT CODE"}
              </button>
            </div>
            {codeError && <p className="text-[10px] text-rose-400 font-mono mt-1">{codeError}</p>}
          </form>
        </div>

        {/* Animated Cyber Terminal Simulator */}
        <div className="max-w-5xl mx-auto rounded-2xl p-1 cyber-panel border border-lime-400/30 shadow-2xl overflow-hidden">
          <div className="bg-[#090d16] rounded-xl p-6 text-left font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-rose-500 inline-block" />
                <span className="h-3 w-3 rounded-full bg-amber-500 inline-block" />
                <span className="h-3 w-3 rounded-full bg-lime-400 inline-block" />
                <span className="text-xs text-slate-400 ml-2">mew-engine://live-telemetry</span>
              </div>
              <span className="text-[10px] text-lime-400 border border-lime-400/30 px-2 py-0.5 rounded-full">
                [POSTMESSAGE_DATAURL_ATTACHMENT]
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <p className="text-slate-500">[17:35:01] &gt; Initiating MEW Autofill sequence on boards.greenhouse.io...</p>
              <p className="text-sky-400">[17:35:01] &gt; Stripping country code: +917892568001 -&gt; 7892568001</p>
              <p className="text-purple-400">[17:35:02] &gt; Broadcasting DataURL stream via postMessage to iframe child frame...</p>
              <p className="neon-lime-text font-bold">[17:35:02] &gt; SUCCESS: Resume.pdf attached natively to &lt;input type="file"&gt;</p>
            </div>
          </div>
        </div>
      </section>

      {/* ATS Compatibility Badges */}
      <section className="py-10 border-y border-slate-800/80 bg-slate-900/40">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-[11px] font-mono text-slate-500 uppercase tracking-widest mb-6">
            // NATIVE ATS COMPATIBILITY MATRIX
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8 text-xs font-mono font-bold text-slate-300">
            <span className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">[GREENHOUSE]</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">[LEVER]</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">[WORKDAY]</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">[LINKEDIN]</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">[BAMBOOHR]</span>
          </div>
        </div>
      </section>
    </div>
  );
}
