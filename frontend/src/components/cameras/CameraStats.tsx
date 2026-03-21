import type { CameraStatus } from "@/types/camera.types";
import { Card } from "@/components/ui";


export function CameraStats({ cameras }: { cameras: CameraStatus[] }) {
  const avgConfidence = cameras.reduce((sum, camera) => sum + camera.avg_confidence, 0) / Math.max(1, cameras.length);
  const detPerMinute = cameras.reduce((sum, camera) => sum + camera.detections_last_minute, 0);

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Latency</div>
        <div className="mt-2 font-display text-4xl text-white">23ms</div>
      </Card>
      <Card>
        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Detections/min</div>
        <div className="mt-2 font-display text-4xl text-white">{detPerMinute}</div>
      </Card>
      <Card>
        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Avg confidence</div>
        <div className="mt-2 font-display text-4xl text-white">{avgConfidence.toFixed(2)}</div>
      </Card>
      <Card>
        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Online cameras</div>
        <div className="mt-2 font-display text-4xl text-white">{cameras.filter((camera) => camera.status === "online").length}</div>
      </Card>
    </div>
  );
}
