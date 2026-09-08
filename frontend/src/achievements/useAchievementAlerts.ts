// Watches the achievements list: a toast fires the first time an achievement becomes claimable (persisted per player so it
// never repeats), and the number of claimable achievements feeds the dot on the Eventi tab / hub tile.
import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/src/api/client";
import { QK } from "@/src/api/hooks";
import { useToast } from "@/src/ui/Toast";
import { storage } from "@/src/utils/storage";

const KEY = (pid: string) => `idle1.ach.notified.${pid}`;

export function useAchievementAlerts(playerId?: string | null): number {
  const toast = useToast();
  const { data } = useQuery({ queryKey: QK.achievements, queryFn: () => api.get("/achievements"), enabled: !!playerId, refetchInterval: 30000 });
  const notified = useRef<Set<string> | null>(null);
  const loadedFor = useRef<string | null>(null);
  const claimable: any[] = data ? data.achievements.filter((a: any) => a.unlocked && !a.claimed) : [];

  useEffect(() => {
    if (!playerId || !data) return;
    let cancelled = false;
    (async () => {
      if (loadedFor.current !== playerId) {
        const raw = await storage.getItem<string>(KEY(playerId), "");
        if (cancelled) return;
        notified.current = new Set(String(raw ?? "").split(",").filter(Boolean));
        loadedFor.current = playerId;
        if (raw === "" || raw === null) {
          // first run on this device: don't spam the whole backlog, only announce future unlocks
          claimable.forEach((a) => notified.current!.add(a.key));
          await storage.setItem(KEY(playerId), Array.from(notified.current).join(","));
          return;
        }
      }
      const fresh = claimable.filter((a) => !notified.current!.has(a.key));
      if (!fresh.length) return;
      fresh.forEach((a) => notified.current!.add(a.key));
      await storage.setItem(KEY(playerId), Array.from(notified.current!).join(","));
      if (cancelled) return;
      const first = fresh[0];
      toast.show(fresh.length === 1 ? `🏆 Impresa completata: ${first.title} — ritira ${first.rubies} Rubini in Eventi › Traguardi` : `🏆 ${fresh.length} imprese completate (${first.title}…) — ritira i Rubini in Eventi › Traguardi`, "success");
    })();
    return () => { cancelled = true; };
  }, [playerId, data]); // eslint-disable-line react-hooks/exhaustive-deps

  return claimable.length;
}
