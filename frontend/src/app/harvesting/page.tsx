"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  Globe,
  Play,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  XCircle,
  ShieldAlert,
  Calendar,
  Newspaper,
  ChevronDown,
  ChevronUp,
  Zap,
  History,
  Info,
  SlidersHorizontal,
  Check,
  Building2,
  Layers,
  Eye,
  ExternalLink,
  Download,
  X,
  FileText,
} from "lucide-react";

// ─────────────────────────────────────── Types

interface HarvestSource {
  id: string;
  name: string;
  publisher: string;
  language: string;
  language_code: string;
  region: string;
  source_type: string;
  requires_login: boolean;
  enabled: boolean;
  last_harvest_status?: string;
  last_harvest_at?: string;
  last_document_id?: string;
}

interface HarvestJob {
  job_id: string;
  target_date: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "PARTIAL" | "FAILED";
  total_sources: number;
  successful_sources: number;
  failed_sources: number;
  auth_required: number;
  manual_action_required: number;
  documents_downloaded: number;
  duration_seconds?: number;
  started_at?: string;
  completed_at?: string;
  triggered_by?: string;
  attempts?: any[];
}

interface HarvestDoc {
  document_id: string;
  file_name: string;
  publication?: string;
  edition?: string;
  publication_date?: string;
  language?: string;
  total_pages?: number;
  processing_status?: string;
  current_stage?: string;
  progress_percent?: number;
  overall_sentiment?: string;
  overall_risk_score?: number;
  created_at?: string;
  harvest_source_id?: string;
  harvest_source_name?: string;
  harvest_edition?: string;
  harvest_region?: string;
}

function normalizeStatus(status?: string): string {
  if (!status) return "";
  return status.replace(/^(AttemptStatus\.|HarvestStatus\.)/, "").toUpperCase();
}

function getStatusBadge(status?: string) {
  const s = normalizeStatus(status);
  switch (s) {
    case "COMPLETED":
    case "PIPELINE_SUBMITTED":
    case "VALIDATED":
      return <span className="badge badge-low">Success</span>;
    case "RUNNING":
    case "DOWNLOAD_STARTED":
      return <span className="badge badge-high animate-pulse">Running</span>;
    case "PARTIAL":
      return <span className="badge badge-medium">Partial</span>;
    case "AUTH_REQUIRED":
      return <span className="badge badge-medium">Auth Needed</span>;
    case "CAPTCHA_REQUIRED":
      return <span className="badge badge-critical">Captcha Blocked</span>;
    case "DUPLICATE":
      return <span className="badge badge-neutral">Duplicate</span>;
    case "FAILED":
    case "DOWNLOAD_FAILED":
    case "INVALID_PDF":
    case "EMPTY_FILE":
    case "TIMEOUT":
      return <span className="badge badge-critical">Failed</span>;
    default:
      return <span className="badge badge-neutral">{s || "Pending"}</span>;
  }
}

function getStatusIcon(status?: string) {
  const s = normalizeStatus(status);
  switch (s) {
    case "COMPLETED":
    case "PIPELINE_SUBMITTED":
    case "VALIDATED":
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
    case "RUNNING":
    case "DOWNLOAD_STARTED":
      return <Loader2 className="h-4 w-4 text-primary-600 animate-spin" />;
    case "PARTIAL":
      return <AlertCircle className="h-4 w-4 text-amber-500" />;
    case "AUTH_REQUIRED":
    case "CAPTCHA_REQUIRED":
      return <ShieldAlert className="h-4 w-4 text-orange-500" />;
    case "DUPLICATE":
      return <Info className="h-4 w-4 text-slate-400" />;
    case "FAILED":
    case "DOWNLOAD_FAILED":
    case "INVALID_PDF":
    case "EMPTY_FILE":
    case "TIMEOUT":
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-slate-400" />;
  }
}

function formatDate(iso?: string) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function getPdfUrl(item: { document_id?: string; file_path?: string }): string | null {
  if (item.document_id) {
    return `/storage/uploads/${item.document_id}.pdf`;
  }
  if (item.file_path) {
    const clean = item.file_path.replace(/\\/g, "/").replace(/^\.?\/?/, "");
    return `/${clean}`;
  }
  return null;
}

export default function HarvestingPage() {
  const [sources, setSources] = useState<HarvestSource[]>([]);
  const [jobs, setJobs] = useState<HarvestJob[]>([]);
  const [harvestDocs, setHarvestDocs] = useState<HarvestDoc[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [activeJob, setActiveJob] = useState<HarvestJob | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [targetDate, setTargetDate] = useState(() => {
    return new Date().toISOString().slice(0, 10);
  });
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<HarvestJob | null>(null);
  const [filterLanguage, setFilterLanguage] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"sources" | "downloads" | "history">("sources");

  // PDF Preview Modal state
  const [previewPdf, setPreviewPdf] = useState<{
    url: string;
    title: string;
    edition?: string;
    date?: string;
    docId?: string;
  } | null>(null);

  // Close modal on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPreviewPdf(null);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const [srcData, jobData, docData] = await Promise.all([
        api.getHarvestingSources().catch(() => []),
        api.getHarvestJobs(20).catch(() => []),
        api.getHarvestDocuments().catch(() => []),
      ]);
      setSources(srcData || []);
      setJobs(jobData || []);
      setHarvestDocs(docData || []);

      const running = (jobData || []).find((j: HarvestJob) => j.status === "RUNNING");
      if (running) {
        setActiveJob(running);
        setIsRunning(true);
      } else {
        setActiveJob(null);
        setIsRunning(false);
      }
    } catch (e: any) {
      console.error("Failed to load harvesting data:", e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll when running
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(async () => {
      try {
        const jobData = await api.getHarvestJobs(5);
        const running = jobData.find((j: HarvestJob) => j.status === "RUNNING");
        if (!running) {
          setIsRunning(false);
          setActiveJob(null);
          refresh();
        } else {
          setActiveJob(running);
        }
      } catch {
        // ignore network glitches while polling
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [isRunning, refresh]);

  // Load selected job details
  useEffect(() => {
    if (!selectedJobId) {
      setSelectedJob(null);
      return;
    }
    api.getHarvestJob(selectedJobId).then(setSelectedJob).catch(() => null);
  }, [selectedJobId, jobs]);

  const handleRunNow = async (scheduled = false) => {
    setIsRunning(true);
    setRunMessage(null);
    try {
      const result = scheduled
        ? await api.runScheduledHarvestNow()
        : await api.runHarvest({ target_date: targetDate });

      setRunMessage(
        `Harvest started (Job ID: ${result.job_id || "running"}). Automated pipeline is acquiring daily editions.`
      );
      setActiveJob({ job_id: result.job_id, status: "RUNNING" } as HarvestJob);
      setTimeout(refresh, 2000);
    } catch (e: any) {
      setRunMessage(`Harvest execution error: ${e.message}`);
      setIsRunning(false);
    }
  };

  const toggleSource = async (src: HarvestSource) => {
    // Optimistic update
    setSources((prev) =>
      prev.map((s) => (s.id === src.id ? { ...s, enabled: !src.enabled } : s))
    );
    try {
      await api.patchHarvestingSource(src.id, { enabled: !src.enabled });
    } catch (e: any) {
      // Revert on failure
      setSources((prev) =>
        prev.map((s) => (s.id === src.id ? { ...s, enabled: src.enabled } : s))
      );
      alert(`Failed to update source status: ${e.message}`);
    }
  };

  // Helper to find latest document for a source
  const findDocForSource = (sourceId: string) => {
    return harvestDocs.find((d) => d.harvest_source_id === sourceId);
  };

  // KPI Calculations
  const enabledCount = sources.filter((s) => s.enabled).length;
  const latestJob = jobs[0];
  const successfulToday = latestJob?.successful_sources ?? 0;
  const failedToday = latestJob?.failed_sources ?? 0;
  const authNeeded = sources.filter((s) => s.requires_login).length;

  const languages = Array.from(new Set(sources.map((s) => s.language).filter(Boolean))).sort();

  const filteredSources = sources.filter((s) => {
    if (filterLanguage !== "all" && s.language !== filterLanguage) return false;
    if (filterStatus === "enabled" && !s.enabled) return false;
    if (filterStatus === "disabled" && s.enabled) return false;
    if (filterStatus === "auth" && !s.requires_login) return false;
    return true;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
              <Newspaper className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              ePaper Harvesting
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Automated regional newspaper acquisition, edition tracking, and scheduled pipeline ingestion
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={refresh}
            disabled={isLoading}
            className="btn-secondary"
            title="Refresh Sources & Jobs"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="kpi-card primary">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-400 tracking-wider uppercase">
              Monitored Sources
            </span>
            <div className="p-2 rounded-xl bg-primary-50 text-primary-600">
              <Globe className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {enabledCount}{" "}
            <span className="text-sm font-semibold text-slate-400">/ {sources.length} active</span>
          </div>
        </div>

        <div className="kpi-card emerald">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-400 tracking-wider uppercase">
              Downloaded Broadsheets
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {harvestDocs.length}
            <span className="text-sm font-semibold text-slate-400 ml-1.5 font-normal">
              editions
            </span>
          </div>
        </div>

        <div className="kpi-card amber">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-400 tracking-wider uppercase">
              Attention Required
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <AlertCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {failedToday}
            <span className="text-sm font-semibold text-slate-400 ml-1.5 font-normal">
              errors
            </span>
          </div>
        </div>

        <div className="kpi-card violet">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-400 tracking-wider uppercase">
              Auth Protected
            </span>
            <div className="p-2 rounded-xl bg-violet-50 text-violet-600">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {authNeeded}
            <span className="text-sm font-semibold text-slate-400 ml-1.5 font-normal">
              subscriptions
            </span>
          </div>
        </div>
      </div>

      {/* ── Trigger Panel */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-1 rounded-md bg-amber-50 text-amber-600">
            <Zap className="w-4 h-4" />
          </div>
          <h2 className="text-base font-bold text-slate-900">
            Trigger Harvest Run
          </h2>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
          <div className="w-full sm:w-72">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              Target Publication Date (IST)
            </label>
            <div className="relative">
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-slate-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2.5 w-full sm:w-auto">
            <button
              onClick={() => handleRunNow(false)}
              disabled={isRunning}
              className="btn-primary"
            >
              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{isRunning ? "Acquiring Editions…" : "Run Daily Harvest"}</span>
            </button>

            <button
              onClick={() => handleRunNow(true)}
              disabled={isRunning}
              className="btn-secondary"
              title="Run as configured in daily automated scheduler"
            >
              <Clock className="w-4 h-4 text-slate-500" />
              <span>Run Scheduled Pipeline</span>
            </button>
          </div>
        </div>

        {runMessage && (
          <div className="mt-4 p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 text-xs font-medium text-slate-700 flex items-center gap-2">
            <Info className="w-4 h-4 text-primary-600 flex-shrink-0" />
            <span>{runMessage}</span>
          </div>
        )}

        {isRunning && activeJob && (
          <div className="mt-4 flex items-center gap-3 bg-sky-50 border border-sky-200/80 rounded-xl px-4 py-3 text-sky-800">
            <Loader2 className="h-4 w-4 text-sky-600 animate-spin flex-shrink-0" />
            <div className="text-sm font-medium">
              Harvest actively running — Job{" "}
              <span className="font-mono text-xs bg-sky-100 px-1.5 py-0.5 rounded text-sky-900 font-semibold">
                {activeJob.job_id}
              </span>
              . Data updates automatically upon completion.
            </div>
          </div>
        )}
      </div>

      {/* ── View Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-200/80 pb-2">
        <button
          onClick={() => setActiveTab("sources")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "sources"
              ? "bg-slate-900 text-white shadow-xs"
              : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/70"
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          <span>Newspaper Sources</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${
            activeTab === "sources" ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-600"
          }`}>
            {sources.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("downloads")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "downloads"
              ? "bg-slate-900 text-white shadow-xs"
              : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/70"
          }`}
        >
          <Eye className="w-3.5 h-3.5 text-primary-500" />
          <span>Downloaded Broadsheets</span>
          {harvestDocs.length > 0 && (
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
              activeTab === "downloads" ? "bg-emerald-600 text-white" : "bg-emerald-100 text-emerald-700"
            }`}>
              {harvestDocs.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === "history"
              ? "bg-slate-900 text-white shadow-xs"
              : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/70"
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Execution History</span>
          <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${
            activeTab === "history" ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-600"
          }`}>
            {jobs.length}
          </span>
        </button>
      </div>

      {/* ── TAB 1: Sources Registry Table */}
      {activeTab === "sources" && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-glass overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700">
                <Globe className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Newspaper Sources
                </h2>
                <p className="text-xs text-slate-500">
                  Configured regional publications and online ePaper endpoints ({filteredSources.length})
                </p>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Status Filter Chips */}
              <div className="flex items-center gap-1 p-1 bg-slate-100/80 rounded-xl border border-slate-200/60 text-xs font-medium">
                {[
                  { label: "All", value: "all" },
                  { label: "Active", value: "enabled" },
                  { label: "Disabled", value: "disabled" },
                  { label: "Auth Only", value: "auth" },
                ].map((f) => (
                  <button
                    key={f.value}
                    onClick={() => setFilterStatus(f.value)}
                    className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                      filterStatus === f.value
                        ? "bg-white text-slate-900 font-semibold shadow-xs border border-slate-200/80"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Language Selector */}
              <select
                value={filterLanguage}
                onChange={(e) => setFilterLanguage(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              >
                <option value="all">All Languages</option>
                {languages.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-600" />
              <p className="text-sm font-medium">Loading sources registry…</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50/80 border-b border-slate-100 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Source Name</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Publisher</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Language & Region</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Type</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Last Status</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700 text-center">View Paper</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700 text-right">Active</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredSources.map((src) => {
                    const matchedDoc = findDocForSource(src.id);
                    const docId = src.last_document_id || matchedDoc?.document_id;
                    const canView = Boolean(docId);

                    return (
                      <tr
                        key={src.id}
                        className={`hover:bg-slate-50/70 transition-colors ${
                          !src.enabled ? "opacity-60 bg-slate-50/30" : ""
                        }`}
                      >
                        <td className="py-3.5 px-4 font-semibold text-slate-900">
                          <div className="flex items-center gap-2.5">
                            {getStatusIcon(src.last_harvest_status)}
                            <div>
                              <div>{src.name}</div>
                              {src.requires_login && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200/70 rounded px-1.5 py-0.5 mt-0.5">
                                  Login Required
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">{src.publisher}</td>
                        <td className="py-3.5 px-4">
                          <div className="text-slate-900 font-medium">{src.language}</div>
                          <div className="text-xs text-slate-400">{src.region}</div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200/80">
                            {src.source_type}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <div>
                            {src.last_harvest_status ? (
                              getStatusBadge(src.last_harvest_status)
                            ) : (
                              <span className="text-xs text-slate-400">Never executed</span>
                            )}
                            {src.last_harvest_at && (
                              <div className="text-[11px] text-slate-400 mt-1">
                                {formatDate(src.last_harvest_at)}
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {canView ? (
                            <button
                              onClick={() =>
                                setPreviewPdf({
                                  url: `/storage/uploads/${docId}.pdf`,
                                  title: src.name,
                                  edition: matchedDoc?.edition || src.region,
                                  date: matchedDoc?.publication_date || src.last_harvest_at,
                                  docId: docId,
                                })
                              }
                              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-primary-50 hover:bg-primary-100 text-primary-700 border border-primary-200 shadow-2xs transition-colors cursor-pointer"
                              title={`View downloaded ${src.name} PDF`}
                            >
                              <Eye className="w-3.5 h-3.5 text-primary-600" />
                              <span>View</span>
                            </button>
                          ) : (
                            <span className="text-slate-300 text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => toggleSource(src)}
                            className={`w-11 h-6 inline-flex items-center rounded-full p-1 transition-colors duration-200 cursor-pointer ${
                              src.enabled ? "bg-primary-600" : "bg-slate-200"
                            }`}
                            title={src.enabled ? "Disable source" : "Enable source"}
                          >
                            <div
                              className={`bg-white w-4 h-4 rounded-full shadow-sm transform transition-transform duration-200 ${
                                src.enabled ? "translate-x-5" : "translate-x-0"
                              }`}
                            />
                          </button>
                        </td>
                      </tr>
                    );
                  })}

                  {filteredSources.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-400 text-sm">
                        No newspaper sources found matching the selected filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: Downloaded Broadsheets Archive */}
      {activeTab === "downloads" && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-glass overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  Downloaded Newspaper Broadsheets
                </h2>
                <p className="text-xs text-slate-500">
                  All editions downloaded by automated harvesters and submitted to the AI pipeline ({harvestDocs.length})
                </p>
              </div>
            </div>
          </div>

          {harvestDocs.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              <Newspaper className="w-10 h-10 mx-auto mb-2 text-slate-300" />
              <p className="font-semibold text-slate-700">No newspaper broadsheets downloaded yet</p>
              <p className="text-xs text-slate-400 mt-1">
                Trigger a harvest run above to acquire regional editions automatically.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50/80 border-b border-slate-100 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Publication & File</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Edition / Region</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Language</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Publication Date</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700">Pipeline Status</th>
                    <th className="py-3.5 px-4 font-semibold text-slate-700 text-right">View Broadsheet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {harvestDocs.map((doc) => {
                    const pdfUrl = `/storage/uploads/${doc.document_id}.pdf`;
                    const isCompleted = doc.processing_status === "COMPLETED";

                    return (
                      <tr key={doc.document_id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3.5 px-4 font-semibold text-slate-900">
                          <div className="flex items-center gap-2.5">
                            <div className="p-2 rounded-xl bg-primary-50 text-primary-600 flex-shrink-0">
                              <FileText className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="text-slate-900 font-bold">
                                {doc.publication || doc.harvest_source_name || doc.file_name}
                              </div>
                              <div className="text-[11px] font-mono text-slate-400">
                                {doc.file_name}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">
                          <span className="capitalize font-medium text-slate-800">
                            {doc.edition || doc.harvest_edition || "Main"}
                          </span>
                          {(doc.harvest_region) && (
                            <span className="text-xs text-slate-400 block">
                              {doc.harvest_region}
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="uppercase font-mono text-xs px-2 py-0.5 rounded bg-slate-100 font-bold text-slate-700">
                            {doc.language}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-slate-700 font-medium">
                          {doc.publication_date || "—"}
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`badge ${
                              isCompleted
                                ? "badge-low"
                                : doc.processing_status === "FAILED"
                                ? "badge-critical"
                                : "badge-neutral"
                            }`}
                          >
                            {isCompleted && <CheckCircle2 className="w-3 h-3" />}
                            {doc.processing_status || "QUEUED"}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() =>
                                setPreviewPdf({
                                  url: pdfUrl,
                                  title: doc.publication || doc.harvest_source_name || "Newspaper Broadsheet",
                                  edition: doc.edition || doc.harvest_edition,
                                  date: doc.publication_date,
                                  docId: doc.document_id,
                                })
                              }
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-primary-600 hover:bg-primary-700 text-white shadow-xs transition-colors cursor-pointer"
                              title="View paper in reader modal"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>View Paper</span>
                            </button>

                            <a
                              href={pdfUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-primary-600 hover:bg-slate-100 transition-colors"
                              title="Open PDF directly in new tab"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </a>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: Execution History & Jobs */}
      {activeTab === "history" && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-glass overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700">
              <History className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Harvest Execution History
              </h2>
              <p className="text-xs text-slate-500">
                Audit log of daily scheduled runs, acquired PDFs, and source retry attempts
              </p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {jobs.length === 0 && (
              <div className="py-12 text-center text-slate-400 text-sm">
                No harvest jobs executed yet. Trigger a run above to start archiving editions.
              </div>
            )}

            {jobs.map((job) => {
              const isExpanded = selectedJobId === job.job_id;
              return (
                <div key={job.job_id} className="transition-colors">
                  <button
                    onClick={() => setSelectedJobId(isExpanded ? null : job.job_id)}
                    className="w-full flex items-center gap-4 px-6 py-4.5 hover:bg-slate-50/70 transition-colors text-left cursor-pointer"
                  >
                    <div className="flex-shrink-0">
                      {getStatusIcon(job.status)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-bold text-sm text-slate-900">
                          Date: {job.target_date}
                        </span>
                        {getStatusBadge(job.status)}
                        {job.triggered_by && (
                          <span className="text-xs text-slate-400 font-medium">
                            via {job.triggered_by}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 mt-1 font-medium flex items-center gap-3">
                        <span className="text-emerald-700">
                          {job.successful_sources ?? 0} Succeeded
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-red-600">
                          {job.failed_sources ?? 0} Failed
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-slate-600">
                          {job.documents_downloaded ?? 0} Documents Archived
                        </span>
                        <span className="text-slate-300">·</span>
                        <span className="text-slate-500">
                          {job.duration_seconds
                            ? `${job.duration_seconds.toFixed(1)}s runtime`
                            : "in progress"}
                        </span>
                      </div>
                    </div>

                    <div className="text-xs font-medium text-slate-400 hidden md:block">
                      {formatDate(job.started_at)}
                    </div>

                    <div className="flex-shrink-0 text-slate-400">
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </button>

                  {/* Expanded Attempt Details */}
                  {isExpanded && selectedJob && (
                    <div className="px-6 pb-6 bg-slate-50/50">
                      <div className="rounded-xl border border-slate-200/80 bg-white overflow-hidden shadow-xs">
                        <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200/80 text-xs font-bold text-slate-700 tracking-wide uppercase">
                          Edition Downloads for Job {job.job_id}
                        </div>
                        <table className="w-full text-xs text-left text-slate-600">
                          <thead className="bg-slate-50/50 border-b border-slate-100 font-semibold text-slate-500">
                            <tr>
                              <th className="px-4 py-2.5">Source</th>
                              <th className="px-4 py-2.5">Edition</th>
                              <th className="px-4 py-2.5">Language</th>
                              <th className="px-4 py-2.5">Status</th>
                              <th className="px-4 py-2.5 hidden md:table-cell">Details / Error</th>
                              <th className="px-4 py-2.5 text-right">View Paper</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {(selectedJob.attempts || []).map((a: any) => {
                              const pdfUrl = getPdfUrl(a);
                              return (
                                <tr key={a.attempt_id} className="hover:bg-slate-50/70">
                                  <td className="px-4 py-2.5 text-slate-900 font-semibold">
                                    {a.source_name}
                                  </td>
                                  <td className="px-4 py-2.5 text-slate-600">
                                    {a.edition_name || "Main Edition"}
                                  </td>
                                  <td className="px-4 py-2.5 text-slate-600">
                                    {a.language}
                                  </td>
                                  <td className="px-4 py-2.5">
                                    {getStatusBadge(a.status)}
                                  </td>
                                  <td className="px-4 py-2.5 text-slate-500 hidden md:table-cell max-w-xs truncate font-mono text-[11px]">
                                    {a.error_message || a.discovered_url || "—"}
                                  </td>
                                  <td className="px-4 py-2.5 text-right">
                                    {pdfUrl ? (
                                      <div className="flex items-center justify-end gap-1.5">
                                        <button
                                          onClick={() =>
                                            setPreviewPdf({
                                              url: pdfUrl,
                                              title: a.source_name,
                                              edition: a.edition_name,
                                              date: a.target_date,
                                              docId: a.document_id,
                                            })
                                          }
                                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-primary-50 hover:bg-primary-100 text-primary-700 border border-primary-200 transition-colors shadow-2xs cursor-pointer"
                                          title="View downloaded newspaper PDF"
                                        >
                                          <Eye className="w-3.5 h-3.5 text-primary-600" />
                                          <span>View</span>
                                        </button>
                                        <a
                                          href={pdfUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="p-1 rounded-lg text-slate-400 hover:text-primary-600 hover:bg-slate-100 transition-colors"
                                          title="Open PDF in new tab"
                                        >
                                          <ExternalLink className="w-3.5 h-3.5" />
                                        </a>
                                      </div>
                                    ) : (
                                      <span className="text-slate-300 text-[11px]">—</span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                            {(selectedJob.attempts || []).length === 0 && (
                              <tr>
                                <td
                                  colSpan={6}
                                  className="px-4 py-6 text-center text-slate-400 font-medium"
                                >
                                  No attempt details recorded for this run.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── PDF Preview Modal with Eye Button Trigger */}
      {previewPdf && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-xs animate-fade-in"
          onClick={() => setPreviewPdf(null)}
        >
          <div
            className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 rounded-xl bg-primary-100 text-primary-700 flex-shrink-0">
                  <Newspaper className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-bold text-slate-900 truncate">
                      {previewPdf.title}
                    </h3>
                    {previewPdf.edition && (
                      <span className="text-xs bg-slate-200/80 text-slate-700 font-semibold px-2 py-0.5 rounded capitalize">
                        {previewPdf.edition}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5 flex-wrap">
                    {previewPdf.date && <span>Date: {previewPdf.date}</span>}
                    {previewPdf.docId && (
                      <>
                        <span>·</span>
                        <span className="font-mono text-[11px] text-slate-400">
                          ID: {previewPdf.docId.substring(0, 8)}...
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                <a
                  href={previewPdf.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
                  title="Open PDF in a new browser tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Open in New Tab</span>
                </a>
                <a
                  href={previewPdf.url}
                  download
                  className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
                  title="Download PDF"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Download</span>
                </a>
                <button
                  onClick={() => setPreviewPdf(null)}
                  className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Close viewer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* PDF Viewer Frame */}
            <div className="flex-1 bg-slate-100 p-2 sm:p-4 overflow-hidden flex flex-col">
              <iframe
                src={previewPdf.url}
                className="w-full h-[72vh] rounded-xl border border-slate-200/80 bg-white shadow-inner"
                title={`Preview of ${previewPdf.title}`}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
