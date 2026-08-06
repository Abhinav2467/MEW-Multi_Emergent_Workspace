"use client";

import { CheckCircle2, Clock, Globe, Briefcase } from "lucide-react";

export default function ApplicationTracker({ applications = [] }) {
  const sampleApps = applications.length > 0 ? applications : [
    {
      id: "app_8f29",
      company_name: "AlphaGrep",
      job_title: "Quantitative AI & Full Stack Engineer",
      timestamp: "2026-07-29T10:30:00Z",
      status: "Submitted",
      portal: "Greenhouse iFrame",
    },
    {
      id: "app_9a11",
      company_name: "Electrovese Solutions",
      job_title: "Agentic Systems Developer",
      timestamp: "2026-07-28T16:45:00Z",
      status: "Interviewing",
      portal: "Workday / Direct",
    },
  ];

  return (
    <div className="glass-panel p-6 rounded-2xl border border-slate-800 my-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-emerald-400" />
            <span>Submitted Applications Tracker</span>
          </h3>
          <p className="text-xs text-slate-400">
            Real-time status of applications filled by MEW extension
          </p>
        </div>
        <span className="text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full">
          {sampleApps.length} Tracked Applications
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-mono">
              <th className="pb-3 px-3">Company</th>
              <th className="pb-3 px-3">Position</th>
              <th className="pb-3 px-3">Portal Type</th>
              <th className="pb-3 px-3">Submitted At</th>
              <th className="pb-3 px-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {sampleApps.map((app) => (
              <tr key={app.id} className="hover:bg-slate-900/40 transition-colors">
                <td className="py-3 px-3 font-semibold text-slate-200">{app.company_name}</td>
                <td className="py-3 px-3 text-slate-300">{app.job_title}</td>
                <td className="py-3 px-3 text-slate-400 font-mono flex items-center gap-1">
                  <Globe className="h-3 w-3 text-sky-400" /> {app.portal}
                </td>
                <td className="py-3 px-3 text-slate-400 font-mono">
                  {new Date(app.timestamp).toLocaleString()}
                </td>
                <td className="py-3 px-3 text-right">
                  <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 rounded-full font-mono text-[10px]">
                    <CheckCircle2 className="h-3 w-3" /> {app.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
