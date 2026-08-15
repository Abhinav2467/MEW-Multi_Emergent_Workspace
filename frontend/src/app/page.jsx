"use client";

import { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import LandingPage from "@/components/LandingPage";
import ResumeStudio from "@/components/ResumeStudio";
import JobExplorer from "@/components/JobExplorer";
import ApplicationTracker from "@/components/ApplicationTracker";
import GoogleAuthModal from "@/components/GoogleAuthModal";
import { Sparkles, Activity, Shield, Zap } from "lucide-react";
import { API_BASE, apiFetch } from "@/lib/api";

export default function Home() {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [isExtensionConnected, setIsExtensionConnected] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Check login session on mount
  useEffect(() => {
    const savedUser = localStorage.getItem("mew_user");
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        setUser({ name: "Candidate", email: "candidate@example.com" });
      }
    }
  }, []);

  // Fetch real profile, jobs, and application logs from FastAPI backend
  useEffect(() => {
    async function loadData() {
      try {
        const pResp = await apiFetch("/api/v1/profile");
        if (pResp.ok) {
          const pData = await pResp.json();
          if (pData?.data) {
            setProfile(pData.data);
          }
        }
      } catch (e) {
        console.warn("Profile fetch fallback:", e);
      }

      try {
        const jResp = await apiFetch("/api/v1/jobs/recency-feed");
        if (jResp.ok) {
          const jData = await jResp.json();
          if (jData?.data) setJobs(jData.data);
        }
      } catch (e) {
        console.warn("Jobs fetch fallback:", e);
      }

      try {
        const aResp = await apiFetch("/api/v1/applications");
        if (aResp.ok) {
          const aData = await aResp.json();
          if (aData?.data) setApplications(aData.data);
        }
      } catch (e) {
        console.warn("Applications fetch fallback:", e);
      }
    }

    loadData();
  }, [user]);

  const handleOpenAuthModal = () => {
    setIsAuthModalOpen(true);
  };

  const handleGoogleLoginWindow = async () => {
    try {
      const resp = await apiFetch("/auth/google");
      if (!resp.ok) throw new Error("Failed to get Google Auth URL");
      const data = await resp.json();
      if (data?.url) {
        window.open(data.url, "_blank");
      }
    } catch (err) {
      alert("Could not initialize Google OAuth: " + err.message);
    }
  };

  const handleManualCodeSubmit = async (code) => {
    const resp = await apiFetch(`/auth/callback?code=${encodeURIComponent(code)}`);
    if (!resp.ok) {
      throw new Error(`OAuth code exchange failed with status ${resp.status}`);
    }
    const data = await resp.json();
    const candidateUser = data?.user || { name: "Candidate", email: "candidate@example.com" };
    
    if (data?.access_token) {
      localStorage.setItem("mew_access_token", data.access_token);
    }
    localStorage.setItem("mew_user", JSON.stringify(candidateUser));
    setUser(candidateUser);
    setIsAuthModalOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("mew_access_token");
    localStorage.removeItem("mew_user");
    setUser(null);
  };

  const handleUploadPdf = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    const resp = await apiFetch("/api/v1/resume/upload", {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) {
      throw new Error(`Upload failed with status ${resp.status}`);
    }
    const data = await resp.json();
    if (data?.data) {
      setProfile(data.data);
      // Sync to browser memory cache & extension
      window.postMessage({ type: "MEW_PROFILE_SYNC", profile: data.data }, "*");
    }
    return data;
  };

  const handleUpdateProfile = async (updatedData) => {
    try {
      const resp = await apiFetch("/api/v1/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedData),
      });

      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        const msg = errorData.detail || "Failed to update profile";
        alert(msg);
        throw new Error(msg);
      }

      const data = await resp.json();
      if (data?.data) {
        setProfile(data.data);
      }
      if (data?.requires_google_reauth) {
        alert(data.message || "Email address updated. Please re-verify with Google Auth to connect Gmail for this email.");
        setIsAuthModalOpen(true);
      }

      // Broadcast memory sync to extension
      window.postMessage({ type: "MEW_PROFILE_SYNC", profile: updatedData }, "*");
    } catch (e) {
      console.warn("Backend sync fallback:", e);
      throw e;
    }
  };

  const handleRescanResume = async () => {
    try {
      const resp = await apiFetch("/api/v1/resume/rescan", { method: "POST" });
      const data = await resp.json();
      if (data?.data) {
        setProfile(data.data);
      }
    } catch (e) {
      console.warn("Rescan fallback:", e);
    }
  };

  const handleRefreshJobs = async () => {
    try {
      const jResp = await apiFetch("/api/v1/jobs/recency-feed");
      if (jResp.ok) {
        const jData = await jResp.json();
        if (jData?.data) setJobs(jData.data);
      }
    } catch (e) {
      console.warn("Refresh jobs fallback:", e);
    }
  };

  const handleDraftEmail = async (companyName, position, location, isRegen = false, hrName = null, hrEmail = null) => {
    const resp = await apiFetch("/api/v1/emails/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: companyName,
        position: position,
        location: location,
        regenerate: isRegen,
        hr_name: hrName,
        hr_email: hrEmail,
      }),
    });
    if (!resp.ok) {
      throw new Error(`Email drafting failed with status ${resp.status}`);
    }
    const data = await resp.json();
    return data.data;
  };

  const handleSaveDraft = async (draftPayload) => {
    const resp = await apiFetch("/api/v1/emails/save-draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draftPayload),
    });
    if (!resp.ok) {
      throw new Error(`Failed to save draft in Gmail with status ${resp.status}`);
    }
    const data = await resp.json();
    return data.data;
  };

  const handleSendEmail = async (emailPayload) => {
    const resp = await apiFetch("/api/v1/emails/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(emailPayload),
    });
    if (!resp.ok) {
      throw new Error(`Email sending failed with status ${resp.status}`);
    }
    return await resp.json();
  };

  // Extract display name cleanly
  const displayName = profile?.personal?.full_name || profile?.full_name || profile?.name || user?.name || "Candidate";

  return (
    <main className="min-h-screen bg-[#08090a] text-slate-100">
      <Navbar
        user={user}
        onGoogleLogin={handleOpenAuthModal}
        onLogout={handleLogout}
        isExtensionConnected={isExtensionConnected}
      />

      <GoogleAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onGoogleLogin={handleGoogleLoginWindow}
        onManualCodeSubmit={handleManualCodeSubmit}
      />

      {!user ? (
        <LandingPage
          onGoogleLogin={handleOpenAuthModal}
          onManualCodeSubmit={handleManualCodeSubmit}
        />
      ) : (
        <div className="max-w-7xl mx-auto px-6 pt-8 pb-16">
          {/* Command Center Dashboard Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="cyber-panel p-4 rounded-xl border border-lime-400/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-slate-400 font-medium">APPLICATIONS LOGGED</span>
                <Activity className="h-4 w-4 text-lime-400" />
              </div>
              <p className="text-2xl font-black text-slate-100">{applications.length}</p>
              <p className="text-[10px] text-lime-400 font-mono mt-1">[LIVE_EXTENSION_SYNC]</p>
            </div>

            <div className="cyber-panel p-4 rounded-xl border border-lime-400/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-slate-400 font-medium">RECENCY MATCHES</span>
                <Zap className="h-4 w-4 text-amber-400" />
              </div>
              <p className="text-2xl font-bold text-slate-100">{jobs.length || 3}</p>
              <p className="text-[10px] text-amber-400 font-mono mt-1">⚡ Posted &lt; 12h ago</p>
            </div>

            <div className="cyber-panel p-4 rounded-xl border border-lime-400/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-slate-400 font-medium">PROFILE STATUS</span>
                <Sparkles className="h-4 w-4 text-purple-400" />
              </div>
              <p className="text-2xl font-bold text-slate-100">100%</p>
              <p className="text-[10px] text-purple-400 font-mono mt-1">[GEMINI_PARSED: {displayName}]</p>
            </div>

            <div className="cyber-panel p-4 rounded-xl border border-lime-400/20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-slate-400 font-medium">OAUTH REFRESH VAULT</span>
                <Shield className="h-4 w-4 text-lime-400" />
              </div>
              <p className="text-2xl font-bold text-slate-100">Active</p>
              <p className="text-[10px] text-lime-400 font-mono mt-1">[OFFLINE_TOKENS_STORED]</p>
            </div>
          </div>

          {/* Section 1: Resume Studio & Profile Hub */}
          <ResumeStudio
            profile={profile}
            onUpdateProfile={handleUpdateProfile}
            onRescanResume={handleRescanResume}
            onUploadPdf={handleUploadPdf}
          />

          {/* Section 2: AI Job Recency Match Explorer with Dual Buttons & Email Drafting */}
          <JobExplorer
            jobs={jobs}
            onRefreshJobs={handleRefreshJobs}
            onDraftEmail={handleDraftEmail}
            onSaveDraft={handleSaveDraft}
            onSendEmail={handleSendEmail}
          />

          {/* Section 3: Applications Tracker */}
          <ApplicationTracker applications={applications} />
        </div>
      )}
    </main>
  );
}
