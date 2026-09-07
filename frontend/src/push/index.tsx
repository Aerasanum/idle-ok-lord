// Push registration (Emergent managed). Real module only in dev/production builds; Expo Go and web are graceful no-ops.
import * as Device from "expo-device";
import { useRouter } from "expo-router";
import { useEffect, useRef } from "react";
import { Platform } from "react-native";

import { api } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";
import { loadNotifications, REMOTE_PUSH_SUPPORTED } from "./adapter";

export { IS_EXPO_GO, REMOTE_PUSH_SUPPORTED } from "./adapter";

export async function registerPushIfPossible(playerId: string): Promise<"registered" | "unavailable" | "denied"> {
  if (!REMOTE_PUSH_SUPPORTED || !Device.isDevice) return "unavailable";
  const N = await loadNotifications();
  if (!N) return "unavailable";
  const perm = await N.getPermissionsAsync();
  let status = perm.status;
  if (status !== "granted" && perm.canAskAgain) status = (await N.requestPermissionsAsync()).status;
  if (status !== "granted") return "denied";
  if (Platform.OS === "android") await N.setNotificationChannelAsync("default", { name: "IDLE 1", importance: N.AndroidImportance.DEFAULT });
  const token = (await N.getDevicePushTokenAsync()).data as string;
  await api.post("/register-push", { user_id: playerId, platform: Platform.OS, device_token: token });
  return "registered";
}

export function PushBootstrap() {
  const { user } = useAuth();
  const router = useRouter();
  const doneFor = useRef<string | null>(null);
  useEffect(() => {
    if (!user || doneFor.current === user.player_id) return;
    doneFor.current = user.player_id;
    registerPushIfPossible(user.player_id).catch((e) => console.warn("push register skipped", e?.message));
  }, [user]);
  useEffect(() => {
    if (!REMOTE_PUSH_SUPPORTED) return;
    let cancelled = false;
    let sub: { remove: () => void } | undefined;
    loadNotifications().then((N) => {
      if (!N || cancelled) return;
      N.setNotificationHandler({ handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }) });
      sub = N.addNotificationResponseReceivedListener((r) => {
        const url = (r.notification.request.content.data as any)?.action_url;
        if (typeof url === "string") router.push(url as any);
      });
    });
    return () => {
      cancelled = true;
      sub?.remove();
    };
  }, [router]);
  return null;
}
