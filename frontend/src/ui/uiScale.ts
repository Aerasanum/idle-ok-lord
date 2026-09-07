// Global UI zoom for text pages (0.85×–1.4×). Persisted locally; every Txt scales its font size with it.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useSyncExternalStore } from "react";

const KEY = "idle1.ui.scale";
export const UI_SCALE_MIN = 0.85, UI_SCALE_MAX = 1.4, UI_SCALE_STEP = 0.1;
let scale = 1;
let loaded = false;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function getUiScale() {
  return scale;
}

export function setUiScale(v: number) {
  const next = Math.round(Math.max(UI_SCALE_MIN, Math.min(UI_SCALE_MAX, v)) * 100) / 100;
  if (next === scale) return;
  scale = next;
  emit();
  AsyncStorage.setItem(KEY, String(scale)).catch(() => {});
}

export function stepUiScale(dir: 1 | -1) {
  setUiScale(Math.round((scale + dir * UI_SCALE_STEP) * 100) / 100);
}

export async function loadUiScale() {
  if (loaded) return;
  loaded = true;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    const v = raw ? parseFloat(raw) : NaN;
    if (!Number.isNaN(v)) {
      scale = Math.max(UI_SCALE_MIN, Math.min(UI_SCALE_MAX, v));
      emit();
    }
  } catch {
    /* ignore */
  }
}

export function useUiScale() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
    getUiScale,
    getUiScale,
  );
}
