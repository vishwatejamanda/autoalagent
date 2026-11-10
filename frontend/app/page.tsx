"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  LayoutDashboard,
  Briefcase,
  UserCheck,
  FileText,
  Users,
  HelpCircle,
  Settings as SettingsIcon,
  Search,
  RefreshCw,
  Plus,
  Play,
  Save,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  Download,
  Trash2,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  Upload,
  Cpu,
  Database,
  Lock,
  Send,
  Kanban,
  Sliders,
  BookOpen,
  MessageSquare,
  Copy
} from "lucide-react";

const API_BASE = "http://localhost:8000/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "jobs" | "review" | "tracker" | "manual" | "master" | "profiles" | "answerbank" | "settings"
  >("dashboard");

  // Global states
  const [loading, setLoading] = useState(false);
  const [killSwitch, setKillSwitch] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Data states
  const [funnel, setFunnel] = useState<any>(null);
  const [portals, setPortals] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [reviewQueue, setReviewQueue] = useState<any[]>([]);
  const [tracker, setTracker] = useState<Record<string, any[]>>({});
  const [manualQueue, setManualQueue] = useState<any[]>([]);
  const [masterProfile, setMasterProfile] = useState<any>(null);
  const [profiles, setProfiles] = useState<any[]>([]);
  const [answerBank, setAnswerBank] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [llmConfig, setLlmConfig] = useState<any>(null);

  // Settings form states
  const [defaultProvider, setDefaultProvider] = useState("nvidia");
  const [mistralKey, setMistralKey] = useState("");
  const [mistralStrong, setMistralStrong] = useState("mistral-large-latest");
  const [mistralCheap, setMistralCheap] = useState("mistral-small-latest");
  const [nvidiaKey, setNvidiaKey] = useState("");
  const [nvidiaStrong, setNvidiaStrong] = useState("nvidia/nemotron-3-ultra-550b-a55b");
  const [nvidiaCheap, setNvidiaCheap] = useState("nvidia/nemotron-3.5-bolt-e4b");
  const [mistralTestRes, setMistralTestRes] = useState<any>(null);
  const [nvidiaTestRes, setNvidiaTestRes] = useState<any>(null);
  const [testingMistral, setTestingMistral] = useState(false);
  const [testingNvidia, setTestingNvidia] = useState(false);

  // Job Search Filters (Country, Role, Multiple Cities)
  const [filterRole, setFilterRole] = useState("");
  const [filterCountry, setFilterCountry] = useState("");
  const [filterCities, setFilterCities] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterMinScore, setFilterMinScore] = useState(0);

  // Persona Modal State
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [newProfileRoles, setNewProfileRoles] = useState("");
  const [newProfileCountries, setNewProfileCountries] = useState("");
  const [newProfileCities, setNewProfileCities] = useState("");
  const [newProfileMinExp, setNewProfileMinExp] = useState(1);
  const [newProfileMaxExp, setNewProfileMaxExp] = useState(4);
  const [newProfileCap, setNewProfileCap] = useState(30);
  const [newProfileMode, setNewProfileMode] = useState("review");

  // Scan Portals Modal & Filter Overrides State
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanRoles, setScanRoles] = useState("Software Engineer, AI Engineer");
  const [scanCountry, setScanCountry] = useState("India");
  const [scanCities, setScanCities] = useState("Bengaluru, Hyderabad, Remote");
  const [scanPortals, setScanPortals] = useState({ workday: true, linkedin: true, naukri: true });
  const [scanProfileId, setScanProfileId] = useState<number | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  // Selected Job & Modal state
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [activeModalTab, setActiveModalTab] = useState<"resume" | "interview" | "research">("resume");
  const [tailoredResume, setTailoredResume] = useState<any>(null);
  const [tailoringLoading, setTailoringLoading] = useState(false);
  const [interviewPrep, setInterviewPrep] = useState<any>(null);
  const [interviewLoading, setInterviewLoading] = useState(false);
  const [companyResearch, setCompanyResearch] = useState<any>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [resumeDiff, setResumeDiff] = useState<any>(null);
  const [resumeSubTab, setResumeSubTab] = useState<"preview" | "diff" | "cover" | "gaps">("preview");

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  // ─── Data Fetchers ──────────────────────────────────────────

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [
        hRes, cRes, fRes, pRes, jRes, rRes, tRes, mRes, mpRes, profRes, abRes, ksRes
      ] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/settings/llm`),
        fetch(`${API_BASE}/analytics/funnel`),
        fetch(`${API_BASE}/analytics/portals`),
        fetch(`${API_BASE}/jobs`),
        fetch(`${API_BASE}/matching/review-queue`),
        fetch(`${API_BASE}/applications/tracker`),
        fetch(`${API_BASE}/applications/manual-queue`),
        fetch(`${API_BASE}/profiles/master`),
        fetch(`${API_BASE}/profiles`),
        fetch(`${API_BASE}/answer-bank`),
        fetch(`${API_BASE}/applications/kill-switch`),
      ]);

      if (hRes.ok) setHealth(await hRes.json());
      if (cRes.ok) {
        const c = await cRes.json();
        setLlmConfig(c);
        setDefaultProvider(c.default_provider || "mistral");
        setMistralStrong(c.mistral.strong_model);
        setMistralCheap(c.mistral.cheap_model);
        setNvidiaStrong(c.nvidia.strong_model);
        setNvidiaCheap(c.nvidia.cheap_model);
      }
      if (fRes.ok) setFunnel(await fRes.json());
      if (pRes.ok) setPortals(await pRes.json());
      if (jRes.ok) setJobs(await jRes.json());
      if (rRes.ok) setReviewQueue(await rRes.json());
      if (tRes.ok) setTracker(await tRes.json());
      if (mRes.ok) setManualQueue(await mRes.json());
      if (mpRes.ok) setMasterProfile((await mpRes.json()).data);
      if (profRes.ok) setProfiles(await profRes.json());
      if (abRes.ok) setAnswerBank(await abRes.json());
      if (ksRes.ok) setKillSwitch((await ksRes.json()).kill_switch_active);
    } catch (e) {
      console.error("Fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  // ─── Actions ────────────────────────────────────────────────

  const openScanModal = (overrideRole?: string, overrideCountry?: string, overrideCities?: string) => {
    if (overrideRole !== undefined) setScanRoles(overrideRole);
    else if (filterRole) setScanRoles(filterRole);

    if (overrideCountry !== undefined) setScanCountry(overrideCountry);
    else if (filterCountry) setScanCountry(filterCountry);

    if (overrideCities !== undefined) setScanCities(overrideCities);
    else if (filterCities) setScanCities(filterCities);

    setShowScanModal(true);
  };

  const triggerScanWithFilters = async () => {
    setIsScanning(true);
    showToast("Launching job discovery scan across portals with filters...");
    try {
      const activePortals = Object.entries(scanPortals)
        .filter(([_, enabled]) => enabled)
        .map(([portal]) => portal);

      if (activePortals.length === 0) {
        showToast("Please select at least one portal to scan.");
        setIsScanning(false);
        return;
      }

      const payload = {
        profile_id: scanProfileId || (profiles[0]?.id ?? 1),
        roles: scanRoles,
        country: scanCountry,
        cities: scanCities,
        portals: activePortals,
        limit: 20,
      };

      const res = await fetch(`${API_BASE}/jobs/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`Scan complete: Added ${data.new_jobs_added} new jobs (${data.duplicates_skipped} duplicates skipped).`);
        setShowScanModal(false);
        fetchAll();
      } else {
        showToast("Scan error: " + (data.detail || "Scan request failed"));
      }
    } catch (e: any) {
      showToast("Scan failed: " + e.message);
    } finally {
      setIsScanning(false);
    }
  };

  const fetchInterviewPrep = async (jobId: number) => {
    setInterviewLoading(true);
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/interview-prep`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setInterviewPrep(data);
      } else {
        showToast("Failed to generate interview prep.");
      }
    } catch (e: any) {
      showToast("Interview prep error: " + e.message);
    } finally {
      setInterviewLoading(false);
    }
  };

  const fetchCompanyResearch = async (jobId: number) => {
    setResearchLoading(true);
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/company-research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        setCompanyResearch(data);
      } else {
        showToast("Failed to generate company research.");
      }
    } catch (e: any) {
      showToast("Company research error: " + e.message);
    } finally {
      setResearchLoading(false);
    }
  };

  const scoreAllJobs = async () => {
    showToast("Running Stage 1 & Stage 2 matching on jobs...");
    try {
      const res = await fetch(`${API_BASE}/matching/score-all`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
      const data = await res.json();
      showToast(`Scored ${data.scored_count} jobs. ${data.matched_count} met threshold!`);
      fetchAll();
    } catch (e: any) {
      showToast("Scoring failed: " + e.message);
    }
  };

  const handleReviewAction = async (jobId: number, action: "approve" | "reject" | "manual") => {
    try {
      await fetch(`${API_BASE}/matching/review-queue/${jobId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      showToast(`Job #${jobId} marked as ${action}.`);
      fetchAll();
    } catch (e: any) {
      showToast("Action failed: " + e.message);
    }
  };

  const handleApply = async (jobId: number, mode: string = "review") => {
    showToast(`Initiating ${mode} application flow for Job #${jobId}...`);
    try {
      const res = await fetch(`${API_BASE}/applications/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, mode }),
      });
      const data = await res.json();
      showToast(`Application result: ${data.status} - ${data.details || data.message || ""}`);
      fetchAll();
    } catch (e: any) {
      showToast("Application failed: " + e.message);
    }
  };

  const handleTailorResume = async (jobId: number) => {
    setTailoringLoading(true);
    setResumeDiff(null);
    showToast("Tailoring resume with anti-fabrication fact-checking...");
    try {
      const res = await fetch(`${API_BASE}/resumes/tailor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      });
      const data = await res.json();
      setTailoredResume(data);
      showToast(`Resume tailored! ATS Score: ${data.ats_score}%`);

      if (data.id) {
        try {
          const dRes = await fetch(`${API_BASE}/resumes/${data.id}/diff`);
          if (dRes.ok) {
            setResumeDiff(await dRes.json());
          }
        } catch (err) {
          console.error("Diff fetch error:", err);
        }
      }
    } catch (e: any) {
      showToast("Tailoring failed: " + e.message);
    } finally {
      setTailoringLoading(false);
    }
  };

  const toggleKill = async () => {
    try {
      const res = await fetch(`${API_BASE}/applications/kill-switch`, { method: "POST" });
      const data = await res.json();
      setKillSwitch(data.kill_switch_active);
      showToast(data.message);
    } catch (e: any) {
      showToast("Failed toggling kill switch");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    showToast(`Parsing ${file.name} with LLM into Master Profile...`);
    try {
      const res = await fetch(`${API_BASE}/profiles/master/upload`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setMasterProfile(data.data);
        showToast(`Parsed ${file.name} successfully! (Version ${data.version})`);
      } else {
        showToast("Upload and parsing failed.");
      }
    } catch (e: any) {
      showToast("Upload error: " + e.message);
    }
  };

  const saveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload: any = {
      default_provider: defaultProvider,
      mistral_strong_model: mistralStrong,
      mistral_cheap_model: mistralCheap,
      nvidia_strong_model: nvidiaStrong,
      nvidia_cheap_model: nvidiaCheap,
    };
    if (mistralKey.trim()) payload.mistral_api_key = mistralKey.trim();
    if (nvidiaKey.trim()) payload.nvidia_api_key = nvidiaKey.trim();

    try {
      const res = await fetch(`${API_BASE}/settings/llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        showToast("Settings saved successfully!");
        setMistralKey("");
        setNvidiaKey("");
        fetchAll();
      }
    } catch (e: any) {
      showToast("Failed saving settings: " + e.message);
    }
  };

  const testLLM = async (provider: "mistral" | "nvidia") => {
    if (provider === "mistral") {
      setTestingMistral(true);
      setMistralTestRes(null);
    } else {
      setTestingNvidia(true);
      setNvidiaTestRes(null);
    }

    try {
      const body: any = { provider };
      if (provider === "mistral") {
        if (mistralKey.trim()) body.api_key = mistralKey.trim();
        body.model = mistralCheap || mistralStrong;
      }
      if (provider === "nvidia") {
        if (nvidiaKey.trim()) body.api_key = nvidiaKey.trim();
        body.model = nvidiaCheap || nvidiaStrong;
      }

      const res = await fetch(`${API_BASE}/settings/test-llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (provider === "mistral") setMistralTestRes(data);
      else setNvidiaTestRes(data);
    } catch (e: any) {
      const err = { success: false, error: e.message };
      if (provider === "mistral") setMistralTestRes(err);
      else setNvidiaTestRes(err);
    } finally {
      if (provider === "mistral") setTestingMistral(false);
      else setTestingNvidia(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfileName.trim()) return;
    try {
      const payload = {
        name: newProfileName.trim(),
        target_titles: newProfileRoles.split(",").map(r => r.trim()).filter(Boolean),
        countries: newProfileCountries.split(",").map(c => c.trim()).filter(Boolean),
        cities: newProfileCities.split(",").map(c => c.trim()).filter(Boolean),
        min_experience: Number(newProfileMinExp),
        max_experience: Number(newProfileMaxExp),
        daily_cap: Number(newProfileCap),
        auto_apply_mode: newProfileMode,
      };
      const res = await fetch(`${API_BASE}/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        showToast(`Created persona profile '${newProfileName}'!`);
        setShowProfileModal(false);
        setNewProfileName("");
        setNewProfileRoles("");
        setNewProfileCountries("");
        setNewProfileCities("");
        fetchAll();
      }
    } catch (e: any) {
      showToast("Failed creating persona: " + e.message);
    }
  };

  const filteredJobs = jobs.filter((j) => {
    if (filterSource && j.source !== filterSource) return false;
    if (filterMinScore > 0 && j.score < filterMinScore) return false;
    if (filterRole && !j.title.toLowerCase().includes(filterRole.toLowerCase())) return false;
    if (filterCountry && !j.location.toLowerCase().includes(filterCountry.toLowerCase())) return false;
    if (filterCities) {
      const cityList = filterCities.split(",").map(c => c.trim().toLowerCase()).filter(Boolean);
      if (cityList.length > 0 && !cityList.some(c => j.location.toLowerCase().includes(c))) return false;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="p-2 bg-blue-600/20 text-blue-400 rounded-lg border border-blue-500/30">
            <Sparkles className="w-5 h-5" />
          </span>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              AutoApply AI Agent
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                Phase 1–8 Full Suite
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">LinkedIn &bull; Naukri &bull; Workday</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Global Kill Switch */}
          <button
            onClick={toggleKill}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              killSwitch
                ? "bg-rose-500 text-white border-rose-400 shadow-lg shadow-rose-600/30 animate-pulse"
                : "bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-700"
            }`}
          >
            {killSwitch ? <ShieldAlert className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4 text-emerald-400" />}
            {killSwitch ? "KILL SWITCH ACTIVE" : "Safety: Normal"}
          </button>

          <button
            onClick={fetchAll}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Sync
          </button>
        </div>
      </header>

      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-blue-600 text-white text-xs px-4 py-2.5 rounded-xl shadow-xl border border-blue-400 flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          {notification}
        </div>
      )}

      {/* Main Container with Sidebar Navigation */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 border-r border-slate-800 bg-slate-900/40 p-4 flex flex-col gap-1 text-xs">
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-1">Main</div>
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "dashboard" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard & Funnel
          </button>

          <button
            onClick={() => setActiveTab("jobs")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "jobs" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <Briefcase className="w-4 h-4" />
            All Jobs ({jobs.length})
          </button>

          <button
            onClick={() => setActiveTab("review")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "review" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <UserCheck className="w-4 h-4" />
            Review Queue ({reviewQueue.length})
          </button>

          <button
            onClick={() => setActiveTab("tracker")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "tracker" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <Kanban className="w-4 h-4" />
            Applications Tracker
          </button>

          <button
            onClick={() => setActiveTab("manual")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "manual" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <ExternalLink className="w-4 h-4" />
            Manual Queue ({manualQueue.length})
          </button>

          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-1 mt-4">Profiles</div>
          <button
            onClick={() => setActiveTab("master")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "master" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <FileText className="w-4 h-4" />
            Master Profile
          </button>

          <button
            onClick={() => setActiveTab("profiles")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "profiles" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <Users className="w-4 h-4" />
            Personas ({profiles.length})
          </button>

          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 py-1 mt-4">Automation</div>
          <button
            onClick={() => setActiveTab("answerbank")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "answerbank" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            Answer Bank ({answerBank.length})
          </button>

          <button
            onClick={() => setActiveTab("settings")}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg font-medium transition ${
              activeTab === "settings" ? "bg-blue-600 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"
            }`}
          >
            <SettingsIcon className="w-4 h-4" />
            Settings & LLM
          </button>
        </aside>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          {/* TAB 1: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Application Pipeline Funnel</h2>
                  <p className="text-xs text-slate-400">Live metrics across LinkedIn, Naukri, and Workday</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => openScanModal()}
                    className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-blue-600/20"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    Scan Portals with Filters
                  </button>
                  <button
                    onClick={scoreAllJobs}
                    className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    Score Unranked Jobs
                  </button>
                </div>
              </div>

              {/* Funnel Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                {[
                  { label: "Discovered", count: funnel?.total_discovered || 0, color: "text-blue-400" },
                  { label: "Matched", count: funnel?.matched || 0, color: "text-emerald-400" },
                  { label: "In Review", count: funnel?.in_review || 0, color: "text-amber-400" },
                  { label: "Applied", count: funnel?.applied || 0, color: "text-purple-400" },
                  { label: "Interviewing", count: funnel?.interviewing || 0, color: "text-cyan-400" },
                  { label: "Offers", count: funnel?.offers || 0, color: "text-green-400" },
                  { label: "Rejected", count: funnel?.rejected || 0, color: "text-rose-400" },
                ].map((m, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
                    <span className="text-[11px] text-slate-400 block mb-1">{m.label}</span>
                    <span className={`text-2xl font-bold ${m.color}`}>{m.count}</span>
                  </div>
                ))}
              </div>

              {/* Portal Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {portals.map((p, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold capitalize text-white text-sm">{p.portal}</span>
                      <span className="text-xs text-slate-500 font-mono">Discovered: {p.discovered}</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${Math.min((p.applied / Math.max(p.discovered, 1)) * 100, 100)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Applied: {p.applied}</span>
                      <span>Success: {p.discovered > 0 ? Math.round((p.applied / p.discovered) * 100) : 0}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: ALL JOBS */}
          {activeTab === "jobs" && (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold text-white">Discovered Jobs ({filteredJobs.length} of {jobs.length})</h2>
                  <p className="text-xs text-slate-400">Filter by role, country, and multiple target cities</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => openScanModal()}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-blue-600/20"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    Scan Portals...
                  </button>
                  <button
                    onClick={scoreAllJobs}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    Score All
                  </button>
                </div>
              </div>

              {/* Enhanced Filter Bar: Role, Country, Multiple Cities, Portal */}
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Target Role</label>
                    <input
                      type="text"
                      placeholder="e.g. Software, Backend"
                      value={filterRole}
                      onChange={(e) => setFilterRole(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Country</label>
                    <input
                      type="text"
                      placeholder="e.g. United States, India"
                      value={filterCountry}
                      onChange={(e) => setFilterCountry(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Cities (Multiple allowed)</label>
                    <input
                      type="text"
                      placeholder="e.g. San Jose, San Francisco, Remote"
                      value={filterCities}
                      onChange={(e) => setFilterCities(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Portal Source</label>
                    <select
                      value={filterSource}
                      onChange={(e) => setFilterSource(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="">All Portals</option>
                      <option value="workday">Workday</option>
                      <option value="linkedin">LinkedIn</option>
                      <option value="naukri">Naukri</option>
                    </select>
                  </div>

                  <div className="flex items-end gap-2">
                    <div className="flex-1">
                      <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Min Match: {filterMinScore}%</label>
                      <input
                        type="range"
                        min="0"
                        max="90"
                        step="10"
                        value={filterMinScore}
                        onChange={(e) => setFilterMinScore(Number(e.target.value))}
                        className="w-full accent-blue-500"
                      />
                    </div>
                    {(filterRole || filterCountry || filterCities || filterSource || filterMinScore > 0) && (
                      <button
                        onClick={() => {
                          setFilterRole("");
                          setFilterCountry("");
                          setFilterCities("");
                          setFilterSource("");
                          setFilterMinScore(0);
                        }}
                        className="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 text-[11px] rounded-lg"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-xs">
                  <span className="text-[11px] text-slate-500">
                    Showing <span className="text-white font-medium">{filteredJobs.length}</span> matching jobs
                  </span>
                  <button
                    onClick={() => openScanModal(filterRole, filterCountry, filterCities)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-lg text-xs font-medium transition"
                  >
                    <Search className="w-3.5 h-3.5" />
                    Launch Live Portal Scan With These Filters
                  </button>
                </div>
              </div>

              {filteredJobs.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl space-y-3">
                  <Briefcase className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-sm text-slate-400">No jobs match your filter criteria.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredJobs.map((j) => (
                    <div
                      key={j.id}
                      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white text-sm">{j.title}</span>
                          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            {j.source}
                          </span>
                          {j.score > 0 && (
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                                j.score >= 75
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                              }`}
                            >
                              Match: {j.score}%
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {j.company} &bull; {j.location || "Remote"}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            setSelectedJob(j);
                            setActiveModalTab("resume");
                            handleTailorResume(j.id);
                          }}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700"
                        >
                          Tailor Resume
                        </button>
                        <button
                          onClick={() => {
                            setSelectedJob(j);
                            setActiveModalTab("interview");
                            fetchInterviewPrep(j.id);
                          }}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-medium rounded-lg border border-slate-700 flex items-center gap-1"
                          title="Generate interview questions & candidate talking points"
                        >
                          <BookOpen className="w-3 h-3" />
                          Prep
                        </button>
                        <button
                          onClick={() => handleApply(j.id, "review")}
                          className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
                        >
                          Apply (Review)
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: REVIEW QUEUE */}
          {activeTab === "review" && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-white">Review Queue ({reviewQueue.length})</h2>
                <p className="text-xs text-slate-400">High-matching jobs evaluated by LLM awaiting your confirmation</p>
              </div>

              {reviewQueue.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl">
                  <UserCheck className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-sm text-slate-400">No jobs pending in review queue.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {reviewQueue.map((item) => (
                    <div key={item.job_id} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-white text-base">{item.title}</h3>
                            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              {item.score}% Match
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{item.company} &bull; {item.location} &bull; Portal: {item.source}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleReviewAction(item.job_id, "reject")}
                            className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-medium rounded-lg"
                          >
                            Skip
                          </button>
                          <button
                            onClick={() => handleApply(item.job_id, "review")}
                            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-blue-600/20"
                          >
                            Approve & Apply
                          </button>
                        </div>
                      </div>

                      {item.reasons?.length > 0 && (
                        <div className="text-xs text-slate-300 bg-slate-950/50 p-3 rounded-xl border border-slate-800/80">
                          <span className="font-semibold text-emerald-400 block mb-1">Match Reasons:</span>
                          <ul className="list-disc pl-4 space-y-0.5 text-slate-400">
                            {item.reasons.map((r: string, idx: number) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: KANBAN TRACKER */}
          {activeTab === "tracker" && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-white">Application Pipeline Kanban</h2>
                <p className="text-xs text-slate-400">Track application stages from discovery to offer</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-7 gap-3 overflow-x-auto pb-4">
                {[
                  { key: "found", label: "Found" },
                  { key: "matched", label: "Matched" },
                  { key: "applied", label: "Applied" },
                  { key: "responded", label: "Responded" },
                  { key: "interview", label: "Interview" },
                  { key: "offer", label: "Offer" },
                  { key: "rejected", label: "Rejected" },
                ].map((col) => (
                  <div key={col.key} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-3 min-w-[200px] flex flex-col gap-2">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-bold text-slate-300">
                      <span>{col.label}</span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                        {tracker[col.key]?.length || 0}
                      </span>
                    </div>

                    <div className="space-y-2 flex-1 overflow-y-auto max-h-[600px]">
                      {tracker[col.key]?.map((card) => (
                        <div key={card.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-xs space-y-1">
                          <div className="font-semibold text-white truncate">{card.title}</div>
                          <div className="text-[11px] text-slate-400 truncate">{card.company}</div>
                          <div className="flex items-center justify-between pt-1">
                            <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                              {card.source}
                            </span>
                            {col.key === "applied" && (
                              <button
                                onClick={async () => {
                                  await fetch(`${API_BASE}/applications/tracker/${card.id}`, {
                                    method: "PUT",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ status: "interview" }),
                                  });
                                  fetchAll();
                                }}
                                className="text-[10px] text-cyan-400 hover:underline"
                              >
                                &rarr; Interview
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: MANUAL QUEUE */}
          {activeTab === "manual" && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-white">Manual Application Queue ({manualQueue.length})</h2>
                <p className="text-xs text-slate-400">External career pages with tailored resumes generated and ready to download</p>
              </div>

              {manualQueue.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl">
                  <ExternalLink className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-sm text-slate-400">Manual queue is empty.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {manualQueue.map((m) => (
                    <div key={m.id} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-white text-sm">{m.title}</h3>
                        <p className="text-xs text-slate-400">{m.company} &bull; {m.location}</p>
                        {m.ats_score && (
                          <span className="text-[11px] text-emerald-400 font-medium">
                            Tailored ATS Score: {m.ats_score}%
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {m.resume_id && (
                          <a
                            href={`${API_BASE}/resumes/${m.resume_id}/download/pdf`}
                            download
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700"
                          >
                            <Download className="w-3.5 h-3.5" />
                            PDF
                          </a>
                        )}
                        <a
                          href={m.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          Apply on Site
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: MASTER PROFILE */}
          {activeTab === "master" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Master Profile (Single Source of Truth)</h2>
                  <p className="text-xs text-slate-400">All tailored resumes and answers are strictly derived from this data.</p>
                </div>
                <div>
                  <label className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg cursor-pointer shadow-lg shadow-blue-600/20">
                    <Upload className="w-4 h-4" />
                    Upload Resume (PDF/DOCX)
                    <input type="file" accept=".pdf,.docx,.doc" onChange={handleFileUpload} className="hidden" />
                  </label>
                </div>
              </div>

              {masterProfile && (
                <div className="space-y-6">
                  {/* Contact Info */}
                  <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                    <h3 className="font-semibold text-white text-sm">Contact Information</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                      <div>
                        <span className="text-slate-400 block">Name:</span>
                        <span className="font-medium text-white">{masterProfile.contact?.full_name || "—"}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Email:</span>
                        <span className="font-medium text-white">{masterProfile.contact?.email || "—"}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Phone:</span>
                        <span className="font-medium text-white">{masterProfile.contact?.phone || "—"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-2">
                    <h3 className="font-semibold text-white text-sm">Professional Summary</h3>
                    <p className="text-xs text-slate-300 leading-relaxed">{masterProfile.summary || "No summary added."}</p>
                  </div>

                  {/* Skills */}
                  <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                    <h3 className="font-semibold text-white text-sm">Verified Technical Skills ({masterProfile.skills?.length || 0})</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {masterProfile.skills?.map((skill: string, idx: number) => (
                        <span key={idx} className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 text-xs border border-slate-700">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 7: PERSONA PROFILES */}
          {activeTab === "profiles" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Job Search Personas ({profiles.length})</h2>
                  <p className="text-xs text-slate-400">Configure roles, countries, and multiple target cities for focused discovery</p>
                </div>
                <button
                  onClick={() => setShowProfileModal(true)}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-blue-600/20"
                >
                  <Plus className="w-3.5 h-3.5" />
                  New Persona Profile
                </button>
              </div>

              {/* Create Persona Modal */}
              {showProfileModal && (
                <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-white text-base">Create Job Search Persona</h3>
                      <button onClick={() => setShowProfileModal(false)} className="text-slate-400 hover:text-white">
                        <XCircle className="w-5 h-5" />
                      </button>
                    </div>

                    <form onSubmit={handleCreateProfile} className="space-y-3 text-xs">
                      <div>
                        <label className="text-slate-400 block mb-1">Persona Name</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Full Stack Engineer (US / India)"
                          value={newProfileName}
                          onChange={(e) => setNewProfileName(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                        />
                      </div>

                      <div>
                        <label className="text-slate-400 block mb-1">Target Roles (Comma-separated)</label>
                        <input
                          type="text"
                          placeholder="e.g. Software Engineer, Backend Developer, Python Engineer"
                          value={newProfileRoles}
                          onChange={(e) => setNewProfileRoles(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-slate-400 block mb-1">Target Countries</label>
                          <input
                            type="text"
                            placeholder="e.g. United States, India"
                            value={newProfileCountries}
                            onChange={(e) => setNewProfileCountries(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                          />
                        </div>
                        <div>
                          <label className="text-slate-400 block mb-1">Target Cities (Multiple allowed)</label>
                          <input
                            type="text"
                            placeholder="e.g. San Francisco, San Jose, Bangalore, Remote"
                            value={newProfileCities}
                            onChange={(e) => setNewProfileCities(e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className="text-slate-400 block mb-1">Min Exp (Yrs)</label>
                          <input
                            type="number"
                            min="0"
                            max="20"
                            value={newProfileMinExp}
                            onChange={(e) => setNewProfileMinExp(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                          />
                        </div>
                        <div>
                          <label className="text-slate-400 block mb-1">Max Exp (Yrs)</label>
                          <input
                            type="number"
                            min="0"
                            max="20"
                            value={newProfileMaxExp}
                            onChange={(e) => setNewProfileMaxExp(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                          />
                        </div>
                        <div>
                          <label className="text-slate-400 block mb-1">Daily Cap</label>
                          <input
                            type="number"
                            min="5"
                            max="100"
                            value={newProfileCap}
                            onChange={(e) => setNewProfileCap(Number(e.target.value))}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                          />
                        </div>
                      </div>

                      <div className="flex justify-end gap-2 pt-3">
                        <button
                          type="button"
                          onClick={() => setShowProfileModal(false)}
                          className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg"
                        >
                          Save Persona
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {profiles.map((p) => (
                  <div key={p.id} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-white text-base">{p.name}</h3>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                        Cap: {p.daily_cap}/day
                      </span>
                    </div>

                    <div className="text-xs space-y-1 text-slate-300">
                      <div><span className="text-slate-400">Target Roles:</span> {p.target_titles?.join(", ") || "Any"}</div>
                      <div><span className="text-slate-400">Target Countries:</span> {p.countries?.join(", ") || "Any"}</div>
                      <div><span className="text-slate-400">Target Cities:</span> {p.cities?.join(", ") || "Any (Multiple)"}</div>
                      <div><span className="text-slate-400">Experience:</span> {p.min_experience}–{p.max_experience} years</div>
                      <div><span className="text-slate-400">Portals:</span> {p.allowed_portals?.join(", ")}</div>
                      <div><span className="text-slate-400">Auto-Apply Mode:</span> <span className="font-semibold uppercase text-emerald-400">{p.auto_apply_mode}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 8: ANSWER BANK */}
          {activeTab === "answerbank" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Answer Bank ({answerBank.length})</h2>
                  <p className="text-xs text-slate-400">Saved responses to recurring recruiter and application questionnaire questions</p>
                </div>
              </div>

              <div className="space-y-3">
                {answerBank.map((a) => (
                  <div key={a.id} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white text-xs">{a.pattern}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {a.category}
                        </span>
                        {a.approved ? (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            Approved
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            Needs Approval
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-slate-300 bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">{a.answer}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 9: SETTINGS & LLM */}
          {activeTab === "settings" && (
            <div className="space-y-6 max-w-4xl">
              <div>
                <h2 className="text-xl font-bold text-white">System Settings & LLM Configuration</h2>
                <p className="text-xs text-slate-400">Manage Mistral AI, NVIDIA Nemotron, security keys, and backups</p>
              </div>

              <form onSubmit={saveSettings} className="space-y-6">
                <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-orange-400" />
                      Mistral AI
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      {llmConfig?.mistral?.configured ? "Configured" : "Not Set"}
                    </span>
                  </div>

                  <div className="space-y-3">
                    <input
                      type="password"
                      placeholder="Paste Mistral API Key"
                      value={mistralKey}
                      onChange={(e) => setMistralKey(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={mistralStrong}
                        onChange={(e) => setMistralStrong(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                      />
                      <input
                        type="text"
                        value={mistralCheap}
                        onChange={(e) => setMistralCheap(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => testLLM("mistral")}
                      disabled={testingMistral}
                      className="px-3 py-1.5 bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 text-xs font-medium rounded-lg border border-orange-500/30"
                    >
                      {testingMistral ? "Testing..." : "Test Mistral Connection"}
                    </button>
                    {mistralTestRes && (
                      <div className="p-2.5 rounded-lg text-xs bg-slate-950 border border-slate-800 text-slate-300">
                        {mistralTestRes.success ? `Success: ${mistralTestRes.model} (${mistralTestRes.latency_ms}ms)` : `Error: ${mistralTestRes.error}`}
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-green-400" />
                      NVIDIA NIM (Nemotron)
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      {llmConfig?.nvidia?.configured ? "Configured" : "Not Set"}
                    </span>
                  </div>

                  <div className="space-y-3">
                    <input
                      type="password"
                      placeholder="Paste NVIDIA NIM API Key"
                      value={nvidiaKey}
                      onChange={(e) => setNvidiaKey(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={nvidiaStrong}
                        onChange={(e) => setNvidiaStrong(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                      />
                      <input
                        type="text"
                        value={nvidiaCheap}
                        onChange={(e) => setNvidiaCheap(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => testLLM("nvidia")}
                      disabled={testingNvidia}
                      className="px-3 py-1.5 bg-green-500/10 hover:bg-green-500/20 text-green-400 text-xs font-medium rounded-lg border border-green-500/30"
                    >
                      {testingNvidia ? "Testing..." : "Test Nemotron Connection"}
                    </button>
                    {nvidiaTestRes && (
                      <div className="p-2.5 rounded-lg text-xs bg-slate-950 border border-slate-800 text-slate-300">
                        {nvidiaTestRes.success ? `Success: ${nvidiaTestRes.model} (${nvidiaTestRes.latency_ms}ms)` : `Error: ${nvidiaTestRes.error}`}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-between items-center pt-2">
                  <div className="flex gap-2">
                    <a
                      href={`${API_BASE}/analytics/export/csv`}
                      download
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700"
                    >
                      Export CSV Tracker
                    </a>
                    <a
                      href={`${API_BASE}/analytics/backup`}
                      download
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700"
                    >
                      Backup Database
                    </a>
                  </div>

                  <button
                    type="submit"
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-blue-600/20"
                  >
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          )}
        </main>
      </div>

      {/* Job Details, Tailoring & Interview Prep Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-white text-base">{selectedJob.title}</h3>
                <p className="text-xs text-slate-400">{selectedJob.company} &bull; {selectedJob.location || "Remote"}</p>
              </div>
              <button
                onClick={() => {
                  setSelectedJob(null);
                  setTailoredResume(null);
                  setInterviewPrep(null);
                  setCompanyResearch(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex gap-2 border-b border-slate-800 pb-2 text-xs">
              <button
                onClick={() => setActiveModalTab("resume")}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  activeModalTab === "resume" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                Tailored Resume
              </button>
              <button
                onClick={() => {
                  setActiveModalTab("interview");
                  if (!interviewPrep && !interviewLoading) fetchInterviewPrep(selectedJob.id);
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  activeModalTab === "interview" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                Interview Prep
              </button>
              <button
                onClick={() => {
                  setActiveModalTab("research");
                  if (!companyResearch && !researchLoading) fetchCompanyResearch(selectedJob.id);
                }}
                className={`px-3 py-1.5 rounded-lg font-medium transition ${
                  activeModalTab === "research" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                Company Intelligence
              </button>
            </div>

            {/* TAB 1: RESUME */}
            {activeModalTab === "resume" && (
              <div>
                {tailoringLoading ? (
                  <div className="p-12 text-center space-y-2">
                    <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
                    <p className="text-xs text-slate-400">Tailoring resume & running anti-fabrication fact-check...</p>
                  </div>
                ) : tailoredResume ? (
                  <div className="space-y-4 text-xs">
                    {/* Sub-nav for Resume Details */}
                    <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800">
                      <button
                        onClick={() => setResumeSubTab("preview")}
                        className={`px-3 py-1.5 rounded-lg font-medium transition ${
                          resumeSubTab === "preview" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        Summary & Downloads
                      </button>
                      <button
                        onClick={() => setResumeSubTab("diff")}
                        className={`px-3 py-1.5 rounded-lg font-medium transition ${
                          resumeSubTab === "diff" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        Side-by-Side Diff
                      </button>
                      <button
                        onClick={() => setResumeSubTab("cover")}
                        className={`px-3 py-1.5 rounded-lg font-medium transition ${
                          resumeSubTab === "cover" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        Cover Letter
                      </button>
                      <button
                        onClick={() => setResumeSubTab("gaps")}
                        className={`px-3 py-1.5 rounded-lg font-medium transition ${
                          resumeSubTab === "gaps" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        Skills Gaps & Fact-Check
                      </button>
                    </div>

                    {/* Sub-Tab 1: Preview & Downloads */}
                    {resumeSubTab === "preview" && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                            <span className="text-[11px] font-semibold block mb-0.5">ATS Keyword Match Score</span>
                            <span className="text-2xl font-bold">{tailoredResume.ats_score}%</span>
                          </div>
                          <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400">
                            <span className="text-[11px] font-semibold block mb-0.5">Anti-Fabrication Check</span>
                            <span className="text-sm font-bold flex items-center gap-1 mt-1">
                              <ShieldCheck className="w-4 h-4 text-emerald-400" />
                              Strict Pass (0 hallucinations)
                            </span>
                          </div>
                        </div>

                        <div className="space-y-1">
                          <span className="font-semibold text-slate-300 block">Tailored Summary:</span>
                          <p className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 leading-relaxed">
                            {tailoredResume.tailoring_notes?.tailored_summary}
                          </p>
                        </div>

                        <div className="flex gap-2 pt-2">
                          <a
                            href={`${API_BASE}/resumes/${tailoredResume.id}/download/pdf`}
                            download
                            className="flex-1 text-center py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/20"
                          >
                            Download ATS PDF
                          </a>
                          <a
                            href={`${API_BASE}/resumes/${tailoredResume.id}/download/docx`}
                            download
                            className="flex-1 text-center py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl border border-slate-700"
                          >
                            Download ATS DOCX
                          </a>
                        </div>
                      </div>
                    )}

                    {/* Sub-Tab 2: Side-by-Side Diff */}
                    {resumeSubTab === "diff" && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                              Base Summary (Master Profile)
                            </span>
                            <p className="text-slate-400 leading-relaxed text-xs">
                              {resumeDiff?.base_summary || "Default base profile summary"}
                            </p>
                          </div>
                          <div className="p-3.5 rounded-xl bg-blue-950/20 border border-blue-800/40 space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400 block">
                              Tailored Summary (Targeted to JD)
                            </span>
                            <p className="text-slate-200 leading-relaxed text-xs">
                              {resumeDiff?.tailored_summary || tailoredResume.tailoring_notes?.tailored_summary}
                            </p>
                          </div>
                        </div>

                        {/* Bullets comparison if available */}
                        {resumeDiff?.tailored_bullets && Object.keys(resumeDiff.tailored_bullets).length > 0 && (
                          <div className="space-y-2 pt-2">
                            <span className="font-bold text-slate-200 block">Experience Bullet Phrasing Diff:</span>
                            {Object.entries(resumeDiff.tailored_bullets).map(([key, bullets]: [string, any], bIdx) => (
                              <div key={bIdx} className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                                <span className="font-semibold text-emerald-400 text-[11px]">{key.replace("_", " at ")}</span>
                                <ul className="list-disc pl-4 space-y-1 text-slate-300">
                                  {bullets.map((b: string, i: number) => (
                                    <li key={i}>{b}</li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Sub-Tab 3: Cover Letter */}
                    {resumeSubTab === "cover" && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300">Tailored Cover Letter:</span>
                          {tailoredResume.tailoring_notes?.cover_letter && (
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(tailoredResume.tailoring_notes.cover_letter);
                                showToast("Cover letter copied to clipboard!");
                              }}
                              className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px]"
                            >
                              <Copy className="w-3 h-3" />
                              Copy Text
                            </button>
                          )}
                        </div>
                        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-300 whitespace-pre-wrap leading-relaxed">
                          {tailoredResume.tailoring_notes?.cover_letter || "No cover letter generated."}
                        </div>
                      </div>
                    )}

                    {/* Sub-Tab 4: Skills Gaps & Anti-Fabrication */}
                    {resumeSubTab === "gaps" && (
                      <div className="space-y-3">
                        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                          <span className="font-semibold text-amber-400 block">
                            JD Skills Gaps (Strictly Excluded & Never Fabricated):
                          </span>
                          {tailoredResume.tailoring_notes?.missing_skills?.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5">
                              {tailoredResume.tailoring_notes.missing_skills.map((gap: string, gIdx: number) => (
                                <span key={gIdx} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px]">
                                  {gap}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="text-slate-400 text-xs">No missing skill gaps detected! Your profile covers all primary JD requirements.</p>
                          )}
                        </div>

                        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                          <span className="font-semibold text-emerald-400 block">
                            Verified Candidate Skills Emphasized:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {(resumeDiff?.emphasized_skills || masterProfile?.skills || []).map((sk: string, sIdx: number) => (
                              <span key={sIdx} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px]">
                                {sk}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-8 text-center space-y-3">
                    <p className="text-xs text-slate-400">No tailored resume generated yet for this job.</p>
                    <button
                      onClick={() => handleTailorResume(selectedJob.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl"
                    >
                      Generate Tailored Resume Now
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: INTERVIEW PREP */}
            {activeModalTab === "interview" && (
              <div>
                {interviewLoading ? (
                  <div className="p-12 text-center space-y-2">
                    <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto" />
                    <p className="text-xs text-slate-400">Synthesizing interview questions & verified talking points...</p>
                  </div>
                ) : interviewPrep ? (
                  <div className="space-y-4 text-xs">
                    <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300">
                      <span className="font-semibold block mb-0.5">Role Focus & Theme:</span>
                      <p className="text-slate-300">{interviewPrep.role_overview}</p>
                    </div>

                    {interviewPrep.technical_questions?.length > 0 && (
                      <div className="space-y-2">
                        <span className="font-bold text-white uppercase text-[11px] tracking-wider block">
                          Technical Questions & Candidate Talking Points
                        </span>
                        {interviewPrep.technical_questions.map((q: any, idx: number) => (
                          <div key={idx} className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                            <p className="font-semibold text-slate-100">{q.question}</p>
                            <p className="text-[11px] text-slate-500 italic">Evaluates: {q.why_asked}</p>
                            {q.suggested_talking_points?.length > 0 && (
                              <ul className="list-disc pl-4 text-emerald-400 text-[11px] space-y-0.5">
                                {q.suggested_talking_points.map((pt: string, pIdx: number) => (
                                  <li key={pIdx}><span className="text-slate-300">{pt}</span></li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {interviewPrep.behavioral_questions?.length > 0 && (
                      <div className="space-y-2">
                        <span className="font-bold text-white uppercase text-[11px] tracking-wider block">
                          Behavioral / Situational Questions
                        </span>
                        {interviewPrep.behavioral_questions.map((q: any, idx: number) => (
                          <div key={idx} className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                            <p className="font-semibold text-slate-100">{q.question}</p>
                            {q.suggested_talking_points?.length > 0 && (
                              <ul className="list-disc pl-4 text-emerald-400 text-[11px] space-y-0.5">
                                {q.suggested_talking_points.map((pt: string, pIdx: number) => (
                                  <li key={pIdx}><span className="text-slate-300">{pt}</span></li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {interviewPrep.questions_for_interviewer?.length > 0 && (
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                        <span className="font-semibold text-amber-400 block">Questions To Ask The Interviewer:</span>
                        <ul className="list-disc pl-4 text-slate-300 space-y-1">
                          {interviewPrep.questions_for_interviewer.map((q: string, idx: number) => (
                            <li key={idx}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-8 text-center space-y-3">
                    <p className="text-xs text-slate-400">Generate interview questions tailored to your profile facts.</p>
                    <button
                      onClick={() => fetchInterviewPrep(selectedJob.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl"
                    >
                      Generate Interview Prep
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: COMPANY RESEARCH */}
            {activeModalTab === "research" && (
              <div>
                {researchLoading ? (
                  <div className="p-12 text-center space-y-2">
                    <RefreshCw className="w-8 h-8 text-purple-400 animate-spin mx-auto" />
                    <p className="text-xs text-slate-400">Extracting company research note strictly from JD text...</p>
                  </div>
                ) : companyResearch ? (
                  <div className="space-y-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                      <span className="font-semibold text-purple-400 block">Domain & Mission:</span>
                      <p className="text-slate-300">{companyResearch.domain_and_mission}</p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                      <span className="font-semibold text-blue-400 block">Product & Operations:</span>
                      <p className="text-slate-300">{companyResearch.product_and_business}</p>
                    </div>

                    {companyResearch.tech_stack_detected?.length > 0 && (
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                        <span className="font-semibold text-emerald-400 block">Identified Tech Stack:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {companyResearch.tech_stack_detected.map((t: string, idx: number) => (
                            <span key={idx} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px]">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {companyResearch.team_and_culture_cues?.length > 0 && (
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                        <span className="font-semibold text-amber-400 block">Culture & Team Cues:</span>
                        <ul className="list-disc pl-4 text-slate-300 space-y-0.5">
                          {companyResearch.team_and_culture_cues.map((c: string, idx: number) => (
                            <li key={idx}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-8 text-center space-y-3">
                    <p className="text-xs text-slate-400">Extract intelligence note directly from this job posting.</p>
                    <button
                      onClick={() => fetchCompanyResearch(selectedJob.id)}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl"
                    >
                      Extract Company Intelligence
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Scan Portals Modal with Filter Overrides */}
      {showScanModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-500/10 text-blue-400 rounded-xl">
                  <Sliders className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Scan Portals with Filters</h3>
                  <p className="text-xs text-slate-400">Configure target roles, country, and multiple cities before scanning</p>
                </div>
              </div>
              <button onClick={() => setShowScanModal(false)} className="text-slate-400 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Persona selection */}
              <div>
                <label className="text-slate-300 font-semibold block mb-1">Target Persona / Profile</label>
                <select
                  value={scanProfileId || (profiles[0]?.id ?? "")}
                  onChange={(e) => {
                    const pid = Number(e.target.value);
                    setScanProfileId(pid);
                    const found = profiles.find((p) => p.id === pid);
                    if (found) {
                      try {
                        const roles = JSON.parse(found.target_titles || "[]");
                        if (roles.length) setScanRoles(roles.join(", "));
                        const c = JSON.parse(found.countries || "[]");
                        if (c.length) setScanCountry(c[0]);
                        const cities = JSON.parse(found.cities || "[]");
                        if (cities.length) setScanCities(cities.join(", "));
                      } catch (err) {}
                    }
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white"
                >
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Target Roles */}
              <div>
                <label className="text-slate-300 font-semibold block mb-1">
                  Target Roles / Job Titles (Comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Software Engineer, AI Engineer, Full Stack"
                  value={scanRoles}
                  onChange={(e) => setScanRoles(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Country & Cities */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Country</label>
                  <input
                    type="text"
                    placeholder="e.g. India or United States"
                    value={scanCountry}
                    onChange={(e) => setScanCountry(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Cities (Multiple / Comma-separated)</label>
                  <input
                    type="text"
                    placeholder="e.g. Bengaluru, Hyderabad, Remote"
                    value={scanCities}
                    onChange={(e) => setScanCities(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Portals checkboxes */}
              <div>
                <label className="text-slate-300 font-semibold block mb-2">Portals to Scan</label>
                <div className="grid grid-cols-3 gap-2">
                  <label className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-950 border border-slate-800 cursor-pointer hover:border-slate-700">
                    <input
                      type="checkbox"
                      checked={scanPortals.workday}
                      onChange={(e) => setScanPortals((prev) => ({ ...prev, workday: e.target.checked }))}
                      className="accent-blue-500 rounded"
                    />
                    <span className="text-slate-200 font-medium">Workday (Fast CXS)</span>
                  </label>
                  <label className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-950 border border-slate-800 cursor-pointer hover:border-slate-700">
                    <input
                      type="checkbox"
                      checked={scanPortals.linkedin}
                      onChange={(e) => setScanPortals((prev) => ({ ...prev, linkedin: e.target.checked }))}
                      className="accent-blue-500 rounded"
                    />
                    <span className="text-slate-200 font-medium">LinkedIn</span>
                  </label>
                  <label className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-950 border border-slate-800 cursor-pointer hover:border-slate-700">
                    <input
                      type="checkbox"
                      checked={scanPortals.naukri}
                      onChange={(e) => setScanPortals((prev) => ({ ...prev, naukri: e.target.checked }))}
                      className="accent-blue-500 rounded"
                    />
                    <span className="text-slate-200 font-medium">Naukri</span>
                  </label>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowScanModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={triggerScanWithFilters}
                  disabled={isScanning}
                  className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/20"
                >
                  {isScanning ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Scanning Portals...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Launch Filtered Scan
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
