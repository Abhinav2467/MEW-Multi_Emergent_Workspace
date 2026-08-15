"use client";

import { useState, useRef, useEffect } from "react";
import { Upload, RefreshCw, Save, FileText, CheckCircle2, User, Mail, Phone, MapPin, Briefcase } from "lucide-react";

export default function ResumeStudio({ profile, onUpdateProfile, onRescanResume, onUploadPdf }) {
  const fileInputRef = useRef(null);

  const getProfileField = (key, fallback = "") => {
    if (!profile) return fallback;
    if (profile.personal && profile.personal[key]) return profile.personal[key];
    if (profile.professional && profile.professional[key]) return profile.professional[key];
    if (profile.parsed_profile?.contact && profile.parsed_profile.contact[key]) return profile.parsed_profile.contact[key];
    if (profile.contact && profile.contact[key]) return profile.contact[key];
    if (profile[key]) return profile[key];
    return fallback;
  };

  const [formData, setFormData] = useState({
    name: getProfileField("full_name") || getProfileField("name") || "Jeet Sarkar",
    email: getProfileField("email") || "jeetsarkar.dev@gmail.com",
    phone: getProfileField("phone") || "+917439761527",
    location: getProfileField("location") || "Bengaluru, India",
    current_title: getProfileField("current_title") || "Full Stack AI Engineer",
    github_url: getProfileField("github_url") || getProfileField("github") || "https://github.com/JeetDev2104",
  });

  useEffect(() => {
    if (profile) {
      const pName = profile.personal?.full_name || profile.full_name || profile.name || profile.contact?.full_name || profile.parsed_profile?.contact?.name;
      const pEmail = profile.personal?.email || profile.email || profile.contact?.email || profile.parsed_profile?.contact?.email;
      const pPhone = profile.personal?.phone || profile.phone || profile.contact?.phone || profile.parsed_profile?.contact?.phone;
      const pLoc = profile.personal?.location || profile.location || profile.contact?.location || profile.parsed_profile?.contact?.location;
      const pTitle = profile.professional?.current_title || profile.current_title || profile.current_role || profile.parsed_profile?.current_role;
      const pGithub = profile.personal?.github_url || profile.personal?.github || profile.github_url || profile.github || profile.contact?.github || profile.contact?.github_url || profile.parsed_profile?.contact?.github;

      setFormData((prev) => ({
        name: pName || prev.name,
        email: pEmail || prev.email,
        phone: pPhone || prev.phone,
        location: pLoc || prev.location,
        current_title: pTitle || prev.current_title,
        github_url: pGithub || prev.github_url,
      }));
    }
  }, [profile]);

  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRescanning, setIsRescanning] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [fileName, setFileName] = useState(profile?.resume_filename || "Jeet_Sarkar_Resume.pdf");

  const handleChange = (field, val) => {
    setFormData((prev) => ({ ...prev, [field]: val }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdateProfile(formData);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Save profile error:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRescan = async () => {
    setIsRescanning(true);
    await onRescanResume();
    setIsRescanning(false);
  };

  const processFile = async (file) => {
    if (!file || !file.name.endsWith(".pdf")) return;
    setIsUploading(true);
    setFileName(file.name);
    try {
      const data = await onUploadPdf(file);
      if (data?.data) {
        const p = data.data.personal || data.data;
        const pro = data.data.professional || data.data;
        setFormData({
          name: p.full_name || p.name || data.data.name || "Candidate",
          email: p.email || data.data.email || "",
          phone: p.phone || data.data.phone || "",
          location: p.location || data.data.location || "Bengaluru, India",
          current_title: pro.current_title || data.data.current_title || "Full Stack AI Engineer",
          github_url: p.github_url || p.github || data.data.github_url || data.data.github || "",
        });
      }
    } catch (err) {
      console.error("Failed to process PDF:", err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 my-8">
      {/* Hidden PDF File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf"
        className="hidden"
      />

      {/* Left Pane: Drag-and-Drop Dropzone & Resume Status */}
      <div className="lg:col-span-5 cyber-panel p-6 rounded-2xl border border-lime-400/20 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-mono font-bold text-slate-200 uppercase flex items-center gap-2 tracking-wide">
              <FileText className="h-4 w-4 text-lime-400" />
              <span>Resume Attachment Vault</span>
            </h3>
            <span className="text-[10px] font-mono bg-lime-400/10 text-lime-400 border border-lime-400/30 px-2 py-0.5 rounded-full">
              [DATAURL_ACTIVE]
            </span>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="border-2 border-dashed border-lime-400/30 rounded-xl p-8 text-center hover:border-lime-400/60 transition-all bg-lime-400/5 group cursor-pointer"
          >
            <div className="h-12 w-12 rounded-full bg-lime-400/10 text-lime-400 flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
              <Upload className={`h-6 w-6 ${isUploading ? "animate-bounce" : ""}`} />
            </div>
            <p className="text-xs font-bold text-slate-200 mb-1">
              {isUploading ? "[PARSING_WITH_GEMINI_AI...]" : "Drop new Resume PDF here or click to browse"}
            </p>
            <p className="text-[10px] text-slate-400 font-mono">
              Auto-syncs across cross-origin extension memory &amp; top windows
            </p>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-lime-400" />
            <span className="text-xs text-slate-300 font-mono truncate max-w-[180px]">{fileName}</span>
          </div>
          <button
            onClick={handleRescan}
            disabled={isRescanning}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono font-medium text-slate-200 border border-slate-700 transition-all"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-lime-400 ${isRescanning ? "animate-spin" : ""}`} />
            <span>{isRescanning ? "RESCANNING..." : "RESCAN GEMINI"}</span>
          </button>
        </div>
      </div>

      {/* Right Pane: Live Profile Cards Editor */}
      <div className="lg:col-span-7 cyber-panel p-6 rounded-2xl border border-lime-400/20">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xs font-mono font-bold text-slate-200 uppercase flex items-center gap-2 tracking-wide">
              <User className="h-4 w-4 text-purple-400" />
              <span>Candidate Profile Hub</span>
            </h3>
            <p className="text-[10px] font-mono text-slate-400">
              Synced directly to Extension Memory &amp; profile.json
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-lime-400 text-slate-950 font-black text-xs uppercase shadow-lg shadow-lime-400/20 hover:bg-lime-300 transition-all"
          >
            {saveSuccess ? (
              <>
                <CheckCircle2 className="h-4 w-4" />
                <span>SAVED &amp; SYNCED!</span>
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                <span>{isSaving ? "SAVING..." : "SAVE & SYNC MEMORY"}</span>
              </>
            )}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1">
              <User className="h-3 w-3 text-lime-400" /> Full Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange("name", e.target.value)}
              placeholder="e.g. Jeet Sarkar"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1">
              <Mail className="h-3 w-3 text-purple-400" /> Email Address
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => handleChange("email", e.target.value)}
              placeholder="e.g. jeetsarkar.dev@gmail.com"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1">
              <Phone className="h-3 w-3 text-amber-400" /> Phone Number (National)
            </label>
            <input
              type="text"
              value={formData.phone}
              onChange={(e) => handleChange("phone", e.target.value)}
              placeholder="e.g. +917439761527"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1">
              <MapPin className="h-3 w-3 text-lime-400" /> Primary Location
            </label>
            <input
              type="text"
              value={formData.location}
              onChange={(e) => handleChange("location", e.target.value)}
              placeholder="e.g. Bengaluru, India"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
            />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1">
              <Briefcase className="h-3 w-3 text-purple-400" /> Primary Title
            </label>
            <input
              type="text"
              value={formData.current_title}
              onChange={(e) => handleChange("current_title", e.target.value)}
              placeholder="e.g. Full Stack AI Engineer"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
            />
          </div>

          <div>
            <label className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1">
              <FileText className="h-3 w-3 text-lime-400" /> GitHub Profile URL
            </label>
            <input
              type="text"
              value={formData.github_url || ""}
              onChange={(e) => handleChange("github_url", e.target.value)}
              placeholder="https://github.com/username"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-lime-400/50"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
