import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { authService } from "@/services/auth.service";
import { useAppStore } from "@/store/useAppStore";
import { Button, Card, Input } from "@/components/ui";


export default function LoginPage() {
  const navigate = useNavigate();
  const { setAuth } = useAppStore();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await authService.login(username, password);
      setAuth(response.user, response.access_token, response.refresh_token);
      navigate("/");
    } catch {
      setError("Invalid credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mesh-background flex min-h-screen items-center justify-center px-6">
      <div className="grid w-full max-w-5xl gap-8 lg:grid-cols-[1.2fr_0.9fr]">
        <div className="rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top_right,rgba(0,194,255,0.12),transparent_30%),rgba(8,12,20,0.72)] p-10">
          <p className="font-mono text-xs uppercase tracking-[0.26em] text-brand-cyan">Smart Inventory Vision</p>
          <h1 className="mt-4 font-display text-6xl uppercase tracking-[0.08em] text-white">See stock. Act before it disappears.</h1>
          <p className="mt-6 max-w-xl text-lg text-slate-300">
            Real camera feeds, zone detection, alerts, and automated purchase ordering in one operations console.
          </p>
        </div>
        <Card className="self-center p-8">
          <div className="mb-6">
            <div className="font-display text-4xl uppercase tracking-[0.08em] text-white">Operator Login</div>
            <div className="mt-2 text-sm text-slate-400">Default demo credentials: admin / admin123</div>
          </div>
          <form className="space-y-4" onSubmit={onSubmit}>
            <Input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Username" />
            <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" />
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <Button className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
