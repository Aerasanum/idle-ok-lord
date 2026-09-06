import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Platform } from "react-native";

import { api, clearTokens, getRefreshToken, loadTokens, saveTokens, setLogoutHandler } from "@/src/api/client";
import { queryClient } from "@/src/query-client";

WebBrowser.maybeCompleteAuthSession();

export type AuthUser = { account: { id: string; email: string; email_verified: boolean; providers: string[] }; player_id: string; display_name: string | null; needs_consent: boolean; legal: any; settings: any };

type Ctx = {
  loading: boolean;
  user: AuthUser | null;
  refreshMe: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (b: { email: string; password: string; display_name: string; age_confirmed: boolean; consent: boolean }) => Promise<void>;
  googleLogin: () => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
};

const AuthCtx = createContext<Ctx | null>(null);
const sentSessions = new Set<string>();

function extractSessionId(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/[?#&]session_id=([^&#]+)/);
  return m ? decodeURIComponent(m[1]) : null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const pendingUrl = useRef<string | null>(null);

  const refreshMe = useCallback(async () => {
    const me = await api.get<AuthUser>("/auth/me");
    setUser(me);
  }, []);

  const signOutLocal = useCallback(async () => {
    await clearTokens();
    queryClient.clear();
    setUser(null);
  }, []);

  const exchangeSession = useCallback(
    async (sessionId: string) => {
      if (sentSessions.has(sessionId)) return;
      sentSessions.add(sessionId);
      try {
        const data = await api.post("/auth/session", { session_id: sessionId, device: Platform.OS });
        await saveTokens(data.access_token, data.refresh_token);
        await refreshMe();
        if (Platform.OS === "web" && typeof window !== "undefined") {
          const url = new URL(window.location.href);
          url.searchParams.delete("session_id");
          const hash = url.hash.replace(/[#&]?session_id=[^&]*/, "");
          url.hash = hash === "#" ? "" : hash;
          window.history.replaceState(window.history.state, "", url.toString());
        }
      } catch (e) {
        console.warn("session exchange failed", e);
      }
    },
    [refreshMe],
  );

  useEffect(() => {
    setLogoutHandler(() => {
      signOutLocal();
    });
    (async () => {
      try {
        let sid: string | null = null;
        if (Platform.OS === "web" && typeof window !== "undefined") sid = extractSessionId(window.location.hash) ?? extractSessionId(window.location.search);
        else sid = extractSessionId(await Linking.getInitialURL());
        if (sid) await exchangeSession(sid);
        else if (await loadTokens()) {
          try {
            await refreshMe();
          } catch {
            await signOutLocal();
          }
        }
      } finally {
        setLoading(false);
      }
    })();
    const sub = Linking.addEventListener("url", ({ url }) => {
      pendingUrl.current = url;
      const sid = extractSessionId(url);
      if (sid) exchangeSession(sid);
    });
    return () => sub.remove();
  }, [exchangeSession, refreshMe, signOutLocal]);

  const login = useCallback(
    async (email: string, password: string) => {
      const d = await api.post("/auth/login", { email, password, device: Platform.OS });
      await saveTokens(d.access_token, d.refresh_token);
      await refreshMe();
    },
    [refreshMe],
  );

  const register = useCallback(
    async (b: any) => {
      const d = await api.post("/auth/register", { ...b, device: Platform.OS });
      await saveTokens(d.access_token, d.refresh_token);
      await refreshMe();
    },
    [refreshMe],
  );

  const googleLogin = useCallback(async () => {
    const redirectUrl = Platform.OS === "web" ? `${window.location.origin}/` : Linking.createURL("");
    const authUrl = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    if (Platform.OS === "web") {
      window.location.href = authUrl;
      return;
    }
    pendingUrl.current = null;
    const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
    let sid = extractSessionId((result as any).url);
    if (!sid) sid = extractSessionId(pendingUrl.current);
    if (!sid) sid = extractSessionId(await Linking.getInitialURL());
    if (sid) await exchangeSession(sid);
  }, [exchangeSession]);

  const logout = useCallback(async () => {
    const rt = await getRefreshToken();
    try {
      if (rt) await api.post("/auth/logout", { refresh_token: rt });
    } catch {}
    await signOutLocal();
  }, [signOutLocal]);

  const logoutAll = useCallback(async () => {
    try {
      await api.post("/auth/logout-all");
    } catch {}
    await signOutLocal();
  }, [signOutLocal]);

  const value = useMemo(() => ({ loading, user, refreshMe, login, register, googleLogin, logout, logoutAll }), [loading, user, refreshMe, login, register, googleLogin, logout, logoutAll]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): Ctx {
  const c = useContext(AuthCtx);
  if (!c) throw new Error("AuthProvider missing");
  return c;
}
