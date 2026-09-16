"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  UploadCloud,
  FileText,
  Image as ImageIcon,
  Play,
  CheckCircle2,
  AlertCircle,
  X,
  Trash2,
  Camera,
  Layers,
  ArrowRight,
  Loader2,
  Sparkles,
} from "lucide-react";

export default function IngestionPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<any[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter((f) =>
      [".pdf", ".png", ".jpg", ".jpeg"].some((ext) =>
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
    const results = [];

    for (const file of files) {
      try {
        const doc = await api.uploadDocument(file);
        results.push({ file: file.name, status: "uploaded", doc });
        // Auto-start processing pipeline
        await api.processDocument(doc.id);
        results[results.length - 1].status = "processing";
      } catch (e: any) {
        results.push({ file: file.name, status: "error", error: e.message });
      }
    }

    setUploadResults(results);
    setFiles([]);
    setUploading(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <UploadCloud className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Document Ingestion
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Upload multi-page newspaper PDFs and scanned broadsheet images for AI processing
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
              Supports scanned broadsheets, PDF editions, and high-res camera captures up to 100MB
            </p>
          </div>
          <div>
            <label className="btn-primary cursor-pointer">
              <Sparkles className="w-4 h-4" />
              <span>Browse Local Files</span>
              <input
                type="file"
                className="hidden"
                multiple
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileSelect}
              />
            </label>
          </div>
        </div>
      </div>

      {/* Upload Queue Card */}
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

      {/* Upload Results Card */}
      {uploadResults.length > 0 && (
        <div className="glass-card overflow-hidden animate-slide-up">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/60">
            <h2 className="text-sm font-bold text-slate-900">Pipeline Ingestion Results</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {uploadResults.map((result, i) => (
              <div
                key={i}
                className="px-6 py-4 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  {result.status === "processing" ? (
                    <div className="w-8 h-8 rounded-full bg-cyan-50 text-cyan-600 flex items-center justify-center">
                      <Loader2 className="w-4 h-4 animate-spin" />
                    </div>
                  ) : result.status === "uploaded" ? (
                    <div className="w-8 h-8 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-red-50 text-red-600 flex items-center justify-center">
                      <AlertCircle className="w-4 h-4" />
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-semibold text-slate-800">
                      {result.file}
                    </p>
                    <p
                      className={`text-xs ${
                        result.status === "error"
                          ? "text-red-600 font-medium"
                          : "text-emerald-600 font-medium"
                      }`}
                    >
                      {result.status === "processing"
                        ? "Dispatched to automated extraction pipeline"
                        : result.status === "uploaded"
                        ? "Uploaded successfully"
                        : result.error}
                    </p>
                  </div>
                </div>
                {result.doc && (
                  <Link
                    href="/processing"
                    className="btn-secondary text-xs"
                  >
                    <span>Track Pipeline</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supported Formats Info Cards */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-bold text-slate-900 mb-3">
          Supported Document Formats
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            {
              ext: "PDF",
              desc: "Scanned or digital e-papers",
              icon: FileText,
              iconColor: "text-red-500 bg-red-50",
            },
            {
              ext: "PNG",
              desc: "Lossless broadsheet scans",
              icon: ImageIcon,
              iconColor: "text-cyan-500 bg-cyan-50",
            },
            {
              ext: "JPG",
              desc: "Newspaper photography",
              icon: Camera,
              iconColor: "text-amber-500 bg-amber-50",
            },
            {
              ext: "JPEG",
              desc: "High-density clippings",
              icon: Layers,
              iconColor: "text-violet-500 bg-violet-50",
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
