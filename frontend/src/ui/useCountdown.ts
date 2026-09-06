import { useEffect, useState } from "react";

/** Server-time aware countdown: `serverTime` is the ISO timestamp the payload was generated with; the device clock is only used for deltas. */
export function useCountdown(endsAt: string | null | undefined, serverTime?: string | null): number {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    if (!endsAt) return setRemaining(0);
    const end = new Date(endsAt).getTime();
    const offset = serverTime ? new Date(serverTime).getTime() - Date.now() : 0;
    const tick = () => setRemaining(Math.max(0, Math.floor((end - (Date.now() + offset)) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [endsAt, serverTime]);
  return remaining;
}
