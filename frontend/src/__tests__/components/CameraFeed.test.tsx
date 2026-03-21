import type { ReactNode } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { CameraFeed } from "@/components/cameras/CameraFeed";


function renderWithProviders(component: ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}>{component}</QueryClientProvider>);
}


describe("CameraFeed", () => {
  it("renders camera feed img with correct src URL", () => {
    renderWithProviders(<CameraFeed cameraId="CAM-01" />);
    const image = screen.getByAltText("CAM-01") as HTMLImageElement;
    expect(image.src).toContain("/stream/CAM-01");
  });

  it("shows offline state when img fails to load", () => {
    renderWithProviders(<CameraFeed cameraId="CAM-01" />);
    fireEvent.error(screen.getByAltText("CAM-01"));
    expect(screen.getByText(/Camera Offline/i)).toBeInTheDocument();
  });

  it("shows reconnect button in offline state", () => {
    renderWithProviders(<CameraFeed cameraId="CAM-01" />);
    fireEvent.error(screen.getByAltText("CAM-01"));
    expect(screen.getByRole("button", { name: /Retry Connection/i })).toBeInTheDocument();
  });

  it("overlay drawn when detections received via mock WS", async () => {
    renderWithProviders(<CameraFeed cameraId="CAM-01" />);
    await act(async () => {
      window.dispatchEvent(
        new CustomEvent("siv:event", {
          detail: {
            id: "1",
            type: "stock_update",
            timestamp: new Date().toISOString(),
            camera_id: "CAM-01",
            severity: "warning",
            data: {
              zones: {
                "A-01": 0.2
              }
            },
            session_id: "session"
          }
        })
      );
    });
    expect(document.querySelector("canvas")).toBeInTheDocument();
  });
});
