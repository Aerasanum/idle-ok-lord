// Remote-push adapter (I15). `expo-notifications` is loaded lazily and ONLY where remote push is supported:
// Expo Go (SDK 53+) throws at import time on Android, so a static import would crash the whole app before any guard runs.
// Web and Expo Go get a no-op (the in-app Inbox keeps working through the backend); dev/production builds get the real module.
import Constants, { ExecutionEnvironment } from "expo-constants";
import { Platform } from "react-native";

export type NotificationsModule = typeof import("expo-notifications");

export const IS_EXPO_GO = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
export const REMOTE_PUSH_SUPPORTED = Platform.OS !== "web" && !IS_EXPO_GO;

let loader: Promise<NotificationsModule | null> | null = null;

/** Resolves the expo-notifications module in native builds, `null` in Expo Go / web. Never throws. */
export function loadNotifications(): Promise<NotificationsModule | null> {
  if (!REMOTE_PUSH_SUPPORTED) return Promise.resolve(null);
  if (!loader) {
    loader = import("expo-notifications").catch((e: any) => {
      console.warn("expo-notifications unavailable in this runtime:", e?.message);
      return null;
    });
  }
  return loader;
}
