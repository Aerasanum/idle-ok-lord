// API client: bearer access token + single-flight rotating refresh. Tokens live in secure storage (Keychain/Keystore).
import { storage } from "@/src/utils/storage";

const BASE = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api`;
const ACCESS_KEY = "idle1.access";
const REFRESH_KEY = "idle1.refresh";

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onLogout: (() => void) | null = null;

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function setLogoutHandler(fn: (() => void) | null) {
  onLogout = fn;
}

export async function saveTokens(access: string, refresh: string) {
  accessToken = access;
  await storage.secureSet(ACCESS_KEY, access);
  await storage.secureSet(REFRESH_KEY, refresh);
}

export async function loadTokens(): Promise<boolean> {
  const a = await storage.secureGet(ACCESS_KEY, null);
  accessToken = typeof a === "string" ? a : null;
  const r = await storage.secureGet(REFRESH_KEY, null);
  return !!(accessToken || r);
}

export async function clearTokens() {
  accessToken = null;
  await storage.secureRemove(ACCESS_KEY);
  await storage.secureRemove(REFRESH_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  const r = await storage.secureGet(REFRESH_KEY, null);
  return typeof r === "string" ? r : null;
}

async function refresh(): Promise<boolean> {
  const old = await getRefreshToken();
  if (!old) return false;
  const r = await fetch(`${BASE}/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: old }) });
  if (!r.ok) {
    await clearTokens();
    return false;
  }
  const data = await r.json();
  await saveTokens(data.access_token, data.refresh_token);
  return true;
}

function parseError(status: number, body: any): ApiError {
  const d = body?.detail;
  if (d && typeof d === "object") return new ApiError(status, d.code ?? "error", d.message ?? d.code ?? "Error");
  if (typeof d === "string") return new ApiError(status, "error", d);
  if (Array.isArray(d)) return new ApiError(status, "validation", d.map((x: any) => x.msg).join(", "));
  return new ApiError(status, "error", body?.error ?? `HTTP ${status}`);
}

export async function request<T = any>(method: string, path: string, body?: any, retry = true): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let r: Response;
  try {
    r = await fetch(`${BASE}${path}`, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError(0, "network", "Sei offline: controlla la connessione");
  }
  if (r.status === 401 && retry) {
    refreshing ??= refresh().finally(() => {
      refreshing = null;
    });
    const ok = await refreshing;
    if (ok) return request<T>(method, path, body, false);
    onLogout?.();
    throw new ApiError(401, "session_expired", "Sessione scaduta");
  }
  const text = await r.text();
  const data = text ? JSON.parse(text) : null;
  if (!r.ok) throw parseError(r.status, data);
  return data as T;
}

export const api = {
  get: <T = any>(p: string) => request<T>("GET", p),
  post: <T = any>(p: string, b?: any) => request<T>("POST", p, b ?? {}),
  put: <T = any>(p: string, b?: any) => request<T>("PUT", p, b ?? {}),
  patch: <T = any>(p: string, b?: any) => request<T>("PATCH", p, b ?? {}),
};
