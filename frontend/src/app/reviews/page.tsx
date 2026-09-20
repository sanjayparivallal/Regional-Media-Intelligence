"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  CheckSquare,
  Check,
  X,
  Edit3,
  Sparkles,
  Languages,
  Activity,
  FileSearch,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from "lucide-react";

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getReviews();
        setReviews(data || []);
      } catch (e) {
        console.warn("Could not load reviews from API:", e);
        setReviews([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleAction = async (id: string, status: string) => {
    try {
      await api.updateReview(id, { status, reviewer: "analyst" });
      setReviews((prev) => prev.map((r) => (r.id === id ? { ...r, status } : r)));
    } catch (e) {
      setReviews((prev) => prev.map((r) => (r.id === id ? { ...r, status } : r)));
    }
  };

  const getReviewIcon = (type: string) => {
    switch (type) {
      case "quality":
        return <FileSearch className="w-5 h-5 text-amber-600" />;
      case "translation":
        return <Languages className="w-5 h-5 text-cyan-600" />;
      case "sentiment":
        return <Activity className="w-5 h-5 text-violet-600" />;
      default:
        return <HelpCircle className="w-5 h-5 text-slate-600" />;
    }
  };

  const pendingCount = reviews.filter((r) => r.status === "pending").length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
              <CheckSquare className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Human-in-the-Loop Review Queue
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Low-confidence AI extractions and boundary decisions flagged for analyst verification
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge bg-amber-50 text-amber-700 ring-amber-200/70 font-bold px-3 py-1">
            {pendingCount} Pending Verification
          </span>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-2xl bg-slate-200/70 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((review, idx) => {
            const isPending = review.status === "pending";
            return (
              <div
                key={`${review.id}-${idx}`}
                className={`glass-card p-6 transition-all ${
                  !isPending ? "opacity-60 bg-slate-50/50" : "hover:border-slate-300"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-start gap-5">
                  <div
                    className={`w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                      review.review_type === "quality"
                        ? "bg-amber-50"
                        : review.review_type === "translation"
                        ? "bg-cyan-50"
                        : review.review_type === "sentiment"
                        ? "bg-violet-50"
                        : "bg-slate-100"
                    }`}
                  >
                    {getReviewIcon(review.review_type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="text-sm font-bold text-slate-900 capitalize">
                        {review.review_type} Verification
                      </span>
                      <span className={`badge badge-${review.priority || "normal"}`}>
                        {(review.priority || "normal").toUpperCase()}
                      </span>
                      <span
                        className={`badge ${
                          review.status === "pending"
                            ? "bg-amber-50 text-amber-700 ring-amber-200/70"
                            : review.status === "approved"
                            ? "bg-emerald-50 text-emerald-700 ring-emerald-200/70"
                            : review.status === "rejected"
                            ? "bg-red-50 text-red-700 ring-red-200/70"
                            : "badge-neutral"
                        }`}
                      >
                        {review.status}
                      </span>
                    </div>

                    <p className="text-sm text-slate-600 font-medium">
                      {review.reason}
                    </p>

                    {review.ai_output && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {Object.entries(review.ai_output).map(([key, value]) => (
                          <span
                            key={key}
                            className="inline-flex items-center gap-1.5 text-xs bg-slate-100/90 text-slate-600 px-2.5 py-1 rounded-lg border border-slate-200/60 font-mono"
                          >
                            <span className="text-slate-400 font-sans">{key}:</span>
                            <span className="font-semibold text-slate-800">
                              {String(value)}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {isPending && (
                    <div className="flex flex-wrap md:flex-col gap-2 flex-shrink-0 self-end md:self-center">
                      <button
                        onClick={() => handleAction(review.id, "approved")}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200/80 rounded-xl text-xs font-semibold transition-all cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Approve</span>
                      </button>
                      <button
                        onClick={() => handleAction(review.id, "corrected")}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200/80 rounded-xl text-xs font-semibold transition-all cursor-pointer"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Correct</span>
                      </button>
                      <button
                        onClick={() => handleAction(review.id, "rejected")}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-red-50 text-red-700 hover:bg-red-100 border border-red-200/80 rounded-xl text-xs font-semibold transition-all cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {reviews.length === 0 && (
            <div className="glass-card p-16 text-center">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
                <Sparkles className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">
                Review Queue Clear
              </h3>
              <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
                All AI OCR outputs, entity mappings, and sentiment classifications meet high confidence thresholds.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
