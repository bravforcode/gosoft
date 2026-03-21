import { useQuery } from "@tanstack/react-query";

import { inventoryService } from "@/services/inventory.service";

export function useInventory(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["inventory", params],
    queryFn: () => inventoryService.getAll(params)
  });
}
