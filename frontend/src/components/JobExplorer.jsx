import { useState } from "react";
import { Zap, ExternalLink, Building2, MapPin, Award, RefreshCw, Mail, Loader2 } from "lucide-react";
import ColdEmailPopupModal from "@/components/ColdEmailPopupModal";

export default function JobExplorer({ jobs = [], onRefreshJobs, onDraftEmail, onSaveDraft }) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [draftingJobId, setDraftingJobId] = useState(null);
  const [activeDraft, setActiveDraft] = useState(null);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    if (onRefreshJobs) {
      await onRefreshJobs();
    }
    setIsRefreshing(false);
  };

  const handleDraftClick = async (job) => {
    setDraftingJobId(job.id);
    try {
      const draft = await onDraftEmail(job.company_name, job.position, job.location);
      setActiveDraft(draft);
    } catch (err) {
      alert("Failed to draft email: " + err.message);
    } finally {
      setDraftingJobId(null);
    }
  };

  const sampleJobs = jobs.length > 0 ? jobs : [
    {
      id: "j_1",
      company_name: "AlphaGrep Technologies",
      position: "Quantitative AI & Full Stack Engineer",
      matching_percentage: 98,
      location: "Bengaluru, India (Hybrid)",
      apply_link: "https://www.alpha-grep.com/career-opportunity/?jid=8622142002",
      posted_hours_ago: 2,
    },
    {
      id: "j_2",
      company_name: "Electrovese Solutions",
      position: "Senior Agentic AI Systems Architect",
      matching_percentage: 94,
      location: "Remote / India",
      apply_link: "https://www.alpha-grep.com/career-opportunity/?jid=8622142002",
      posted_hours_ago: 5,
    },
    {
      id: "j_3",
      company_name: "DeepMind Tech Labs",
      position: "Full Stack Engineer (Next.js & Python)",
      matching_percentage: 91,
      location: "Bengaluru, India",
      apply_link: "https://www.alpha-grep.com/career-opportunity/?jid=8622142002",
      posted_hours_ago: 12,
    },
  ];

  return (
    <div className="cyber-panel p-6 rounded-2xl border border-lime-400/20 my-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-sm font-black text-slate-100 flex items-center gap-2 uppercase tracking-wide">
            <Zap className="h-4 w-4 text-amber-400" />
            <span>AI JOB RECENCY &amp; MATCH EXPLORER</span>
          </h3>
          <p className="text-xs font-mono text-slate-400 mt-0.5">
            Real-time candidate skill matching sorted by recency
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-lime-400/10 hover:bg-lime-400/20 text-lime-400 border border-lime-400/30 text-xs font-mono font-bold transition-all"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>{isRefreshing ? "[FETCHING_LIVE_JOBS...]" : "🔄 REFRESH LIVE JOB MATCHES"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {sampleJobs.map((job) => (
          <div
            key={job.id}
            className="cyber-panel p-5 rounded-xl border border-slate-800 hover:border-lime-400/40 transition-all flex flex-col justify-between group"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="flex items-center gap-1 text-[11px] font-mono font-bold text-lime-400 bg-lime-400/10 border border-lime-400/30 px-2 py-0.5 rounded-full">
                  <Award className="h-3 w-3" /> {job.matching_percentage}% MATCH
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  ⚡ {job.posted_hours_ago || 2}h ago
                </span>
              </div>

              <h4 className="text-xs font-bold text-slate-100 mb-1 group-hover:text-lime-400 transition-colors">
                {job.position}
              </h4>
              <p className="text-[11px] text-slate-400 flex items-center gap-1 mb-2">
                <Building2 className="h-3 w-3 text-slate-500" /> {job.company_name}
              </p>
              <p className="text-[10px] text-slate-500 flex items-center gap-1 mb-4 font-mono">
                <MapPin className="h-3 w-3 text-slate-600" /> {job.location}
              </p>
            </div>

            {/* DUAL ACTION BUTTONS */}
            <div className="space-y-2 pt-2 border-t border-slate-800/80">
              <a
                href={job.apply_link}
                target="_blank"
                rel="noreferrer"
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-lime-400 text-slate-950 text-xs font-black uppercase transition-all hover:bg-lime-300"
              >
                <span>⚡ Autofill Application</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>

              <button
                onClick={() => handleDraftClick(job)}
                disabled={draftingJobId === job.id}
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 text-xs font-mono font-bold transition-all"
              >
                {draftingJobId === job.id ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
                    <span>DRAFTING EMAIL...</span>
                  </>
                ) : (
                  <>
                    <Mail className="h-3.5 w-3.5 text-purple-400" />
                    <span>✉️ Draft AI Cold Email</span>
                  </>
                )}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* AI Cold Email Popup Modal */}
      <ColdEmailPopupModal
        isOpen={Boolean(activeDraft)}
        onClose={() => setActiveDraft(null)}
        emailDraft={activeDraft}
        onRedraft={(company, role, location, isRegen, hrName, hrEmail) => onDraftEmail(company, role, location, isRegen, hrName, hrEmail)}
        onSaveDraft={onSaveDraft}
      />
    </div>
  );
}
