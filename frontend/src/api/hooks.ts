import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import { useToast } from "@/src/ui/Toast";

export const QK = {
  profile: ["profile"],
  kingdom: ["kingdom"],
  research: ["research"],
  army: ["army"],
  domain: ["domain"],
  inventory: ["inventory"],
  forge: ["forge"],
  hero: ["hero"],
  offline: ["offline"],
  events: ["events"],
  dungeons: ["dungeons"],
  quests: ["quests"],
  achievements: ["achievements"],
  codex: ["codex"],
  season: ["season"],
  alliance: ["alliance"],
  alliances: ["alliances"],
  warMap: ["warMap"],
  wars: ["wars"],
  boss: ["boss"],
  store: ["store"],
  notifications: ["notifications"],
  canon: ["canon"],
  purchases: ["purchases"],
};

export const useProfile = () => useQuery({ queryKey: QK.profile, queryFn: () => api.get("/profile"), staleTime: 5000, refetchInterval: 30000 });
export const useCanon = () => useQuery({ queryKey: QK.canon, queryFn: () => api.get("/canon/static"), staleTime: Infinity });
export const useKingdom = () => useQuery({ queryKey: QK.kingdom, queryFn: () => api.get("/kingdom"), refetchInterval: 15000 });
export const useResearch = () => useQuery({ queryKey: QK.research, queryFn: () => api.get("/research"), refetchInterval: 20000 });
export const useArmy = () => useQuery({ queryKey: QK.army, queryFn: () => api.get("/army"), refetchInterval: 20000 });
export const useDomain = () => useQuery({ queryKey: QK.domain, queryFn: () => api.get("/domain") });
export const useInventory = () => useQuery({ queryKey: QK.inventory, queryFn: () => api.get("/gear/inventory") });
export const useForgeCosts = () => useQuery({ queryKey: QK.forge, queryFn: () => api.get("/forge/costs") });
export const useHero = () => useQuery({ queryKey: QK.hero, queryFn: () => api.get("/hero") });
export const useOffline = () => useQuery({ queryKey: QK.offline, queryFn: () => api.get("/offline") });
export const useEvents = () => useQuery({ queryKey: QK.events, queryFn: () => api.get("/events"), refetchInterval: 20000 });
export const useDungeons = () => useQuery({ queryKey: QK.dungeons, queryFn: () => api.get("/dungeons"), refetchInterval: 20000 });
export const useQuests = () => useQuery({ queryKey: QK.quests, queryFn: () => api.get("/quests") });
export const useAchievements = () => useQuery({ queryKey: QK.achievements, queryFn: () => api.get("/achievements") });
export const useCodex = () => useQuery({ queryKey: QK.codex, queryFn: () => api.get("/codex") });
export const useSeason = () => useQuery({ queryKey: QK.season, queryFn: () => api.get("/season") });
export const useMyAlliance = () => useQuery({ queryKey: QK.alliance, queryFn: () => api.get("/alliances/mine"), refetchInterval: 30000 });
export const useAlliances = (q: string) => useQuery({ queryKey: [...QK.alliances, q], queryFn: () => api.get(`/alliances?q=${encodeURIComponent(q)}`) });
export const useWarMap = () => useQuery({ queryKey: QK.warMap, queryFn: () => api.get("/wars/map"), refetchInterval: 30000 });
export const useWars = () => useQuery({ queryKey: QK.wars, queryFn: () => api.get("/wars"), refetchInterval: 30000 });
export const useWar = (id: string | undefined) => useQuery({ queryKey: [...QK.wars, id], queryFn: () => api.get(`/wars/${id}`), enabled: !!id, refetchInterval: 30000 });
export const useBoss = () => useQuery({ queryKey: QK.boss, queryFn: () => api.get("/alliance-boss"), refetchInterval: 20000 });
export const useStore = () => useQuery({ queryKey: QK.store, queryFn: () => api.get("/store/catalog") });
export const usePurchases = () => useQuery({ queryKey: QK.purchases, queryFn: () => api.get("/account/purchases") });
export const useNotifications = () => useQuery({ queryKey: QK.notifications, queryFn: () => api.get("/notifications"), refetchInterval: 30000 });
export const useChat = (channel: string | null) =>
  useQuery({ queryKey: ["chat", channel], queryFn: () => api.get(`/chat/messages?channel=${encodeURIComponent(channel!)}`), enabled: !!channel, refetchInterval: 4000 });

/** Generic mutation with toast + invalidation. */
export function useAction(method: "post" | "put" | "patch", path: string, invalidate: (readonly string[])[] = [QK.profile], opts?: { silent?: boolean; success?: (d: any) => string | void }) {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (body?: any) => (api as any)[method](path, body),
    onSuccess: (d) => {
      invalidate.forEach((k) => qc.invalidateQueries({ queryKey: k as any }));
      qc.invalidateQueries({ queryKey: QK.profile });
      const msg = opts?.success?.(d);
      if (msg) toast.show(msg, "success");
    },
    onError: (e: any) => {
      if (!opts?.silent) toast.show(e?.message ?? "Errore", "error");
    },
  });
}
