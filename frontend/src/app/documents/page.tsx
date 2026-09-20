"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  FileText,
  UploadCloud,
  Layers,
  Search,
  CheckCircle2,
  Loader2,
  Clock,
  AlertCircle,
  ExternalLink,
  Trash2,
  HardDrive,
} from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let isSubscribed = true;
    async function load() {
      try {
        const data = await api.getDocuments();
        const unique = (data || []).filter((d: any, idx: number, arr: any[]) =>
          arr.findIndex((item: any) => item.id === d.id) === idx
        );
        if (isSubscribed) setDocuments(unique);
      } catch (e) {
        console.error("Failed to load documents:", e);
        if (isSubscribed) setDocuments([]);
      } finally {
        if (isSubscribed) setLoading(false);
      }
    }
    load();

    const intervalId = setInterval(() => {
      setDocuments((prev) => {
        if (prev.some((d) => d.status === "PROCESSING" || d.status === "UPLOADED")) {
          api.getDocuments().then((data) => {
            if (isSubscribed) {
              const unique = (data || []).filter((d: any, idx: number, arr: any[]) =>
                arr.findIndex((item: any) => item.id === d.id) === idx
              );
              setDocuments(unique);
            }
          }).catch(console.error);
        }
        return prev;
      });
    }, 2000);

    return () => {
      isSubscribed = false;
      clearInterval(intervalId);
    };
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this document and all associated extracted data?")) {
      return;
    }
    try {
      if ((api as any).deleteDocument) {
        await (api as any).deleteDocument(id);
      }
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      console.error(e);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    }
  };

  const filtered = documents.filter((d) =>
    (d.original_filename || "").toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = documents.reduce((acc, d) => acc + (d.page_count || 0), 0);
  const totalSize = documents.reduce((acc, d) => acc + (d.file_size || 0), 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
              <FileText className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Document Archive
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Master registry of all ingested newspaper issues and processing statuses
          </p>
        </div>
        <Link href="/ingestion" className="btn-primary self-start sm:self-auto">
          <UploadCloud className="w-4 h-4" />
          <span>Upload Edition</span>
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card primary">
          <p className="text-xs font-semibold text-slate-500 uppercase">Registered Files</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">{documents.length}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Scanned editions</p>
        </div>
        <div className="kpi-card cyan">
          <p className="text-xs font-semibold text-slate-500 uppercase">Total Pages</p>
          <p className="text-2xl font-extrabold text-cyan-600 mt-1">{totalPages}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Rendered broadsheets</p>
        </div>
        <div className="kpi-card emerald">
          <p className="text-xs font-semibold text-slate-500 uppercase">Completed</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">
            {documents.filter((d) => d.status === "COMPLETED").length}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Fully indexed</p>
        </div>
        <div className="kpi-card violet">
          <p className="text-xs font-semibold text-slate-500 uppercase">Storage Used</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">
            {(totalSize / 1024 / 1024).toFixed(1)} MB
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Local PDF & OCR cache</p>
        </div>
      </div>

      {/* Search Input */}
      <div className="glass-card p-4">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter documents by filename or ID..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 rounded-xl text-sm border border-slate-200/80 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all"
          />
        </div>
      </div>

      {/* Documents Data Table Card */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/75 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="px-6 py-3.5">Document</th>
                <th className="px-6 py-3.5">Type</th>
                <th className="px-6 py-3.5">Pages</th>
                <th className="px-6 py-3.5">Status & Progress</th>
                <th className="px-6 py-3.5">Sentiment</th>
                <th className="px-6 py-3.5">Uploaded</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((doc, idx) => {
                const isCompleted = doc.status === "COMPLETED";
                const isProcessing = doc.status === "PROCESSING";
                const isFailed = doc.status === "FAILED";

                return (
                  <tr
                    key={`${doc.id}-${idx}`}
                    className="hover:bg-slate-50/60 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center text-slate-600 group-hover:bg-primary-50 group-hover:text-primary-600 transition-colors">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-900 leading-tight">
                            {doc.original_filename}
                          </p>
                          <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                            ID: {doc.id?.substring(0, 8)}...
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md font-mono border border-slate-200/60">
                        {doc.document_type || "pdf_scanned"}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-700">
                      {doc.page_count || 1}
                    </td>
                    <td className="px-6 py-4">
                      {isProcessing ? (
                        <div className="w-52">
                          {/* Phase label */}
                          {(() => {
                            const stage = (doc.current_stage || "").toLowerCase();
                            const pct = Math.round(doc.progress_percent || 0);
                            let phaseNum = 1, phaseColor = "text-violet-700", barColor = "bg-violet-500", bgColor = "bg-violet-100";
                            if (stage.includes("phase 2") || stage.includes("translat")) {
                              phaseNum = 2; phaseColor = "text-amber-700"; barColor = "bg-amber-500"; bgColor = "bg-amber-100";
                            } else if (stage.includes("phase 3") || stage.includes("sentiment")) {
                              phaseNum = 3; phaseColor = "text-emerald-700"; barColor = "bg-emerald-500"; bgColor = "bg-emerald-100";
                            }
                            const labels = ["OCR Scan", "Translating", "Sentiment"];
                            return (
                              <>
                                <div className="flex justify-between items-center mb-1">
                                  <span className={`text-[10px] font-bold uppercase ${phaseColor}`}>
                                    Phase {phaseNum}: {labels[phaseNum - 1]}
                                  </span>
                                  <span className={`text-[10px] font-bold ${phaseColor}`}>{pct}%</span>
                                </div>
                                <div className={`w-full ${bgColor} rounded-full h-1.5 overflow-hidden`}>
                                  <div className={`${barColor} h-1.5 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                                </div>
                                <div className="flex gap-1 mt-1.5">
                                  {[1, 2, 3].map(n => (
                                    <div key={n} className={`flex-1 h-0.5 rounded-full ${
                                      n < phaseNum ? "bg-slate-400" : n === phaseNum ? barColor : "bg-slate-200"
                                    }`} />
                                  ))}
                                </div>
                              </>
                            );
                          })()}
                        </div>
                      ) : (
                        <span
                          className={`badge ${
                            isCompleted
                              ? "badge-low"
                              : isFailed
                              ? "badge-critical"
                              : "badge-neutral"
                          }`}
                        >
                          {isCompleted && <CheckCircle2 className="w-3 h-3" />}
                          {isFailed && <AlertCircle className="w-3 h-3" />}
                          {doc.status}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {doc.overall_sentiment ? (
                        <span className={`px-2 py-1 text-[11px] font-bold rounded-lg ${
                          doc.overall_sentiment === "NEGATIVE" ? "bg-red-50 text-red-700" :
                          doc.overall_sentiment === "POSITIVE" ? "bg-emerald-50 text-emerald-700" :
                          "bg-slate-100 text-slate-700"
                        }`}>
                          {doc.overall_sentiment}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {doc.created_at
                        ? new Date(doc.created_at).toLocaleString("en-IN", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })
                        : "—"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href="/processing"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-primary-600 hover:bg-primary-50 transition-colors"
                          title="View in Processing Pipeline"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                          title="Delete Document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-12 text-center text-slate-400">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <p className="font-semibold text-slate-700">No documents found</p>
                    <p className="text-xs text-slate-400 mt-1">
                      Upload a newspaper broadsheet to populate this archive
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
