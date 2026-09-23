// "Cosa fare adesso": the few taps that are worth the most right now, so nothing that regenerates is wasted.
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { Pressable, View } from "react-native";

import { useDungeons, useEvents, useProfile, useQuests } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Icon, IconName, Panel, RES_LABEL, Row, Txt } from "@/src/ui";

type Action = { key: string; icon: IconName; title: string; hint: string; href: string; urgent?: boolean };

const MAX_SHOWN = 3;
const STOCKS = ["grain", "wood", "clay", "iron"];
const FULL_AT = 0.95;

function chestCount(track: any): number {
  if (!track) return 0;
  return (track.chests ?? []).filter((c: any, i: number) => track.points >= c.points && !track.chests_claimed.includes(i)).length;
}

/** Everything the player could collect right now, most wasteful first. */
export function nextActions(profile: any, quests: any, dungeons: any, events: any, now: number): Action[] {
  const out: Action[] = [];
  const running = (dungeons?.active_runs ?? []).filter((r: any) => new Date(r.ends_at).getTime() > now);
  const done = (dungeons?.active_runs ?? []).length - running.length;
  if (done > 0) out.push({ key: "dungeon-done", icon: "treasure-chest", title: "Dungeon completato", hint: "Riscuoti il bottino e fai ripartire una spedizione", href: "/events/dungeons", urgent: true });

  const cap = profile?.warehouse_capacity ?? 0;
  const full = cap ? STOCKS.filter((r) => (profile.resources?.[r] ?? 0) >= cap * FULL_AT) : [];
  if (full.length) out.push({ key: "warehouse", icon: "warehouse", title: "Magazzino al limite", hint: `${full.map((r) => RES_LABEL[r]).join(", ")}: la produzione in eccesso va persa. Potenzia il Magazzino o spendi.`, href: "/(tabs)/kingdom", urgent: true });

  const off = profile?.offline_preview;
  if (off?.full) out.push({ key: "offline-full", icon: "treasure-chest", title: "Cassa offline piena", hint: `${off.max_hours} ore accumulate: finché non la riscuoti non guadagni più`, href: "/offline", urgent: true });
  else if (off?.claimable && (off?.hours ?? 0) >= 1) out.push({ key: "offline", icon: "treasure-chest", title: "Cassa offline pronta", hint: `${Math.floor(off.hours)} ore da riscuotere`, href: "/offline" });

  if (events && events.energy >= events.energy_max) out.push({ key: "energy", icon: "lightning-bolt", title: "Energia al massimo", hint: `${events.energy}/${events.energy_max}: non rigenera più, spendila nell'evento`, href: "/events/weekly", urgent: true });

  if (quests && !quests.login.claimed_today) {
    const bonus = quests.login.bonus_pct ? ` · +${quests.login.bonus_pct}% dalla serie` : "";
    out.push({ key: "login", icon: "calendar-check", title: "Bonus di accesso da ritirare", hint: `Serie a ${quests.login.streak_if_claimed_today} giorni${bonus}`, href: "/events/quests" });
  }

  const chests = chestCount(quests?.daily) + chestCount(quests?.weekly);
  if (chests > 0) out.push({ key: "chests", icon: "clipboard-check", title: `${chests} ${chests === 1 ? "forziere missioni pronto" : "forzieri missioni pronti"}`, hint: "Punti già guadagnati, ricompense ancora lì", href: "/events/quests" });

  const free = (dungeons?.dungeons ?? []).reduce((n: number, d: any) => n + d.free_left, 0);
  if (dungeons?.unlocked && free > 0 && !running.length && !done) out.push({ key: "dungeon-free", icon: "door-closed", title: `${free} ingressi dungeon gratuiti`, hint: "Scadono alla mezzanotte UTC: risorse e truppe extra", href: "/events/dungeons" });

  return out;
}

/** Wall clock refreshed every 15s: a dungeon that finishes while the tab is open must show up by itself. */
function useNow(): number {
  const [now, setNow] = useState(0);
  useEffect(() => {
    const tick = () => setNow(Date.now());
    tick();
    const id = setInterval(tick, 15000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export function NextActions() {
  const { colors } = useTheme();
  const router = useRouter();
  const { data: profile } = useProfile();
  const { data: quests } = useQuests();
  const { data: dungeons } = useDungeons();
  const { data: events } = useEvents();
  const now = useNow();
  if (!profile) return null;
  const all = nextActions(profile, quests, dungeons, events, now);
  const shown = all.slice(0, MAX_SHOWN);
  return (
    <Panel style={{ marginHorizontal: 12, marginTop: 12 }} testID="next-actions">
      <Row style={{ justifyContent: "space-between" }}>
        <Txt v="h3">Cosa fare adesso</Txt>
        {all.length > MAX_SHOWN ? <Txt v="caption" testID="next-actions-more">+{all.length - MAX_SHOWN} altre</Txt> : null}
      </Row>
      {shown.length ? (
        <View style={{ gap: 6, marginTop: 6 }}>
          {shown.map((a) => (
            <Pressable
              key={a.key}
              onPress={() => router.push(a.href as any)}
              testID={`next-action-${a.key}`}
              style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10, minHeight: 48, paddingHorizontal: 8, borderRadius: 6, borderWidth: 1, borderColor: a.urgent ? colors.burgundy : colors.wood, backgroundColor: colors.surfaceTertiary, opacity: pressed ? 0.8 : 1 })}
            >
              <Icon name={a.icon} size={22} color={a.urgent ? colors.goldBright : colors.brandSecondary} />
              <View style={{ flex: 1, paddingVertical: 6 }}>
                <Txt v="bodyBold" color={a.urgent ? colors.goldBright : colors.onSurface}>{a.title}</Txt>
                <Txt v="small" color={colors.muted}>{a.hint}</Txt>
              </View>
              <Icon name="chevron-right" size={20} color={colors.gold} />
            </Pressable>
          ))}
        </View>
      ) : (
        <Txt v="small" color={colors.muted} testID="next-actions-empty">Sei in pari: niente da riscuotere e nulla che stia andando sprecato.</Txt>
      )}
    </Panel>
  );
}
