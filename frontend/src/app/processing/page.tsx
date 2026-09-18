"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import {
  Upload,
  FileText,
  Layers,
  ScanText,
  LayoutGrid,
  Scissors,
  Globe,
  Languages,
  Tag,
  BarChart2,
  ShieldAlert,
  Bell,
  Database,
  CheckCircle2,
  Loader2,
  XCircle,
  Clock,
  Trash2,
  StopCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Timer,
  Cpu,
  RefreshCw,
  RotateCcw,
} from "lucide-react";

interface PipelineStage {
  key: string;
  label: string;
  Icon: React.ElementType;
  description: string;
}

const pipelineStages: PipelineStage[] = [
  { key: "upload", label: "Upload", Icon: Upload, description: "File received & validated" },
  { key: "pdf_classification", label: "PDF Classification", Icon: FileText, description: "Classify document type" },
  { key: "page_rendering", label: "Page Rendering", Icon: Layers, description: "Render pages to images" },
  { key: "ocr", label: "OCR", Icon: ScanText, description: "Extract text from images" },
  { key: "layout_analysis", label: "Layout Analysis", Icon: LayoutGrid, description: "Detect columns & regions" },
  { key: "article_extraction", label: "Article Extraction", Icon: Scissors, description: "Segment individual articles" },
  { key: "language_detection", label: "Language Detection", Icon: Globe, description: "Identify article languages" },
  { key: "translation", label: "Translation", Icon: Languages, description: "Translate to English" },
  { key: "entity_detection", label: "Entity Detection", Icon: Tag, description: "Extract named entities" },
  { key: "sentiment_analysis", label: "Sentiment Analysis", Icon: BarChart2, description: "Analyze tone & sentiment" },
  { key: "crisis_analysis", label: "Crisis Analysis", Icon: ShieldAlert, description: "Detect crisis topics" },
  { key: "alert_generation", label: "Alert Generation", Icon: Bell, description: "Generate brand alerts" },
  { key: "evidence_indexed", label: "Evidence Indexed", Icon: Database, description: "Index for evidence chain" },
];

type StageStatus = "completed" | "running" | "pending" | "failed";

function StageIcon({ status }: { status: StageStatus }) {
  if (status === "completed") return <CheckCircle2 size={14} className="text-emerald-500" />;
  if (status === "running") return <Loader2 size={14} className="text-blue-500 animate-spin" />;
  if (status === "failed") return <XCircle size={14} className="text-red-500" />;
  return <Clock size={14} className="text-slate-300" />;
}

function StatusBadge({ status }: { status: string }) {
  const s = status?.toLowerCase();
  const configs: Record<string, { label: string; cls: string; dot: string }> = {
    completed: { label: "Completed", cls: "bg-emerald-50 text-emerald-700 border-emerald-200", dot: "bg-emerald-500" },
    processing: { label: "Processing", cls: "bg-blue-50 text-blue-700 border-blue-200", dot: "bg-blue-500 animate-pulse" },
    queued: { label: "Queued", cls: "bg-amber-50 text-amber-700 border-amber-200", dot: "bg-amber-500" },
    uploaded: { label: "Uploaded", cls: "bg-slate-50 text-slate-600 border-slate-200", dot: "bg-slate-400" },
    failed: { label: "Failed", cls: "bg-red-50 text-red-700 border-red-200", dot: "bg-red-500" },
  };
  const c = configs[s] ?? configs["uploaded"];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ProcessingPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [jobs, setJobs] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const inFlightRef = useRef(false);

  const load = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    try {
      const docs = await api.getDocuments();
      setDocuments(docs || []);
      setLoading(false);

      // Concurrently fetch jobs for active documents without blocking UI
      const activeStatuses = ["processing", "queued", "uploaded"];
      const activeDocs = (docs || []).filter((d: any) => activeStatuses.includes(d.status?.toLowerCase()));
      if (activeDocs.length > 0) {
        Promise.allSettled(
          activeDocs.map(async (doc: any) => {
            try {
              const docJobs = await api.getDocumentJobs(doc.id);
              if (docJobs && docJobs.length > 0) {
                setJobs(prev => ({ ...prev, [doc.id]: docJobs[0] }));
              }
            } catch { /* ignore individual job fetch errors */ }
          })
        );
      }
    } catch (e) {
      console.warn("Could not load documents from API:", e);
      // Preserve existing documents if already loaded; only fallback if completely empty
      setDocuments(prev => {
        if (prev && prev.length > 0) return prev;
        return [];
      });
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Only poll when there are active documents in progress
  const hasActive = documents.some(d =>
    ["processing", "queued"].includes(d.status?.toLowerCase())
  );

  useEffect(() => {
    if (!hasActive) return;
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [hasActive, load]);

  // Auto-expand active documents
  useEffect(() => {
    const active = documents.filter(d => ["processing", "queued"].includes(d.status?.toLowerCase()));
    if (active.length > 0) {
      setExpandedDocs(prev => new Set([...prev, ...active.map(d => d.id)]));
    }
  }, [documents]);

  const toggleExpand = (id: string) => {
    setExpandedDocs(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleCancel = async (docId: string) => {
    setActionLoading(prev => ({ ...prev, [`cancel_${docId}`]: true }));
    try {
      await api.cancelDocument(docId);
      await load();
    } catch (e) {
      console.error("Cancel failed:", e);
    } finally {
      setActionLoading(prev => ({ ...prev, [`cancel_${docId}`]: false }));
    }
  };

  const handleProcess = async (docId: string) => {
    setActionLoading(prev => ({ ...prev, [`process_${docId}`]: true }));
    try {
      await api.processDocument(docId);
      await load();
    } catch (e) {
      console.error("Process failed:", e);
    } finally {
      setActionLoading(prev => ({ ...prev, [`process_${docId}`]: false }));
    }
  };

  const handleDelete = async (docId: string) => {
    setActionLoading(prev => ({ ...prev, [`delete_${docId}`]: true }));
    setDeleteConfirm(null);
    try {
      await api.deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch (e) {
      console.error("Delete failed:", e);
    } finally {
      setActionLoading(prev => ({ ...prev, [`delete_${docId}`]: false }));
    }
  };

  const completedDocs = documents.filter(d => d.status?.toLowerCase() === "completed");
  const activeDocs = documents.filter(d => ["processing", "queued", "uploaded", "failed"].includes(d.status?.toLowerCase()));

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Processing Pipeline</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time AI pipeline progress — {documents.length} document{documents.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => load()}
            className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:border-slate-300 px-3 py-2 rounded-xl transition-all shadow-2xs cursor-pointer font-medium"
            title="Refresh pipeline status"
          >
            <RefreshCw size={13} className={hasActive ? "animate-spin text-blue-600" : "text-slate-500"} />
            <span>Refresh</span>
          </button>
          <div className="flex items-center gap-2 text-xs bg-slate-50 border border-slate-200/80 px-3 py-2 rounded-xl font-medium">
            {hasActive ? (
              <>
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                <span className="text-blue-700 font-semibold">Live Polling (8s)</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="text-slate-500">Pipeline Idle</span>
              </>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="bg-white rounded-2xl border border-slate-100 shadow-sm h-48 animate-pulse" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <Layers size={28} className="text-slate-300" />
          </div>
          <p className="text-slate-600 font-medium">No documents yet</p>
          <p className="text-sm text-slate-400 mt-1">Upload a document from the Ingestion page to get started.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Active / In-Progress */}
          {activeDocs.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Active</h2>
                <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {activeDocs.length}
                </span>
              </div>
              {activeDocs.map(doc => <DocumentCard
                key={doc.id}
                doc={doc}
                job={jobs[doc.id]}
                expanded={expandedDocs.has(doc.id)}
                onToggle={() => toggleExpand(doc.id)}
                onCancel={() => handleCancel(doc.id)}
                onProcess={() => handleProcess(doc.id)}
                onDeleteRequest={() => setDeleteConfirm(doc.id)}
                cancelLoading={!!actionLoading[`cancel_${doc.id}`]}
                processLoading={!!actionLoading[`process_${doc.id}`]}
                deleteLoading={!!actionLoading[`delete_${doc.id}`]}
              />)}
            </section>
          )}

          {/* Completed */}
          {completedDocs.length > 0 && (
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Completed</h2>
                <span className="bg-emerald-100 text-emerald-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {completedDocs.length}
                </span>
              </div>
              {completedDocs.map(doc => <DocumentCard
                key={doc.id}
                doc={doc}
                job={jobs[doc.id]}
                expanded={expandedDocs.has(doc.id)}
                onToggle={() => toggleExpand(doc.id)}
                onCancel={() => handleCancel(doc.id)}
                onProcess={() => handleProcess(doc.id)}
                onDeleteRequest={() => setDeleteConfirm(doc.id)}
                cancelLoading={!!actionLoading[`cancel_${doc.id}`]}
                processLoading={!!actionLoading[`process_${doc.id}`]}
                deleteLoading={!!actionLoading[`delete_${doc.id}`]}
              />)}
            </section>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 p-6 w-full max-w-md mx-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
                <AlertTriangle size={20} className="text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900">Delete Document</h3>
                <p className="text-sm text-slate-500 mt-1">
                  This will permanently delete the document and all associated pages, articles, mentions, and alerts.
                  This action cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex gap-3 mt-6 justify-end">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors flex items-center gap-2"
              >
                <Trash2 size={14} />
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface DocumentCardProps {
  doc: any;
  job: any;
  expanded: boolean;
  onToggle: () => void;
  onCancel: () => void;
  onProcess: () => void;
  onDeleteRequest: () => void;
  cancelLoading: boolean;
  processLoading: boolean;
  deleteLoading: boolean;
}

function DocumentCard({
  doc, job, expanded, onToggle, onCancel, onProcess, onDeleteRequest, cancelLoading, processLoading, deleteLoading,
}: DocumentCardProps) {
  const status = doc.status?.toLowerCase();
  const isActive = ["processing", "queued"].includes(status);
  const isFailed = status === "failed";

  const stageStatuses: Record<string, StageStatus> = Object.fromEntries(
    pipelineStages.map(s => [
      s.key,
      status === "completed" ? "completed" : "pending"
    ])
  );
  if (job?.stages) {
    Object.assign(stageStatuses, job.stages);
  }

  const progress = job?.progress_percent ?? (status === "completed" ? 100 : 0);
  const completedCount = Object.values(stageStatuses).filter(s => s === "completed").length;
  const runningStage = pipelineStages.find(s => stageStatuses[s.key] === "running");

  const progressColor =
    status === "completed" ? "from-emerald-500 to-emerald-400" :
    isFailed ? "from-red-500 to-red-400" :
    "from-blue-600 to-blue-400";

  return (
    <div className={`bg-white rounded-2xl border shadow-sm transition-all duration-300 overflow-hidden ${
      isFailed ? "border-red-200" : isActive ? "border-blue-200" : "border-slate-100"
    }`}>
      {/* Top accent bar */}
      <div className={`h-0.5 w-full bg-gradient-to-r ${progressColor}`}
        style={{ width: `${progress}%`, transition: "width 0.6s ease" }}
      />

      {/* Header */}
      <div className="px-5 py-4 flex items-center gap-4">
        {/* File Icon */}
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isFailed ? "bg-red-50" : isActive ? "bg-blue-50" : "bg-emerald-50"
        }`}>
          <FileText size={18} className={
            isFailed ? "text-red-500" : isActive ? "text-blue-500" : "text-emerald-500"
          } />
        </div>

        {/* Doc Info */}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 truncate text-sm">
            {doc.original_filename || doc.filename}
          </p>
          <div className="flex items-center gap-3 mt-0.5 flex-wrap">
            <span className="text-xs text-slate-400">
              {doc.page_count > 0 ? `${doc.page_count} page${doc.page_count !== 1 ? "s" : ""}` : "—"}
            </span>
            {doc.file_size > 0 && (
              <span className="text-xs text-slate-400">{formatFileSize(doc.file_size)}</span>
            )}
            {doc.processing_duration_ms && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Timer size={11} />
                {formatDuration(doc.processing_duration_ms)}
              </span>
            )}
          </div>
        </div>

        {/* Progress + Status */}
        <div className="flex items-center gap-4 flex-shrink-0">
          {/* Progress bar */}
          <div className="hidden sm:flex flex-col items-end gap-1">
            <div className="w-28 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${progressColor} transition-all duration-700`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs font-mono text-slate-400">{Math.round(progress)}%</span>
          </div>

          <StatusBadge status={doc.status} />

          {/* Action Buttons */}
          <div className="flex items-center gap-1.5">
            {(isFailed || status === "uploaded") && (
              <button
                onClick={onProcess}
                disabled={processLoading}
                title={isFailed ? "Retry processing" : "Start processing"}
                className="p-2 rounded-lg text-blue-600 hover:bg-blue-50 hover:text-blue-700 transition-colors disabled:opacity-40"
              >
                {processLoading
                  ? <Loader2 size={15} className="animate-spin" />
                  : <RotateCcw size={15} />
                }
              </button>
            )}
            {isActive && (
              <button
                onClick={onCancel}
                disabled={cancelLoading}
                title="Stop processing"
                className="p-2 rounded-lg text-amber-600 hover:bg-amber-50 hover:text-amber-700 transition-colors disabled:opacity-40"
              >
                {cancelLoading
                  ? <Loader2 size={15} className="animate-spin" />
                  : <StopCircle size={15} />
                }
              </button>
            )}
            <button
              onClick={onDeleteRequest}
              disabled={deleteLoading}
              title="Delete document"
              className="p-2 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-40"
            >
              {deleteLoading
                ? <Loader2 size={15} className="animate-spin" />
                : <Trash2 size={15} />
              }
            </button>
            <button
              onClick={onToggle}
              className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors"
              title={expanded ? "Collapse stages" : "Expand stages"}
            >
              {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
          </div>
        </div>
      </div>

      {/* Running Stage Banner */}
      {runningStage && (
        <div className="mx-5 mb-3 flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2">
          <Loader2 size={13} className="text-blue-500 animate-spin flex-shrink-0" />
          <span className="text-xs text-blue-700 font-medium">
            Currently running: <span className="font-semibold">{runningStage.label}</span>
          </span>
          <span className="text-xs text-blue-500 ml-auto">{completedCount}/{pipelineStages.length} stages</span>
        </div>
      )}

      {/* Cancelled/Failed Banner */}
      {isFailed && doc.error_message && (
        <div className="mx-5 mb-3 flex items-center gap-2 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
          <XCircle size={13} className="text-red-500 flex-shrink-0" />
          <span className="text-xs text-red-700 font-medium">{doc.error_message}</span>
        </div>
      )}

      {/* Pipeline Stages Grid */}
      {expanded && (
        <div className="px-5 pb-5">
          <div className="border-t border-slate-100 pt-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
              {pipelineStages.map((stage, idx) => {
                const stageStatus = stageStatuses[stage.key] as StageStatus || "pending";
                const { Icon } = stage;

                return (
                  <div
                    key={stage.key}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all duration-200 ${
                      stageStatus === "completed"
                        ? "bg-emerald-50 border-emerald-100"
                        : stageStatus === "running"
                        ? "bg-blue-50 border-blue-200 shadow-sm"
                        : stageStatus === "failed"
                        ? "bg-red-50 border-red-100"
                        : "bg-slate-50 border-slate-100"
                    }`}
                  >
                    {/* Stage number */}
                    <span className={`text-[10px] font-bold w-4 text-center flex-shrink-0 ${
                      stageStatus === "completed" ? "text-emerald-400" :
                      stageStatus === "running" ? "text-blue-400" :
                      stageStatus === "failed" ? "text-red-400" :
                      "text-slate-300"
                    }`}>
                      {String(idx + 1).padStart(2, "0")}
                    </span>

                    {/* Stage icon */}
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      stageStatus === "completed" ? "bg-emerald-100" :
                      stageStatus === "running" ? "bg-blue-100" :
                      stageStatus === "failed" ? "bg-red-100" :
                      "bg-slate-200"
                    }`}>
                      <Icon size={13} className={
                        stageStatus === "completed" ? "text-emerald-600" :
                        stageStatus === "running" ? "text-blue-600" :
                        stageStatus === "failed" ? "text-red-600" :
                        "text-slate-400"
                      } />
                    </div>

                    {/* Stage info */}
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs font-semibold truncate ${
                        stageStatus === "completed" ? "text-emerald-700" :
                        stageStatus === "running" ? "text-blue-700" :
                        stageStatus === "failed" ? "text-red-700" :
                        "text-slate-400"
                      }`}>
                        {stage.label}
                      </p>
                      <p className="text-[10px] text-slate-400 truncate">{stage.description}</p>
                    </div>

                    {/* Status icon */}
                    <div className="flex-shrink-0">
                      <StageIcon status={stageStatus} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
