"use client";

import { useState } from "react";
import {
  History,
  UploadCloud,
  FileCheck,
  Image as ImageIcon,
  ScanText,
  LayoutGrid,
  Scissors,
  Globe,
  Languages,
  Tag,
  Building2,
  Activity,
  AlertTriangle,
  BarChart3,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Filter,
} from "lucide-react";

export default function AuditPage() {
  const [selectedDoc, setSelectedDoc] = useState("Dainik_Jagran_2024.pdf");

  const auditSteps = [
    { action: "document_uploaded", stage: "upload", time: "0ms", status: "completed", icon: UploadCloud },
    { action: "pdf_classified", stage: "pdf_classification", time: "1,200ms", status: "completed", icon: FileCheck },
    { action: "pages_rendered", stage: "page_rendering", time: "3,500ms", status: "completed", icon: ImageIcon },
    { action: "ocr_completed", stage: "ocr", time: "15,000ms", status: "completed", icon: ScanText },
    { action: "layout_analyzed", stage: "layout_analysis", time: "2,800ms", status: "completed", icon: LayoutGrid },
    { action: "articles_extracted", stage: "article_extraction", time: "1,500ms", status: "completed", icon: Scissors },
    { action: "language_detected", stage: "language_detection", time: "200ms", status: "completed", icon: Globe },
    { action: "translation_completed", stage: "translation", time: "8,500ms", status: "completed", icon: Languages },
    { action: "entities_extracted", stage: "entity_detection", time: "1,200ms", status: "completed", icon: Tag },
    { action: "brands_matched", stage: "brand_matching", time: "300ms", status: "completed", icon: Building2 },
    { action: "sentiment_analyzed", stage: "sentiment", time: "2,100ms", status: "completed", icon: Activity },
    { action: "crisis_classified", stage: "crisis", time: "800ms", status: "completed", icon: AlertTriangle },
    { action: "risk_score_calculated", stage: "risk_scoring", time: "100ms", status: "completed", icon: BarChart3 },
    { action: "alert_generated", stage: "alert", time: "50ms", status: "completed", icon: ShieldAlert },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
              <History className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              AI Decision Audit Trail
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Immutable, reproducible decision log across every stage of the multimodal extraction pipeline
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium">Document:</span>
          <span className="font-mono font-bold text-slate-800 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200/60">
            {selectedDoc}
          </span>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card primary">
          <p className="text-xs font-semibold text-slate-500 uppercase">Pipeline Steps</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">14</p>
          <p className="text-[11px] text-slate-400 mt-0.5">End-to-end trace</p>
        </div>
        <div className="kpi-card emerald">
          <p className="text-xs font-semibold text-slate-500 uppercase">Total Execution</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">37.2s</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Local GPU accelerated</p>
        </div>
        <div className="kpi-card cyan">
          <p className="text-xs font-semibold text-slate-500 uppercase">Verification</p>
          <p className="text-2xl font-extrabold text-cyan-600 mt-1">100%</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Zero unverified hops</p>
        </div>
        <div className="kpi-card violet">
          <p className="text-xs font-semibold text-slate-500 uppercase">Integrity Status</p>
          <p className="text-2xl font-extrabold text-violet-600 mt-1">Verified</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Cryptographic checksum</p>
        </div>
      </div>

      {/* Audit Timeline Card */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">
            Pipeline Stage Execution Log
          </h2>
          <span className="text-xs text-slate-400">Chronological sequence</span>
        </div>

        <div className="divide-y divide-slate-100">
          {auditSteps.map((entry, i) => {
            const Icon = entry.icon;
            return (
              <div
                key={i}
                className="px-6 py-4 flex items-center justify-between gap-4 hover:bg-slate-50/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-primary-50/70 text-primary-600 flex items-center justify-center flex-shrink-0 border border-primary-100/60">
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-900 capitalize leading-tight">
                      {entry.action.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Stage: <span className="font-mono font-medium text-slate-600">{entry.stage}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md">
                    {entry.time}
                  </span>
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600">
                    <CheckCircle2 className="w-4 h-4" />
                    <span className="hidden sm:inline">Completed</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
