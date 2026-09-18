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
  AlertCircle,
  Bell,
} from "lucide-react";

export default function EvidenceExplorerPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any>({ articles: [], alerts: [], brands: [] });
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recentAlerts, setRecentAlerts] = useState<any[]>([]);

  // Load recent alerts as quick-filter suggestions
  useEffect(() => {
    api
      .getAlerts({ limit: "5" })
      .then((data) => setRecentAlerts(data))
      .catch(() => {});
  }, []);

  const handleSearch = async (overrideQuery?: string) => {
    const q = overrideQuery ?? query;
    if (!q.trim()) return;
    setSearched(true);
    setLoading(true);
    try {
      const data = await api.search(q);
      setResults(data);
    } catch {
      setResults({ articles: [], alerts: [], brands: [] });
    }
    setLoading(false);
  };

  const totalResults =
    (results.articles?.length || 0) +
    (results.alerts?.length || 0) +
    (results.brands?.length || 0);

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

        {/* Dynamic Suggestions from Recent Alerts */}
        {recentAlerts.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-500">
            <span className="font-semibold text-slate-400">Recent alerts:</span>
            {recentAlerts.slice(0, 5).map((a) => (
              <button
                key={a.id}
                onClick={() => {
                  const q = a.brand_name || a.title?.split(":")[0] || "";
                  setQuery(q);
                  handleSearch(q);
                }}
                className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 hover:bg-primary-50 hover:text-primary-700 transition-colors font-medium cursor-pointer truncate max-w-[200px]"
              >
                {a.brand_name || a.title?.split(":")[0]}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Search Results */}
      {searched && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 px-1">
            <span>
              {loading ? "Searching..." : `${totalResults} result${totalResults !== 1 ? "s" : ""} retrieved`}
            </span>
          </div>

          {loading && (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="glass-card p-6 animate-pulse">
                  <div className="h-4 bg-slate-200 rounded w-2/3 mb-3" />
                  <div className="h-3 bg-slate-100 rounded w-full mb-2" />
                  <div className="h-3 bg-slate-100 rounded w-3/4" />
                </div>
              ))}
            </div>
          )}

          {!loading && (
            <div className="space-y-4">
              {/* Articles */}
              {results.articles?.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
                    Articles ({results.articles.length})
                  </p>
                  {results.articles.map((article: any, i: number) => (
                    <div
                      key={article.id || i}
                      className="glass-card p-5 hover:border-slate-300 transition-all"
                    >
                      <div className="flex flex-col md:flex-row md:items-start gap-4">
                        <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center flex-shrink-0">
                          <Newspaper className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1.5">
                            <span className="badge bg-violet-50 text-violet-700 ring-violet-200/70">
                              Article
                            </span>
                          </div>
                          <h3 className="text-base font-bold text-slate-900 mb-1">
                            {article.headline || "Untitled Article"}
                          </h3>
                          <p className="text-xs text-slate-400">Extracted from regional broadsheet scan</p>
                        </div>
                        <div className="flex-shrink-0 self-end md:self-center">
                          <span className="text-xs text-slate-400 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                            Article extracted
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Alerts */}
              {results.alerts?.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
                    Alerts ({results.alerts.length})
                  </p>
                  {results.alerts.map((alert: any, i: number) => (
                    <div
                      key={alert.id || i}
                      className="glass-card p-5 hover:border-slate-300 transition-all"
                    >
                      <div className="flex flex-col md:flex-row md:items-start gap-4">
                        <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center flex-shrink-0">
                          <Bell className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1.5">
                            <span className={`badge badge-${alert.priority || "medium"}`}>
                              {(alert.priority || "ALERT").toUpperCase()}
                            </span>
                          </div>
                          <h3 className="text-base font-bold text-slate-900 mb-1">
                            {alert.title || "Alert"}
                          </h3>
                        </div>
                        <div className="flex-shrink-0 self-end md:self-center">
                          {/* alert.id is a real alert UUID — evidence viewer works correctly */}
                          <Link href={`/evidence/${alert.id}`} className="btn-secondary text-xs">
                            <span>View Evidence</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Brands */}
              {results.brands?.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
                    Brands ({results.brands.length})
                  </p>
                  {results.brands.map((brand: any, i: number) => (
                    <div
                      key={brand.id || i}
                      className="glass-card p-5 hover:border-slate-300 transition-all"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-bold text-slate-900">{brand.name}</span>
                          <p className="text-xs text-slate-400 mt-0.5">Brand Profile</p>
                        </div>
                        <Link href="/brands" className="btn-secondary text-xs">
                          <span>View Brand</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {totalResults === 0 && (
                <div className="glass-card p-12 text-center">
                  <AlertCircle className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                  <h3 className="text-base font-bold text-slate-800">No results found</h3>
                  <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
                    No articles, alerts, or brands matched &quot;{query}&quot;. Try different keywords.
                  </p>
                </div>
              )}
            </div>
          )}
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
