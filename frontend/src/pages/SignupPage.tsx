import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../lib/api";
import { Logo } from "../components/brand/Logo";
import { AuroraBackdrop } from "../components/brand/AuroraBackdrop";
import { Card } from "../components/primitives/Card";
import { Input } from "../components/primitives/Input";
import { Button } from "../components/primitives/Button";
import { Reveal } from "../motion/Reveal";

export function SignupPage() {
  const [form, setForm] = useState({ name: "", email: "", mobile: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await authApi.signup(form);
      localStorage.setItem("novaa_token", res.data.access_token);
      localStorage.setItem("novaa_user", JSON.stringify(res.data.user));
      navigate("/app/overview");
    } catch {
      setError("Could not create account");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas relative">
      <AuroraBackdrop />
      <Reveal className="w-full max-w-md px-4">
        <div className="text-center mb-8">
          <Logo size={36} className="justify-center" />
          <p className="text-muted text-sm mt-2">Create your NOVAA workspace</p>
        </div>
        <Card>
          <form onSubmit={submit} className="space-y-4">
            <Input placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <Input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            <Input placeholder="Mobile (+91)" value={form.mobile} onChange={(e) => setForm({ ...form, mobile: e.target.value })} required />
            <Input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            {error && <p className="text-coral text-sm">{error}</p>}
            <Button type="submit" className="w-full">Create account</Button>
          </form>
          <p className="text-center text-sm text-muted mt-4">
            Have an account? <Link to="/login" className="text-nova hover:underline">Sign in</Link>
          </p>
        </Card>
      </Reveal>
    </div>
  );
}
