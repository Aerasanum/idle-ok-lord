// Game audio: region music loops + battle SFX (procedural assets from backend/scripts/gen_audio.py) via expo-audio.
// Volumes live in memory for instant response, are cached locally and mirrored to the server profile (settings.music_volume / sfx_volume).
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { Platform } from "react-native";

import { api } from "@/src/api/client";
import { AUDIO } from "./manifest";

export type SfxName = "hit" | "kill" | "crit" | "skill" | "victory" | "defeat" | "coin" | "ui_tap" | "build";

const STORAGE_KEY = "idle1.audio.volumes";
const state = { music: 0.6, sfx: 0.8, ready: false, region: 0 };
const listeners = new Set<() => void>();
let musicPlayer: AudioPlayer | null = null;
let musicToken: number | null = null;
const sfxPool = new Map<SfxName, AudioPlayer[]>();
let lastSfxAt: Record<string, number> = {};
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function notify() {
  listeners.forEach((l) => l());
}

export function subscribeAudio(l: () => void) {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

export function getVolumes() {
  return { music: state.music, sfx: state.sfx };
}

/** Load cached volumes (local first, then server profile values when they arrive). Idempotent. */
export async function initAudio(fromProfile?: { music_volume?: number; sfx_volume?: number }) {
  if (!state.ready) {
    state.ready = true;
    try {
      await setAudioModeAsync({ playsInSilentMode: true, interruptionMode: "mixWithOthers", shouldPlayInBackground: false });
    } catch (e: any) {
      console.warn("audio mode", e?.message);
    }
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) {
        const v = JSON.parse(raw);
        if (typeof v.music === "number") state.music = v.music;
        if (typeof v.sfx === "number") state.sfx = v.sfx;
      }
    } catch {
      /* ignore */
    }
  }
  if (fromProfile) {
    if (typeof fromProfile.music_volume === "number") state.music = fromProfile.music_volume;
    if (typeof fromProfile.sfx_volume === "number") state.sfx = fromProfile.sfx_volume;
  }
  applyMusicVolume();
  notify();
}

export function setVolumes(v: { music?: number; sfx?: number }) {
  if (typeof v.music === "number") state.music = Math.max(0, Math.min(1, v.music));
  if (typeof v.sfx === "number") state.sfx = Math.max(0, Math.min(1, v.sfx));
  applyMusicVolume();
  notify();
  AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ music: state.music, sfx: state.sfx })).catch(() => {});
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    api.patch("/account/settings", { music_volume: state.music, sfx_volume: state.sfx }).catch(() => {});
  }, 700);
}

function applyMusicVolume() {
  if (musicPlayer) {
    musicPlayer.volume = state.music;
    if (state.music <= 0 && musicPlayer.playing) musicPlayer.pause();
    else if (state.music > 0 && !musicPlayer.playing) musicPlayer.play();
  }
}

/** Start (or switch to) the region loop. Same region keeps playing. */
export function playRegionMusic(region: number) {
  const key = `music/region_${Math.max(1, Math.min(10, region))}`;
  const token = AUDIO[key];
  if (!token) return;
  if (musicToken === token && musicPlayer) return;
  stopMusic();
  try {
    musicPlayer = createAudioPlayer(token);
    musicPlayer.loop = true;
    musicPlayer.volume = state.music;
    musicToken = token;
    state.region = region;
    if (state.music > 0) musicPlayer.play();
  } catch (e: any) {
    console.warn("music", e?.message);
  }
}

export function stopMusic() {
  if (musicPlayer) {
    try {
      musicPlayer.pause();
      musicPlayer.remove();
    } catch {
      /* ignore */
    }
  }
  musicPlayer = null;
  musicToken = null;
}

/** Fire-and-forget SFX with a tiny pool per sound and a 60 ms de-dupe so bursts do not stack into noise. */
export function playSfx(name: SfxName, gain = 1) {
  if (state.sfx <= 0) return;
  const token = AUDIO[`sfx/${name}`];
  if (!token) return;
  const now = Date.now();
  if (now - (lastSfxAt[name] ?? 0) < 60) return;
  lastSfxAt[name] = now;
  try {
    let pool = sfxPool.get(name);
    if (!pool) {
      pool = [];
      sfxPool.set(name, pool);
    }
    let p = pool.find((x) => !x.playing);
    if (!p) {
      if (pool.length >= 3) p = pool[0];
      else {
        p = createAudioPlayer(token);
        pool.push(p);
      }
    }
    p.volume = Math.max(0, Math.min(1, state.sfx * gain));
    p.seekTo(0).catch(() => {});
    p.play();
  } catch (e: any) {
    if (Platform.OS === "web") return; // autoplay policies before first gesture
    console.warn("sfx", e?.message);
  }
}

export function resetSfxDedupe() {
  lastSfxAt = {};
}
