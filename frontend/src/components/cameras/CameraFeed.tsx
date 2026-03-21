import { useEffect, useMemo, useRef, useState } from "react";
import { CameraOff, Download, RefreshCw } from "lucide-react";

import { cameraService } from "@/services/camera.service";
import type { SIVEvent } from "@/types/events.types";
import { Badge, Button } from "@/components/ui";
import { DetectionOverlay } from "@/components/cameras/DetectionOverlay";
import { cn } from "@/utils/cn";


interface CameraFeedProps {
  cameraId: string;
  showOverlay?: boolean;
  size?: "sm" | "md" | "lg" | "fullscreen";
  onSnapshot?: (dataUrl: string) => void;
}

const sizeMap: Record<NonNullable<CameraFeedProps["size"]>, string> = {
  sm: "aspect-video",
  md: "aspect-video",
  lg: "aspect-[16/9]",
  fullscreen: "aspect-[16/9] min-h-[72vh]"
};

export function CameraFeed({ cameraId, showOverlay = true, size = "md", onSnapshot }: CameraFeedProps) {
  const imgRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [offline, setOffline] = useState(false);
  const [lastSeen, setLastSeen] = useState<string | null>(null);
  const [latestEvent, setLatestEvent] = useState<SIVEvent | null>(null);

  const mjpegUrl = useMemo(() => cameraService.getMjpegUrl(cameraId, true), [cameraId]);

  useEffect(() => {
    const listener = (rawEvent: Event) => {
      const event = (rawEvent as CustomEvent<SIVEvent>).detail;
      if (event.camera_id === cameraId) {
        setLatestEvent(event);
        setLastSeen(event.timestamp);
      }
    };
    window.addEventListener("siv:event", listener as EventListener);
    return () => window.removeEventListener("siv:event", listener as EventListener);
  }, [cameraId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const image = imgRef.current;
    if (!canvas || !image || !latestEvent || latestEvent.type !== "stock_update") {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    canvas.width = image.clientWidth;
    canvas.height = image.clientHeight;
    context.clearRect(0, 0, canvas.width, canvas.height);
    const zones = latestEvent.data.zones as Record<string, number> | undefined;
    if (!zones) {
      return;
    }
    const keys = Object.keys(zones);
    keys.forEach((zoneId, index) => {
      const col = index % 5;
      const row = Math.floor(index / 5);
      const width = canvas.width / 5;
      const height = canvas.height / 3;
      const fullness = zones[zoneId] ?? 0;
      context.strokeStyle = fullness < 0.25 ? "#ef4444" : fullness < 0.5 ? "#f59e0b" : "#00c2ff";
      context.fillStyle = fullness < 0.25 ? "rgba(239,68,68,0.18)" : fullness < 0.5 ? "rgba(245,158,11,0.18)" : "rgba(0,194,255,0.12)";
      context.fillRect(col * width, row * height, width, height);
      context.strokeRect(col * width + 4, row * height + 4, width - 8, height - 8);
      context.fillStyle = "#ffffff";
      context.font = "12px IBM Plex Mono";
      context.fillText(`${zoneId} ${Math.round(fullness * 100)}%`, col * width + 10, row * height + 20);
    });
  }, [latestEvent]);

  const handleSnapshot = async () => {
    const image = imgRef.current;
    if (!image) {
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth || image.width;
    canvas.height = image.naturalHeight || image.height;
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    onSnapshot?.(dataUrl);
    await cameraService.snapshot(cameraId);
  };

  return (
    <div className={cn("glass-panel relative overflow-hidden rounded-[1.8rem] border border-white/10", sizeMap[size])}>
      {!offline ? (
        <>
          <img
            ref={imgRef}
            src={mjpegUrl}
            crossOrigin="anonymous"
            className="h-full w-full object-cover"
            onError={() => setOffline(true)}
            onLoad={() => setOffline(false)}
            alt={cameraId}
          />
          {showOverlay ? (
            <>
              <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />
              <DetectionOverlay critical={latestEvent?.severity === "critical"} />
            </>
          ) : null}
          <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4">
            <Badge className="bg-black/40 text-white">{cameraId}</Badge>
            <Badge className="border-red-500/30 bg-red-500/10 text-red-300">REC</Badge>
          </div>
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/80 to-transparent p-4">
            <div className="font-mono text-xs uppercase tracking-[0.18em] text-slate-300">YOLOv8n · 23ms · 30fps</div>
            <div className="flex items-center gap-2">
              <Button className="bg-white/10 px-3 text-xs hover:bg-white/15" onClick={handleSnapshot}>
                <Download className="mr-2 h-3.5 w-3.5" />
                Snapshot
              </Button>
            </div>
          </div>
        </>
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-4 bg-[radial-gradient(circle_at_top,rgba(239,68,68,0.2),transparent_35%),#070b12] text-center">
          <CameraOff className="h-12 w-12 text-slate-400" />
          <div>
            <div className="font-display text-3xl uppercase tracking-[0.12em] text-white">Camera Offline</div>
            <div className="mt-2 text-sm text-slate-400">Last seen {lastSeen ?? "unknown"}</div>
          </div>
          <Button className="bg-white/10 hover:bg-white/15" onClick={() => setOffline(false)}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry Connection
          </Button>
        </div>
      )}
    </div>
  );
}
