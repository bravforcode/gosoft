import { createElement, type PropsWithChildren } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";

import { useWebSocket } from "@/hooks/useWebSocket";
import { useAppStore } from "@/store/useAppStore";


class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => this.onopen?.(), 0);
  }

  close() {
    this.onclose?.();
  }
}

const wrapper = ({ children }: PropsWithChildren) =>
  createElement(QueryClientProvider, { client: new QueryClient() }, children);


describe("useWebSocket", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    useAppStore.setState({
      user: null,
      token: "token-1",
      refreshToken: "refresh-1",
      wsConnected: false,
      wsStatus: "disconnected",
      frameCount: 0,
      eventCount: 0,
      activeAlertCount: 0,
      selectedCameraId: null,
      sidebarCollapsed: false,
      demoMode: true,
      inventorySnapshot: {}
    } as never);
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);
  });

  it("connects to correct URL with token", async () => {
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    await waitFor(() => expect(result.current.status).toBe("connected"));
    expect(MockWebSocket.instances[0]?.url).toContain("token=token-1");
  });

  it("handles stock_update event and updates store", async () => {
    renderHook(() => useWebSocket(), { wrapper });
    await waitFor(() => expect(MockWebSocket.instances.length).toBeGreaterThan(0));
    const socket = MockWebSocket.instances[0];
    await act(async () => {
      socket.onmessage?.(
        new MessageEvent("message", {
          data: JSON.stringify({
            id: "1",
            type: "stock_update",
            timestamp: new Date().toISOString(),
            camera_id: "CAM-01",
            sku: "SKU-001",
            severity: "warning",
            data: { current_stock: 2 },
            session_id: "session"
          })
        })
      );
    });
    await waitFor(() => expect(useAppStore.getState().inventorySnapshot["SKU-001"]).toBeDefined());
  });

  it("handles alert_created event and increments counter", () => {
    useAppStore.getState().addEvent({
      id: "1",
      type: "alert_created",
      timestamp: new Date().toISOString(),
      camera_id: null,
      zone: null,
      product_id: null,
      sku: null,
      severity: "critical",
      data: {},
      session_id: "session"
    });
    expect(useAppStore.getState().activeAlertCount).toBe(1);
  });
});
