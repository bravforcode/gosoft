import { useQuery } from "@tanstack/react-query";

import { cameraService } from "@/services/camera.service";

export function useCameras() {
  return useQuery({
    queryKey: ["cameras"],
    queryFn: cameraService.getAll
  });
}
