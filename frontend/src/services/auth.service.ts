import { api } from "@/services/api";
import type { User } from "@/types/events.types";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export const authService = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>("/api/v1/auth/login", { username, password });
    return response.data;
  },
  logout: async (): Promise<void> => {
    await api.post("/api/v1/auth/logout");
  },
  refresh: async (refreshToken: string): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>("/api/v1/auth/refresh", { refresh_token: refreshToken });
    return response.data;
  },
  getMe: async (): Promise<User> => {
    const response = await api.get<User>("/api/v1/auth/me");
    return response.data;
  }
};
