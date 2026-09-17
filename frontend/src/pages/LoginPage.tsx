import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi, dashboardApi } from "../lib/api";
import { Logo } from "../components/brand/Logo";
import { AuroraBackdrop } from "../components/brand/AuroraBackdrop";
import { Card } from "../components/primitives/Card";
import { Input } from "../components/primitives/Input";
import { Button } from "../components/primitives/Button";
import { Magnetic } from "../motion/Magnetic";
import { Reveal } from "../motion/Reveal";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await authApi.login(email, password);
      localStorage.setItem("novaa_token", res.data.access_token);
      localStorage.setItem("novaa_user", JSON.stringify(res.data.user));
      navigate("/app/overview");
    } catch {
      setError("Invalid credentials");
    }
  };

  const demo = async () => {
    const res = await authApi.demoLogin();
    localStorage.setItem("novaa_token", res.data.access_token);
    localStorage.setItem("novaa_user", JSON.stringify(res.data.user));
    await dashboardApi.loadMock();
    navigate("/app/overview");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas relative">
      <AuroraBackdrop />
      <Reveal className="w-full max-w-md px-4">
        <div className="text-center mb-8">
          <Logo size={36} className="justify-center" />
          <p className="text-muted text-sm mt-2">Sign in to your analytics workspace</p>
        </div>
        <Card>
          <form onSubmit={submit} className="space-y-4">
            <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error && <p className="text-coral text-sm">{error}</p>}
            <Magnetic>
              <Button type="submit" className="w-full">Sign in</Button>
            </Magnetic>
          </form>
          <div className="mt-4 text-center">
            <button onClick={demo} className="text-sm text-nova hover:underline">Try with demo data</button>
          </div>
          <p className="text-center text-sm text-muted mt-4">
            No account? <Link to="/signup" className="text-nova hover:underline">Sign up</Link>
          </p>
        </Card>
      </Reveal>
    </div>
  );
}
