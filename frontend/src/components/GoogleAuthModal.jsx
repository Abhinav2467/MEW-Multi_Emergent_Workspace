"use client";

import { useState } from "react";
import { X, Key, Zap, Shield, ArrowRight } from "lucide-react";

export default function GoogleAuthModal({ isOpen, onClose, onGoogleLogin, onManualCodeSubmit }) {
  const [authCode, setAuthCode] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  if (!isOpen) return null;

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    if (!authCode.trim()) return;
    setIsVerifying(true);
    setErrorMsg(null);
    try {
      await onManualCodeSubmit(authCode.trim());
      onClose();
    } catch (err) {
      setErrorMsg(err.message || "Invalid Google Authorization Code");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="relative max-w-md w-full cyber-panel p-6 rounded-2xl border border-lime-400/40 shadow-2xl text-left">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-lime-400 text-slate-950 flex items-center justify-center font-black">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-black uppercase text-slate-100 tracking-wide">
              Google OAuth Vault
            </h3>
            <p className="text-[10px] font-mono text-lime-400">
              [PERSISTENT_REFRESH_TOKEN_VAULT]
            </p>
          </div>
        </div>

        {/* Step 1: Open Google Window */}
        <div className="mb-6 pb-6 border-b border-slate-800">
          <label className="text-xs font-mono text-slate-300 block mb-2 font-bold">
            STEP 1: OPEN GOOGLE PERMISSION WINDOW
          </label>
          <button
            onClick={onGoogleLogin}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-lime-400 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg shadow-lime-400/20 hover:bg-lime-300 transition-all"
          >
            <Zap className="h-4 w-4 fill-slate-950" />
            <span>Open Google Login Window</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {/* Step 2: Paste Authorization Code */}
        <form onSubmit={handleVerifyCode}>
          <label className="text-xs font-mono text-slate-300 block mb-2 font-bold flex items-center gap-1.5">
            <Key className="h-3.5 w-3.5 text-lime-400" />
            <span>STEP 2: PASTE AUTHORIZATION CODE</span>
          </label>
          <p className="text-[11px] text-slate-400 mb-3">
            Copy the code displayed on Google&apos;s page (`4/1AXEQ...`) and paste it below:
          </p>
          <div className="space-y-3">
            <input
              type="text"
              value={authCode}
              onChange={(e) => setAuthCode(e.target.value)}
              placeholder="e.g. 4/1AXEQxIde_Eu8v2qM72ng-..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-100 focus:outline-none focus:border-lime-400/60"
            />
            <button
              type="submit"
              disabled={isVerifying}
              className="w-full py-3 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-mono font-bold text-xs uppercase tracking-wider transition-all"
            >
              {isVerifying ? "VERIFYING CODE..." : "VERIFY & LOG IN"}
            </button>
          </div>
          {errorMsg && (
            <p className="text-xs text-rose-400 font-mono mt-2">{errorMsg}</p>
          )}
        </form>
      </div>
    </div>
  );
}
