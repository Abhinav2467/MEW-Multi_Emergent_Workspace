"use client";

import { useState } from "react";
import { Mail, RefreshCw, Send, Sparkles, Check, FileText } from "lucide-react";

export default function EmailStudio({ emailDraft, onRegenerate, onOpenSendModal }) {
  const [subject, setSubject] = useState(emailDraft?.subject || "");
  const [body, setBody] = useState(emailDraft?.body || "");
  const [isRegenerating, setIsRegenerating] = useState(false);

  if (!emailDraft) return null;

  const handleRegenerateClick = async () => {
    setIsRegenerating(true);
    if (onRegenerate) {
      const newDraft = await onRegenerate(emailDraft.company_name, emailDraft.position);
      if (newDraft) {
        setSubject(newDraft.subject || subject);
        setBody(newDraft.body || body);
      }
    }
    setIsRegenerating(false);
  };

  return (
    <div className="cyber-panel p-6 rounded-2xl border border-purple-500/30 my-6 text-left">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/30 flex items-center justify-center font-bold">
            <Mail className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-black uppercase text-slate-100 tracking-wide flex items-center gap-2">
              <span>AI COLD EMAIL STUDIO</span>
              <span className="text-[10px] font-mono text-purple-400 bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 rounded-full">
                [{emailDraft.company_name} // {emailDraft.position}]
              </span>
            </h4>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRegenerateClick}
            disabled={isRegenerating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-mono border border-slate-800 transition-all"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-purple-400 ${isRegenerating ? "animate-spin" : ""}`} />
            <span>{isRegenerating ? "REGENERATING..." : "🔄 REGENERATE EMAIL"}</span>
          </button>

          <button
            onClick={() => onOpenSendModal({ ...emailDraft, subject, body })}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-lime-400 hover:bg-lime-300 text-slate-950 font-black font-mono text-xs uppercase transition-all shadow-lg shadow-lime-400/20"
          >
            <Send className="h-3.5 w-3.5" />
            <span>🚀 SEND EMAIL VIA GMAIL OAUTH</span>
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-[11px] font-mono text-slate-400 mb-1 block">
            EMAIL SUBJECT LINE
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-mono text-lime-400 focus:outline-none focus:border-purple-500/50"
          />
        </div>

        <div>
          <label className="text-[11px] font-mono text-slate-400 mb-1 block">
            PERSONALIZED COLD EMAIL BODY
          </label>
          <textarea
            rows={8}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-purple-500/50 leading-relaxed"
          />
        </div>
      </div>
    </div>
  );
}
