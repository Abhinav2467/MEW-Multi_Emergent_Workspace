"use client";

import { Zap, Shield, LogIn, User, LogOut, Terminal } from "lucide-react";

export default function Navbar({ user, onGoogleLogin, onLogout, isExtensionConnected }) {
  return (
    <header className="sticky top-0 z-50 cyber-panel border-b border-lime-400/20 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <a href="/" className="flex items-center gap-3 group">
          <div className="h-10 w-10 rounded-xl bg-lime-400 text-slate-950 p-0.5 shadow-lg shadow-lime-400/20 flex items-center justify-center font-black group-hover:scale-105 transition-transform">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tighter uppercase gradient-title">
              MEW_SYSTEMS
            </h1>
            <p className="text-[10px] font-mono text-lime-400 tracking-wider">
              [SYS_AGENTIC_AUTOFILL_v2.0]
            </p>
          </div>
        </a>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono border bg-lime-400/10 border-lime-400/30 text-lime-400">
            <span className="h-2 w-2 rounded-full bg-lime-400 animate-ping" />
            <span>[EXT_MEMORY_SYNCED]</span>
          </div>

          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-3 cyber-panel-purple px-3.5 py-1.5 rounded-xl border border-purple-500/40">
                <div className="h-7 w-7 rounded-full bg-purple-500 text-slate-950 flex items-center justify-center font-black text-xs">
                  {user.name ? user.name.charAt(0) : "C"}
                </div>
                <div className="text-left hidden md:block">
                  <p className="text-xs font-bold text-slate-100">{user.name || user.email || "Candidate"}</p>
                  <p className="text-[10px] text-lime-400 font-mono">
                    [OAUTH_VAULT_ACTIVE]
                  </p>
                </div>
              </div>
              <button
                onClick={onLogout}
                title="Sign Out"
                className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onGoogleLogin}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-lime-400 text-slate-950 font-black text-xs tracking-wide shadow-lg shadow-lime-400/25 hover:bg-lime-300 transition-all hover:scale-[1.02] active:scale-[0.98] uppercase"
            >
              <LogIn className="h-4 w-4" />
              <span>Login with Google</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
