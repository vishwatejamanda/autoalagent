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
  Copy,
  KeyRound
} from "lucide-react";

const API_BASE = "http://localhost:8000/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "jobs" | "review" | "tracker" | "manual" | "master" | "profiles" | "answerbank" | "settings"
  >("dashboard");

  // Global states
  const ROLE_PRESETS = [
    "Software Engineer",
    "Junior Software Engineer",
    "Associate Software Engineer",
    "Graduate Engineer Trainee",
    "Software Developer Intern",
    "Backend Developer",
    "Java Developer",
    "Spring Boot Developer",
    "Python Developer",
    "Django Developer",
    "Full Stack Developer",
    "AI / ML Engineer",
    "NLP Engineer",
    "Data Analyst",
    "Cloud Engineer",
    "QA / Test Engineer",
    "Frontend Developer",
    "DevOps Engineer",
  ];

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
  const [scanLimit, setScanLimit] = useState<number>(50);
  const [isScanning, setIsScanning] = useState(false);

  // Application Defaults (Fresher / N/A & Custom Q&A) + LaTeX Import states
  const [appDefaults, setAppDefaults] = useState<any>({
    experience_level: "fresher",
    years_of_experience: "0",
    previous_company: "N/A",
    previous_role: "N/A",
    current_ctc: "N/A",
    expected_ctc: "As per company standards",
    notice_period: "Immediate",
    willing_to_relocate: "Yes",
    work_authorization: "Authorized to work in India",
    key_skills: "",
    custom_qa_notes: "",
  });
  const [savingDefaults, setSavingDefaults] = useState(false);
  const [launchingBrowser, setLaunchingBrowser] = useState<string | null>(null);
  const [latexTemplateInput, setLatexTemplateInput] = useState("");
  const [importingLatex, setImportingLatex] = useState(false);

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
  const [resumeSubTab, setResumeSubTab] = useState<"preview" | "latex" | "diff" | "cover" | "gaps">("preview");

  // Workday Companies State
  const [workdayCompanies, setWorkdayCompanies] = useState<any[]>([]);
  const [showAddCompany, setShowAddCompany] = useState(false);
  const [compName, setCompName] = useState("");
  const [compTenant, setCompTenant] = useState("");
  const [compSite, setCompSite] = useState("");
  const [compUrl, setCompUrl] = useState("");

  // Phase 5 Matching & Review Queue State
  const [reviewProfileId, setReviewProfileId] = useState<string>("all");
  const [reviewMinScore, setReviewMinScore] = useState<number>(60);
  const [reviewSourceFilter, setReviewSourceFilter] = useState<string>("all");
  const [isScoringAll, setIsScoringAll] = useState(false);
  const [forceRescore, setForceRescore] = useState(false);
  const [scoringSingleId, setScoringSingleId] = useState<number | null>(null);

  // Phase 6/7/8 Automation, History, Answer Bank, Audit & CAPTCHA State
  const [appHistory, setAppHistory] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [captchaAlert, setCaptchaAlert] = useState<any>(null);
  const [lastApplyResult, setLastApplyResult] = useState<any>(null);
  const [showAddAnswer, setShowAddAnswer] = useState(false);
  const [ansPattern, setAnsPattern] = useState("");
  const [ansText, setAnsText] = useState("");
  const [ansCategory, setAnsCategory] = useState("general");
  const [ansApproved, setAnsApproved] = useState(true);
  const [draggedJobId, setDraggedJobId] = useState<number | null>(null);

  const showToast = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  // ─── Data Fetchers ──────────────────────────────────────────

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [
        hRes, cRes, fRes, pRes, jRes, rRes, tRes, mRes, mpRes, profRes, abRes, ksRes, wdRes, histRes, audRes, defRes
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
        fetch(`${API_BASE}/jobs/workday/companies`),
        fetch(`${API_BASE}/applications/history?limit=15`),
        fetch(`${API_BASE}/analytics/audit?limit=15`),
        fetch(`${API_BASE}/settings/application-defaults`),
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
      if (mpRes.ok) {
        const mpJson = await mpRes.json();
        setMasterProfile(mpJson.data);
        if (mpJson.data?.latex_template && !latexTemplateInput) {
          setLatexTemplateInput(mpJson.data.latex_template);
        }
      }
      if (profRes.ok) setProfiles(await profRes.json());
      if (abRes.ok) setAnswerBank(await abRes.json());
      if (ksRes.ok) setKillSwitch((await ksRes.json()).kill_switch_active);
      if (wdRes.ok) setWorkdayCompanies(await wdRes.json());
      if (histRes.ok) setAppHistory(await histRes.json());
      if (audRes.ok) setAuditLogs(await audRes.json());
      if (defRes.ok) setAppDefaults(await defRes.json());
    } catch (e) {
      console.error("Fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchReviewQueueFiltered = async (minScore?: number, profileId?: string, source?: string) => {
    try {
      const ms = minScore !== undefined ? minScore : reviewMinScore;
      const pid = profileId !== undefined ? profileId : reviewProfileId;
      const src = source !== undefined ? source : reviewSourceFilter;
      let url = `${API_BASE}/matching/review-queue?min_score=${ms}`;
      if (pid && pid !== "all") url += `&profile_id=${pid}`;
      if (src && src !== "all") url += `&source=${src}`;
      const res = await fetch(url);
      if (res.ok) {
        setReviewQueue(await res.json());
      }
    } catch (e) {
      console.error("Error fetching review queue:", e);
    }
  };

  useEffect(() => {
    fetchAll();

    let es: EventSource | null = null;
    try {
      es = new EventSource(`${API_BASE}/events/stream`);
      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "matching_progress") {
            setNotification(`Scoring: ${payload.data.current}/${payload.data.total} jobs (${payload.data.matched_count} matched)`);
          } else if (payload.type === "matching_completed") {
            showToast(`Batch matching finished: ${payload.data.scored_count} scored, ${payload.data.matched_count} matched.`);
            fetchAll();
          } else if (payload.type === "review_action_completed" || payload.type === "tracker_updated") {
            fetchAll();
          } else if (payload.type === "application_started") {
            setNotification(`Bot applying to ${payload.data.title} at ${payload.data.company} (${payload.data.mode} mode)...`);
          } else if (payload.type === "application_completed") {
            showToast(`Application ${payload.data.status}: ${payload.data.title} (${payload.data.company})`);
            fetchAll();
          } else if (payload.type === "captcha_detected") {
            setCaptchaAlert(payload.data);
            showToast(`CAPTCHA detected on ${payload.data.portal}! Automation safely paused.`);
            fetchAll();
          }
        } catch (err) {
          // ignore keepalive comments
        }
      };
    } catch (e) {
      console.warn("SSE connection error", e);
    }

    return () => {
      if (es) es.close();
    };
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
        limit: scanLimit,
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
    setIsScoringAll(true);
    showToast("Evaluating jobs with Stage 1 heuristics & Nemotron LLM...");
    try {
      const body: any = { force_rescore: forceRescore };
      if (reviewProfileId !== "all") {
        body.profile_id = Number(reviewProfileId);
      }
      const res = await fetch(`${API_BASE}/matching/score-all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Scored ${data.scored_count} jobs. ${data.matched_count} met threshold (${data.min_score_threshold}%)!`);
        fetchReviewQueueFiltered();
        fetchAll();
      } else {
        showToast("Scoring finished with warnings");
      }
    } catch (e: any) {
      showToast("Scoring failed: " + e.message);
    } finally {
      setIsScoringAll(false);
    }
  };

  const scoreSingleJob = async (jobId: number) => {
    setScoringSingleId(jobId);
    showToast(`Evaluating Job #${jobId} with Stage 1 & Stage 2 LLM...`);
    try {
      const body: any = {};
      if (reviewProfileId !== "all") {
        body.profile_id = Number(reviewProfileId);
      }
      const res = await fetch(`${API_BASE}/matching/score/${jobId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Job #${jobId} scored ${data.score}% match! (${data.reasons?.length || 0} reasons, ${data.gaps?.length || 0} gaps)`);
        fetchAll();
      } else {
        showToast("Failed to score job");
      }
    } catch (e: any) {
      showToast("Scoring error: " + e.message);
    } finally {
      setScoringSingleId(null);
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
    const jobMeta = jobs.find((x) => x.id === jobId);
    try {
      const res = await fetch(`${API_BASE}/applications/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, mode }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(`Blocked: ${data.detail || "Application could not proceed"}`);
        return;
      }
      setLastApplyResult({
        ...data,
        portal: jobMeta?.source || "naukri",
        job_title: jobMeta?.title || `Job #${jobId}`,
        company: jobMeta?.company || "",
      });
      showToast(`Application ${data.status}: ${data.error || data.details || data.message || ""}`);
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

  const handleMoveKanbanStage = async (jobId: number, status: string) => {
    try {
      const res = await fetch(`${API_BASE}/applications/tracker/${jobId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        showToast(`Moved Job #${jobId} to '${status}'`);
        fetchAll();
      } else {
        showToast("Failed to update stage");
      }
    } catch (e: any) {
      showToast("Stage update error: " + e.message);
    }
  };

  const handleAddAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/answer-bank`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pattern: ansPattern,
          answer: ansText,
          category: ansCategory,
          approved: ansApproved,
        }),
      });
      if (res.ok) {
        showToast("Saved answer to Answer Bank!");
        setAnsPattern("");
        setAnsText("");
        setShowAddAnswer(false);
        fetchAll();
      } else {
        showToast("Failed adding answer");
      }
    } catch (e: any) {
      showToast("Error saving answer: " + e.message);
    }
  };

  const handleApproveAnswer = async (entryId: number, approved: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/answer-bank/${entryId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      if (res.ok) {
        showToast(approved ? "Answer approved for autofill!" : "Answer marked as needs approval");
        fetchAll();
      }
    } catch (e: any) {
      showToast("Error updating answer");
    }
  };

  const handleDeleteAnswer = async (entryId: number) => {
    try {
      const res = await fetch(`${API_BASE}/answer-bank/${entryId}`, { method: "DELETE" });
      if (res.ok) {
        showToast("Answer removed.");
        fetchAll();
      }
    } catch (e: any) {
      showToast("Error deleting answer");
    }
  };

  const handleUpdateProfileMode = async (profileId: number, autoApplyMode: string) => {
    try {
      const res = await fetch(`${API_BASE}/profiles/${profileId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_apply_mode: autoApplyMode }),
      });
      if (res.ok) {
        showToast(`Auto-apply mode set to '${autoApplyMode.toUpperCase()}'`);
        fetchAll();
      }
    } catch (e: any) {
      showToast("Failed updating profile mode");
    }
  };

  const handleRestoreDatabase = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    showToast(`Restoring database from ${file.name}...`);
    try {
      const res = await fetch(`${API_BASE}/analytics/restore`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        showToast("Database restored successfully! Reloading data...");
        fetchAll();
      } else {
        showToast("Database restore failed.");
      }
    } catch (err: any) {
      showToast("Restore error: " + err.message);
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

  const handleAddCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!compTenant.trim() || !compSite.trim()) {
      showToast("Tenant ID and Site Name are required.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/jobs/workday/companies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: compName.trim() || compTenant.trim(),
          tenant: compTenant.trim(),
          site: compSite.trim(),
          base_url: compUrl.trim() || undefined,
        }),
      });
      if (res.ok) {
        showToast(`Added ${compName || compTenant} to Workday companies!`);
        setCompName("");
        setCompTenant("");
        setCompSite("");
        setCompUrl("");
        setShowAddCompany(false);
        fetchAll();
      } else {
        const err = await res.json();
        showToast(`Failed: ${err.detail || "Error adding company"}`);
      }
    } catch (err: any) {
      showToast("Error adding company: " + err.message);
    }
  };

  const handleDeleteCompany = async (tenant: string) => {
    if (!confirm(`Remove ${tenant} from configured Workday companies?`)) return;
    try {
      const res = await fetch(`${API_BASE}/jobs/workday/companies/${tenant}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast(`Removed Workday tenant ${tenant}.`);
        fetchAll();
      } else {
        showToast("Failed to remove company.");
      }
    } catch (err: any) {
      showToast("Error removing company: " + err.message);
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

  const saveApplicationDefaults = async () => {
    setSavingDefaults(true);
    try {
      const res = await fetch(`${API_BASE}/settings/application-defaults`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(appDefaults),
      });
      if (res.ok) {
        showToast("Saved Fresher / N/A application defaults & skills!");
        fetchAll();
      } else {
        showToast("Failed to save application defaults.");
      }
    } catch (e: any) {
      showToast("Error saving defaults: " + e.message);
    } finally {
      setSavingDefaults(false);
    }
  };

  const launchBrowserLogin = async (portal: "naukri" | "linkedin" | "workday") => {
    setLaunchingBrowser(portal);
    try {
      const res = await fetch(`${API_BASE}/settings/browser-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portal }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(data.message);
      } else {
        showToast("Failed to open login window: " + (data.detail || "unknown error"));
      }
    } catch (e: any) {
      showToast("Browser login helper error: " + e.message);
    } finally {
      setLaunchingBrowser(null);
    }
  };

  const loadSampleLatexTemplate = async () => {
    try {
      const res = await fetch(`${API_BASE}/profiles/master/default-latex-template`);
      if (res.ok) {
        const data = await res.json();
        setLatexTemplateInput(data.latex || "");
        showToast("Loaded LaTeX resume template! Click Import to apply it.");
      }
    } catch (e: any) {
      showToast("Failed loading template: " + e.message);
    }
  };

  const handleImportLatex = async () => {
    if (!latexTemplateInput.trim()) {
      showToast("Paste LaTeX code first or click Load Sample Template.");
      return;
    }
    setImportingLatex(true);
    try {
      const res = await fetch(`${API_BASE}/profiles/master/import-latex`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latex: latexTemplateInput }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Imported LaTeX resume into Master Profile (v${data.version})!`);
        fetchAll();
      } else {
        showToast("Import error: " + (data.detail || "Invalid LaTeX"));
      }
    } catch (e: any) {
      showToast("LaTeX import error: " + e.message);
    } finally {
      setImportingLatex(false);
    }
  };

  const toggleCommaToken = (current: string, token: string): string => {
    const items = current.split(",").map((s) => s.trim()).filter(Boolean);
    const exists = items.some((i) => i.toLowerCase() === token.toLowerCase());
    if (exists) {
      return items.filter((i) => i.toLowerCase() !== token.toLowerCase()).join(", ");
    }
    return [...items, token].join(", ");
  };

  const filteredJobs = jobs.filter((j) => {
    if (filterSource && j.source !== filterSource) return false;
    if (filterMinScore > 0 && j.score < filterMinScore) return false;
    if (filterRole) {
      const roleTokens = filterRole.split(",").map((r) => r.trim().toLowerCase()).filter(Boolean);
      if (roleTokens.length > 0 && !roleTokens.some((r) => j.title.toLowerCase().includes(r))) return false;
    }
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
          {/* Global CAPTCHA Alert Banner */}
          {captchaAlert && (
            <div className="mb-6 p-4 rounded-2xl bg-rose-950/60 border border-rose-500/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <span className="font-bold text-rose-300 block">
                    CAPTCHA Challenge Detected on {captchaAlert.portal}
                  </span>
                  <p className="text-rose-200/80">
                    {captchaAlert.message || "Automation safely paused. Please solve the CAPTCHA in the browser."}
                    {captchaAlert.title ? ` (${captchaAlert.title} at ${captchaAlert.company})` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {captchaAlert.screenshot_url && (
                  <a
                    href={`${API_BASE.replace("/api", "")}${captchaAlert.screenshot_url}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold rounded-lg border border-rose-500/40"
                  >
                    View Screenshot
                  </a>
                )}
                <button
                  onClick={() => setCaptchaAlert(null)}
                  className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs rounded-lg border border-slate-700"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Actionable Application Result Banner (Screenshot + Login Recovery) */}
          {lastApplyResult && (
            <div className="mb-6 p-4 rounded-2xl bg-slate-900/90 border border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="text-xs space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                    lastApplyResult.status === "submitted"
                      ? "bg-emerald-500/20 text-emerald-400"
                      : lastApplyResult.status === "login_required"
                      ? "bg-amber-500/20 text-amber-300"
                      : "bg-blue-500/20 text-blue-300"
                  }`}>
                    {lastApplyResult.status}
                  </span>
                  <span className="font-semibold text-white">
                    {lastApplyResult.job_title} {lastApplyResult.company ? `@ ${lastApplyResult.company}` : ""}
                  </span>
                </div>
                <p className="text-slate-300">
                  {lastApplyResult.error || lastApplyResult.details || lastApplyResult.message}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {lastApplyResult.status === "login_required" && (
                  <button
                    type="button"
                    onClick={() =>
                      launchBrowserLogin(
                        (lastApplyResult.portal === "linkedin" || lastApplyResult.portal === "workday")
                          ? lastApplyResult.portal
                          : "naukri"
                      )
                    }
                    className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-semibold rounded-lg border border-amber-500/40"
                  >
                    Open Browser Login ({lastApplyResult.portal})
                  </button>
                )}
                {lastApplyResult.screenshot_url && (
                  <a
                    href={`${API_BASE.replace("/api", "")}${lastApplyResult.screenshot_url}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700"
                  >
                    View Screenshot
                  </a>
                )}
                <button
                  onClick={() => setLastApplyResult(null)}
                  className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-slate-400 text-xs rounded-lg border border-slate-800"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* TAB 1: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    Application Pipeline Funnel
                    {health?.components?.scheduler?.running && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        Scheduler Active
                      </span>
                    )}
                  </h2>
                  <p className="text-xs text-slate-400">
                    Live metrics across LinkedIn, Naukri, and Workday &bull; Response Rate:{" "}
                    <span className="text-cyan-400 font-semibold">{funnel?.response_rate_percent ?? 0}%</span>
                  </p>
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

              {/* Recent Application Runs & System Audit Log */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                  <h3 className="font-semibold text-white text-sm flex items-center justify-between">
                    <span>Recent Application Runs ({appHistory.length})</span>
                    <span className="text-[10px] text-slate-500 font-normal">Latest automation history &amp; screenshots</span>
                  </h3>
                  {appHistory.length === 0 ? (
                    <p className="text-xs text-slate-500 py-4 text-center">No automated application runs recorded yet.</p>
                  ) : (
                    <div className="space-y-2 max-h-[280px] overflow-y-auto">
                      {appHistory.map((h) => (
                        <div key={h.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-between gap-2 text-xs">
                          <div className="min-w-0">
                            <div className="font-medium text-white truncate">{h.job_title}</div>
                            <div className="text-[11px] text-slate-400 truncate">
                              {h.company} &bull; {h.portal} &bull; mode: {h.mode}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span
                              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                                h.status === "submitted"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                              }`}
                            >
                              {h.status}
                            </span>
                            {h.screenshot_url && (
                              <a
                                href={`${API_BASE.replace("/api", "")}${h.screenshot_url}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[11px] text-blue-400 hover:underline"
                              >
                                Screenshot
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                  <h3 className="font-semibold text-white text-sm flex items-center justify-between">
                    <span>System Audit Log ({auditLogs.length})</span>
                    <span className="text-[10px] text-slate-500 font-normal">Recent agent &amp; scheduler activity</span>
                  </h3>
                  {auditLogs.length === 0 ? (
                    <p className="text-xs text-slate-500 py-4 text-center">No audit log events yet.</p>
                  ) : (
                    <div className="space-y-2 max-h-[280px] overflow-y-auto">
                      {auditLogs.map((log) => (
                        <div key={log.id} className="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 text-xs space-y-0.5">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[10px] font-bold text-cyan-400">{log.action}</span>
                            <span className="text-[10px] text-slate-500">
                              {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ""}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-300">{log.details}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
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

                {/* Quick Role Presets */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold mr-1">Quick Roles:</span>
                  {ROLE_PRESETS.slice(0, 12).map((roleName) => {
                    const active = filterRole.split(",").map((s) => s.trim().toLowerCase()).includes(roleName.toLowerCase());
                    return (
                      <button
                        key={roleName}
                        type="button"
                        onClick={() => setFilterRole((prev) => toggleCommaToken(prev, roleName))}
                        className={`px-2 py-0.5 rounded-md text-[11px] border transition ${
                          active
                            ? "bg-blue-600 text-white border-blue-500"
                            : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
                        }`}
                      >
                        {roleName}
                      </button>
                    );
                  })}
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
                          onClick={() => scoreSingleJob(j.id)}
                          disabled={scoringSingleId === j.id}
                          className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-400 text-xs font-medium rounded-lg border border-slate-700 flex items-center gap-1"
                          title="Run Stage 1 & Stage 2 matching score"
                        >
                          <Sparkles className={`w-3 h-3 ${scoringSingleId === j.id ? "animate-spin text-amber-400" : ""}`} />
                          {scoringSingleId === j.id ? "Scoring..." : (j.score > 0 ? "Rescore" : "Score")}
                        </button>
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
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
                        >
                          Apply (Review)
                        </button>
                        <button
                          onClick={() => handleApply(j.id, "auto")}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg"
                          title="Auto-fill with tailored PDF + Application Defaults and submit (pauses safely on review/CAPTCHA/login)"
                        >
                          Auto Apply
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
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <UserCheck className="w-5 h-5 text-emerald-400" />
                    Review Queue ({reviewQueue.length})
                  </h2>
                  <p className="text-xs text-slate-400">
                    High-matching jobs evaluated by Stage 1 heuristics &amp; Nemotron LLM
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 cursor-pointer hover:border-slate-700">
                    <input
                      type="checkbox"
                      checked={forceRescore}
                      onChange={(e) => setForceRescore(e.target.checked)}
                      className="rounded accent-blue-600"
                    />
                    <span>Force Rescore</span>
                  </label>
                  <button
                    onClick={scoreAllJobs}
                    disabled={isScoringAll}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white text-xs font-semibold rounded-lg shadow-lg shadow-blue-600/20 transition"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isScoringAll ? "animate-spin" : ""}`} />
                    {isScoringAll ? "Scoring Jobs..." : "Score All Jobs"}
                  </button>
                </div>
              </div>

              {/* Filters Bar */}
              <div className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Target Persona</label>
                    <select
                      value={reviewProfileId}
                      onChange={(e) => {
                        setReviewProfileId(e.target.value);
                        fetchReviewQueueFiltered(reviewMinScore, e.target.value, reviewSourceFilter);
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="all">All Personas</option>
                      {profiles.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Min Match Score: <span className="text-white font-bold">{reviewMinScore}%</span>
                    </label>
                    <input
                      type="range"
                      min="40"
                      max="90"
                      step="5"
                      value={reviewMinScore}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setReviewMinScore(val);
                        fetchReviewQueueFiltered(val, reviewProfileId, reviewSourceFilter);
                      }}
                      className="w-full accent-blue-500 mt-1"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Portal Source</label>
                    <select
                      value={reviewSourceFilter}
                      onChange={(e) => {
                        setReviewSourceFilter(e.target.value);
                        fetchReviewQueueFiltered(reviewMinScore, reviewProfileId, e.target.value);
                      }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="all">All Portals</option>
                      <option value="workday">Workday</option>
                      <option value="linkedin">LinkedIn</option>
                      <option value="naukri">Naukri</option>
                    </select>
                  </div>
                </div>
              </div>

              {reviewQueue.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl space-y-3">
                  <UserCheck className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-sm text-slate-400">No jobs met the {reviewMinScore}% match threshold.</p>
                  <button
                    onClick={() => {
                      setReviewMinScore(40);
                      fetchReviewQueueFiltered(40, reviewProfileId, reviewSourceFilter);
                    }}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 rounded-lg"
                  >
                    Lower threshold to 40%
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {reviewQueue.map((item) => (
                    <div key={item.job_id} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3.5 hover:border-slate-700 transition">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-bold text-white text-base">{item.title}</h3>
                            <span
                              className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                                item.score >= 80
                                  ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                                  : item.score >= 65
                                  ? "bg-blue-500/20 text-blue-400 border-blue-500/40"
                                  : "bg-amber-500/20 text-amber-400 border-amber-500/40"
                              }`}
                            >
                              {item.score}% Match
                            </span>
                            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                              {item.source}
                            </span>
                            {item.easy_apply && (
                              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                                Easy Apply
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400">
                            {item.company} &bull; {item.location || "Remote"}
                          </p>
                        </div>

                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            onClick={() => scoreSingleJob(item.job_id)}
                            disabled={scoringSingleId === item.job_id}
                            className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 text-xs font-medium rounded-lg border border-slate-700 flex items-center gap-1"
                            title="Rescore this job with LLM"
                          >
                            <Sparkles className={`w-3 h-3 ${scoringSingleId === item.job_id ? "animate-spin text-amber-400" : ""}`} />
                            Rescore
                          </button>
                          <button
                            onClick={() => {
                              const matchJob = jobs.find((j) => j.id === item.job_id) || {
                                id: item.job_id,
                                title: item.title,
                                company: item.company,
                                location: item.location,
                                source: item.source,
                                url: item.url,
                                description: item.description_preview || "",
                                score: item.score,
                              };
                              setSelectedJob(matchJob);
                              setActiveModalTab("resume");
                              handleTailorResume(item.job_id);
                            }}
                            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 flex items-center gap-1"
                          >
                            <FileText className="w-3.5 h-3.5 text-blue-400" />
                            Tailor Resume
                          </button>
                          <button
                            onClick={() => handleReviewAction(item.job_id, "reject")}
                            className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-medium rounded-lg"
                          >
                            Skip
                          </button>
                          <button
                            onClick={() => handleApply(item.job_id, "review")}
                            className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-blue-600/20"
                          >
                            Apply (Review)
                          </button>
                          <button
                            onClick={() => handleApply(item.job_id, "auto")}
                            className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg"
                          >
                            Auto Apply
                          </button>
                        </div>
                      </div>

                      {/* Reasons & Gaps Breakdown */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        {item.reasons?.length > 0 && (
                          <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800/80 space-y-1">
                            <span className="font-semibold text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Match Strengths ({item.reasons.length})
                            </span>
                            <ul className="list-disc pl-4 space-y-0.5 text-slate-300 text-[11px]">
                              {item.reasons.map((r: string, idx: number) => (
                                <li key={idx}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="space-y-2">
                          {item.gaps?.length > 0 && (
                            <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800/80 space-y-1">
                              <span className="font-semibold text-amber-400 flex items-center gap-1">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                Missing Skills ({item.gaps.length})
                              </span>
                              <div className="flex flex-wrap gap-1 pt-1">
                                {item.gaps.map((g: string, idx: number) => (
                                  <span key={idx} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[10px]">
                                    {g}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {item.red_flags?.length > 0 && (
                            <div className="bg-rose-950/20 p-2.5 rounded-xl border border-rose-500/30 text-[11px] text-rose-300 space-y-0.5">
                              <span className="font-semibold text-rose-400 flex items-center gap-1">
                                <XCircle className="w-3.5 h-3.5" />
                                Flagged Potential Issues:
                              </span>
                              <ul className="list-disc pl-4 space-y-0.5">
                                {item.red_flags.map((rf: string, idx: number) => (
                                  <li key={idx}>{rf}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
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
                <p className="text-xs text-slate-400">Drag cards or select a stage to move applications from discovery to offer</p>
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
                  <div
                    key={col.key}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => {
                      if (draggedJobId !== null) {
                        handleMoveKanbanStage(draggedJobId, col.key);
                        setDraggedJobId(null);
                      }
                    }}
                    className="bg-slate-900/50 border border-slate-800 rounded-2xl p-3 min-w-[200px] flex flex-col gap-2"
                  >
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-bold text-slate-300">
                      <span>{col.label}</span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400">
                        {tracker[col.key]?.length || 0}
                      </span>
                    </div>

                    <div className="space-y-2 flex-1 overflow-y-auto max-h-[600px]">
                      {tracker[col.key]?.map((card) => (
                        <div
                          key={card.id}
                          draggable
                          onDragStart={() => setDraggedJobId(card.id)}
                          className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 hover:border-slate-700 text-xs space-y-1.5 cursor-grab active:cursor-grabbing"
                        >
                          <div className="font-semibold text-white truncate">{card.title}</div>
                          <div className="text-[11px] text-slate-400 truncate">{card.company}</div>
                          <div className="flex items-center justify-between pt-1 gap-1">
                            <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                              {card.source}
                            </span>
                            <select
                              value={col.key}
                              onChange={(e) => handleMoveKanbanStage(card.id, e.target.value)}
                              className="bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 text-[10px] text-slate-300 focus:outline-none focus:border-blue-500"
                              title="Move to stage"
                            >
                              <option value="found">Found</option>
                              <option value="matched">Matched</option>
                              <option value="applied">Applied</option>
                              <option value="responded">Responded</option>
                              <option value="interview">Interview</option>
                              <option value="offer">Offer</option>
                              <option value="rejected">Rejected</option>
                            </select>
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
                    <div key={m.id} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-white text-sm">{m.title}</h3>
                        <p className="text-xs text-slate-400">{m.company} &bull; {m.location || "Remote"}</p>
                        {m.ats_score && (
                          <span className="text-[11px] text-emerald-400 font-medium">
                            Tailored ATS Score: {m.ats_score}%
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 flex-wrap">
                        {m.resume_id && (
                          <>
                            <a
                              href={`${API_BASE}/resumes/${m.resume_id}/download/pdf`}
                              download
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700"
                            >
                              <Download className="w-3.5 h-3.5" />
                              PDF
                            </a>
                            <a
                              href={`${API_BASE}/resumes/${m.resume_id}/download/docx`}
                              download
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700"
                            >
                              <Download className="w-3.5 h-3.5" />
                              DOCX
                            </a>
                            <a
                              href={`${API_BASE}/resumes/${m.resume_id}/download/tex`}
                              download
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-300 text-xs font-medium rounded-lg border border-slate-700"
                            >
                              <Download className="w-3.5 h-3.5" />
                              LaTeX (.tex)
                            </a>
                          </>
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
                        <button
                          onClick={() => handleMoveKanbanStage(m.id, "applied")}
                          className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-medium rounded-lg"
                        >
                          Mark Applied
                        </button>
                        <button
                          onClick={() => handleMoveKanbanStage(m.id, "rejected")}
                          className="px-2.5 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-medium rounded-lg"
                        >
                          Skip
                        </button>
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

                  {/* Projects (especially relevant for Freshers) */}
                  {masterProfile.projects?.length > 0 && (
                    <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                      <h3 className="font-semibold text-white text-sm">Academic & Personal Projects ({masterProfile.projects.length})</h3>
                      <div className="space-y-3">
                        {masterProfile.projects.map((proj: any, idx: number) => (
                          <div key={idx} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 text-xs">
                            <div className="font-semibold text-white">{proj.name}</div>
                            {proj.technologies?.length > 0 && (
                              <div className="text-[11px] text-blue-400">Tech: {proj.technologies.join(", ")}</div>
                            )}
                            {proj.bullets?.length > 0 && (
                              <ul className="list-disc pl-4 text-slate-300 space-y-0.5">
                                {proj.bullets.map((b: string, bi: number) => (
                                  <li key={bi}>{b}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Education & Certifications */}
                  {masterProfile.education?.length > 0 && (
                    <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-2.5 text-xs">
                      <h3 className="font-semibold text-white text-sm">Education & Certifications</h3>
                      {masterProfile.education.map((edu: any, idx: number) => (
                        <div key={idx} className="flex items-center justify-between text-slate-300 border-b border-slate-800/50 pb-1.5">
                          <span className="font-medium text-white">{edu.degree}{edu.institution ? ` — ${edu.institution}` : ""}</span>
                          <span className="text-slate-400">{edu.graduation_date}</span>
                        </div>
                      ))}
                      {masterProfile.certifications?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {masterProfile.certifications.map((c: any, ci: number) => (
                            <span key={ci} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px]">
                              {c.name} {c.date ? `(${c.date})` : ""}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* LaTeX Resume Importer */}
              <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                      <FileText className="w-4 h-4 text-emerald-400" />
                      LaTeX Resume Source & Template Import (.tex)
                    </h3>
                    <p className="text-xs text-slate-400">
                      Import your LaTeX resume directly so AI tailoring preserves your exact preamble, macros, projects, and fresher structure.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={loadSampleLatexTemplate}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700"
                    >
                      Load Built-In LaTeX Template
                    </button>
                    <button
                      type="button"
                      onClick={handleImportLatex}
                      disabled={importingLatex}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg"
                    >
                      {importingLatex ? "Importing..." : "Import LaTeX into Master Profile"}
                    </button>
                  </div>
                </div>
                <textarea
                  rows={8}
                  placeholder="Paste your LaTeX (.tex) resume code here, or click 'Load Built-In LaTeX Template'..."
                  value={latexTemplateInput}
                  onChange={(e) => setLatexTemplateInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>
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
                        <label className="text-slate-400 block mb-1">Target Roles (Comma-separated or click presets)</label>
                        <input
                          type="text"
                          placeholder="e.g. Software Engineer, Backend Developer, Python Engineer"
                          value={newProfileRoles}
                          onChange={(e) => setNewProfileRoles(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                        />
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {ROLE_PRESETS.slice(0, 12).map((r) => {
                            const active = newProfileRoles.split(",").map((s) => s.trim().toLowerCase()).includes(r.toLowerCase());
                            return (
                              <button
                                key={r}
                                type="button"
                                onClick={() => setNewProfileRoles((prev) => toggleCommaToken(prev, r))}
                                className={`px-2 py-0.5 rounded text-[10px] border ${
                                  active ? "bg-blue-600 text-white border-blue-500" : "bg-slate-950 text-slate-400 border-slate-800"
                                }`}
                              >
                                {active ? `✓ ${r}` : `+ ${r}`}
                              </button>
                            );
                          })}
                          <button
                            type="button"
                            onClick={() => {
                              setNewProfileMinExp(0);
                              setNewProfileMaxExp(1);
                            }}
                            className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          >
                            Preset: Fresher (0–1 yrs)
                          </button>
                        </div>
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
                      <div className="flex items-center justify-between pt-1">
                        <div>
                          <span className="text-slate-400">Auto-Apply Mode: </span>
                          <span className="font-semibold uppercase text-emerald-400">{p.auto_apply_mode}</span>
                        </div>
                        <select
                          value={p.auto_apply_mode || "off"}
                          onChange={(e) => handleUpdateProfileMode(p.id, e.target.value)}
                          className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-blue-500"
                          title="Change persona auto-apply mode"
                        >
                          <option value="off">Off (Manual)</option>
                          <option value="review">Review (Pause Before Submit)</option>
                          <option value="auto">Auto (Autonomous Submit)</option>
                        </select>
                      </div>
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
                <button
                  onClick={() => setShowAddAnswer(!showAddAnswer)}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-lg shadow-blue-600/20"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Answer
                </button>
              </div>

              {showAddAnswer && (
                <form onSubmit={handleAddAnswer} className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="sm:col-span-2">
                      <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Question Pattern *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. What is your notice period?"
                        value={ansPattern}
                        onChange={(e) => setAnsPattern(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Category</label>
                      <select
                        value={ansCategory}
                        onChange={(e) => setAnsCategory(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="general">General</option>
                        <option value="experience">Experience</option>
                        <option value="legal">Legal / Visa</option>
                        <option value="salary">Salary / CTC</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Approved Answer *</label>
                    <textarea
                      required
                      rows={2}
                      placeholder="e.g. Immediate joiner / 15 days notice period."
                      value={ansText}
                      onChange={(e) => setAnsText(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={ansApproved}
                        onChange={(e) => setAnsApproved(e.target.checked)}
                        className="rounded accent-blue-600"
                      />
                      <span>Approve for automated form filling</span>
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setShowAddAnswer(false)}
                        className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg"
                      >
                        Save Answer
                      </button>
                    </div>
                  </div>
                </form>
              )}

              <div className="space-y-3">
                {answerBank.map((a) => (
                  <div key={a.id} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="font-semibold text-white text-xs">{a.pattern}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {a.category}
                        </span>
                        {a.approved ? (
                          <button
                            onClick={() => handleApproveAnswer(a.id, false)}
                            className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                            title="Click to revoke auto-fill approval"
                          >
                            Approved
                          </button>
                        ) : (
                          <button
                            onClick={() => handleApproveAnswer(a.id, true)}
                            className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20"
                            title="Click to approve for auto-fill"
                          >
                            Approve Now
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteAnswer(a.id)}
                          className="p-1 text-slate-500 hover:text-rose-400"
                          title="Delete answer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
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
                  <div className="flex gap-2 flex-wrap">
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
                    <label className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 cursor-pointer">
                      Restore DB
                      <input type="file" accept=".db,.sqlite,.sqlite3" onChange={handleRestoreDatabase} className="hidden" />
                    </label>
                  </div>

                  <button
                    type="submit"
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-blue-600/20"
                  >
                    Save Changes
                  </button>
                </div>
              </form>

              {/* Application Form Defaults (Fresher / N/A & AI Skill Context) */}
              <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      Application Form Defaults & Fresher / N/A Filter Rules
                    </h3>
                    <p className="text-xs text-slate-400">
                      Used by modular AI skills for portal screening questions (Experience, Previous Company, CTC, Skills) and to strictly filter out non-fresher roles when set to Fresher.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setAppDefaults((prev: any) => ({
                        ...prev,
                        experience_level: "fresher",
                        years_of_experience: "0",
                        previous_company: "N/A",
                        previous_role: "N/A",
                        current_ctc: "N/A",
                        notice_period: "Immediate",
                      }))
                    }
                    className="px-3 py-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium"
                  >
                    Fill Fresher / N/A Presets
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Experience Level</label>
                    <select
                      value={appDefaults.experience_level || "fresher"}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, experience_level: e.target.value }))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="fresher">Fresher / Student (0 yrs / N/A)</option>
                      <option value="experienced">Experienced</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Years of Experience</label>
                    <input
                      type="text"
                      value={appDefaults.years_of_experience || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, years_of_experience: e.target.value }))}
                      placeholder="0 or N/A"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Previous Company</label>
                    <input
                      type="text"
                      value={appDefaults.previous_company || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, previous_company: e.target.value }))}
                      placeholder="N/A (Fresher)"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Previous Role</label>
                    <input
                      type="text"
                      value={appDefaults.previous_role || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, previous_role: e.target.value }))}
                      placeholder="N/A"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Current CTC</label>
                    <input
                      type="text"
                      value={appDefaults.current_ctc || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, current_ctc: e.target.value }))}
                      placeholder="N/A"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Notice Period</label>
                    <input
                      type="text"
                      value={appDefaults.notice_period || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, notice_period: e.target.value }))}
                      placeholder="Immediate"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Expected CTC</label>
                    <input
                      type="text"
                      value={appDefaults.expected_ctc || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, expected_ctc: e.target.value }))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Work Authorization</label>
                    <input
                      type="text"
                      value={appDefaults.work_authorization || ""}
                      onChange={(e) => setAppDefaults((p: any) => ({ ...p, work_authorization: e.target.value }))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <div className="text-xs">
                  <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Key Skills for Custom Questions (Comma-separated)</label>
                  <input
                    type="text"
                    value={appDefaults.key_skills || ""}
                    onChange={(e) => setAppDefaults((p: any) => ({ ...p, key_skills: e.target.value }))}
                    placeholder="Java, Python, Spring Boot, Django, MySQL, NLP, REST APIs"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                  />
                </div>

                <div className="text-xs">
                  <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Custom Q&amp;A Notes / Context for AI Form Skill</label>
                  <textarea
                    rows={2}
                    value={appDefaults.custom_qa_notes || ""}
                    onChange={(e) => setAppDefaults((p: any) => ({ ...p, custom_qa_notes: e.target.value }))}
                    placeholder="e.g. Final-year BCA student graduating 2026; open to internships, FTE, and relocation across Hyderabad/Bengaluru."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={saveApplicationDefaults}
                    disabled={savingDefaults}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {savingDefaults ? "Saving..." : "Save Application Defaults"}
                  </button>
                </div>
              </div>

              {/* Portal Browser Login Helper (Fixes Continue with Google / Workday Sign In walls) */}
              <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
                <div>
                  <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                    <KeyRound className="w-4 h-4 text-amber-400" />
                    Portal Persistent Browser Login (Fix Login / Google Auth Gates)
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    If automated applying stops at &ldquo;Continue with Google&rdquo; (Naukri) or &ldquo;Sign In&rdquo; (Workday/LinkedIn), click below to open the persistent browser window, sign in once manually, then close the window. Cookies remain saved for future applies.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2.5 text-xs">
                  <button
                    type="button"
                    onClick={() => launchBrowserLogin("naukri")}
                    disabled={launchingBrowser !== null}
                    className="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-xl font-medium"
                  >
                    {launchingBrowser === "naukri" ? "Launching Naukri..." : "Browser Login → Naukri"}
                  </button>
                  <button
                    type="button"
                    onClick={() => launchBrowserLogin("linkedin")}
                    disabled={launchingBrowser !== null}
                    className="px-4 py-2 bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/30 rounded-xl font-medium"
                  >
                    {launchingBrowser === "linkedin" ? "Launching LinkedIn..." : "Browser Login → LinkedIn"}
                  </button>
                  <button
                    type="button"
                    onClick={() => launchBrowserLogin("workday")}
                    disabled={launchingBrowser !== null}
                    className="px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-xl font-medium"
                  >
                    {launchingBrowser === "workday" ? "Launching Workday..." : "Browser Login → Workday"}
                  </button>
                </div>
              </div>

              {/* Workday Company Directory Manager */}
              <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-blue-400" />
                      Workday Company Directory ({workdayCompanies.length} Tenants)
                    </h3>
                    <p className="text-xs text-slate-400">
                      Configured career site tenants searched via public CXS REST endpoints (persisted in workday_companies.yaml)
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAddCompany(!showAddCompany)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 rounded-lg text-xs font-semibold"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add Company
                  </button>
                </div>

                {showAddCompany && (
                  <form onSubmit={handleAddCompany} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                    <span className="font-semibold text-xs text-slate-200 block">Add New Workday Tenant</span>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      <div>
                        <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Company Name</label>
                        <input
                          type="text"
                          placeholder="e.g. Target"
                          value={compName}
                          onChange={(e) => setCompName(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Tenant ID *</label>
                        <input
                          type="text"
                          placeholder="e.g. target"
                          value={compTenant}
                          onChange={(e) => setCompTenant(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                          required
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Site Name *</label>
                        <input
                          type="text"
                          placeholder="e.g. targetcareers"
                          value={compSite}
                          onChange={(e) => setCompSite(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                          required
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Career Site URL (Optional)</label>
                      <input
                        type="text"
                        placeholder="e.g. https://target.wd5.myworkdayjobs.com/targetcareers"
                        value={compUrl}
                        onChange={(e) => setCompUrl(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white"
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => setShowAddCompany(false)}
                        className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
                      >
                        Save Tenant
                      </button>
                    </div>
                  </form>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 text-xs">
                  {workdayCompanies.map((c: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-white block">{c.name || c.tenant}</span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {c.tenant} &bull; {c.site}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        {c.base_url && (
                          <a
                            href={c.base_url}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 text-slate-400 hover:text-white"
                            title="Open Career Site"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDeleteCompany(c.tenant)}
                          className="p-1.5 text-slate-500 hover:text-rose-400"
                          title="Remove Tenant"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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
                        onClick={() => setResumeSubTab("latex")}
                        className={`px-3 py-1.5 rounded-lg font-medium transition ${
                          resumeSubTab === "latex" ? "bg-slate-800 text-emerald-300" : "text-slate-400 hover:text-white"
                        }`}
                      >
                        LaTeX (.tex)
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

                        <div className="flex flex-wrap gap-2 pt-2">
                          <a
                            href={`${API_BASE}/resumes/${tailoredResume.id}/download/pdf`}
                            download
                            className="flex-1 text-center py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-600/20"
                          >
                            Download ATS PDF
                          </a>
                          <a
                            href={`${API_BASE}/resumes/${tailoredResume.id}/download/tex`}
                            download
                            className="flex-1 text-center py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl"
                          >
                            Download LaTeX (.tex)
                          </a>
                          <a
                            href={`${API_BASE}/resumes/${tailoredResume.id}/download/docx`}
                            download
                            className="flex-1 text-center py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl border border-slate-700"
                          >
                            Download ATS DOCX
                          </a>
                        </div>
                      </div>
                    )}

                    {/* Sub-Tab 1b: LaTeX (.tex) Source & Copy */}
                    {resumeSubTab === "latex" && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="font-semibold text-emerald-400">
                            Tailored LaTeX Resume (.tex) — compile cleanly on Overleaf or pdflatex:
                          </span>
                          <div className="flex items-center gap-2">
                            {tailoredResume.tailoring_notes?.latex_source && (
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(tailoredResume.tailoring_notes.latex_source);
                                  showToast("LaTeX code copied to clipboard!");
                                }}
                                className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-[11px]"
                              >
                                <Copy className="w-3 h-3" />
                                Copy LaTeX
                              </button>
                            )}
                            <a
                              href={`${API_BASE}/resumes/${tailoredResume.id}/download/tex`}
                              download
                              className="flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[11px] font-medium"
                            >
                              <Download className="w-3 h-3" />
                              Download .tex
                            </a>
                          </div>
                        </div>
                        <pre className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 font-mono text-[11px] overflow-x-auto max-h-72 overflow-y-auto whitespace-pre">
                          {tailoredResume.tailoring_notes?.latex_source || "LaTeX source not yet generated for this cached resume — regenerate tailoring after updating Master Profile."}
                        </pre>
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
                  Target Roles / Job Titles (Comma-separated or toggle presets below)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Software Engineer, AI Engineer, Full Stack"
                  value={scanRoles}
                  onChange={(e) => setScanRoles(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {ROLE_PRESETS.map((roleName) => {
                    const active = scanRoles.split(",").map((s) => s.trim().toLowerCase()).includes(roleName.toLowerCase());
                    return (
                      <button
                        key={roleName}
                        type="button"
                        onClick={() => setScanRoles((prev) => toggleCommaToken(prev, roleName))}
                        className={`px-2 py-0.5 rounded-md text-[10px] border transition ${
                          active
                            ? "bg-blue-600 text-white border-blue-500"
                            : "bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700 hover:text-slate-200"
                        }`}
                      >
                        {active ? `✓ ${roleName}` : `+ ${roleName}`}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Max Results Limit */}
              <div>
                <label className="text-slate-300 font-semibold block mb-1">
                  Max Jobs Per Portal
                </label>
                <select
                  value={scanLimit}
                  onChange={(e) => setScanLimit(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white"
                >
                  <option value={20}>20 per portal</option>
                  <option value={40}>40 per portal</option>
                  <option value={60}>60 per portal</option>
                  <option value={100}>100 per portal (Deep scan)</option>
                </select>
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
