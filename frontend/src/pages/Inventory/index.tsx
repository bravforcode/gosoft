import { useMemo, useState } from "react";
import { formatDistanceToNowStrict } from "date-fns";

import { Button, Card, Input, Progress, SectionTitle, Select } from "@/components/ui";
import { useInventory } from "@/hooks/useInventory";
import { inventoryService } from "@/services/inventory.service";


export default function InventoryPage() {
  const [search, setSearch] = useState("");
  const [zone, setZone] = useState("");
  const { data } = useInventory({ search: search || undefined, zone: zone || undefined, limit: 100 });

  const items = useMemo(() => data?.items ?? [], [data?.items]);

  const exportCsv = async () => {
    const blob = await inventoryService.exportCSV();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="space-y-6">
      <SectionTitle title="Inventory Matrix" eyebrow="Realtime stock" action={<Button onClick={exportCsv}>Export CSV</Button>} />
      <Card>
        <div className="grid gap-4 md:grid-cols-[1.2fr_0.3fr]">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search SKU, brand, product name" />
          <Select value={zone} onChange={(event) => setZone(event.target.value)}>
            <option value="">All zones</option>
            <option value="A-01">Zone A</option>
            <option value="B-01">Zone B</option>
            <option value="C-01">Zone C</option>
            <option value="D-01">Zone D</option>
          </Select>
        </div>
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-[0.18em] text-slate-500">
              <tr>
                <th className="pb-3">Product</th>
                <th className="pb-3">Zone</th>
                <th className="pb-3">Stock</th>
                <th className="pb-3">Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {items.map((item) => (
                <tr key={item.id} className="animate-fade-in-up">
                  <td className="py-4">
                    <div className="flex items-center gap-3">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.product_color_hex }} />
                      <div>
                        <div className="font-medium text-white">{item.name_en}</div>
                        <div className="font-mono text-xs uppercase tracking-[0.16em] text-slate-500">{item.sku}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 text-slate-300">{item.zone_id}</td>
                  <td className="py-4">
                    <div className="min-w-[180px]">
                      <Progress value={(item.current_stock / item.max_capacity) * 100} />
                      <div className="mt-2 font-mono text-xs uppercase tracking-[0.16em] text-slate-500">
                        {item.current_stock} / {item.max_capacity}
                      </div>
                    </div>
                  </td>
                  <td className="py-4 text-slate-400">{formatDistanceToNowStrict(new Date(item.updated_at), { addSuffix: true })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
