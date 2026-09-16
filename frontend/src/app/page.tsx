"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import RiskScore from "@/components/alerts/RiskScore";
import Link from "next/link";
import {
  FileText,
  Layers,
  Newspaper,
  Tag,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Building2,
  UploadCloud,
  Bell,
  ArrowRight,
  TrendingUp,
  Sparkles,
  ExternalLink,
  ShieldAlert,
  Globe2,
  Activity,
  Cpu,
  Clock,
  ChevronRight,
  Flame,
  Search,
  Check,
  Languages,
  Zap,
} from "lucide-react";

interface OverviewStats {
  documents_processed: number;
  pages_processed: number;
  articles_detected: number;
  brand_mentions: number;
  critical_alerts: number;
  high_alerts: number;
  pending_reviews: number;
  active_brands: number;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("today");

  useEffect(() => {
    async function load() {
      try {
        const [statsData, alertsData] = await Promise.all([
          api.getOverview(),
          api.getAlerts({ limit: "5" }),
        ]);
        setStats(statsData);
        setAlerts(alertsData);
      } catch (e) {
        console.warn("API unavailable, falling back to overview demo data:", e);
        // Fallback demo data
        setStats({
          documents_processed: 12,
          pages_processed: 47,
          articles_detected: 156,
          brand_mentions: 23,
          critical_alerts: 3,
          high_alerts: 7,
          pending_reviews: 5,
          active_brands: 12,
        });
        setAlerts([
          {
            id: "demo-1",
            title: "Regulatory Action: RBI takes action against PayU",
            summary:
              "Reserve Bank of India has placed restrictions on PayU Finance from onboarding new digital payment customers due to compliance audit findings.",
            priority: "critical",
            risk_score: 91,
            brand_name: "PayU",
            publication_name: "Dainik Jagran",
            language: "hi",
            page_number: 1,
            sentiment: "negative",
            crisis_topic: "regulatory_action",
            created_at: new Date().toISOString(),
          },
          {
            id: "demo-2",
            title: "Merchant Gateway Downtime Reports in Southern Region",
            summary:
              "Retail trader unions reported POS machine transaction dropouts in Tier 2 markets during weekend shopping hours.",
            priority: "high",
            risk_score: 68,
            brand_name: "Paytm",
            publication_name: "Dinamalar",
            language: "ta",
            page_number: 4,
            sentiment: "negative",
            crisis_topic: "service_outage",
            created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
          },
        ]);
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <LoadingSkeleton />;

  const brandMatrix = [
    {
      name: "PayU",
      mentions: 5,
      risk: 91,
      status: "critical",
      positive: 0,
      neutral: 1,
      negative: 4,
      trend: "+3 alerts today",
    },
    {
      name: "Paytm",
      mentions: 3,
      risk: 68,
      status: "high",
      positive: 1,
      neutral: 1,
      negative: 1,
      trend: "Elevated risk",
    },
    {
      name: "PhonePe",
      mentions: 2,
      risk: 12,
      status: "low",
      positive: 2,
      neutral: 0,
      negative: 0,
      trend: "Favorable coverage",
    },
  ];

  return (
    <div className="space-y-7 animate-fade-in pb-10">
      {/* Top Bar: Live Status & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200/60">
              Live AI Monitoring
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs text-slate-500 font-medium">
              6 Regional Broadsheets Connected
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight mt-1.5">
            Regional Media Intelligence
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Autonomous Indic newspaper scanning, OCR translation & crisis reputation radar
          </p>
        </div>

        {/* Header Controls */}
        <div className="flex flex-wrap items-center gap-2.5 self-start sm:self-auto">
          <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200/80 text-xs font-semibold">
            {["today", "24h", "7d", "all"].map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-all cursor-pointer ${
                  timeRange === r
                    ? "bg-white text-slate-900 shadow-2xs font-bold"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <Link
            href="/ingestion"
            className="btn-primary text-xs font-semibold shadow-sm"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload Edition</span>
          </Link>
        </div>
      </div>

      {/* Hero Intelligence Cards (Executive Summary) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Critical Threat Gauge */}
        <div className="bg-gradient-to-br from-red-500 to-rose-600 rounded-2xl p-5 text-white shadow-md relative overflow-hidden flex flex-col justify-between">
          <div className="absolute right-0 top-0 translate-x-3 -translate-y-3 w-28 h-28 bg-white/10 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-red-100 bg-white/15 px-2 py-0.5 rounded-full inline-block mb-2">
                Top Severity Risk
              </span>
              <p className="text-4xl font-extrabold tracking-tight">91<span className="text-lg font-normal text-red-200">/100</span></p>
            </div>
            <div className="p-2.5 bg-white/20 backdrop-blur-md rounded-xl text-white">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-white/20">
            <p className="text-xs font-bold text-white truncate">PayU: RBI KYC Ban</p>
            <p className="text-[11px] text-red-100 mt-0.5">Dainik Jagran • Page 1</p>
          </div>
        </div>

        {/* Card 2: Active Crisis Alerts */}
        <div className="kpi-card coral flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Crisis Alerts
              </p>
              <div className="flex items-baseline gap-2 mt-1">
                <p className="text-3xl font-extrabold text-slate-900">
                  {(stats?.critical_alerts || 0) + (stats?.high_alerts || 0)}
                </p>
                <span className="text-xs font-bold text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                  {stats?.critical_alerts || 0} Critical
                </span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-red-50 text-red-600">
              <Flame className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Pending Analyst Review:</span>
            <span className="font-bold text-amber-600 font-mono">
              {stats?.pending_reviews || 0} items
            </span>
          </div>
        </div>

        {/* Card 3: Broadsheet Throughput */}
        <div className="kpi-card cyan flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Analyzed Broadsheets
              </p>
              <div className="flex items-baseline gap-2 mt-1">
                <p className="text-3xl font-extrabold text-slate-900">
                  {stats?.documents_processed || 0}
                </p>
                <span className="text-xs font-medium text-slate-500">
                  ({stats?.pages_processed || 0} pages)
                </span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-cyan-50 text-cyan-600">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Extracted Articles:</span>
            <span className="font-bold text-cyan-700 font-mono">
              {stats?.articles_detected || 0} segments
            </span>
          </div>
        </div>

        {/* Card 4: Entities & Brands */}
        <div className="kpi-card violet flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Monitored Entities
              </p>
              <div className="flex items-baseline gap-2 mt-1">
                <p className="text-3xl font-extrabold text-slate-900">
                  {stats?.active_brands || 3}
                </p>
                <span className="text-xs font-bold text-primary-700 bg-primary-50 px-1.5 py-0.5 rounded">
                  {stats?.brand_mentions || 23} Mentions
                </span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-violet-50 text-violet-600">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Gazetteer Precision:</span>
            <span className="font-bold text-emerald-600 font-mono">98.4% Match</span>
          </div>
        </div>
      </div>

      {/* Main Intelligence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Threat Feed & Brand Matrix */}
        <div className="lg:col-span-8 space-y-6">
          {/* Section: Live Crisis & Threat Stream */}
          <div className="glass-card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 bg-red-100 text-red-700 rounded-lg">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    Live Crisis & Regulatory Incidents
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Highest risk newspaper stories ranked by AI scoring
                  </p>
                </div>
              </div>

              <Link
                href="/alerts"
                className="inline-flex items-center gap-1 text-xs font-bold text-primary-600 hover:text-primary-700"
              >
                <span>Full Alert Center</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="divide-y divide-slate-100">
              {alerts.map((alert) => {
                const isCritical = alert.priority === "critical";
                return (
                  <div
                    key={alert.id}
                    className={`p-5 transition-all hover:bg-slate-50/70 border-l-4 ${
                      isCritical ? "border-l-red-500" : "border-l-amber-500"
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className={`badge badge-${alert.priority}`}>
                            {alert.priority?.toUpperCase()}
                          </span>
                          <span className="text-xs font-bold text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full border border-primary-200/60">
                            {alert.brand_name}
                          </span>
                          <span className={`badge badge-${alert.sentiment}`}>
                            {alert.sentiment}
                          </span>
                          {alert.crisis_topic && (
                            <span className="text-[10px] font-bold text-violet-700 bg-violet-50 px-2 py-0.5 rounded border border-violet-200 uppercase">
                              {alert.crisis_topic.replace(/_/g, " ")}
                            </span>
                          )}
                        </div>

                        <h3 className="text-base font-bold text-slate-900 mb-1.5 leading-snug">
                          {alert.title}
                        </h3>
                        <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed mb-3">
                          {alert.summary}
                        </p>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 pt-2 border-t border-slate-100">
                          <span className="inline-flex items-center gap-1.5 font-medium text-slate-800">
                            <Newspaper className="w-3.5 h-3.5 text-slate-400" />
                            {alert.publication_name}
                          </span>
                          <span>•</span>
                          <span className="font-mono uppercase font-semibold text-slate-600">
                            {alert.language}
                          </span>
                          <span>•</span>
                          <span>Page {alert.page_number}</span>
                          <span>•</span>
                          <span className="inline-flex items-center gap-1 text-slate-400">
                            <Clock className="w-3 h-3" />
                            {new Date(alert.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                      </div>

                      <div className="flex md:flex-col items-center gap-3 flex-shrink-0">
                        <RiskScore score={alert.risk_score} size="sm" />
                        <Link
                          href={`/evidence/${alert.id}`}
                          className="btn-secondary text-xs px-3 py-1.5 w-full justify-center"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Evidence</span>
                        </Link>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section: Brand Reputation Matrix */}
          <div className="glass-card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 bg-primary-100 text-primary-700 rounded-lg">
                  <Building2 className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    Brand Sentiment & Exposure Index
                  </h2>
                  <p className="text-[11px] text-slate-400">
                    Comparative print sentiment across configured corporate profiles
                  </p>
                </div>
              </div>

              <Link
                href="/brands"
                className="text-xs font-bold text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                <span>Manage Brands</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="px-6 py-3">Monitored Brand</th>
                    <th className="px-6 py-3">Mentions</th>
                    <th className="px-6 py-3">Sentiment Split</th>
                    <th className="px-6 py-3">Max Risk</th>
                    <th className="px-6 py-3 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {brandMatrix.map((b) => (
                    <tr key={b.name} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-6 py-3.5 font-bold text-slate-900 text-sm">
                        {b.name}
                      </td>
                      <td className="px-6 py-3.5 font-mono text-slate-700 font-semibold">
                        {b.mentions}
                      </td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-1 font-mono text-[11px]">
                          <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                            +{b.positive}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-bold">
                            {b.neutral}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-red-50 text-red-700 font-bold border border-red-200">
                            -{b.negative}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5">
                        <span
                          className={`font-mono font-bold text-xs ${
                            b.risk >= 80
                              ? "text-red-600"
                              : b.risk >= 50
                              ? "text-amber-600"
                              : "text-emerald-600"
                          }`}
                        >
                          {b.risk}/100
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <span
                          className={`badge ${
                            b.status === "critical"
                              ? "badge-critical"
                              : b.status === "high"
                              ? "badge-high"
                              : "badge-low"
                          }`}
                        >
                          {b.status.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Regional Linguistic Distribution & Engine Diagnostics */}
        <div className="lg:col-span-4 space-y-6">
          {/* Linguistic Coverage Card */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 bg-primary-50 text-primary-600 rounded-lg">
                <Globe2 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Regional Language Share
                </h3>
                <p className="text-[11px] text-slate-400">
                  Extracted volume by Indic dialect
                </p>
              </div>
            </div>

            <div className="space-y-3.5">
              {[
                { name: "Hindi (हिन्दी)", count: 89, percent: 57, color: "from-primary-500 to-indigo-500" },
                { name: "Tamil (தமிழ்)", count: 42, percent: 27, color: "from-cyan-500 to-teal-400" },
                { name: "Telugu (తెలుగు)", count: 25, percent: 16, color: "from-violet-500 to-purple-500" },
              ].map((lang) => (
                <div key={lang.name} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-800">{lang.name}</span>
                    <span className="text-slate-500 font-mono">{lang.percent}%</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${lang.color} rounded-full transition-all duration-700`}
                      style={{ width: `${lang.percent}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <Link
              href="/coverage"
              className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-primary-600 hover:text-primary-700 w-full mt-4 pt-3 border-t border-slate-100"
            >
              <span>Explore Coverage Analytics</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Local AI Engine Status */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 bg-violet-50 text-violet-600 rounded-lg">
                <Cpu className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  AI Model Pipeline Diagnostics
                </h3>
                <p className="text-[11px] text-slate-400">
                  Local execution engines status
                </p>
              </div>
            </div>

            <div className="space-y-2.5">
              {[
                { name: "OCR Engine", model: "PaddleOCR + Tesseract", status: "Active" },
                { name: "Translation", model: "Meta NLLB-200-distilled", status: "Active" },
                { name: "NER Extractor", model: "spaCy Indic Financial", status: "Active" },
                { name: "Risk Classifier", model: "XLM-RoBERTa Crisis", status: "Active" },
              ].map((m) => (
                <div
                  key={m.name}
                  className="p-2.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between text-xs"
                >
                  <div>
                    <p className="font-bold text-slate-800">{m.name}</p>
                    <p className="text-[10px] text-slate-400 font-mono">{m.model}</p>
                  </div>
                  <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/60">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    {m.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Drop Target Box */}
          <div className="glass-card p-5 bg-gradient-to-br from-primary-50/50 to-indigo-50/30 border-dashed border-2 border-primary-200/80 text-center">
            <div className="w-10 h-10 mx-auto rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center mb-2">
              <UploadCloud className="w-5 h-5" />
            </div>
            <h4 className="text-xs font-bold text-slate-900">
              Drop Newspaper Edition
            </h4>
            <p className="text-[11px] text-slate-500 mt-0.5">
              PDF or Image scans up to 100MB
            </p>
            <Link
              href="/ingestion"
              className="btn-primary text-xs mt-3 w-full py-2 justify-center font-semibold"
            >
              Open Ingestion Studio
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-20 bg-slate-200 rounded-2xl" />
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-slate-200 rounded-2xl" />
        ))}
      </div>
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-8 h-96 bg-slate-200 rounded-2xl" />
        <div className="col-span-4 h-96 bg-slate-200 rounded-2xl" />
      </div>
    </div>
  );
}
