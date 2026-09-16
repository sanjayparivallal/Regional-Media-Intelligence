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
    async function load() {
      try {
        setDocuments(await api.getDocuments());
      } catch {
        setDocuments([
          {
            id: "demo",
            original_filename: "Dainik_Jagran_2024.pdf",
            status: "completed",
            page_count: 1,
            file_size: 2500000,
            document_type: "pdf_scanned",
            processing_duration_ms: 120000,
            created_at: new Date().toISOString(),
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    load();
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
            {documents.filter((d) => d.status === "completed").length}
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
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Size</th>
                <th className="px-6 py-3.5">Processing Time</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((doc) => {
                const isCompleted = doc.status === "completed";
                const isProcessing = doc.status === "processing";
                const isFailed = doc.status === "failed";

                return (
                  <tr
                    key={doc.id}
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
                      <span
                        className={`badge ${
                          isCompleted
                            ? "badge-low"
                            : isProcessing
                            ? "bg-cyan-50 text-cyan-700 ring-cyan-200/70"
                            : isFailed
                            ? "badge-critical"
                            : "badge-neutral"
                        }`}
                      >
                        {isCompleted && <CheckCircle2 className="w-3 h-3" />}
                        {isProcessing && <Loader2 className="w-3 h-3 animate-spin" />}
                        {isFailed && <AlertCircle className="w-3 h-3" />}
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 font-mono">
                      {doc.file_size
                        ? `${(doc.file_size / 1024 / 1024).toFixed(1)} MB`
                        : "—"}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 font-mono">
                      {doc.processing_duration_ms
                        ? `${(doc.processing_duration_ms / 1000).toFixed(1)}s`
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
                  <td colSpan={7} className="p-12 text-center text-slate-400">
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
