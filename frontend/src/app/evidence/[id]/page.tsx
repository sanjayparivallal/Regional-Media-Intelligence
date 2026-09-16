"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import RiskScore from "@/components/alerts/RiskScore";
import Link from "next/link";
import {
  FileText,
  Languages,
  BrainCircuit,
  History,
  Newspaper,
  ShieldAlert,
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  Layers,
  ChevronRight,
} from "lucide-react";

export default function EvidenceViewerPage() {
  const params = useParams();
  const alertId = params.id as string;
  const [evidence, setEvidence] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("ocr");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getAlertEvidence(alertId);
        setEvidence(data);
      } catch {
        // Fallback demo evidence
        setEvidence({
          alert: {
            id: alertId,
            title: "Regulatory Action: RBI takes action against PayU",
            priority: "critical",
            risk_score: 91,
            risk_breakdown: {
              sentiment: { score: 28, max: 30 },
              brand: { score: 24, max: 25 },
              topic: { score: 18, max: 20 },
              reach: { score: 13, max: 15 },
              confidence: { score: 8, max: 10 },
              total: 91,
              priority: "critical",
            },
            brand_name: "PayU",
            publication_name: "Dainik Jagran",
            page_number: 1,
            language: "hi",
            sentiment: "negative",
            sentiment_confidence: 91,
            crisis_topic: "regulatory_action",
          },
          article: {
            headline: "PayU पर RBI की कार्रवाई: डिजिटल भुगतान कंपनी पर लगा प्रतिबंध",
            body_text:
              "भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है। RBI ने कहा कि कंपनी ने KYC नियमों का उल्लंघन किया है।",
            full_text:
              "PayU पर RBI की कार्रवाई: डिजिटल भुगतान कंपनी पर लगा प्रतिबंध भारतीय रिजर्व बैंक ने PayU फाइनेंस पर नए ग्राहकों को जोड़ने पर रोक लगा दी है।",
            detected_language: "hi",
            ocr_confidence: 92.5,
            bbox_x: 50,
            bbox_y: 80,
            bbox_width: 900,
            bbox_height: 280,
          },
          page: {
            page_number: 1,
            width: 2480,
            height: 3508,
            ocr_confidence: 92.5,
            ocr_engine_used: "hybrid(paddleocr)",
          },
          document: {
            filename: "Dainik_Jagran_2024.pdf",
            original_filename: "Dainik_Jagran_2024_Sep_10.pdf",
          },
          translations: [
            {
              source_language: "hi",
              translated_text:
                "RBI takes action against PayU: Ban imposed on digital payment company. The Reserve Bank of India has banned PayU Finance from onboarding new customers. RBI stated that the company violated KYC regulations.",
              confidence: 91,
            },
          ],
          entities: [
            { text: "PayU", entity_type: "ORGANIZATION", confidence: 0.98 },
            { text: "RBI", entity_type: "REGULATOR", confidence: 0.97 },
            { text: "Reserve Bank of India", entity_type: "REGULATOR", confidence: 0.96 },
          ],
          audit_trail: [
            { action: "document_uploaded", stage: "upload", processing_time_ms: 0, created_at: new Date(Date.now() - 300000).toISOString() },
            { action: "pdf_classified", stage: "pdf_classification", processing_time_ms: 1200, created_at: new Date(Date.now() - 290000).toISOString() },
            { action: "pages_rendered", stage: "page_rendering", processing_time_ms: 3500, created_at: new Date(Date.now() - 280000).toISOString() },
            { action: "ocr_completed", stage: "ocr", processing_time_ms: 15000, created_at: new Date(Date.now() - 260000).toISOString() },
            { action: "layout_analyzed", stage: "layout_analysis", processing_time_ms: 2800, created_at: new Date(Date.now() - 240000).toISOString() },
            { action: "articles_extracted", stage: "article_extraction", processing_time_ms: 1500, created_at: new Date(Date.now() - 230000).toISOString() },
            { action: "language_detected", stage: "language_detection", processing_time_ms: 200, created_at: new Date(Date.now() - 225000).toISOString() },
            { action: "translation_completed", stage: "translation", processing_time_ms: 8500, created_at: new Date(Date.now() - 210000).toISOString() },
            { action: "entities_extracted", stage: "entity_detection", processing_time_ms: 1200, created_at: new Date(Date.now() - 200000).toISOString() },
            { action: "brands_matched", stage: "brand_matching", processing_time_ms: 300, created_at: new Date(Date.now() - 195000).toISOString() },
            { action: "sentiment_analyzed", stage: "sentiment_analysis", processing_time_ms: 2100, created_at: new Date(Date.now() - 190000).toISOString() },
            { action: "crisis_classified", stage: "crisis_analysis", processing_time_ms: 800, created_at: new Date(Date.now() - 185000).toISOString() },
            { action: "risk_score_calculated", stage: "risk_scoring", processing_time_ms: 100, created_at: new Date(Date.now() - 183000).toISOString() },
            { action: "alert_generated", stage: "alert_generation", processing_time_ms: 50, created_at: new Date(Date.now() - 182000).toISOString() },
          ],
        });
      }
      setLoading(false);
    }
    load();
  }, [alertId]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-96 rounded-2xl bg-slate-200" />
      </div>
    );
  }

  if (!evidence) {
    return <div>Evidence record not found</div>;
  }

  const { alert, article, page, document: doc, translations, entities, audit_trail } = evidence;

  const tabs = [
    { id: "ocr", label: "Original OCR", icon: FileText },
    { id: "translation", label: "Translation", icon: Languages },
    { id: "analysis", label: "AI Analysis", icon: BrainCircuit },
    { id: "audit", label: "Audit Trail", icon: History },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Breadcrumbs & Back button */}
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <Link href="/alerts" className="hover:text-primary-600 flex items-center gap-1 font-medium">
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Alerts
        </Link>
        <span>/</span>
        <span className="text-slate-800 font-semibold truncate max-w-xs">
          Evidence for {alert.brand_name}
        </span>
      </div>

      {/* Header Banner */}
      <div className="glass-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className={`badge badge-${alert.priority}`}>
              {alert.priority?.toUpperCase()}
            </span>
            <span className="text-xs font-bold text-primary-700 bg-primary-50 px-2.5 py-0.5 rounded-full border border-primary-200/60">
              {alert.brand_name}
            </span>
            <span className="text-xs text-slate-400">Traceable Evidence Dossier</span>
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
            {alert.title}
          </h1>
        </div>
        <div className="flex-shrink-0">
          <RiskScore
            score={alert.risk_score}
            size="md"
            showBreakdown={true}
            breakdown={alert.risk_breakdown}
          />
        </div>
      </div>

      {/* Inspection Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: Newspaper Broadsheet Preview */}
        <div className="lg:col-span-5 glass-card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Newspaper className="w-4 h-4 text-slate-500" />
              <p className="text-xs font-bold text-slate-800">Scanned Broadsheet View</p>
            </div>
            <p className="text-[11px] font-mono text-slate-500">
              Page {page?.page_number}
            </p>
          </div>

          <div className="relative bg-slate-100 aspect-[3/4] flex items-center justify-center p-4">
            <div className="absolute inset-4 bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden p-3">
              <div className="w-full h-full relative">
                {/* Simulated newspaper columns */}
                <div className="space-y-2 opacity-30">
                  <div className="h-3 bg-slate-400 rounded w-3/4" />
                  <div className="grid grid-cols-2 gap-2 mt-3">
                    <div className="space-y-1">
                      <div className="h-1.5 bg-slate-300 rounded w-full" />
                      <div className="h-1.5 bg-slate-300 rounded w-5/6" />
                      <div className="h-1.5 bg-slate-300 rounded w-full" />
                    </div>
                    <div className="space-y-1">
                      <div className="h-1.5 bg-slate-300 rounded w-full" />
                      <div className="h-1.5 bg-slate-300 rounded w-4/5" />
                    </div>
                  </div>
                </div>

                {/* Article highlight overlay */}
                {article && (
                  <div
                    className="absolute border-2 border-red-500 bg-red-500/15 rounded-md shadow-xs transition-all"
                    style={{
                      left: `${(article.bbox_x / (page?.width || 2480)) * 100}%`,
                      top: `${(article.bbox_y / (page?.height || 3508)) * 100}%`,
                      width: `${(article.bbox_width / (page?.width || 2480)) * 100}%`,
                      height: `${(article.bbox_height / (page?.height || 3508)) * 100}%`,
                    }}
                  >
                    <div className="absolute -top-6 left-0 bg-red-600 text-white text-[9px] px-2 py-0.5 rounded font-bold tracking-wider uppercase shadow-xs">
                      Extracted Article
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="p-4 space-y-2 text-xs border-t border-slate-100 bg-slate-50/40">
            <div className="flex justify-between text-slate-500">
              <span>OCR Pipeline Engine:</span>
              <span className="font-mono font-semibold text-slate-700">
                {page?.ocr_engine_used}
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Bounding Confidence:</span>
              <span className="font-mono font-bold text-emerald-600">
                {page?.ocr_confidence?.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Resolution:</span>
              <span className="font-mono text-slate-600">
                {page?.width} × {page?.height} px
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT: Multi-tab Evidence Dossier */}
        <div className="lg:col-span-7 space-y-6">
          <div className="glass-card overflow-hidden">
            {/* Tab Navigation */}
            <div className="flex border-b border-slate-100 bg-slate-50/50">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-5 py-3 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                      active
                        ? "border-primary-600 text-primary-700 bg-white shadow-xs"
                        : "border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100/50"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="p-6">
              {/* Tab 1: OCR */}
              {activeTab === "ocr" && (
                <div className="space-y-5">
                  <div>
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Extracted Regional Headline (OCR)
                    </h3>
                    <div className="p-4 bg-amber-50/60 rounded-xl border border-amber-200/80 font-serif text-lg text-slate-900 leading-snug">
                      {article?.headline}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Extracted Body Content (OCR)
                    </h3>
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-sm text-slate-700 leading-relaxed font-sans whitespace-pre-wrap">
                      {article?.body_text || article?.full_text}
                    </div>
                  </div>

                  <div className="flex gap-4 pt-2">
                    <div className="px-3 py-1.5 bg-primary-50 rounded-lg text-xs font-medium">
                      <span className="text-slate-500">Detected Language: </span>
                      <span className="font-bold text-primary-700 font-mono">
                        {article?.detected_language?.toUpperCase()}
                      </span>
                    </div>
                    <div className="px-3 py-1.5 bg-emerald-50 rounded-lg text-xs font-medium">
                      <span className="text-slate-500">OCR Precision: </span>
                      <span className="font-bold text-emerald-700 font-mono">
                        {article?.ocr_confidence?.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Translation */}
              {activeTab === "translation" && (
                <div className="space-y-4">
                  {translations?.map((t: any, i: number) => (
                    <div key={i} className="space-y-3">
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                        English Translation ({t.source_language?.toUpperCase()} → EN)
                      </h3>
                      <div className="p-5 bg-cyan-50/60 rounded-xl border border-cyan-200/80 text-sm text-slate-900 leading-relaxed">
                        {t.translated_text}
                      </div>
                      <div className="px-3 py-1.5 bg-cyan-50 rounded-lg text-xs font-semibold text-cyan-800 w-fit">
                        Model Confidence: {t.confidence}% (NLLB-200)
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 3: AI Analysis */}
              {activeTab === "analysis" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5">
                      Named Entities Recognized (NER)
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {entities?.map((e: any, i: number) => (
                        <span
                          key={i}
                          className={`px-3 py-1 rounded-lg text-xs font-semibold border ${
                            e.entity_type === "REGULATOR"
                              ? "bg-red-50 text-red-700 border-red-200"
                              : e.entity_type === "ORGANIZATION"
                              ? "bg-primary-50 text-primary-700 border-primary-200"
                              : "bg-slate-100 text-slate-700 border-slate-200"
                          }`}
                        >
                          {e.text}{" "}
                          <span className="opacity-70 font-mono text-[10px]">
                            ({e.entity_type})
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-1">
                        Sentiment Classification
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`badge badge-${alert.sentiment}`}>
                          {alert.sentiment?.toUpperCase()}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          {alert.sentiment_confidence}% Conf
                        </span>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-1">
                        Crisis Classification
                      </h4>
                      <span className="text-xs font-bold text-violet-700 bg-violet-50 px-2.5 py-1 rounded-md inline-block mt-1">
                        {alert.crisis_topic?.replace(/_/g, " ").toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Audit Trail */}
              {activeTab === "audit" && (
                <div className="divide-y divide-slate-100">
                  {audit_trail?.map((entry: any, i: number) => (
                    <div key={i} className="py-2.5 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <div>
                          <p className="font-bold text-slate-800 capitalize">
                            {entry.action.replace(/_/g, " ")}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            Stage: {entry.stage}
                          </p>
                        </div>
                      </div>
                      <span className="font-mono text-slate-500">
                        {entry.processing_time_ms}ms
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Evidence Chain Flow */}
          <div className="glass-card p-5">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Verifiable Evidence Chain
            </h3>
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
              <span className="bg-slate-100 px-2.5 py-1 rounded text-slate-700 font-semibold">
                PDF Scan
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="bg-cyan-50 px-2.5 py-1 rounded text-cyan-700 font-semibold">
                Page {page?.page_number}
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="bg-violet-50 px-2.5 py-1 rounded text-violet-700 font-semibold">
                OCR Text
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="bg-primary-50 px-2.5 py-1 rounded text-primary-700 font-semibold">
                NER Match
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span className="bg-red-50 px-2.5 py-1 rounded text-red-700 font-bold border border-red-200">
                Risk Alert
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
