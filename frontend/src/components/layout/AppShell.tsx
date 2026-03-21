import { format } from "date-fns";
import { AlertTriangle, BarChart3, Camera, Cog, LayoutDashboard, ListChecks, LogOut, PackageSearch, Radio } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Badge, Button } from "@/components/ui";
import { useAppStore } from "@/store/useAppStore";
import { cn } from "@/utils/cn";


const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/cameras", label: "Cameras", icon: Camera },
  { to: "/inventory", label: "Inventory", icon: PackageSearch },
  { to: "/alerts", label: "Alerts", icon: AlertTriangle },
  { to: "/purchase-orders", label: "POs", icon: ListChecks },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Cog }
];

export function AppShell() {
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebar, frameCount, activeAlertCount, wsStatus, user, clearAuth } = useAppStore();

  return (
    <div className="flex min-h-screen">
      <aside className={cn("border-r border-white/10 bg-black/20 px-3 py-4 transition-all duration-300", sidebarCollapsed ? "w-16" : "w-56")}>
        <div className="mb-6 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-blue font-display text-lg font-semibold">S</div>
          {!sidebarCollapsed ? (
            <div>
              <div className="font-display text-2xl uppercase tracking-[0.12em] text-white">SIV Pro</div>
              <div className="font-mono text-xs uppercase tracking-[0.22em] text-slate-400">Retail Vision Stack</div>
            </div>
          ) : null}
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-2xl border border-transparent px-3 py-3 text-sm font-medium text-slate-300 transition hover:border-white/10 hover:bg-white/5 hover:text-white",
                  isActive && "border-brand-blue/50 bg-brand-blue/15 text-white"
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!sidebarCollapsed ? <span>{item.label}</span> : null}
            </NavLink>
          ))}
        </nav>
        <div className="mt-6 space-y-3">
          <Button className="w-full bg-white/5 text-slate-200 hover:bg-white/10" onClick={toggleSidebar}>
            {sidebarCollapsed ? ">" : "Collapse"}
          </Button>
          {!sidebarCollapsed ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-400">
              <div className="mb-1 uppercase tracking-[0.18em] text-slate-500">System</div>
              <div className="flex items-center justify-between">
                <span>WebSocket</span>
                <span className={cn("font-mono", wsStatus === "connected" ? "text-emerald-400" : "text-amber-300")}>{wsStatus}</span>
              </div>
            </div>
          ) : null}
        </div>
      </aside>
      <div className="flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-[rgba(6,9,15,0.8)] px-6 py-4 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Badge className="border-red-500/30 bg-red-500/10 text-red-300"><Radio className="mr-2 inline h-3 w-3 animate-pulse-slow" />LIVE</Badge>
              <span className="font-mono text-xs uppercase tracking-[0.24em] text-slate-400">{format(new Date(), "yyyy-MM-dd HH:mm:ss")}</span>
              <span className="font-mono text-xs uppercase tracking-[0.24em] text-slate-400">Frames {frameCount}</span>
            </div>
            <div className="flex items-center gap-3">
              <Badge className="border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan">AI Processing</Badge>
              <Button className="bg-white/5 text-white hover:bg-white/10" onClick={() => navigate("/alerts")}>Alerts {activeAlertCount}</Button>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-sm">
                <div className="font-medium text-white">{user?.username ?? "guest"}</div>
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{user?.role}</div>
              </div>
              <Button
                className="bg-white/5 px-3 text-slate-100 hover:bg-white/10"
                onClick={() => {
                  clearAuth();
                  navigate("/login");
                }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </div>
          </div>
        </header>
        <main className="flex-1 px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
