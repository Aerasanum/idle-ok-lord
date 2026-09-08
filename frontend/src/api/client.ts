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

/** Italian fallbacks for server error codes (the server message wins when it is already Italian). */
const IT: Record<string, string> = {
  officer_required: "Solo il leader e gli ufficiali possono farlo",
  displaced: "L'alleanza si sta ricollocando dopo aver perso il castello: attendi 12 ore",
  min_members: "Servono almeno 10 membri per attaccare",
  attack_cooldown: "Un solo attacco ogni 24 ore per alleanza",
  war_active: "La tua alleanza è già impegnata in una guerra",
  node_not_found: "Nodo non trovato",
  own_node: "Questo nodo è già tuo",
  not_adjacent: "Puoi attaccare solo nodi adiacenti al tuo territorio",
  node_contested: "Su questo nodo c'è già una guerra in corso",
  defender_busy: "L'alleanza difensore è già impegnata in un'altra guerra",
  not_in_alliance: "Non sei in un'alleanza",
  war_not_open: "La guerra non è più in preparazione",
  roster_locked: "Schieramento bloccato: mancano meno di 30 minuti alla risoluzione",
  not_in_war: "La tua alleanza non partecipa a questa guerra",
  insufficient: "Risorse insufficienti",
  insufficient_rubies: "Rubini insufficienti",
  queue_full: "Coda piena",
  max_level: "Livello massimo raggiunto",
  unit_locked: "Unità non ancora sbloccata",
  stage_locked: "Stage non ancora sbloccato",
  castle_gate: "Serve un Castello di livello superiore",
  forge_max: "Forgia già al massimo",
  rate_limited: "Troppe richieste: riprova tra poco",
  chat_rate_limit: "Stai scrivendo troppo in fretta",
};
const looksEnglish = (m: string) => /\b(must|already|need|not|per|cannot|invalid|only)\b/i.test(m) && !/[àèéìòù]/.test(m);

function parseError(status: number, body: any): ApiError {
  const d = body?.detail;
  if (d && typeof d === "object") {
    const code = d.code ?? "error";
    const msg = d.message && !looksEnglish(d.message) ? d.message : IT[code] ?? d.message ?? code;
    return new ApiError(status, code, msg);
  }
  if (typeof d === "string") return new ApiError(status, "error", IT[d] ?? d);
  if (Array.isArray(d)) return new ApiError(status, "validation", d.map((x: any) => x.msg).join(", "));
  if (status === 429) return new ApiError(status, "rate_limited", IT.rate_limited);
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
