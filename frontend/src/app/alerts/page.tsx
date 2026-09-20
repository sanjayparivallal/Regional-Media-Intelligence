"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import RiskScore from "@/components/alerts/RiskScore";
import Link from "next/link";
import {
  Bell,
  Filter,
  Newspaper,
  Globe,
  FileText,
  Clock,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  X,
  CheckCircle2,
} from "lucide-react";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ priority: "", sentiment: "", language: "" });

  useEffect(() => {
    async function load() {
      try {
        const params: Record<string, string> = {};
        if (filters.priority) params.priority = filters.priority;
        if (filters.sentiment) params.sentiment = filters.sentiment;
        if (filters.language) params.language = filters.language;
        const data = await api.getAlerts(params);
        setAlerts(data);
      } catch (e) {
        console.error("Failed to load alerts:", e);
        setAlerts([]);
      }
      setLoading(false);
    }
    load();
  }, [filters]);

  const priorityOptions = [
    { label: "All Priorities", value: "" },
    { label: "Critical", value: "critical" },
    { label: "High", value: "high" },
    { label: "Medium", value: "medium" },
    { label: "Low", value: "low" },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-red-100 text-red-700">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Crisis Alert Center
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Real-time reputation and regulatory risk alerts ranked by severity score
          </p>
        </div>

        {/* Priority Filter Chips */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100/80 rounded-xl border border-slate-200/60">
          <Filter className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" />
          {priorityOptions.map((p) => {
            const active = filters.priority === p.value;
            return (
              <button
                key={p.value}
                onClick={() => setFilters((f) => ({ ...f, priority: p.value }))}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  active
                    ? "bg-white text-slate-900 shadow-xs border border-slate-200/80"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-2xl bg-slate-200/70 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert, idx) => {
            const isCritical = alert.priority === "critical";
            const isHigh = alert.priority === "high";
            const borderAccent = isCritical
              ? "border-l-4 border-l-red-500"
              : isHigh
              ? "border-l-4 border-l-amber-500"
              : "border-l-4 border-l-primary-500";

            return (
              <div
                key={`${alert.id}-${idx}`}
                className={`glass-card p-6 animate-slide-up ${borderAccent} hover:border-slate-300 transition-all`}
              >
                <div className="flex flex-col lg:flex-row lg:items-start gap-6">
                  <div className="flex-shrink-0 flex items-center justify-center">
                    <RiskScore
                      score={alert.risk_score}
                      size="md"
                      showBreakdown={true}
                      breakdown={alert.risk_breakdown}
                    />
                  </div>

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
                        <span className="badge bg-violet-50 text-violet-700 ring-violet-200/70">
                          {alert.crisis_topic.replace(/_/g, " ").toUpperCase()}
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-slate-900 mb-1.5 leading-snug">
                      {alert.title}
                    </h3>
                    <p className="text-sm text-slate-600 line-clamp-2 leading-relaxed">
                      {alert.summary}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
                        <Newspaper className="w-3.5 h-3.5 text-slate-400" />
                        {alert.publication_name || "Unknown Publication"}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Globe className="w-3.5 h-3.5 text-slate-400" />
                        {alert.language?.toUpperCase()}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        Page {alert.page_number}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {alert.created_at
                          ? new Date(alert.created_at).toLocaleString("en-IN", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })
                          : "—"}
                      </span>
                    </div>
                  </div>

                  <div className="flex lg:flex-col gap-2 flex-shrink-0">
                    <Link
                      href={`/evidence/${alert.id}`}
                      className="btn-primary text-xs w-full justify-center"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      View Evidence
                    </Link>
                    <button className="btn-secondary text-xs w-full justify-center text-slate-600">
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {alerts.length === 0 && (
            <div className="glass-card p-16 text-center">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
                <ShieldCheck className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">
                All Clear — No Matching Alerts
              </h3>
              <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
                There are no alerts matching your current filter criteria.
              </p>
              <button
                onClick={() => setFilters({ priority: "", sentiment: "", language: "" })}
                className="btn-secondary text-xs mt-4"
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
