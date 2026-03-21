import { describe, expect, it, vi } from "vitest";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

import { api, NetworkError, requestInterceptor, responseErrorInterceptor } from "@/services/api";
import { useAppStore } from "@/store/useAppStore";


describe("api service", () => {
  it("attaches Authorization header", async () => {
    useAppStore.setState({ token: "abc", refreshToken: null, user: null });
    const config = await requestInterceptor({ headers: {}, url: "/api/v1/test" } as InternalAxiosRequestConfig);
    expect(config?.headers?.Authorization).toBe("Bearer abc");
  });

  it("refreshes token on 401", async () => {
    useAppStore.setState({
      token: "old",
      refreshToken: "refresh",
      user: {
        id: "1",
        username: "admin",
        email: "admin@example.com",
        role: "admin",
        is_active: true,
        created_at: new Date().toISOString()
      }
    });
    const refreshSpy = vi.spyOn(api, "post").mockResolvedValue({
      data: {
        access_token: "new-token",
        refresh_token: "new-refresh",
        user: useAppStore.getState().user
      }
    } as never);
    const requestSpy = vi.spyOn(api, "request").mockResolvedValue({ data: { ok: true } } as never);
    const error = {
      response: { status: 401 },
      config: { headers: {}, url: "/api/v1/test" }
    } as AxiosError;
    await responseErrorInterceptor(error);
    expect(refreshSpy).toHaveBeenCalled();
    expect(requestSpy).toHaveBeenCalled();
  });

  it("handles network error with custom class", async () => {
    await expect(responseErrorInterceptor({ message: "offline" } as AxiosError)).rejects.toBeInstanceOf(NetworkError);
  });
});
