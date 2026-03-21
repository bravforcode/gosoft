import { useQuery } from "@tanstack/react-query";

import { Card, SectionTitle } from "@/components/ui";
import { purchaseOrderService } from "@/services/purchaseOrder.service";


export default function PurchaseOrdersPage() {
  const { data } = useQuery({
    queryKey: ["purchase-orders"],
    queryFn: () => purchaseOrderService.getAll({ limit: 100 })
  });

  return (
    <div className="space-y-6">
      <SectionTitle title="Purchase Orders" eyebrow="Procurement flow" />
      <div className="grid gap-4 lg:grid-cols-2">
        {data?.items.map((po) => (
          <Card key={po.id}>
            <div className="font-display text-3xl uppercase tracking-[0.08em] text-white">{po.id}</div>
            <div className="mt-2 text-sm text-slate-400">Status: {po.status}</div>
            <div className="mt-4 font-mono text-xs uppercase tracking-[0.18em] text-slate-500">
              Qty {po.quantity_ordered} · Total ฿{po.total_amount}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
