"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Flame,
  ShieldAlert,
  AlertOctagon,
  Clock,
  ArrowUpRight,
  CheckCircle2,
  Building2,
  Newspaper,
  Layers,
  ChevronRight,
  Filter,
} from "lucide-react";

interface Incident {
  id: string;
  incident_number: string;
  title: string;
  brand: string;
  severity: "critical" | "high" | "medium";
  status: "active" | "investigating" | "mitigated" | "resolved";
  risk_score: number;
  alert_count: number;
  publications: string[];
  first_detected: string;
  last_updated: string;
  summary: string;
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([
    {
      id: "inc-01",
      incident_number: "INC-2024-001",
      title: "Regulatory Non-Compliance & Customer Ban on PayU Finance",
      brand: "PayU",
      severity: "critical",
      status: "active",
      risk_score: 91,
      alert_count: 3,
      publications: ["Dainik Jagran", "Amar Ujala", "Dainik Bhaskar"],
      first_detected: "Today, 08:30 AM",
      last_updated: "15 mins ago",
      summary:
        "Multiple regional editions reporting Reserve Bank restriction on new customer onboarding due to recurring KYC and compliance audits.",
    },
    {
      id: "inc-02",
      incident_number: "INC-2024-002",
      title: "Merchant Gateway Downtime Reports Across Tier 2 Markets",
      brand: "Paytm",
      severity: "high",
      status: "investigating",
      risk_score: 68,
      alert_count: 2,
      publications: ["Dinamalar", "Eenadu"],
      first_detected: "Yesterday, 04:15 PM",
      last_updated: "2 hours ago",
      summary:
        "Local trade associations in southern editions reporting intermittent POS terminal failures during peak weekend retail hours.",
    },
  ]);

  const [filterStatus, setFilterStatus] = useState<string>("all");

  const updateStatus = (id: string, newStatus: Incident["status"]) => {
    setIncidents((prev) =>
      prev.map((inc) => (inc.id === id ? { ...inc, status: newStatus } : inc))
    );
  };

  const filtered = incidents.filter(
    (inc) => filterStatus === "all" || inc.status === filterStatus
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-red-100 text-red-700">
              <Flame className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Crisis Incident Center
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Clustered intelligence events grouped across regional publications into actionable incidents
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100/80 rounded-xl border border-slate-200/60">
          <Filter className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" />
          {["all", "active", "investigating", "mitigated", "resolved"].map(
            (status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${
                  filterStatus === status
                    ? "bg-white text-slate-900 shadow-xs border border-slate-200/80"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {status}
              </button>
            )
          )}
        </div>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card coral">
          <p className="text-xs font-semibold text-slate-500 uppercase">Active Incidents</p>
          <p className="text-2xl font-extrabold text-red-600 mt-1">
            {incidents.filter((i) => i.status === "active").length}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">High-priority triage</p>
        </div>
        <div className="kpi-card amber">
          <p className="text-xs font-semibold text-slate-500 uppercase">Under Investigation</p>
          <p className="text-2xl font-extrabold text-amber-600 mt-1">
            {incidents.filter((i) => i.status === "investigating").length}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Analyst review</p>
        </div>
        <div className="kpi-card primary">
          <p className="text-xs font-semibold text-slate-500 uppercase">Total Linked Alerts</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">
            {incidents.reduce((acc, i) => acc + i.alert_count, 0)}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Across all editions</p>
        </div>
        <div className="kpi-card emerald">
          <p className="text-xs font-semibold text-slate-500 uppercase">Avg Resolution</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">2.4h</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Standard response cycle</p>
        </div>
      </div>

      {/* Incidents List Cards */}
      <div className="space-y-4">
        {filtered.map((inc) => (
          <div
            key={inc.id}
            className={`glass-card p-6 border-l-4 ${
              inc.severity === "critical"
                ? "border-l-red-500"
                : inc.severity === "high"
                ? "border-l-amber-500"
                : "border-l-primary-500"
            }`}
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                  {inc.incident_number}
                </span>
                <span className={`badge badge-${inc.severity}`}>
                  {inc.severity.toUpperCase()}
                </span>
                <span className="text-xs font-bold text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full border border-primary-200/60">
                  {inc.brand}
                </span>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize ${
                    inc.status === "active"
                      ? "bg-red-50 text-red-700 border border-red-200"
                      : inc.status === "investigating"
                      ? "bg-amber-50 text-amber-700 border border-amber-200"
                      : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  }`}
                >
                  {inc.status}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  Detected: {inc.first_detected}
                </span>
                <span>•</span>
                <span>Updated: {inc.last_updated}</span>
              </div>
            </div>

            <h3 className="text-base font-bold text-slate-900 mb-2">{inc.title}</h3>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">{inc.summary}</p>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-slate-100">
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <span className="inline-flex items-center gap-1 font-medium text-slate-700">
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                  {inc.alert_count} Linked Alerts
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1">
                  <Newspaper className="w-3.5 h-3.5 text-slate-400" />
                  {inc.publications.join(", ")}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {inc.status === "active" && (
                  <button
                    onClick={() => updateStatus(inc.id, "investigating")}
                    className="btn-secondary text-xs"
                  >
                    Start Investigation
                  </button>
                )}
                {inc.status === "investigating" && (
                  <button
                    onClick={() => updateStatus(inc.id, "resolved")}
                    className="btn-primary text-xs"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Mark Resolved
                  </button>
                )}
                <Link href="/alerts" className="btn-secondary text-xs">
                  <span>View Grouped Alerts</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="glass-card p-16 text-center">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              No incidents in this view
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No crisis incidents match the selected status filter.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
