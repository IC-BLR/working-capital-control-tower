import { AP_API_BASE } from "../../config";

export async function api(path, options = {}) {
  const token = localStorage.getItem("ap_auth_token");
  const baseHeaders = options.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`${AP_API_BASE}${path}`, {
    ...options,
    headers: { ...baseHeaders, ...authHeaders, ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = `API error ${response.status}`;
    try {
      message = (await response.json()).detail || message;
    } catch {}
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json();
}
