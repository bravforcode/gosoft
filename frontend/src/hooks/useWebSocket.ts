import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAppStore } from "@/store/useAppStore";
import type { SIVEvent } from "@/types/events.types";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export function useWebSocket() {
  const queryClient = useQueryClient();
  const { token, setWsStatus, addEvent, updateInventoryItem, incrementFrameCount } = useAppStore();
  const reconnectRef = useRef(0);
  const socketRef = useRef<WebSocket | null>(null);
  const [lastEvent, setLastEvent] = useState<SIVEvent | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    let closedManually = false;

    const connect = () => {
      setWsStatus("connecting");
      const ws = new WebSocket(`${WS_URL.replace(/^http/, "ws")}/ws/events?token=${token}`);
      socketRef.current = ws;

      ws.onopen = () => {
        reconnectRef.current = 0;
        setWsStatus("connected");
      };

      ws.onmessage = (message) => {
        const event = JSON.parse(message.data) as SIVEvent;
        setLastEvent(event);
        addEvent(event);
        window.dispatchEvent(new CustomEvent("siv:event", { detail: event }));
        handleEvent(event);
      };

      ws.onerror = () => setWsStatus("error");
      ws.onclose = () => {
        setWsStatus("disconnected");
        if (closedManually) {
          return;
        }
        reconnectRef.current += 1;
        const delay = Math.min(60000, 1000 * 2 ** Math.max(0, reconnectRef.current - 1));
        window.setTimeout(connect, delay);
      };
    };

    const handleEvent = (event: SIVEvent) => {
      switch (event.type) {
        case "stock_update": {
          const sku = event.sku;
          const zones = event.data.zones as Record<string, number> | undefined;
          if (sku) {
            updateInventoryItem(sku, {
              updated_at: event.timestamp,
              current_stock: typeof event.data.current_stock === "number" ? event.data.current_stock : undefined
            });
          }
          queryClient.invalidateQueries({ queryKey: ["inventory"] });
          if (zones) {
            queryClient.setQueryData(["camera-zones", event.camera_id], zones);
          }
          break;
        }
        case "alert_created":
          queryClient.invalidateQueries({ queryKey: ["alerts"] });
          break;
        case "alert_resolved":
          queryClient.invalidateQueries({ queryKey: ["alerts"] });
          break;
        case "reorder_triggered":
        case "po_approved":
          queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
          break;
        case "camera_status":
          queryClient.invalidateQueries({ queryKey: ["cameras"] });
          break;
        case "heartbeat":
          incrementFrameCount();
          break;
        default:
          break;
      }
    };

    connect();

    return () => {
      closedManually = true;
      socketRef.current?.close();
    };
  }, [token, addEvent, incrementFrameCount, queryClient, setWsStatus, updateInventoryItem]);

  return {
    status: useAppStore((state) => state.wsStatus),
    lastEvent,
    reconnect: () => {
      socketRef.current?.close();
    }
  };
}
