"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  Globe2,
  Languages,
  Activity,
  AlertTriangle,
  Tag,
  BarChart3,
  TrendingUp,
  Smile,
  Meh,
  Frown,
} from "lucide-react";

export default function CoveragePage() {
  const [coverage, setCoverage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setCoverage(await api.getCoverage());
      } catch {
        setCoverage({
          language_coverage: [
            { language: "hi", count: 89, percentage: 57.1 },
            { language: "ta", count: 42, percentage: 26.9 },
            { language: "en", count: 25, percentage: 16.0 },
          ],
          sentiment_distribution: { positive: 34, neutral: 78, negative: 44 },
          crisis_topics: [
            { topic: "regulatory_action", count: 8, avg_risk_score: 76 },
            { topic: "product_complaint", count: 5, avg_risk_score: 52 },
            { topic: "financial_issue", count: 3, avg_risk_score: 61 },
          ],
          brand_mentions: [
            {
              brand_name: "PayU",
              total_mentions: 5,
              positive: 0,
              neutral: 1,
              negative: 4,
              critical_alerts: 2,
              avg_risk_score: 78,
            },
            {
              brand_name: "Paytm",
              total_mentions: 3,
              positive: 1,
              neutral: 1,
              negative: 1,
              critical_alerts: 0,
              avg_risk_score: 42,
            },
            {
              brand_name: "PhonePe",
              total_mentions: 2,
              positive: 2,
              neutral: 0,
              negative: 0,
              critical_alerts: 0,
              avg_risk_score: 12,
            },
          ],
        });
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-14 w-1/3 bg-slate-200 rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-64 rounded-2xl bg-slate-200" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <Globe2 className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Coverage Analytics
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Regional newspaper monitoring footprint, linguistic distribution, and sentiment breakdown
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Language Distribution */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2.5 mb-5">
            <div className="p-2 rounded-xl bg-primary-50 text-primary-600">
              <Languages className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Language Distribution
              </h3>
              <p className="text-xs text-slate-400">
                Extracted article count per regional language
              </p>
            </div>
          </div>
          <div className="space-y-4">
            {coverage?.language_coverage?.map((lang: any) => (
              <div key={lang.language} className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-slate-700 uppercase font-mono">
                    {lang.language}
                  </span>
                  <span className="text-slate-500 font-mono">
                    {lang.count} articles ({lang.percentage}%)
                  </span>
                </div>
                <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden p-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-primary-500 to-violet-500 rounded-full transition-all duration-700"
                    style={{ width: `${lang.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sentiment Distribution */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2.5 mb-5">
            <div className="p-2 rounded-xl bg-violet-50 text-violet-600">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Sentiment Distribution
              </h3>
              <p className="text-xs text-slate-400">
                Aggregated sentiment breakdown across editions
              </p>
            </div>
          </div>
          <div className="flex items-end justify-around h-44 pt-4 border-b border-slate-100 pb-2">
            {[
              {
                label: "Positive",
                icon: Smile,
                value: coverage?.sentiment_distribution?.positive || 0,
                color: "bg-emerald-500",
                textColor: "text-emerald-600",
                bgLight: "bg-emerald-50",
              },
              {
                label: "Neutral",
                icon: Meh,
                value: coverage?.sentiment_distribution?.neutral || 0,
                color: "bg-slate-400",
                textColor: "text-slate-600",
                bgLight: "bg-slate-50",
              },
              {
                label: "Negative",
                icon: Frown,
                value: coverage?.sentiment_distribution?.negative || 0,
                color: "bg-red-500",
                textColor: "text-red-600",
                bgLight: "bg-red-50",
              },
            ].map((item) => {
              const max = Math.max(
                coverage?.sentiment_distribution?.positive || 1,
                coverage?.sentiment_distribution?.neutral || 1,
                coverage?.sentiment_distribution?.negative || 1
              );
              const height = (item.value / max) * 100;
              const Icon = item.icon;
              return (
                <div key={item.label} className="flex flex-col items-center gap-2 w-20">
                  <span className={`text-base font-extrabold ${item.textColor}`}>
                    {item.value}
                  </span>
                  <div
                    className={`w-12 rounded-t-xl ${item.color} transition-all duration-700 shadow-sm`}
                    style={{ height: `${Math.max(height, 12)}%` }}
                  />
                  <div className="flex items-center gap-1 mt-1">
                    <Icon className={`w-3.5 h-3.5 ${item.textColor}`} />
                    <span className="text-[11px] font-semibold text-slate-600">
                      {item.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Crisis Topics */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Crisis Topics
              </h3>
              <p className="text-xs text-slate-400">
                Frequency and average severity of classified risk topics
              </p>
            </div>
          </div>
          <div className="space-y-2.5">
            {coverage?.crisis_topics?.map((topic: any) => (
              <div
                key={topic.topic}
                className="flex items-center justify-between p-3.5 bg-slate-50/80 hover:bg-slate-50 rounded-xl border border-slate-100 transition-colors"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-800 capitalize">
                    {topic.topic.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-slate-400">
                    {topic.count} detected incidents
                  </p>
                </div>
                <div
                  className={`badge ${
                    topic.avg_risk_score >= 70
                      ? "badge-critical"
                      : topic.avg_risk_score >= 50
                      ? "badge-high"
                      : "badge-medium"
                  }`}
                >
                  Avg Risk {Math.round(topic.avg_risk_score)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Brand Mentions */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="p-2 rounded-xl bg-primary-50 text-primary-600">
              <Tag className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Brand Sentiment Summary
              </h3>
              <p className="text-xs text-slate-400">
                Total mentions and sentiment balance by brand
              </p>
            </div>
          </div>
          <div className="space-y-2.5">
            {coverage?.brand_mentions?.map((brand: any) => (
              <div
                key={brand.brand_name}
                className="flex items-center justify-between p-3.5 bg-slate-50/80 hover:bg-slate-50 rounded-xl border border-slate-100 transition-colors"
              >
                <div>
                  <span className="text-sm font-bold text-primary-700">
                    {brand.brand_name}
                  </span>
                  <p className="text-xs text-slate-400">
                    {brand.total_mentions} mentions • Avg Risk: {brand.avg_risk_score}
                  </p>
                </div>
                <div className="flex items-center gap-1.5 font-mono text-xs">
                  <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200/60">
                    +{brand.positive}
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-semibold border border-slate-200/60">
                    {brand.neutral}
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-red-50 text-red-700 font-semibold border border-red-200/60">
                    -{brand.negative}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
