import type { CameraStatus } from "@/types/camera.types";
import { CameraFeed } from "@/components/cameras/CameraFeed";
import { cn } from "@/utils/cn";


export function CameraGrid({
  cameras,
  selectedCameraId,
  onSelect
}: {
  cameras: CameraStatus[];
  selectedCameraId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {cameras.map((camera, index) => (
        <button
          key={camera.id}
          onClick={() => onSelect(camera.id)}
          className={cn("overflow-hidden rounded-[1.8rem] border transition", selectedCameraId === camera.id ? "border-brand-blue shadow-[0_0_0_1px_rgba(0,87,255,0.55)]" : "border-white/10")}
        >
          <CameraFeed cameraId={camera.id} size={index === 0 ? "lg" : "sm"} />
        </button>
      ))}
    </div>
  );
}
