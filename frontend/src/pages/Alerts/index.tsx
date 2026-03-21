import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Badge, Button, Card, SectionTitle } from "@/components/ui";
import { useAlerts } from "@/hooks/useAlerts";
import { alertsService } from "@/services/alerts.service";


export default function AlertsPage() {
  const queryClient = useQueryClient();
  const { data } = useAlerts({ limit: 100 });
  const acknowledge = useMutation({
    mutationFn: (alertId: string) => alertsService.acknowledge(alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] })
  });

  const resolve = useMutation({
    mutationFn: (alertId: string) => alertsService.resolve(alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] })
  });

  return (
    <div className="space-y-6">
      <SectionTitle title="Alert Center" eyebrow="Prioritized incidents" />
      <div className="grid gap-4">
        {data?.items.map((alert) => (
          <Card key={alert.id} className="border-l-4 border-l-red-500">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-medium text-white">{alert.title}</div>
                <div className="mt-2 text-sm text-slate-400">{alert.description}</div>
                <div className="mt-3 flex items-center gap-2">
                  <Badge>{alert.severity}</Badge>
                  <Badge className="text-slate-300">{alert.status}</Badge>
                </div>
              </div>
              <div className="flex gap-2">
                <Button className="bg-white/10 hover:bg-white/15" onClick={() => acknowledge.mutate(alert.id)}>Acknowledge</Button>
                <Button className="bg-white/10 hover:bg-white/15" onClick={() => resolve.mutate(alert.id)}>Resolve</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
