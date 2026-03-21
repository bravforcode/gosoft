import { useMemo } from "react";

import { CameraGrid } from "@/components/cameras/CameraGrid";
import { CameraStats } from "@/components/cameras/CameraStats";
import { Card, SectionTitle } from "@/components/ui";
import { useCameras } from "@/hooks/useCameras";
import { useAppStore } from "@/store/useAppStore";


export default function CamerasPage() {
  const { data: cameras = [] } = useCameras();
  const selectedCameraId = useAppStore((state) => state.selectedCameraId);
  const setSelectedCamera = useAppStore((state) => state.setSelectedCamera);
  const activeCamera = useMemo(() => cameras.find((camera) => camera.id === selectedCameraId) ?? cameras[0], [cameras, selectedCameraId]);

  return (
    <div className="space-y-6">
      <SectionTitle title="Camera Operations" eyebrow="Inference live" />
      <CameraStats cameras={cameras} />
      <CameraGrid cameras={cameras} selectedCameraId={selectedCameraId} onSelect={setSelectedCamera} />
      <Card>
        <SectionTitle title="Detection Log" eyebrow={activeCamera?.name ?? "No camera"} />
        <div className="space-y-3 text-sm text-slate-300">
          {(activeCamera ? [activeCamera] : []).map((camera) => (
            <div key={camera.id} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4">
              <span>{camera.name}</span>
              <span className="font-mono text-xs uppercase tracking-[0.18em] text-slate-500">
                {camera.detections_last_minute} det · {camera.avg_confidence.toFixed(2)} conf
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
