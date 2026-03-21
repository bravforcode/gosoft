import { createBrowserRouter, Navigate } from "react-router-dom";

import { App } from "@/app/App";
import { AppShell } from "@/components/layout/AppShell";
import { useAppStore } from "@/store/useAppStore";
import DashboardPage from "@/pages/Dashboard";
import CamerasPage from "@/pages/Cameras";
import InventoryPage from "@/pages/Inventory";
import AlertsPage from "@/pages/Alerts";
import PurchaseOrdersPage from "@/pages/PurchaseOrders";
import AnalyticsPage from "@/pages/Analytics";
import SettingsPage from "@/pages/Settings";
import LoginPage from "@/pages/Login";


function ProtectedRoute() {
  const token = useAppStore((state) => state.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <AppShell />;
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />
  },
  {
    path: "/",
    element: <App />,
    children: [
      {
        element: <ProtectedRoute />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "cameras", element: <CamerasPage /> },
          { path: "inventory", element: <InventoryPage /> },
          { path: "alerts", element: <AlertsPage /> },
          { path: "purchase-orders", element: <PurchaseOrdersPage /> },
          { path: "analytics", element: <AnalyticsPage /> },
          { path: "settings", element: <SettingsPage /> }
        ]
      }
    ]
  }
]);
