"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  Newspaper,
  MapPin,
  Users,
  Languages,
  BarChart3,
  CheckCircle2,
} from "lucide-react";

export default function PublicationsPage() {
  const [pubs, setPubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setPubs(await api.getPublications());
      } catch {
        setPubs([
          {
            id: "1",
            name: "Dainik Jagran",
            language: "hi",
            region: "North India",
            state: "Uttar Pradesh & Delhi NCR",
            reach_tier: 1,
            estimated_circulation: 4000000,
          },
          {
            id: "2",
            name: "Dinamalar",
            language: "ta",
            region: "South India",
            state: "Tamil Nadu",
            reach_tier: 1,
            estimated_circulation: 1500000,
          },
          {
            id: "3",
            name: "Amar Ujala",
            language: "hi",
            region: "North India",
            state: "Uttar Pradesh & Uttarakhand",
            reach_tier: 1,
            estimated_circulation: 3000000,
          },
          {
            id: "4",
            name: "Dainik Bhaskar",
            language: "hi",
            region: "Central & Western India",
            state: "Madhya Pradesh & Rajasthan",
            reach_tier: 1,
            estimated_circulation: 4500000,
          },
          {
            id: "5",
            name: "Eenadu",
            language: "te",
            region: "South India",
            state: "Andhra Pradesh & Telangana",
            reach_tier: 1,
            estimated_circulation: 1800000,
          },
          {
            id: "6",
            name: "Lokmat",
            language: "mr",
            region: "Western India",
            state: "Maharashtra",
            reach_tier: 1,
            estimated_circulation: 2200000,
          },
        ]);
      }
      setLoading(false);
    }
    load();
  }, []);

  const totalCirculation = pubs.reduce(
    (acc, p) => acc + (p.estimated_circulation || 0),
    0
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
            <Newspaper className="w-4 h-4" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Monitored Regional Publications
          </h1>
        </div>
        <p className="text-sm text-slate-500">
          Indian regional newspaper broadsheets configured for daily ingestion and AI layout OCR
        </p>
      </div>

      {/* KPI Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="kpi-card primary">
          <p className="text-xs font-semibold text-slate-500 uppercase">Publications</p>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">{pubs.length}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Active monitoring</p>
        </div>
        <div className="kpi-card cyan">
          <p className="text-xs font-semibold text-slate-500 uppercase">Languages</p>
          <p className="text-2xl font-extrabold text-cyan-600 mt-1">
            {new Set(pubs.map((p) => p.language)).size}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Hindi, Tamil, Telugu, Marathi</p>
        </div>
        <div className="kpi-card emerald">
          <p className="text-xs font-semibold text-slate-500 uppercase">Total Circulation</p>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">
            {(totalCirculation / 1000000).toFixed(1)}M
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">Daily print readers</p>
        </div>
        <div className="kpi-card violet">
          <p className="text-xs font-semibold text-slate-500 uppercase">Tier 1 Coverage</p>
          <p className="text-2xl font-extrabold text-violet-600 mt-1">100%</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Regional state capitals</p>
        </div>
      </div>

      {/* Publications Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {pubs.map((pub) => (
          <div
            key={pub.id}
            className="glass-card p-6 hover:shadow-glass-lg hover:-translate-y-0.5 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-700">
                    <Newspaper className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 leading-tight">
                      {pub.display_name || pub.name}
                    </h3>
                    <span className="text-[11px] font-semibold text-slate-400">
                      Tier {pub.reach_tier} Broadsheet
                    </span>
                  </div>
                </div>
                <span className="badge bg-slate-100 text-slate-700 font-mono text-[11px] uppercase">
                  {pub.language}
                </span>
              </div>

              <div className="space-y-2 mt-4 pt-4 border-t border-slate-100 text-xs text-slate-600">
                <div className="flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                  <span className="truncate">
                    {pub.region} • {pub.state}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Users className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                  <span>
                    {pub.estimated_circulation?.toLocaleString()} daily circulation
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Active Feeder
              </span>
              <span className="font-mono text-slate-400">Daily Ingest</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
