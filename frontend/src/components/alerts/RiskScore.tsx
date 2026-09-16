"use client";

interface RiskScoreProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showBreakdown?: boolean;
  breakdown?: {
    sentiment: { score: number; max: number };
    brand: { score: number; max: number };
    topic: { score: number; max: number };
    reach: { score: number; max: number };
    confidence: { score: number; max: number };
  };
}

export default function RiskScore({ score, size = "md", showBreakdown = false, breakdown }: RiskScoreProps) {
  const priority = score >= 81 ? "critical" : score >= 61 ? "high" : score >= 31 ? "medium" : "low";

  const colors = {
    critical: { stroke: "#EF4444", bg: "bg-red-50", text: "text-red-700", label: "CRITICAL" },
    high: { stroke: "#F97316", bg: "bg-coral-50", text: "text-coral-700", label: "HIGH" },
    medium: { stroke: "#F59E0B", bg: "bg-amber-50", text: "text-amber-700", label: "MEDIUM" },
    low: { stroke: "#10B981", bg: "bg-emerald-50", text: "text-emerald-700", label: "LOW" },
  };

  const config = colors[priority];
  const sizes = {
    sm: { container: "w-14 h-14", radius: 22, strokeWidth: 3, fontSize: "text-sm", labelSize: "text-[8px]" },
    md: { container: "w-20 h-20", radius: 32, strokeWidth: 4, fontSize: "text-xl", labelSize: "text-[9px]" },
    lg: { container: "w-28 h-28", radius: 46, strokeWidth: 5, fontSize: "text-3xl", labelSize: "text-xs" },
  };

  const s = sizes[size];
  const circumference = 2 * Math.PI * s.radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`${s.container} relative flex items-center justify-center`}>
        <svg className="score-circle absolute inset-0 w-full h-full" viewBox={`0 0 ${(s.radius + s.strokeWidth) * 2} ${(s.radius + s.strokeWidth) * 2}`}>
          <circle
            cx={s.radius + s.strokeWidth}
            cy={s.radius + s.strokeWidth}
            r={s.radius}
            fill="none"
            stroke="#E2E8F0"
            strokeWidth={s.strokeWidth}
          />
          <circle
            cx={s.radius + s.strokeWidth}
            cy={s.radius + s.strokeWidth}
            r={s.radius}
            fill="none"
            stroke={config.stroke}
            strokeWidth={s.strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <span className={`${s.fontSize} font-bold ${config.text} relative z-10`}>
          {Math.round(score)}
        </span>
      </div>
      <span className={`${s.labelSize} font-bold ${config.text} tracking-wider`}>
        {config.label}
      </span>

      {showBreakdown && breakdown && (
        <div className="mt-3 space-y-1.5 w-full max-w-xs">
          {[
            { label: "Sentiment", ...breakdown.sentiment, color: "bg-red-400" },
            { label: "Brand", ...breakdown.brand, color: "bg-primary-400" },
            { label: "Topic", ...breakdown.topic, color: "bg-violet-400" },
            { label: "Reach", ...breakdown.reach, color: "bg-cyan-400" },
            { label: "Confidence", ...breakdown.confidence, color: "bg-emerald-400" },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <span className="w-20 text-slate-500">{item.label}</span>
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${item.color} transition-all duration-700`}
                  style={{ width: `${(item.score / item.max) * 100}%` }}
                />
              </div>
              <span className="w-12 text-right font-mono text-slate-600">
                {item.score}/{item.max}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
