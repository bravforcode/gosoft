import type { DetectionEvent } from "@/types/inventory.types";

export interface CameraStatus {
  id: string;
  name: string;
  zone: string;
  stream_url: string;
  status: "online" | "offline" | "error";
  resolution_width: number;
  resolution_height: number;
  fps_processing: number;
  is_active: boolean;
  last_frame_at?: string | null;
  detections_last_minute: number;
  avg_confidence: number;
}

export interface CameraDetail extends CameraStatus {
  current_detections: DetectionEvent[];
  stats: Record<string, unknown>;
}
