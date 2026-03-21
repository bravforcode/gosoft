import { api } from "@/services/api";
import type { CameraDetail, CameraStatus } from "@/types/camera.types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const cameraService = {
  getAll: async (): Promise<CameraStatus[]> => {
    const response = await api.get<CameraStatus[]>("/api/v1/cameras");
    return response.data;
  },
  getById: async (cameraId: string): Promise<CameraDetail> => {
    const response = await api.get<CameraDetail>(`/api/v1/cameras/${cameraId}`);
    return response.data;
  },
  snapshot: async (cameraId: string) => {
    const response = await api.post(`/api/v1/cameras/${cameraId}/snapshot`);
    return response.data;
  },
  testConnection: async (cameraId: string) => {
    const response = await api.post(`/api/v1/cameras/${cameraId}/test`);
    return response.data;
  },
  getMjpegUrl: (cameraId: string, overlay = true): string => `${API_URL}/stream/${cameraId}${overlay ? "" : "/raw"}`
};
