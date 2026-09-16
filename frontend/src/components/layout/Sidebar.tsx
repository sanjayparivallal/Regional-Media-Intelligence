"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  Globe2,
  Tag,
  Flame,
  UploadCloud,
  FileText,
  Cpu,
  CheckSquare,
  Search,
  History,
  Building2,
  Newspaper,
  Sliders,
  Radio,
  Sparkles,
} from "lucide-react";

const navSections = [
  {
    label: "INTELLIGENCE",
    items: [
      { href: "/", icon: BarChart3, label: "Overview" },
      { href: "/alerts", icon: Bell, label: "Alerts" },
      { href: "/coverage", icon: Globe2, label: "Coverage" },
      { href: "/mentions", icon: Tag, label: "Mentions" },
      { href: "/incidents", icon: Flame, label: "Incidents" },
    ],
  },
  {
    label: "OPERATIONS",
    items: [
      { href: "/ingestion", icon: UploadCloud, label: "Ingestion" },
      { href: "/documents", icon: FileText, label: "Documents" },
      { href: "/processing", icon: Cpu, label: "Processing" },
      { href: "/reviews", icon: CheckSquare, label: "Review Queue" },
    ],
  },
  {
    label: "EVIDENCE",
    items: [
      { href: "/evidence", icon: Search, label: "Evidence Explorer" },
      { href: "/audit", icon: History, label: "Audit Trail" },
    ],
  },
  {
    label: "CONFIGURATION",
    items: [
      { href: "/brands", icon: Building2, label: "Brands" },
      { href: "/publications", icon: Newspaper, label: "Publications" },
      { href: "/settings", icon: Sliders, label: "Settings" },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-white border-r border-slate-200/80 flex flex-col shadow-xs flex-shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-600 to-violet-600 flex items-center justify-center shadow-sm text-white ring-2 ring-primary-100">
            <Radio className="w-5 h-5 animate-pulse-soft" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="text-sm font-bold text-slate-900 tracking-tight leading-none">
                Regional Media
              </h1>
            </div>
            <div className="flex items-center gap-1 mt-1">
              <Sparkles className="w-3 h-3 text-primary-500" />
              <p className="text-[10px] font-semibold text-primary-600 tracking-wider uppercase">
                Intelligence Agent
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {navSections.map((section) => (
          <div key={section.label}>
            <p className="px-3.5 mb-2 text-[10px] font-bold text-slate-400 tracking-widest uppercase">
              {section.label}
            </p>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`nav-item group ${isActive ? "active" : ""}`}
                  >
                    <Icon
                      className={`w-4 h-4 transition-colors ${
                        isActive
                          ? "text-primary-600"
                          : "text-slate-400 group-hover:text-slate-700"
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-slate-600 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>AI Online</span>
          </div>
          <span className="text-[10px] bg-primary-100/70 text-primary-700 px-2 py-0.5 rounded-full font-semibold border border-primary-200/50">
            ENTERPRISE
          </span>
        </div>
      </div>
    </aside>
  );
}
