import { Card, Input, SectionTitle } from "@/components/ui";


export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <SectionTitle title="Settings" eyebrow="Operators & integrations" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="font-display text-2xl uppercase tracking-[0.08em] text-white">Notifications</div>
          <div className="mt-4 space-y-3">
            <Input placeholder="LINE token" />
            <Input placeholder="Webhook URL" />
            <Input placeholder="SMTP host" />
          </div>
        </Card>
        <Card>
          <div className="font-display text-2xl uppercase tracking-[0.08em] text-white">Integrations</div>
          <div className="mt-4 space-y-3">
            <Input placeholder="GOSOFT ERP URL" />
            <Input placeholder="API key" />
            <Input placeholder="SAP B1 Service URL" />
          </div>
        </Card>
      </div>
    </div>
  );
}
