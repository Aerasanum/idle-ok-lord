import { useState, useSyncExternalStore } from "react";

const SECOND = 1000;

const listeners = new Set<() => void>();
let nowMs = Date.now();
let timer: ReturnType<typeof setInterval> | null = null;

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  timer ??= setInterval(() => {
    nowMs = Date.now();
    listeners.forEach((l) => l());
  }, SECOND);
  return () => {
    listeners.delete(onChange);
    if (listeners.size === 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  };
}

function snapshot(): number {
  return nowMs;
}

/**
 * The device clock as a reactive value, advanced once per second.
 *
 * Reading `Date.now()` while rendering makes a countdown freeze until something
 * unrelated re-renders the screen. Subscribing instead re-renders on every tick, and a
 * single shared interval serves every countdown on screen.
 */
export function useNow(): number {
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}

/**
 * How far the device clock is behind the server, in milliseconds.
 *
 * `serverTime` is the ISO timestamp a payload was generated with. The difference is
 * measured once per payload and then held: it describes the two clocks, so it must not
 * be recomputed as time passes, or the countdown would stand still.
 */
function useServerSkew(serverTime: string | null | undefined, now: number): number {
  const key = serverTime ?? null;
  const measure = () => (key ? new Date(key).getTime() - now : 0);
  const [anchor, setAnchor] = useState(() => ({ key, skew: measure() }));
  if (anchor.key !== key) {
    setAnchor({ key, skew: measure() });
    return measure();
  }
  return anchor.skew;
}

/** The server clock as a reactive value: the device clock corrected by the measured skew. */
export function useServerNow(serverTime?: string | null): number {
  const now = useNow();
  const skew = useServerSkew(serverTime, now);
  return now + skew;
}

/** Seconds left until `endsAt`, never negative. */
export function useCountdown(endsAt: string | null | undefined, serverTime?: string | null): number {
  const now = useNow();
  const skew = useServerSkew(serverTime, now);
  if (!endsAt) return 0;
  return Math.max(0, Math.floor((new Date(endsAt).getTime() - (now + skew)) / SECOND));
}

/** Seconds between now and `at`; negative once `at` is in the past. */
export function useSecondsUntil(at: string | null | undefined): number {
  const now = useNow();
  if (!at) return 0;
  return (new Date(at).getTime() - now) / SECOND;
}
