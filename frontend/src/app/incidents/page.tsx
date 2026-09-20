"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  Flame,
  ShieldAlert,
  Clock,
  CheckCircle2,
  Newspaper,
  Layers,
  ChevronRight,
  Filter,
  RefreshCw,
} from "lucide-react";

interface Incident {
  id: string;
  incident_number?: string;
  title: string;
  brand?: string;
  brand_name?: string;
  severity?: string;
  priority?: string;
  status: string;
  risk_score: number;
  alert_count?: number;
  publications?: string[];
  publication_name?: string;
  first_detected?: string;
  created_at?: string;
  summary?: string;
  description?: string;
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getIncidents();
      setIncidents(data);
    } catch (e: any) {
      console.error("Failed to load incidents:", e);
      setError(e.message || "Failed to load incidents");
      setIncidents([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const updateStatus = (id: string, newStatus: string) => {
    setIncidents((prev) => prev.map((inc) => (inc.id === id ? { ...inc, status: newStatus } : inc)));
  };

  const getSeverity = (inc: Incident) =>
    inc.severity || inc.priority || (inc.risk_score >= 80 ? "critical" : inc.risk_score >= 50 ? "high" : "medium");
  const getBrand = (inc: Incident) => inc.brand || inc.brand_name || "Unknown";
  const getSummary = (inc: Incident) => inc.summary || inc.description || "";
  const getIncidentNumber = (inc: Incident) => inc.incident_number || `INC-${inc.id.slice(0, 6).toUpperCase()}`;
  const getDetected = (inc: Incident) => {
    const dt = inc.first_detected || inc.created_at;
    if (!dt) return "Unknown";
    const d = new Date(dt);
    const diffMs = Date.now() - d.getTime();
    const diffH = Math.floor(diffMs / 3600000);
    if (diffH < 1) return `${Math.floor(diffMs / 60000)} mins ago`;
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString();
  };

  const filtered = incidents.filter((inc) => filterStatus === "all" || inc.status === filterStatus);
  const activeCount = incidents.filter((i) => ["active", "open"].includes(i.status)).length;
  const investigatingCount = incidents.filter((i) => i.status === "investigating").length;
  const totalAlerts = incidents.reduce((acc, i) => acc + (i.alert_count || 1), 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-red-100 text-red-700"><Flame className="w-4 h-4" /></div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Crisis Incident Center</h1>
          </div>
          <p className="text-sm text-slate-500">Clustered intelligence events grouped across regional publications into actionable incidents</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-secondary text-xs"><RefreshCw className="w-3.5 h-3.5" />Refresh</button>
          <div className="flex items-center gap-1.5 p-1 bg-slate-100/80 rounded-xl border border-slate-200/60">
            <Filter className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" />
            {["all","active","investigating","mitigated","resolved"].map((status) => (
              <button key={status} onClick={() => setFilterStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${
                  filterStatus === status
                    ? "bg-white text-slate-900 shadow-xs border border-slate-200/80"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card coral"><p className="text-xs font-semibold text-slate-500 uppercase">Active Incidents</p><p className="text-2xl font-extrabold text-red-600 mt-1">{activeCount}</p><p className="text-[11px] text-slate-400 mt-0.5">High-priority triage</p></div>
        <div className="kpi-card amber"><p className="text-xs font-semibold text-slate-500 uppercase">Under Investigation</p><p className="text-2xl font-extrabold text-amber-600 mt-1">{investigatingCount}</p><p className="text-[11px] text-slate-400 mt-0.5">Analyst review</p></div>
        <div className="kpi-card primary"><p className="text-xs font-semibold text-slate-500 uppercase">Total Linked Alerts</p><p className="text-2xl font-extrabold text-slate-900 mt-1">{totalAlerts}</p><p className="text-[11px] text-slate-400 mt-0.5">Across all editions</p></div>
        <div className="kpi-card emerald"><p className="text-xs font-semibold text-slate-500 uppercase">Total Incidents</p><p className="text-2xl font-extrabold text-emerald-600 mt-1">{incidents.length}</p><p className="text-[11px] text-slate-400 mt-0.5">All time</p></div>
      </div>

      {loading && (
        <div className="space-y-4">{[1,2].map((i) => (<div key={i} className="glass-card p-6 animate-pulse"><div className="h-4 bg-slate-200 rounded w-1/3 mb-3" /><div className="h-3 bg-slate-100 rounded w-2/3" /></div>))}</div>
      )}

      {!loading && error && (
        <div className="glass-card p-10 text-center">
          <ShieldAlert className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-slate-700">{error}</p>
          <button onClick={load} className="btn-primary text-xs mt-4">Retry</button>
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-4">
          {filtered.map((inc, idx) => {
            const severity = getSeverity(inc);
            return (
              <div key={`${inc.id}-${idx}`} className={`glass-card p-6 border-l-4 ${severity === "critical" ? "border-l-red-500" : severity === "high" ? "border-l-amber-500" : "border-l-primary-500"}`}>
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">{getIncidentNumber(inc)}</span>
                    <span className={`badge badge-${severity}`}>{severity.toUpperCase()}</span>
                    <span className="text-xs font-bold text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full border border-primary-200/60">{getBrand(inc)}</span>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize ${["active","open"].includes(inc.status) ? "bg-red-50 text-red-700 border border-red-200" : inc.status === "investigating" ? "bg-amber-50 text-amber-700 border border-amber-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200"}`}>{inc.status}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5 text-slate-400" />Detected: {getDetected(inc)}</span>
                    {inc.risk_score > 0 && <><span>•</span><span className="font-mono font-bold text-slate-700">Risk: {Math.round(inc.risk_score)}/100</span></>}
                  </div>
                </div>
                <h3 className="text-base font-bold text-slate-900 mb-2">{inc.title}</h3>
                {getSummary(inc) && <p className="text-sm text-slate-600 leading-relaxed mb-4">{getSummary(inc)}</p>}
                <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-slate-100">
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    {inc.alert_count !== undefined && <span className="inline-flex items-center gap-1 font-medium text-slate-700"><Layers className="w-3.5 h-3.5 text-slate-400" />{inc.alert_count} Linked Alerts</span>}
                    {(inc.publications?.length || inc.publication_name) && <><span>•</span><span className="inline-flex items-center gap-1"><Newspaper className="w-3.5 h-3.5 text-slate-400" />{inc.publications?.join(", ") || inc.publication_name}</span></>}
                  </div>
                  <div className="flex items-center gap-2">
                    {["active","open"].includes(inc.status) && <button onClick={() => updateStatus(inc.id,"investigating")} className="btn-secondary text-xs">Start Investigation</button>}
                    {inc.status === "investigating" && <button onClick={() => updateStatus(inc.id,"resolved")} className="btn-primary text-xs"><CheckCircle2 className="w-3.5 h-3.5" />Mark Resolved</button>}
                    <Link href="/alerts" className="btn-secondary text-xs"><span>View Grouped Alerts</span><ChevronRight className="w-3.5 h-3.5" /></Link>
                  </div>
                </div>
              </div>
            );
          })}

          {filtered.length === 0 && (
            <div className="glass-card p-16 text-center">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3"><CheckCircle2 className="w-6 h-6" /></div>
              <h3 className="text-base font-bold text-slate-900">{incidents.length === 0 ? "No incidents detected" : "No incidents in this view"}</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">{incidents.length === 0 ? "Incidents are automatically created when multiple related crisis alerts are detected across publications." : "No crisis incidents match the selected status filter."}</p>
              {incidents.length === 0 && <Link href="/alerts" className="btn-primary text-xs mt-4 inline-flex">View Alerts</Link>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
