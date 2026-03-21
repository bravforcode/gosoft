import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, SectionTitle } from "@/components/ui";
import { analyticsService } from "@/services/analytics.service";


export default function AnalyticsPage() {
  const summary = useQuery({ queryKey: ["analytics-summary"], queryFn: analyticsService.getSummary });
  const events = useQuery({ queryKey: ["analytics-events"], queryFn: analyticsService.getEvents });
  const accuracy = useQuery({ queryKey: ["analytics-accuracy"], queryFn: analyticsService.getAccuracyTrend });
  const heatmap = useQuery({ queryKey: ["analytics-heatmap"], queryFn: analyticsService.getHeatmap });

  return (
    <div className="space-y-6">
      <SectionTitle title="Analytics" eyebrow="Retail intelligence" />
      <div className="grid gap-4 md:grid-cols-4">
        <Card><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Prevented stockouts</div><div className="mt-2 font-display text-4xl">{summary.data?.auto_pos_generated ?? 0}</div></Card>
        <Card><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Revenue saved</div><div className="mt-2 font-display text-4xl">฿{Math.round(summary.data?.revenue_saved_estimate ?? 0)}</div></Card>
        <Card><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Labor saved</div><div className="mt-2 font-display text-4xl">42h</div></Card>
        <Card><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Auto POs</div><div className="mt-2 font-display text-4xl">{summary.data?.auto_pos_generated ?? 0}</div></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="h-[320px]">
          <SectionTitle title="Events Timeline" />
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={events.data?.items ?? []}>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="bucket" stroke="#8f9ab3" />
              <YAxis stroke="#8f9ab3" />
              <Tooltip />
              <Bar dataKey="total" fill="#0057ff" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="h-[320px]">
          <SectionTitle title="Accuracy Trend" />
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={accuracy.data?.items ?? []}>
              <defs>
                <linearGradient id="accuracyFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00c2ff" stopOpacity={0.65} />
                  <stop offset="100%" stopColor="#0057ff" stopOpacity={0.08} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="date" stroke="#8f9ab3" />
              <YAxis stroke="#8f9ab3" />
              <Tooltip />
              <Area dataKey="accuracy" stroke="#00c2ff" fill="url(#accuracyFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
        <Card className="h-[320px]">
          <SectionTitle title="Zone Heatmap" />
          <div className="grid h-full grid-cols-5 gap-2">
            {heatmap.data?.items.map((cell: { zone: string; intensity: number; count: number }) => (
              <div key={cell.zone} className="flex flex-col items-center justify-center rounded-2xl border border-white/10" style={{ background: `rgba(0,194,255,${0.08 + cell.intensity * 0.5})` }}>
                <div className="font-mono text-xs uppercase tracking-[0.18em] text-slate-400">{cell.zone}</div>
                <div className="font-display text-3xl text-white">{cell.count}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="h-[320px]">
          <SectionTitle title="Stock Distribution" />
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={[
                  { name: "ok", value: 68, color: "#22c55e" },
                  { name: "low", value: 18, color: "#f59e0b" },
                  { name: "critical", value: 9, color: "#ef4444" },
                  { name: "empty", value: 5, color: "#a855f7" }
                ]}
                innerRadius={70}
                outerRadius={110}
                dataKey="value"
              >
                {[
                  { color: "#22c55e" },
                  { color: "#f59e0b" },
                  { color: "#ef4444" },
                  { color: "#a855f7" }
                ].map((entry) => (
                  <Cell key={entry.color} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
