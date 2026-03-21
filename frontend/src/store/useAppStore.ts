import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ProductSummary } from "@/types/inventory.types";
import type { SIVEvent, User } from "@/types/events.types";

interface AppState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  setAuth: (user: User, token: string, refreshToken: string) => void;
  clearAuth: () => void;
  wsConnected: boolean;
  wsStatus: "connecting" | "connected" | "disconnected" | "error";
  setWsStatus: (status: AppState["wsStatus"]) => void;
  frameCount: number;
  eventCount: number;
  activeAlertCount: number;
  incrementFrameCount: () => void;
  addEvent: (event: SIVEvent) => void;
  selectedCameraId: string | null;
  setSelectedCamera: (id: string | null) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  demoMode: boolean;
  inventorySnapshot: Record<string, ProductSummary>;
  updateInventoryItem: (sku: string, update: Partial<ProductSummary>) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      setAuth: (user, token, refreshToken) => set({ user, token, refreshToken }),
      clearAuth: () => set({ user: null, token: null, refreshToken: null, wsConnected: false, wsStatus: "disconnected" }),
      wsConnected: false,
      wsStatus: "disconnected",
      setWsStatus: (status) => set({ wsStatus: status, wsConnected: status === "connected" }),
      frameCount: 0,
      eventCount: 0,
      activeAlertCount: 0,
      incrementFrameCount: () => set((state) => ({ frameCount: state.frameCount + 1 })),
      addEvent: (event) =>
        set((state) => ({
          eventCount: state.eventCount + 1,
          activeAlertCount:
            event.type === "alert_created"
              ? state.activeAlertCount + 1
              : event.type === "alert_resolved"
                ? Math.max(0, state.activeAlertCount - 1)
                : state.activeAlertCount
        })),
      selectedCameraId: null,
      setSelectedCamera: (id) => set({ selectedCameraId: id }),
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      demoMode: true,
      inventorySnapshot: {},
      updateInventoryItem: (sku, update) =>
        set((state) => ({
          inventorySnapshot: {
            ...state.inventorySnapshot,
            [sku]: {
              ...state.inventorySnapshot[sku],
              ...update
            } as ProductSummary
          }
        }))
    }),
    {
      name: "siv-app-store",
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        demoMode: state.demoMode
      })
    }
  )
);
