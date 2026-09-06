// Push registration (Emergent managed). Works only in native builds (not Expo Go / web); gracefully no-ops elsewhere.
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { useRouter } from "expo-router";
import { useEffect, useRef } from "react";
import { Platform } from "react-native";

import { api } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";

const isExpoGo = Constants.executionEnvironment === "storeClient";

if (!isExpoGo && Platform.OS !== "web") {
  Notifications.setNotificationHandler({ handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: false }) });
}

export async function registerPushIfPossible(playerId: string): Promise<"registered" | "unavailable" | "denied"> {
  if (isExpoGo || Platform.OS === "web" || !Device.isDevice) return "unavailable";
  const perm = await Notifications.getPermissionsAsync();
  let status = perm.status;
  if (status !== "granted" && perm.canAskAgain) status = (await Notifications.requestPermissionsAsync()).status;
  if (status !== "granted") return "denied";
  if (Platform.OS === "android") await Notifications.setNotificationChannelAsync("default", { name: "IDLE 1", importance: Notifications.AndroidImportance.DEFAULT });
  const token = (await Notifications.getDevicePushTokenAsync()).data as string;
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
    if (isExpoGo || Platform.OS === "web") return;
    const sub = Notifications.addNotificationResponseReceivedListener((r) => {
      const url = (r.notification.request.content.data as any)?.action_url;
      if (typeof url === "string") router.push(url as any);
    });
    return () => sub.remove();
  }, [router]);
  return null;
}
