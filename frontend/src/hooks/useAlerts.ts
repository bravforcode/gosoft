import { useQuery } from "@tanstack/react-query";

import { alertsService } from "@/services/alerts.service";

export function useAlerts(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["alerts", params],
    queryFn: () => alertsService.getAll(params)
  });
}
