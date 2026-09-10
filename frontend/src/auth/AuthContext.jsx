import React, { createContext, useContext, useMemo, useState, useCallback } from "react";
import { AP_API_BASE } from "../config";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("ap_auth_user") || "null");
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem("ap_auth_token"));

  const login = useCallback(async (email, password) => {
    const response = await fetch(`${AP_API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      let message = `Login failed (${response.status})`;
      try {
        message = (await response.json()).detail || message;
      } catch {}
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    const result = await response.json();
    localStorage.setItem("ap_auth_token", result.token);
    localStorage.setItem("ap_auth_user", JSON.stringify(result.user));
    setToken(result.token);
    setUser(result.user);
    return result.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${AP_API_BASE}/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({}),
      });
    } catch {}
    localStorage.removeItem("ap_auth_token");
    localStorage.removeItem("ap_auth_user");
    setToken(null);
    setUser(null);
  }, [token]);

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
    }),
    [user, token, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
