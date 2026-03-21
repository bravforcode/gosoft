import "@testing-library/jest-dom";
import { vi } from "vitest";

vi.stubGlobal("crypto", {
  randomUUID: () => "test-request-id"
});

const mockContext = {
  clearRect: vi.fn(),
  fillRect: vi.fn(),
  strokeRect: vi.fn(),
  fillText: vi.fn(),
  drawImage: vi.fn(),
  set strokeStyle(_value: string) {},
  set fillStyle(_value: string) {},
  set font(_value: string) {}
};

vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => mockContext as unknown as CanvasRenderingContext2D);
vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue("data:image/jpeg;base64,test");
