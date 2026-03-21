import { api } from "@/services/api";

export const analyticsService = {
  getSummary: async () => (await api.get("/api/v1/analytics/summary")).data,
  getEvents: async () => (await api.get("/api/v1/analytics/events")).data,
  getAccuracyTrend: async () => (await api.get("/api/v1/analytics/accuracy")).data,
  getHeatmap: async () => (await api.get("/api/v1/analytics/heatmap")).data,
  getAlertTrend: async () => (await api.get("/api/v1/analytics/alerts")).data,
  getStockouts: async () => (await api.get("/api/v1/analytics/stockouts")).data,
  getVendors: async () => (await api.get("/api/v1/analytics/vendors")).data
};
