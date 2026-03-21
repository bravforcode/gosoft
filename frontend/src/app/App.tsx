import { Outlet } from "react-router-dom";

import { useWebSocket } from "@/hooks/useWebSocket";

export function App() {
  useWebSocket();
  return <Outlet />;
}
