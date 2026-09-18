"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  Building2,
  Plus,
  Tag,
  AlertTriangle,
  TrendingUp,
  X,
  CheckCircle2,
  Search,
  Trash2,
  PowerOff,
  Power,
  Loader2,
} from "lucide-react";

export default function BrandsPage() {
  const [brands, setBrands] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newBrand, setNewBrand] = useState({
    name: "",
    display_name: "",
    industry: "",
    keywords: "",
  });

  useEffect(() => {
    async function load() {
      try {
        setBrands(await api.getBrands());
      } catch {
        setBrands([
          {
            id: "1",
            name: "PayU",
            display_name: "PayU India",
            industry: "Fintech & Payments",
            active: true,
            total_mentions: 5,
            critical_alerts: 2,
            aliases: [{ alias: "Pay U" }, { alias: "PayU Finance" }],
            keywords: ["digital payment", "UPI", "RBI regulation", "KYC"],
          },
          {
            id: "2",
            name: "Paytm",
            display_name: "Paytm Payments Bank",
            industry: "Fintech & Banking",
            active: true,
            total_mentions: 3,
            critical_alerts: 0,
            aliases: [{ alias: "One97 Communications" }],
            keywords: ["wallet", "UPI", "soundbox", "POS"],
          },
          {
            id: "3",
            name: "PhonePe",
            display_name: "PhonePe",
            industry: "Digital Payments",
            active: true,
            total_mentions: 2,
            critical_alerts: 0,
            aliases: [{ alias: "PhonePe India" }],
            keywords: ["UPI Lite", "merchant app", "insurance"],
          },
        ]);
      }
      setLoading(false);
    }
    load();
  }, []);

  const handleCreate = async () => {
    try {
      const data = {
        ...newBrand,
        keywords: newBrand.keywords.split(",").map((k) => k.trim()).filter(Boolean),
      };
      const created = await api.createBrand(data);
      setBrands((prev) => [...prev, created]);
      setShowCreate(false);
      setNewBrand({ name: "", display_name: "", industry: "", keywords: "" });
    } catch (e) {
      console.error(e);
      // Fallback local create for demo
      setBrands((prev) => [
        ...prev,
        {
          id: String(Date.now()),
          name: newBrand.name,
          display_name: newBrand.display_name || newBrand.name,
          industry: newBrand.industry || "General",
          active: true,
          total_mentions: 0,
          critical_alerts: 0,
          aliases: [],
          keywords: newBrand.keywords.split(",").map((k) => k.trim()).filter(Boolean),
        },
      ]);
      setShowCreate(false);
      setNewBrand({ name: "", display_name: "", industry: "", keywords: "" });
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this brand profile and all associated data? This cannot be undone.")) return;
    try {
      await api.deleteBrand(id);
    } catch (e) {
      console.error(e);
    } finally {
      setBrands((prev) => prev.filter((b) => b.id !== id));
    }
  };

  const handleToggleActive = async (id: string, currentActive: boolean) => {
    // Optimistic update
    setBrands((prev) =>
      prev.map((b) => (b.id === id ? { ...b, active: !currentActive } : b))
    );
    try {
      await api.updateBrand(id, { active: !currentActive });
    } catch (e) {
      console.error(e);
      // Revert on failure
      setBrands((prev) =>
        prev.map((b) => (b.id === id ? { ...b, active: currentActive } : b))
      );
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600">
              <Building2 className="w-4 h-4" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Brand Profiles & Gazetteers
            </h1>
          </div>
          <p className="text-sm text-slate-500">
            Monitored corporate entities, regional aliases, and keyword matching dictionaries
          </p>
        </div>

        <button
          onClick={() => setShowCreate(!showCreate)}
          className="btn-primary self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Brand Profile</span>
        </button>
      </div>

      {/* Create Modal / Expansion Card */}
      {showCreate && (
        <div className="glass-card p-6 border-2 border-primary-200/80 animate-slide-up shadow-glass-lg">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900">
              Configure New Brand Profile
            </h3>
            <button
              onClick={() => setShowCreate(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">
                Internal Name
              </label>
              <input
                placeholder="e.g. PayU"
                value={newBrand.name}
                onChange={(e) =>
                  setNewBrand((p) => ({ ...p, name: e.target.value }))
                }
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">
                Display Name
              </label>
              <input
                placeholder="e.g. PayU Payments India"
                value={newBrand.display_name}
                onChange={(e) =>
                  setNewBrand((p) => ({ ...p, display_name: e.target.value }))
                }
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">
                Industry Vertical
              </label>
              <input
                placeholder="e.g. Fintech, Banking, Retail"
                value={newBrand.industry}
                onChange={(e) =>
                  setNewBrand((p) => ({ ...p, industry: e.target.value }))
                }
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">
                Keywords (Comma Separated)
              </label>
              <input
                placeholder="e.g. payments, UPI, wallet, KYC"
                value={newBrand.keywords}
                onChange={(e) =>
                  setNewBrand((p) => ({ ...p, keywords: e.target.value }))
                }
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-5">
            <button onClick={handleCreate} className="btn-primary text-xs">
              Save Brand Profile
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Brands Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {brands.map((brand) => (
          <div
            key={brand.id}
            className="glass-card p-6 hover:shadow-glass-lg hover:-translate-y-0.5 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-primary-50 text-primary-700 flex items-center justify-center font-bold text-sm border border-primary-100/80">
                    {brand.name.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 leading-tight">
                      {brand.display_name || brand.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">{brand.industry}</p>
                  </div>
                </div>
                <span
                  className={`badge ${
                    brand.active
                      ? "badge-low"
                      : "badge-neutral"
                  }`}
                >
                  {brand.active ? "Active" : "Paused"}
                </span>
              </div>

              {/* Stats Bar */}
              <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50/80 border border-slate-100 mb-4 text-center">
                <div>
                  <p className="text-xs font-semibold text-slate-400">Total Mentions</p>
                  <p className="text-xl font-extrabold text-primary-700 mt-0.5">
                    {brand.total_mentions || 0}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-400">Critical Alerts</p>
                  <p
                    className={`text-xl font-extrabold mt-0.5 ${
                      (brand.critical_alerts || 0) > 0
                        ? "text-red-600"
                        : "text-slate-700"
                    }`}
                  >
                    {brand.critical_alerts || 0}
                  </p>
                </div>
              </div>

              {/* Aliases */}
              {brand.aliases?.length > 0 && (
                <div className="mb-3">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Monitored Aliases
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {brand.aliases.map((a: any, i: number) => (
                      <span
                        key={i}
                        className="text-xs bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-md font-medium border border-slate-200/60"
                      >
                        {a.alias}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Keywords */}
              {brand.keywords?.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                    Trigger Keywords
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {brand.keywords.map((kw: string, i: number) => (
                      <span
                        key={i}
                        className="text-[11px] bg-primary-50 text-primary-700 px-2.5 py-0.5 rounded-md font-medium border border-primary-200/60"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Card Footer: Actions */}
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
              <button
                onClick={() => handleToggleActive(brand.id, brand.active)}
                className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all border cursor-pointer ${
                  brand.active
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-red-50 hover:text-red-700 hover:border-red-200"
                    : "bg-slate-100 text-slate-600 border-slate-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200"
                }`}
                title={brand.active ? "Pause monitoring" : "Resume monitoring"}
              >
                {brand.active ? (
                  <><PowerOff className="w-3.5 h-3.5" /><span>Pause</span></>
                ) : (
                  <><Power className="w-3.5 h-3.5" /><span>Resume</span></>
                )}
              </button>
              <button
                onClick={() => handleDelete(brand.id)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                title="Delete brand profile"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
