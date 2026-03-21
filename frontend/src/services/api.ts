import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";

import { useAppStore } from "@/store/useAppStore";

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 10000
});

let refreshPromise: Promise<string | null> | null = null;

type RetryableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export const requestInterceptor = (config: InternalAxiosRequestConfig) => {
  const { token } = useAppStore.getState();
  config.headers = config.headers ?? {};
  config.headers["X-Request-ID"] = crypto.randomUUID();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (config.url?.includes("/stream/")) {
    config.timeout = 30000;
  }
  return config;
};

export const responseErrorInterceptor = async (error: AxiosError) => {
  if (!error.response) {
    throw new NetworkError(error.message || "Network request failed.");
  }

  const originalConfig = error.config as RetryableConfig | undefined;
  if (error.response.status === 401 && originalConfig && !originalConfig._retry) {
    originalConfig._retry = true;
    const { refreshToken, clearAuth, setAuth, user } = useAppStore.getState();
    if (!refreshToken) {
      clearAuth();
      window.location.href = "/login";
      throw error;
    }

    if (!refreshPromise) {
      refreshPromise = api
        .post("/api/v1/auth/refresh", { refresh_token: refreshToken })
        .then((response) => {
          const nextToken = response.data.access_token as string;
          const nextRefresh = response.data.refresh_token as string;
          setAuth(response.data.user ?? user, nextToken, nextRefresh);
          return nextToken;
        })
        .catch(() => {
          clearAuth();
          window.location.href = "/login";
          return null;
        })
        .finally(() => {
          refreshPromise = null;
        });
    }

    const newToken = await refreshPromise;
    if (newToken) {
      originalConfig.headers = originalConfig.headers ?? {};
      originalConfig.headers.Authorization = `Bearer ${newToken}`;
      return api.request(originalConfig);
    }
  }

  throw error;
};

api.interceptors.request.use(requestInterceptor);
api.interceptors.response.use((response) => response, responseErrorInterceptor);
