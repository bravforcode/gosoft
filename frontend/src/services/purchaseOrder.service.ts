import { api } from "@/services/api";

export interface PurchaseOrder {
  id: string;
  product_id: string;
  quantity_ordered: number;
  total_amount: number;
  status: string;
  expected_delivery?: string | null;
  notes?: string | null;
}

export interface PaginatedPurchaseOrders {
  items: PurchaseOrder[];
  pagination: {
    total: number;
    skip: number;
    limit: number;
  };
}

export const purchaseOrderService = {
  getAll: async (params?: Record<string, unknown>): Promise<PaginatedPurchaseOrders> => {
    const response = await api.get<PaginatedPurchaseOrders>("/api/v1/purchase-orders", { params });
    return response.data;
  },
  getById: async (poId: string): Promise<PurchaseOrder> => {
    const response = await api.get<PurchaseOrder>(`/api/v1/purchase-orders/${poId}`);
    return response.data;
  },
  approve: async (poId: string): Promise<PurchaseOrder> => {
    const response = await api.post<PurchaseOrder>(`/api/v1/purchase-orders/${poId}/approve`);
    return response.data;
  },
  reject: async (poId: string): Promise<PurchaseOrder> => {
    const response = await api.post<PurchaseOrder>(`/api/v1/purchase-orders/${poId}/reject`);
    return response.data;
  },
  create: async (payload: Record<string, unknown>): Promise<PurchaseOrder> => {
    const response = await api.post<PurchaseOrder>("/api/v1/purchase-orders", payload);
    return response.data;
  }
};
