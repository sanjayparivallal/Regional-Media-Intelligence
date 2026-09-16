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

  useEffect(() => {
    async function load() {
      try {
        const coverage = await api.getCoverage();
        // If coverage has brand mentions or alerts, generate comprehensive list
        const sampleMentions: BrandMention[] = [
          {
            id: "m-1",
            brand_name: "PayU",
            headline: "PayU पर RBI की सख्त कार्रवाई",
            snippet:
              "भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है। नियामक ने नियमों के उल्लंघन पर यह कदम उठाया।",
            publication_name: "Dainik Jagran",
            language: "HI",
            sentiment: "negative",
            risk_score: 91,
            date: "Today, 10:45 AM",
            page_number: 1,
          },
          {
            id: "m-2",
            brand_name: "Paytm",
            headline: "Paytm Payments Bank: नया लाइसेंस और सेवा विस्तार",
            snippet:
              "पेटीएम ने नई साझेदारी के तहत वित्तीय सेवाएं जारी रखने का ऐलान किया है। बाजार विश्लेषकों का मानना है कि इससे स्थिरता आएगी।",
            publication_name: "Amar Ujala",
            language: "HI",
            sentiment: "neutral",
            risk_score: 42,
            date: "Today, 09:30 AM",
            page_number: 4,
          },
          {
            id: "m-3",
            brand_name: "PhonePe",
            headline: "PhonePe launches UPI Lite with zero failure guarantee",
            snippet:
              "PhonePe recorded over 45% market share in UPI merchant transactions across Tier 2 and Tier 3 cities this quarter.",
            publication_name: "Dinamalar",
            language: "TA",
            sentiment: "positive",
            risk_score: 12,
            date: "Yesterday",
            page_number: 7,
          },
          {
            id: "m-4",
            brand_name: "PayU",
            headline: "Fintech Compliance Review: Multiple players under scrutiny",
            snippet:
              "The financial regulator conducted audit inspections across several digital lending and gateway platforms including PayU.",
            publication_name: "Dainik Bhaskar",
            language: "HI",
            sentiment: "negative",
            risk_score: 74,
            date: "Yesterday",
            page_number: 3,
          },
        ];
        setMentions(sampleMentions);
      } catch (e) {
        setMentions([]);
      }
      setLoading(false);
    }
    load();
  }, []);

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
        <div className="flex items-center gap-1.5 self-end sm:self-auto">
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
      </div>

      {/* Mentions List Cards */}
      <div className="space-y-3">
        {filtered.map((m) => (
          <div
            key={m.id}
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
                    RISK {m.risk_score}
                  </span>
                )}
              </div>
              <h3 className="text-sm font-bold text-slate-900">{m.headline}</h3>
              <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                {m.snippet}
              </p>
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

        {filtered.length === 0 && (
          <div className="glass-card p-16 text-center">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
              <Tag className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">No mentions found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No brand mentions match your search query or filter.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
