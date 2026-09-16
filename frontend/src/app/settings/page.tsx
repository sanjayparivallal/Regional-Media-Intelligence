"use client";

import {
  Sliders,
  Cpu,
  Database,
  ShieldCheck,
  Server,
  Sparkles,
  HardDrive,
  Languages,
  ScanText,
  Activity,
  CheckCircle2,
} from "lucide-react";

export default function SettingsPage() {
  const models = [
    {
      name: "OCR Engine",
      value: "PaddleOCR + Tesseract (Hybrid Pipeline)",
      desc: "Optimized for Indian Devanagari & Dravidian newspaper scripts",
      icon: ScanText,
      status: "Operational",
    },
    {
      name: "Translation Engine",
      value: "Meta NLLB-200-distilled-600M",
      desc: "Local direct neural machine translation into English",
      icon: Languages,
      status: "Operational",
    },
    {
      name: "NER & Entity Extractor",
      value: "spaCy Indic + Regulatory Gazetteers",
      desc: "Financial entities, regulators, and regional executives",
      icon: Database,
      status: "Operational",
    },
    {
      name: "Sentiment & Crisis Classifier",
      value: "XLM-RoBERTa + Crisis Severity Rules",
      desc: "Multi-lingual classification and regulatory action detection",
      icon: Activity,
      status: "Operational",
    },
  ];

  const configs = [
    { key: "Autonomous Mode", value: "Enabled", note: "Auto-runs extraction upon PDF upload" },
    { key: "OCR Confidence Floor", value: "85%", note: "Below threshold routes to Human Review" },
    { key: "Crisis Risk Threshold", value: "60 / 100", note: "Triggers immediate critical notification" },
    { key: "Target Ingest File Size", value: "Max 100MB", note: "PDF / PNG / JPG broadsheets" },
    { key: "Database Storage", value: "PostgreSQL 16 + pgvector", note: "Local audit & embedding persistence" },
    { key: "Execution Environment", value: "Local Python CUDA / CPU", note: "Zero external cloud data leaks" },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <Sliders className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            System & Engine Configuration
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Local open-source AI inference engines, confidence thresholds, and hardware allocation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI Models Card */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2.5 mb-5">
            <div className="p-2 rounded-xl bg-violet-50 text-violet-600">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Inference AI Models
              </h3>
              <p className="text-xs text-slate-400">
                Locally hosted neural networks and extractors
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {models.map((model) => {
              const Icon = model.icon;
              return (
                <div
                  key={model.name}
                  className="p-4 bg-slate-50/80 rounded-2xl border border-slate-100 flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-xl bg-white text-slate-700 shadow-2xs border border-slate-200/60 mt-0.5">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-900 leading-tight">
                        {model.name}
                      </p>
                      <p className="text-xs font-mono font-medium text-primary-700 mt-0.5">
                        {model.value}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1">
                        {model.desc}
                      </p>
                    </div>
                  </div>
                  <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200/60">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{model.status}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Policies Card */}
        <div className="glass-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-5">
              <div className="p-2 rounded-xl bg-primary-50 text-primary-600">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Execution Policies & Thresholds
                </h3>
                <p className="text-xs text-slate-400">
                  Automation guardrails and regulatory alerting parameters
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {configs.map((config) => (
                <div
                  key={config.key}
                  className="flex items-center justify-between p-3.5 bg-slate-50/80 rounded-xl border border-slate-100"
                >
                  <div>
                    <span className="text-sm font-semibold text-slate-800">
                      {config.key}
                    </span>
                    <p className="text-[11px] text-slate-400">{config.note}</p>
                  </div>
                  <span className="font-mono text-xs font-bold text-slate-800 bg-white px-3 py-1 rounded-lg border border-slate-200 shadow-2xs">
                    {config.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 p-4 rounded-2xl bg-gradient-to-r from-primary-50 to-indigo-50 border border-primary-100 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 text-primary-900 font-semibold">
              <Server className="w-4 h-4 text-primary-600" />
              <span>Full Air-Gapped / Local Processing Capable</span>
            </div>
            <span className="font-mono text-[11px] text-primary-600 font-bold">
              v1.0.0
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
