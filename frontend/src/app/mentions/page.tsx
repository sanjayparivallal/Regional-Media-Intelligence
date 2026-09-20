"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  Tag,
  Search,
  Building2,
  Newspaper,
  ExternalLink,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ArrowUpRight,
  RefreshCw,
} from "lucide-react";

interface BrandMention {
  id: string;
  brand_name: string;
  headline: string;
  snippet: string;
  publication_name: string;
  language: string;
  sentiment: "positive" | "neutral" | "negative";
  risk_score: number;
  date: string;
  page_number: number;
}

export default function MentionsPage() {
  const [mentions, setMentions] = useState<BrandMention[]>([]);
  const [search, setSearch] = useState("");
  const [selectedSentiment, setSelectedSentiment] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMentions({ limit: "100" });
      setMentions(
        data.map((m: any) => ({
          id: m.id,
          brand_name: m.brand_name || "Unknown",
          headline: m.headline || m.snippet || "No headline",
          snippet: m.snippet || "",
          publication_name: m.publication_name || "Regional Broadsheet",
          language: (m.language || "hi").toUpperCase(),
          sentiment: m.sentiment || "neutral",
          risk_score: m.risk_score || 0,
          date: m.date
            ? new Date(m.date).toLocaleString("en-IN", {
                dateStyle: "short",
                timeStyle: "short",
              })
            : "—",
          page_number: m.page_number || 1,
        }))
      );
    } catch (e: any) {
      console.error("Failed to load mentions:", e);
      setError(e.message || "Failed to load mentions");
      setMentions([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = mentions.filter((m) => {
    const matchesSearch =
      m.brand_name.toLowerCase().includes(search.toLowerCase()) ||
      m.headline.toLowerCase().includes(search.toLowerCase()) ||
      m.publication_name.toLowerCase().includes(search.toLowerCase());
    const matchesSentiment =
      selectedSentiment === "all" || m.sentiment === selectedSentiment;
    return matchesSearch && matchesSentiment;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <Tag className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Brand Mentions Stream
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Continuous detection of monitored brand entities across regional newspaper scans
        </p>
      </div>

      {/* Top Stat Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card primary">
          <p className="text-xs font-semibold text-slate-500 uppercase">Total Mentions</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">{mentions.length}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Across active editions</p>
        </div>
        <div className="kpi-card coral">
          <p className="text-xs font-semibold text-slate-500 uppercase">Negative Sentiment</p>
          <p className="text-2xl font-extrabold text-red-600 mt-1">
            {mentions.filter((m) => m.sentiment === "negative").length}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Flagged for risk review</p>
        </div>
        <div className="kpi-card emerald">
          <p className="text-xs font-semibold text-slate-500 uppercase">Positive Sentiment</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">
            {mentions.filter((m) => m.sentiment === "positive").length}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Favorable coverage</p>
        </div>
        <div className="kpi-card violet">
          <p className="text-xs font-semibold text-slate-500 uppercase">Brands Tracked</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">
            {new Set(mentions.map((m) => m.brand_name)).size}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Configured profiles</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="glass-card p-4 flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by brand, article text, or newspaper name..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 rounded-xl text-sm border border-slate-200/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
          />
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <div className="flex items-center gap-1.5">
            {["all", "negative", "neutral", "positive"].map((s) => (
              <button
                key={s}
                onClick={() => setSelectedSentiment(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${
                  selectedSentiment === s
                    ? "bg-slate-900 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
          <button
            onClick={load}
            className="p-2 rounded-lg text-slate-500 hover:text-primary-600 hover:bg-primary-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-2xl bg-slate-200/70 animate-pulse" />
          ))}
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="glass-card p-10 text-center">
          <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-slate-700">{error}</p>
          <p className="text-xs text-slate-400 mt-1">
            Upload and process newspaper editions to see brand mentions here.
          </p>
          <button onClick={load} className="btn-primary text-xs mt-4">
            Retry
          </button>
        </div>
      )}

      {/* Mentions List Cards */}
      {!loading && !error && (
        <div className="space-y-3">
          {filtered.map((m, idx) => (
            <div
              key={`${m.id}-${idx}`}
              className="glass-card p-5 hover:border-slate-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-md border border-primary-200/60">
                    {m.brand_name}
                  </span>
                  <span className={`badge badge-${m.sentiment}`}>
                    {m.sentiment.toUpperCase()}
                  </span>
                  {m.risk_score >= 60 && (
                    <span className="badge badge-critical">
                      RISK {Math.round(m.risk_score)}
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-bold text-slate-900">{m.headline}</h3>
                {m.snippet && (
                  <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                    {m.snippet}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-3 pt-2 text-xs text-slate-400">
                  <span className="flex items-center gap-1 font-medium text-slate-600">
                    <Newspaper className="w-3.5 h-3.5 text-slate-400" />
                    {m.publication_name}
                  </span>
                  <span>•</span>
                  <span className="font-mono uppercase">{m.language}</span>
                  <span>•</span>
                  <span>Page {m.page_number}</span>
                  <span>•</span>
                  <span>{m.date}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0">
                <Link href="/evidence" className="btn-secondary text-xs">
                  <span>View Evidence</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}

          {filtered.length === 0 && !loading && (
            <div className="glass-card p-16 text-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
                <Tag className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-800">
                {mentions.length === 0 ? "No mentions yet" : "No mentions found"}
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                {mentions.length === 0
                  ? "Brand mentions are detected automatically when newspapers are processed. Upload an edition to get started."
                  : "No brand mentions match your search query or sentiment filter."}
              </p>
              {mentions.length === 0 && (
                <Link href="/ingestion" className="btn-primary text-xs mt-4 inline-flex">
                  Upload Edition
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
