"use client";

import { useState } from "react";
import { X, Mail, Send, CheckCircle2, UserCheck, Sparkles } from "lucide-react";

export default function HrVerificationModal({ isOpen, onClose, emailDraft, onConfirmSend }) {
  const [hrName, setHrName] = useState(emailDraft?.hr_recruiter_name || "AlphaGrep Talent Acquisition Team");
  const [hrEmail, setHrEmail] = useState(emailDraft?.hr_recruiter_email || "careers@alpha-grep.com");
  const [isSending, setIsSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState(false);

  if (!isOpen || !emailDraft) return null;

  const handleSend = async (e) => {
    e.preventDefault();
    setIsSending(true);
    try {
      await onConfirmSend({
        ...emailDraft,
        hr_name: hrName,
        hr_email: hrEmail,
      });
      setSendSuccess(true);
      setTimeout(() => {
        setSendSuccess(false);
        onClose();
      }, 2000);
    } catch (err) {
      alert("Failed to dispatch Gmail: " + err.message);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
      <div className="relative max-w-lg w-full cyber-panel p-6 rounded-2xl border border-lime-400/40 shadow-2xl text-left">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-lime-400 text-slate-950 flex items-center justify-center font-black">
            <UserCheck className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-black uppercase text-slate-100 tracking-wide">
              HR Recruiter Verification
            </h3>
            <p className="text-[10px] font-mono text-lime-400">
              [VERIFY_RECRUITER_CONTACT_BEFORE_DISPATCH]
            </p>
          </div>
        </div>

        <form onSubmit={handleSend} className="space-y-4">
          <div>
            <label className="text-xs font-mono text-slate-300 block mb-1 font-bold">
              RECRUITER / TALENT LEAD NAME
            </label>
            <input
              type="text"
              value={hrName}
              onChange={(e) => setHrName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-lime-400/60"
            />
          </div>

          <div>
            <label className="text-xs font-mono text-slate-300 block mb-1 font-bold">
              VERIFIED HR RECRUITER EMAIL ADDRESS
            </label>
            <input
              type="email"
              value={hrEmail}
              onChange={(e) => setHrEmail(e.target.value)}
              placeholder="e.g. hr@company.com"
              required
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-mono text-lime-400 focus:outline-none focus:border-lime-400/60"
            />
          </div>

          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] font-mono text-slate-500 block mb-1">SUBJECT PREVIEW:</span>
            <p className="text-xs text-slate-300 font-mono font-semibold">{emailDraft.subject}</p>
          </div>

          {sendSuccess ? (
            <div className="p-3 rounded-xl bg-lime-400/10 border border-lime-400/40 text-lime-400 font-mono text-xs text-center flex items-center justify-center gap-2 font-bold">
              <CheckCircle2 className="h-4 w-4" />
              <span>[GMAIL_OAUTH_DISPATCH_SUCCESSFUL]</span>
            </div>
          ) : (
            <button
              type="submit"
              disabled={isSending}
              className="w-full py-3.5 rounded-xl bg-lime-400 hover:bg-lime-300 text-slate-950 font-mono font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-lime-400/25 transition-all"
            >
              <Send className="h-4 w-4" />
              <span>{isSending ? "DISPATCHING GMAIL..." : "CONFIRM & SEND NOW VIA GMAIL OAUTH"}</span>
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
