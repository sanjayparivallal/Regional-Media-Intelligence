"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  Search,
  Newspaper,
  Globe,
  FileText,
  ExternalLink,
  Sparkles,
  ArrowRight,
  Filter,
} from "lucide-react";

export default function EvidenceExplorerPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (overrideQuery?: string) => {
    const q = overrideQuery ?? query;
    if (!q.trim()) return;
    setSearched(true);
    setLoading(true);
    try {
      const data = await api.search(q);
      setResults(data.articles || []);
    } catch {
      setResults([
        {
          id: "demo-1",
          headline: "PayU पर RBI की कार्रवाई: डिजिटल भुगतान पर प्रतिबंध",
          publication_name: "Dainik Jagran",
          language: "hi",
          page_number: 1,
          detected_language: "hi",
          ocr_confidence: 92.5,
          sentiment: "negative",
          body_snippet:
            "भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है। RBI ने कहा कि कंपनी ने KYC नियमों का उल्लंघन किया है।",
        },
      ]);
    }
    setLoading(false);
  };

  const suggestions = ["PayU", "RBI Regulation", "KYC Violation", "UPI Failure", "Paytm"];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <Search className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Evidence Explorer
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Semantic search across all extracted OCR text, entity mentions, and translated clippings
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="glass-card p-4 space-y-3">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search by keywords, regulations, entities, or extracted phrases..."
              className="w-full pl-11 pr-4 py-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 shadow-2xs transition-all"
            />
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="btn-primary px-6"
          >
            <span>Search</span>
          </button>
        </div>

        {/* Quick Suggestions */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-400">Quick filters:</span>
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => {
                setQuery(s);
                handleSearch(s);
              }}
              className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 hover:bg-primary-50 hover:text-primary-700 transition-colors font-medium cursor-pointer"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Search Results */}
      {searched && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 px-1">
            <span>
              {results.length} result{results.length !== 1 ? "s" : ""} retrieved
            </span>
          </div>

          <div className="space-y-3">
            {results.map((article, i) => (
              <div
                key={article.id || i}
                className="glass-card p-6 hover:border-slate-300 transition-all"
              >
                <div className="flex flex-col md:flex-row md:items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center flex-shrink-0">
                    <Newspaper className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="font-semibold text-xs text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full border border-primary-200/60">
                        {article.publication_name}
                      </span>
                      <span className="font-mono text-xs uppercase bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                        {article.detected_language}
                      </span>
                      <span className={`badge badge-${article.sentiment}`}>
                        {article.sentiment}
                      </span>
                      {article.ocr_confidence && (
                        <span className="text-xs text-slate-400 font-mono">
                          {article.ocr_confidence}% OCR Conf
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-slate-900 mb-1">
                      {article.headline || "Untitled Extraction"}
                    </h3>

                    {article.body_snippet && (
                      <p className="text-sm text-slate-600 line-clamp-2 leading-relaxed mt-1">
                        {article.body_snippet}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-slate-400">
                      <span>Page {article.page_number}</span>
                      <span>•</span>
                      <span>Scanned Edition</span>
                    </div>
                  </div>

                  <div className="flex-shrink-0 self-end md:self-center">
                    <Link
                      href={`/evidence/${article.id || "demo-1"}`}
                      className="btn-secondary text-xs"
                    >
                      <span>Inspect Evidence</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Initial Empty State */}
      {!searched && (
        <div className="glass-card p-16 text-center">
          <div className="w-14 h-14 rounded-2xl bg-primary-50 text-primary-600 flex items-center justify-center mx-auto mb-3">
            <Search className="w-7 h-7" />
          </div>
          <h3 className="text-base font-bold text-slate-800">
            Query Multi-Lingual Intelligence
          </h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            Search headlines, body content, and translations across all regional Indian newspaper broadsheets.
          </p>
        </div>
      )}
    </div>
  );
}
