import { api } from "@/services/api";
import type { PaginatedProducts, ProductDetail, ProductSummary, StockHistoryPoint } from "@/types/inventory.types";

export const inventoryService = {
  getAll: async (params?: Record<string, unknown>): Promise<PaginatedProducts> => {
    const response = await api.get<PaginatedProducts>("/api/v1/inventory", { params });
    return response.data;
  },
  getById: async (sku: string): Promise<ProductDetail> => {
    const response = await api.get<ProductDetail>(`/api/v1/inventory/${sku}`);
    return response.data;
  },
  update: async (sku: string, payload: Partial<ProductSummary>): Promise<ProductDetail> => {
    const response = await api.put<ProductDetail>(`/api/v1/inventory/${sku}`, payload);
    return response.data;
  },
  exportCSV: async (): Promise<Blob> => {
    const response = await api.get("/api/v1/inventory/export", { responseType: "blob" });
    return response.data as Blob;
  },
  importCSV: async (file: File): Promise<{ imported: number; skipped: number; errors: string[] }> => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post("/api/v1/inventory/import", formData);
    return response.data;
  },
  getCritical: async (): Promise<ProductSummary[]> => {
    const response = await api.get<ProductSummary[]>("/api/v1/inventory/critical");
    return response.data;
  },
  getHistory: async (sku: string): Promise<StockHistoryPoint[]> => {
    const response = await api.get<StockHistoryPoint[]>(`/api/v1/inventory/${sku}/history`);
    return response.data;
  }
};
