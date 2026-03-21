import { api } from "@/services/api";
import type { AlertSummary } from "@/types/inventory.types";

export interface PaginatedAlerts {
  items: AlertSummary[];
  pagination: {
    total: number;
    skip: number;
    limit: number;
  };
}

export const alertsService = {
  getAll: async (params?: Record<string, unknown>): Promise<PaginatedAlerts> => {
    const response = await api.get<PaginatedAlerts>("/api/v1/alerts", { params });
    return response.data;
  },
  getById: async (alertId: string): Promise<AlertSummary> => {
    const response = await api.get<AlertSummary>(`/api/v1/alerts/${alertId}`);
    return response.data;
  },
  acknowledge: async (alertId: string): Promise<AlertSummary> => {
    const response = await api.post<AlertSummary>(`/api/v1/alerts/${alertId}/acknowledge`);
    return response.data;
  },
  resolve: async (alertId: string): Promise<AlertSummary> => {
    const response = await api.post<AlertSummary>(`/api/v1/alerts/${alertId}/resolve`);
    return response.data;
  },
  bulkAcknowledge: async (alertIds: string[]) => {
    const response = await api.post("/api/v1/alerts/bulk-acknowledge", alertIds);
    return response.data;
  }
};
