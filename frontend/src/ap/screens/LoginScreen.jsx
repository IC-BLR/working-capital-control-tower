import React, { useState } from "react";
import { UserRound } from "lucide-react";
import BrandLockup from "../components/BrandLockup";

export default function LoginScreen({ onLogin }) {
  const demoUsers = [
    ["ap.analyst@demo.com", "Anita Rao", "AP Analyst"],
    ["finance.manager@demo.com", "Ravi Menon", "Finance Manager"],
    ["tax.reviewer@demo.com", "Priya Nair", "Tax Reviewer"],
    ["controller@demo.com", "Karan Shah", "Controller"],
  ];
  const [email, setEmail] = useState(demoUsers[0][0]);
  const [password, setPassword] = useState("Demo@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try { await onLogin(email, password); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <div className="login-shell">
    <form className="login-card" onSubmit={submit}>
      <div className="login-brand-panel">
  <BrandLockup variant="login" />

      
    </div>
      <label>Email<input value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
      {error && <div className="message">{error}</div>}
      <button disabled={busy}>{busy ? "Signing in" : "Sign in"}</button>
      <div className="demo-users">{demoUsers.map(([mail, name, role]) => <button type="button" className={email === mail ? "active" : "ghost"} key={mail} onClick={() => { setEmail(mail); setPassword("Demo@123"); }}><UserRound size={16}/><span>{name}</span><strong>{role}</strong></button>)}</div>
      <p className="login-hint">All demo users use password <strong>Demo@123</strong>.</p>
    </form>
  </div>;
}
