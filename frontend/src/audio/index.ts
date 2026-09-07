// Game audio: region music loops (procedural assets from backend/scripts/gen_audio.py) via expo-audio. Music only — no SFX by owner choice.
// Volume lives in memory for instant response, is cached locally and mirrored to the server profile (settings.music_volume).
import AsyncStorage from "@react-native-async-storage/async-storage";
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";

import { api } from "@/src/api/client";
import { AUDIO } from "./manifest";

const STORAGE_KEY = "idle1.audio.volumes";
const state = { music: 0.6, ready: false, region: 0 };
const listeners = new Set<() => void>();
let musicPlayer: AudioPlayer | null = null;
let musicToken: number | null = null;
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
  return { music: state.music };
}

/** Load cached volume (local first, then the server profile value when it arrives). Idempotent. */
export async function initAudio(fromProfile?: { music_volume?: number }) {
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
      }
    } catch {
      /* ignore */
    }
  }
  if (fromProfile && typeof fromProfile.music_volume === "number") state.music = fromProfile.music_volume;
  applyMusicVolume();
  notify();
}

export function setVolumes(v: { music?: number }) {
  if (typeof v.music === "number") state.music = Math.max(0, Math.min(1, v.music));
  applyMusicVolume();
  notify();
  AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ music: state.music })).catch(() => {});
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    api.patch("/account/settings", { music_volume: state.music, sfx_volume: 0 }).catch(() => {});
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
