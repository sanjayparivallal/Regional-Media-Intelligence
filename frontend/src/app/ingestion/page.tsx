"use client";

import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  UploadCloud,
  FileText,
  Image as ImageIcon,
  Play,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Layers,
  ArrowRight,
  Loader2,
  Sparkles,
  ScanText,
  Languages,
  BrainCircuit,
  Clock,
} from "lucide-react";

interface PipelineDocItem {
  id: string;
  filename: string;
  original_filename: string;
  status: "uploaded" | "processing" | "completed" | "failed" | "error";
  current_stage?: string;
  progress_percent?: number;
  overall_sentiment?: string;
  overall_risk_score?: number;
  error?: string;
  fileSize?: number;
  isPdf?: boolean;
}

const PIPELINE_STEPS = [
  {
    key: "classify",
    label: "Document Classification",
    desc: "Classifying format & rendering pages",
    Icon: Layers,
    minProgress: 10,
  },
  {
    key: "ocr",
    label: "Indic-OCR Scanning",
    desc: "Extracting regional characters & bounding boxes",
    Icon: ScanText,
    minProgress: 35,
  },
  {
    key: "translation",
    label: "IndicTrans2 Translation",
    desc: "Translating regional text to English",
    Icon: Languages,
    minProgress: 70,
  },
  {
    key: "sentiment",
    label: "LFM Sentiment & Crisis",
    desc: "Analyzing tone, sentiment & crisis signals",
    Icon: BrainCircuit,
    minProgress: 85,
  },
  {
    key: "complete",
    label: "Indexing & Verification",
    desc: "Indexed for evidence verification",
    Icon: CheckCircle2,
    minProgress: 100,
  },
];

export default function IngestionPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [activePipelineDocs, setActivePipelineDocs] = useState<PipelineDocItem[]>([]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter((f) =>
      [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"].some((ext) =>
        f.name.toLowerCase().endsWith(ext)
      )
    );
    setFiles((prev) => [...prev, ...droppedFiles]);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
      }
    },
    []
  );

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);

    const newTrackedDocs: PipelineDocItem[] = [];

    for (const file of files) {
      const isPdf = file.name.toLowerCase().endsWith(".pdf");
      try {
        const doc = await api.uploadDocument(file);
        const item: PipelineDocItem = {
          id: doc.id,
          filename: doc.filename || file.name,
          original_filename: file.name,
          status: "processing",
          current_stage: "classifying_document",
          progress_percent: 10,
          fileSize: file.size,
          isPdf,
        };
        newTrackedDocs.push(item);
        // Start AI pipeline
        await api.processDocument(doc.id);
      } catch (e: any) {
        newTrackedDocs.push({
          id: `err-${Date.now()}-${Math.random()}`,
          filename: file.name,
          original_filename: file.name,
          status: "error",
          error: e.message || "Failed to upload document",
          fileSize: file.size,
          isPdf,
        });
      }
    }

    setActivePipelineDocs((prev) => {
      const newIds = new Set(newTrackedDocs.map((d) => d.id));
      const filteredPrev = prev.filter((d) => !newIds.has(d.id));
      return [...newTrackedDocs, ...filteredPrev];
    });
    setFiles([]);
    setUploading(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Poll active pipeline documents
  useEffect(() => {
    const hasActive = activePipelineDocs.some(
      (d) => d.status === "processing" || d.status === "uploaded"
    );
    if (!hasActive) return;

    const interval = setInterval(async () => {
      try {
        const updatedDocs = await api.getDocuments();
        if (!updatedDocs) return;

        setActivePipelineDocs((prev) =>
          prev.map((tracked) => {
            if (tracked.status === "error") return tracked;
            const remote = updatedDocs.find((d: any) => d.id === tracked.id);
            if (!remote) return tracked;

            const remoteStatus = (remote.status || "").toLowerCase();
            const isFinished = remoteStatus === "completed";
            const isFailed = remoteStatus === "failed";

            return {
              ...tracked,
              status: isFinished
                ? "completed"
                : isFailed
                ? "failed"
                : "processing",
              current_stage: remote.current_stage || tracked.current_stage,
              progress_percent: remote.progress_percent ?? tracked.progress_percent ?? (isFinished ? 100 : 15),
              overall_sentiment: remote.overall_sentiment || tracked.overall_sentiment,
              overall_risk_score: remote.overall_risk_score ?? tracked.overall_risk_score,
              error: remote.error_message || tracked.error,
            };
          })
        );
      } catch (err) {
        console.warn("Polling document status warning:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activePipelineDocs]);

  const getStageMessage = (doc: PipelineDocItem) => {
    const stage = (doc.current_stage || "").toLowerCase();
    const progress = doc.progress_percent || 0;

    if (doc.status === "completed") {
      return "✨ All pipeline stages completed successfully! Characters extracted via Indic-OCR, translated via IndicTrans2, and sentiment analyzed via LFM.";
    }
    if (doc.status === "failed") {
      return `❌ Pipeline encountered an error: ${doc.error || "Processing failed"}`;
    }
    if (stage.includes("indicocr") || stage.includes("ocr") || stage.includes("extracting")) {
      return "🔍 Indic-OCR Scanning: Scanning document image and extracting regional language characters (Tamil/Hindi/etc.)...";
    }
    if (stage.includes("layout") || stage.includes("segment")) {
      return "📐 Layout Analysis: Analyzing columns, region boundaries, and segmenting articles...";
    }
    if (stage.includes("indictrans") || stage.includes("translat")) {
      return "🌐 IndicTrans2 Translation: Translating extracted regional text to English with entity protection...";
    }
    if (stage.includes("sentiment") || stage.includes("lfm")) {
      return "🧠 Sentiment & Crisis Analysis: Analyzing tone, brand mentions, and risk severity using LFM model...";
    }
    if (progress < 25) {
      return "📄 Classifying document type and rendering high-resolution broadsheet pages...";
    }
    return "⚡ AI Pipeline processing document...";
  };

  const getActiveStepIndex = (doc: PipelineDocItem) => {
    if (doc.status === "completed") return 4;
    const stage = (doc.current_stage || "").toLowerCase();
    const progress = doc.progress_percent || 0;

    if (stage.includes("sentiment") || stage.includes("lfm") || progress >= 85) return 3;
    if (stage.includes("translat") || progress >= 70) return 2;
    if (stage.includes("ocr") || stage.includes("extract") || stage.includes("segment") || progress >= 35) return 1;
    return 0;
  };

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <UploadCloud className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Document Ingestion & AI Pipeline
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Upload multi-page newspaper PDFs and scanned broadsheets for automated Indic-OCR character extraction, IndicTrans2 translation, and LFM sentiment analysis.
        </p>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`relative rounded-3xl border-2 border-dashed p-10 text-center transition-all duration-300 ${
          dragActive
            ? "border-primary-500 bg-primary-50/70 scale-[1.008]"
            : "border-slate-300/80 bg-white hover:border-primary-400 hover:bg-slate-50/50"
        }`}
      >
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary-100 to-indigo-100 flex items-center justify-center text-primary-600 shadow-xs ring-4 ring-primary-50">
            <UploadCloud className="w-8 h-8" />
          </div>
          <div>
            <p className="text-lg font-bold text-slate-900">
              {dragActive ? "Drop documents here" : "Drag & drop newspaper editions"}
            </p>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Supports scanned broadsheets, PDF editions, and high-res images (PNG, JPG, JPEG, TIFF) up to 100MB
            </p>
          </div>
          <div>
            <label className="btn-primary cursor-pointer inline-flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              <span>Browse Local Files</span>
              <input
                type="file"
                className="hidden"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
                onChange={handleFileSelect}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Upload Queue Card (Staged Files) */}
      {files.length > 0 && (
        <div className="glass-card overflow-hidden animate-slide-up">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary-600" />
              <h2 className="text-sm font-bold text-slate-900">
                Staged for Processing ({files.length} file{files.length > 1 ? "s" : ""})
              </h2>
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="btn-primary text-xs"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Ingesting Documents...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Launch Ingestion Pipeline</span>
                </>
              )}
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {files.map((file, i) => {
              const isPdf = file.name.toLowerCase().endsWith(".pdf");
              return (
                <div
                  key={i}
                  className="px-6 py-3.5 flex items-center gap-4 hover:bg-slate-50/50 transition-colors"
                >
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      isPdf ? "bg-red-50 text-red-600" : "bg-cyan-50 text-cyan-600"
                    }`}
                  >
                    {isPdf ? (
                      <FileText className="w-5 h-5" />
                    ) : (
                      <ImageIcon className="w-5 h-5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {(file.size / 1024 / 1024).toFixed(2)} MB •{" "}
                      {isPdf ? "Adobe PDF Broadsheet" : "Scanned Image"}
                    </p>
                  </div>
                  <button
                    onClick={() => removeFile(i)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
                    title="Remove from queue"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Live Pipeline Execution Monitor */}
      {activePipelineDocs.length > 0 && (
        <div className="space-y-6 animate-slide-up">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-indigo-600 animate-pulse" />
              <h2 className="text-lg font-extrabold text-slate-900">
                Live AI Pipeline Monitor
              </h2>
            </div>
            <span className="text-xs text-slate-400 font-medium">
              Real-time Indic-OCR, IndicTrans2 & LFM Processing
            </span>
          </div>

          <div className="space-y-4">
            {activePipelineDocs.map((doc, idx) => {
              const activeStepIdx = getActiveStepIndex(doc);
              const progress = doc.progress_percent || (doc.status === "completed" ? 100 : 15);
              const isCompleted = doc.status === "completed";
              const isFailed = doc.status === "failed" || doc.status === "error";

              return (
                <div
                  key={`${doc.id}-${idx}`}
                  className={`bg-white rounded-3xl border shadow-sm overflow-hidden transition-all duration-300 ${
                    isCompleted
                      ? "border-emerald-200 ring-2 ring-emerald-50"
                      : isFailed
                      ? "border-red-200 ring-2 ring-red-50"
                      : "border-indigo-200 ring-2 ring-indigo-50/60"
                  }`}
                >
                  {/* Top Animated Progress Bar */}
                  <div className="h-1.5 w-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-700 bg-gradient-to-r ${
                        isCompleted
                          ? "from-emerald-500 to-teal-400"
                          : isFailed
                          ? "from-red-500 to-rose-400"
                          : "from-indigo-600 via-cyan-500 to-blue-500"
                      }`}
                      style={{ width: `${Math.max(progress, 8)}%` }}
                    />
                  </div>

                  {/* Main Header & Status */}
                  <div className="p-6 space-y-6">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div className="flex items-center gap-3.5">
                        <div
                          className={`w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                            isCompleted
                              ? "bg-emerald-50 text-emerald-600"
                              : isFailed
                              ? "bg-red-50 text-red-600"
                              : "bg-indigo-50 text-indigo-600"
                          }`}
                        >
                          {isCompleted ? (
                            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                          ) : isFailed ? (
                            <AlertCircle className="w-6 h-6 text-red-600" />
                          ) : (
                            <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
                          )}
                        </div>

                        <div>
                          <p className="text-base font-bold text-slate-900 truncate max-w-md">
                            {doc.original_filename || doc.filename}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-slate-400">
                              {doc.fileSize ? `${(doc.fileSize / 1024 / 1024).toFixed(2)} MB • ` : ""}
                              {doc.isPdf ? "PDF Broadsheet" : "Scanned Image"}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Status Badges & Action Links */}
                      <div className="flex items-center gap-3 flex-wrap">
                        {isCompleted && (
                          <>
                            {doc.overall_sentiment && (
                              <span
                                className={`px-3 py-1 rounded-full text-xs font-extrabold uppercase tracking-wide border ${
                                  doc.overall_sentiment === "POSITIVE"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : doc.overall_sentiment === "NEGATIVE"
                                    ? "bg-rose-50 text-rose-700 border-rose-200"
                                    : "bg-slate-50 text-slate-700 border-slate-200"
                                }`}
                              >
                                Sentiment: {doc.overall_sentiment}
                              </span>
                            )}
                            {doc.overall_risk_score !== undefined && (
                              <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                Risk: {Math.round(doc.overall_risk_score)} / 100
                              </span>
                            )}
                          </>
                        )}

                        <span
                          className={`px-3 py-1 rounded-full text-xs font-bold border inline-flex items-center gap-1.5 ${
                            isCompleted
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : isFailed
                              ? "bg-red-50 text-red-700 border-red-200"
                              : "bg-blue-50 text-blue-700 border-blue-200 animate-pulse"
                          }`}
                        >
                          {!isCompleted && !isFailed && (
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-ping" />
                          )}
                          {isCompleted
                            ? "Completed (100%)"
                            : isFailed
                            ? "Pipeline Failed"
                            : `Processing (${Math.round(progress)}%)`}
                        </span>

                        {doc.id && !doc.id.startsWith("err-") && (
                          <Link
                            href={`/processing`}
                            className="btn-secondary text-xs py-1.5 px-3"
                          >
                            <span>Track Pipeline</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        )}
                      </div>
                    </div>

                    {/* Live Stage Message Banner */}
                    <div
                      className={`p-3.5 rounded-2xl text-xs font-medium flex items-center gap-2.5 ${
                        isCompleted
                          ? "bg-emerald-50/80 text-emerald-800 border border-emerald-100"
                          : isFailed
                          ? "bg-red-50/80 text-red-800 border border-red-100"
                          : "bg-indigo-50/80 text-indigo-900 border border-indigo-100/80"
                      }`}
                    >
                      {!isCompleted && !isFailed && (
                        <Loader2 className="w-4 h-4 text-indigo-600 animate-spin flex-shrink-0" />
                      )}
                      {isCompleted && (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      )}
                      {isFailed && (
                        <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                      )}
                      <span className="leading-relaxed">{getStageMessage(doc)}</span>
                    </div>

                    {/* 5-Step Visual Stepper */}
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-2">
                      {PIPELINE_STEPS.map((step, idx) => {
                        const StepIcon = step.Icon;
                        const isStepDone = isCompleted || activeStepIdx > idx;
                        const isStepCurrent = !isCompleted && !isFailed && activeStepIdx === idx;

                        return (
                          <div
                            key={step.key}
                            className={`p-3.5 rounded-2xl border transition-all duration-300 ${
                              isStepDone
                                ? "bg-emerald-50/60 border-emerald-200/80 text-emerald-900"
                                : isStepCurrent
                                ? "bg-indigo-50/80 border-indigo-300 text-indigo-950 ring-2 ring-indigo-200/60 shadow-xs"
                                : "bg-slate-50/60 border-slate-100 text-slate-400 opacity-60"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span
                                className={`text-[10px] font-extrabold uppercase px-1.5 py-0.5 rounded-md ${
                                  isStepDone
                                    ? "bg-emerald-100 text-emerald-700"
                                    : isStepCurrent
                                    ? "bg-indigo-100 text-indigo-700"
                                    : "bg-slate-200 text-slate-500"
                                }`}
                              >
                                Step 0{idx + 1}
                              </span>
                              {isStepDone ? (
                                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              ) : isStepCurrent ? (
                                <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
                              ) : (
                                <Clock className="w-3.5 h-3.5 text-slate-300" />
                              )}
                            </div>

                            <div className="flex items-center gap-2 mb-1">
                              <StepIcon
                                className={`w-4 h-4 ${
                                  isStepDone
                                    ? "text-emerald-600"
                                    : isStepCurrent
                                    ? "text-indigo-600"
                                    : "text-slate-400"
                                }`}
                              />
                              <p className="text-xs font-bold truncate">
                                {step.label}
                              </p>
                            </div>
                            <p className="text-[11px] leading-tight text-slate-500 line-clamp-2">
                              {step.desc}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Supported Formats Info Cards */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-bold text-slate-900 mb-3">
          Supported Document Formats & Pipeline Models
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              ext: "Indic-OCR",
              desc: "Tamil, Hindi, Devanagari regional OCR",
              icon: ScanText,
              iconColor: "text-indigo-600 bg-indigo-50",
            },
            {
              ext: "IndicTrans2",
              desc: "High-accuracy regional-to-English NMT",
              icon: Languages,
              iconColor: "text-cyan-600 bg-cyan-50",
            },
            {
              ext: "LFM 2.5",
              desc: "Liquid AI sentiment, summary & crisis",
              icon: BrainCircuit,
              iconColor: "text-amber-600 bg-amber-50",
            },
            {
              ext: "PDF & Scans",
              desc: "Multi-page editions & broadsheets",
              icon: FileText,
              iconColor: "text-violet-600 bg-violet-50",
            },
          ].map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.ext}
                className="flex items-center gap-3 p-3.5 rounded-2xl bg-slate-50 border border-slate-100"
              >
                <div className={`p-2 rounded-xl ${f.iconColor}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-800">{f.ext}</p>
                  <p className="text-[11px] text-slate-400">{f.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
