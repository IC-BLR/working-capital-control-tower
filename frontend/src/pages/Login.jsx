import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { UserRound } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

const DEMO_USERS = [
  ["ap.analyst@demo.com", "Anita Rao", "AP Analyst"],
  ["finance.manager@demo.com", "Ravi Menon", "Finance Manager"],
  ["tax.reviewer@demo.com", "Priya Nair", "Tax Reviewer"],
  ["controller@demo.com", "Karan Shah", "Controller"],
];

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(DEMO_USERS[0][0]);
  const [password, setPassword] = useState("Demo@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 via-white to-emerald-50 px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-2xl border bg-white/90 backdrop-blur shadow-lg p-8 space-y-5"
      >
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Enterprise POC</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope, sans-serif" }}>
            Working Capital Control Tower
          </h1>
          <p className="text-sm text-slate-600 mt-2">
            Sign in once for the Cash Calendar, AR Sensei, and AP Control Tower.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>

        <div className="space-y-2">
          <p className="text-xs text-slate-500">Demo users (password <strong>Demo@123</strong>)</p>
          <div className="grid gap-2">
            {DEMO_USERS.map(([mail, name, role]) => (
              <button
                key={mail}
                type="button"
                onClick={() => {
                  setEmail(mail);
                  setPassword("Demo@123");
                }}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm transition ${email === mail ? "border-emerald-400 bg-emerald-50" : "hover:bg-slate-50"
                  }`}
              >
                <UserRound className="w-4 h-4 text-slate-500 shrink-0" />
                <span className="flex-1">
                  <span className="font-medium text-slate-900 block">{name}</span>
                  <span className="text-xs text-slate-500">{mail}</span>
                </span>
                <strong className="text-xs text-slate-600">{role}</strong>
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
}
