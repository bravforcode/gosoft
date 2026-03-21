import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { CameraFeed } from "@/components/cameras/CameraFeed";
import { Badge, Button, Card, Progress, SectionTitle } from "@/components/ui";
import { analyticsService } from "@/services/analytics.service";
import { inventoryService } from "@/services/inventory.service";
import { useAppStore } from "@/store/useAppStore";


export default function DashboardPage() {
  const { eventCount, activeAlertCount } = useAppStore();
  const summaryQuery = useQuery({ queryKey: ["analytics-summary"], queryFn: analyticsService.getSummary });
  const criticalQuery = useQuery({ queryKey: ["critical-products"], queryFn: inventoryService.getCritical });

  const kpis = useMemo(
    () => [
      { label: "SKUs", value: summaryQuery.data?.total_skus ?? 0, accent: "text-brand-cyan" },
      { label: "Accuracy", value: `${summaryQuery.data?.avg_accuracy ?? 0}%`, accent: "text-emerald-300" },
      { label: "Active Alerts", value: activeAlertCount, accent: "text-amber-300" },
      { label: "Events Today", value: summaryQuery.data?.events_today ?? eventCount, accent: "text-white" }
    ],
    [activeAlertCount, eventCount, summaryQuery.data]
  );

  return (
    <div className="space-y-6">
      <SectionTitle title="Operations Dashboard" eyebrow="Live overview" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((item) => (
          <Card key={item.label} className="animate-fade-in-up">
            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{item.label}</div>
            <div className={`mt-4 font-display text-5xl ${item.accent}`}>{item.value}</div>
          </Card>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <CameraFeed cameraId="CAM-01" size="lg" />
        <Card>
          <SectionTitle title="Event Flow" eyebrow="Realtime bus" />
          <div className="space-y-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Event count</div>
              <div className="mt-2 font-display text-5xl">{eventCount}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-300">Alert pressure</span>
                <Badge className="text-amber-300">{activeAlertCount}</Badge>
              </div>
              <div className="mt-4"><Progress value={Math.min(100, activeAlertCount * 12)} /></div>
            </div>
          </div>
        </Card>
      </div>
      <Card>
        <SectionTitle title="Critical SKUs" eyebrow="Needs action" action={<Button>Create PO</Button>} />
        <div className="space-y-4">
          {criticalQuery.data?.slice(0, 5).map((product) => {
            const pct = (product.current_stock / product.max_capacity) * 100;
            return (
              <div key={product.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-medium text-white">{product.name_en}</div>
                    <div className="font-mono text-xs uppercase tracking-[0.18em] text-slate-500">{product.sku} · {product.zone_id}</div>
                  </div>
                  <Badge className="text-red-300">{Math.round(pct)}%</Badge>
                </div>
                <div className="mt-4"><Progress value={pct} /></div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
