// Eventi & Missioni hub: one place for daily/weekly quests, login calendar, weekly event, dungeons, Titan Hunt, achievements, codex and shop.
import { useRouter } from "expo-router";
import React from "react";
import { ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAchievements, useBoss, useDungeons, useEvents, useMyAlliance, useProfile, useQuests } from "@/src/api/hooks";
import { hubArt } from "@/src/art";
import { useTheme } from "@/src/theme";
import { Loading, ResourceBar, Txt, fmt, fmtDuration } from "@/src/ui";
import { HubTile } from "@/src/ui/HubTile";
import { useCountdown } from "@/src/ui/useCountdown";

export default function EventsHubTab() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: profile } = useProfile();
  const { data: q } = useQuests();
  const { data: e } = useEvents();
  const { data: d } = useDungeons();
  const { data: ach } = useAchievements();
  const { data: mine } = useMyAlliance();
  const { data: boss } = useBoss();
  const ends = useCountdown(e?.event?.ends_at);
  if (!profile) return <Loading />;
  const claimableChests = (k: any) => (k ? k.chests.filter((c: any) => k.points >= c.points && !k.chests_claimed.includes(c.points)).length : 0);
  const dailyBadge = claimableChests(q?.daily);
  const weeklyBadge = claimableChests(q?.weekly);
  const loginBadge = q && !q.login.claimed_today ? "!" : null;
  const achBadge = ach ? ach.achievements.filter((a: any) => a.unlocked && !a.claimed).length : 0;
  const freeLeft = d?.dungeons ? d.dungeons.reduce((s: number, x: any) => s + x.free_left, 0) : 0;
  const returned = e?.active_deployments?.filter((x: any) => x.status !== "running" || new Date(x.ends_at) <= new Date()).length ?? 0;
  const run = boss?.run;
  const bossPct = run ? Math.round((run.hp / run.hp_max) * 100) : null;
  const inAlliance = !!mine?.alliance;
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="events-hub-screen">
      <View style={{ paddingTop: insets.top, backgroundColor: colors.surfaceSecondary }}>
        <ResourceBar resources={profile.resources} compact />
      </View>
      <ScrollView contentContainerStyle={{ padding: 12, paddingBottom: 28, gap: 10 }} showsVerticalScrollIndicator={false}>
        <Txt v="h1">Eventi & Missioni</Txt>
        <Txt v="small" color={colors.muted}>Tutto ciò che ti premia ogni giorno: missioni, calendario, evento della settimana, dungeon e la caccia al Titano.</Txt>

        <Txt v="h2" style={{ marginTop: 4 }}>Missioni</Txt>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
          <HubTile art={hubArt("daily_quests")} icon="clipboard-check" title="Giornaliere" subtitle={q ? `${q.daily.points}/100 punti · reset ${q.daily.resets}` : "…"} badge={dailyBadge || null} onPress={() => router.push("/events/quests")} testID="hub-daily" />
          <HubTile art={hubArt("weekly_quests")} icon="calendar-week" title="Settimanali" subtitle={q ? `${q.weekly.points}/100 punti` : "…"} badge={weeklyBadge || null} onPress={() => router.push("/events/quests")} testID="hub-weekly" />
          <HubTile art={hubArt("login_calendar")} icon="calendar-check" title="Calendario accessi" subtitle={q ? `Giorno ${q.login.cycle_day}/${q.login.cycle_days} · ${q.login.claimed_today ? "ritirato oggi" : "premio da ritirare"}` : "…"} badge={loginBadge} onPress={() => router.push("/events/quests")} testID="hub-login" wide height={104} />
        </View>

        <Txt v="h2" style={{ marginTop: 4 }}>Eventi</Txt>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
          <HubTile art={hubArt("weekly_event")} icon="calendar-star" title={e?.event?.archetype ?? "Evento settimanale"} subtitle={e ? `Termina in ${fmtDuration(ends)} · energia ${e.energy}/${e.energy_max}` : "…"} badge={returned || null} onPress={() => router.push("/events/weekly")} testID="hub-event" wide height={132} />
          <HubTile art={hubArt("dungeons")} icon="door-closed" title="Dungeon" subtitle={d ? (d.unlocked ? `${freeLeft} ingressi gratis oggi · tier max ${d.max_tier}` : `Si sblocca allo stage ${d.unlock_stage}`) : "…"} locked={d ? !d.unlocked : false} onPress={() => router.push("/events/dungeons")} testID="hub-dungeons" />
          <HubTile art={hubArt("titan_hunt")} icon="skull-crossbones" title="Titan Hunt" subtitle={!inAlliance ? "Serve un'alleanza (Castello 8)" : run ? `${boss.titan_family} · PV ${bossPct}% · ${fmt(run.hp)}` : "Nessuna caccia attiva"} badge={run && boss?.my_attacks_today && boss.my_attacks_today.free < boss.rules.free_attacks_per_day ? `${boss.rules.free_attacks_per_day - boss.my_attacks_today.free}` : null} onPress={() => router.push(inAlliance ? "/alliance/boss" : "/social")} testID="hub-titan" />
        </View>

        <Txt v="h2" style={{ marginTop: 4 }}>Collezione</Txt>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
          <HubTile art={hubArt("achievements")} icon="trophy" title="Traguardi" subtitle={ach ? `${ach.achievements.filter((a: any) => a.claimed).length}/${ach.achievements.length} completati` : "…"} badge={achBadge || null} onPress={() => router.push("/events/achievements")} testID="hub-achievements" />
          <HubTile art={hubArt("codex")} icon="book-open-variant" title="Codex" subtitle="Mostri, regioni, equipaggiamento" onPress={() => router.push("/events/codex")} testID="hub-codex" />
          <HubTile art={hubArt("shop")} icon="storefront" title="Negozio" subtitle="Skin del Lord e del Castello · Rubini · Pass" onPress={() => router.push("/shop")} testID="hub-shop" wide height={120} />
        </View>
      </ScrollView>
    </View>
  );
}
