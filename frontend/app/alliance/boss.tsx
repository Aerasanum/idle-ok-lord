import React, { useState } from "react";
import { Image, Pressable, View } from "react-native";

import { QK, useAction, useBoss, useProfile } from "@/src/api/hooks";
import { monsterArt } from "@/src/art";
import { useTheme } from "@/src/theme";
import { TitanStage } from "@/src/titan/TitanStage";
import { Btn, Icon, Loading, Panel, Progress, RES_LABEL, Row, Screen, Txt, fmt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

export default function BossScreen() {
  const { colors } = useTheme();
  const { data: b, isLoading } = useBoss();
  const { data: profile } = useProfile();
  const [tier, setTier] = useState(1);
  const [strike, setStrike] = useState<{ tick: number; damage?: number }>({ tick: 0 });
  const start = useAction("post", "/alliance-boss/start", [QK.boss], { success: () => "Titan Hunt iniziata!" });
  const attack = useAction("post", "/alliance-boss/attack", [QK.boss], { success: (d) => `${fmt(d.damage)} danni${d.killed ? " — TITANO ABBATTUTO!" : ""}` });
  const ends = useCountdown(b?.run?.ends_at, b?.server_time);
  if (isLoading || !b) return <Loading />;
  if (!b.alliance_id) return <Screen title="Titan Hunt" testID="boss-screen"><Txt v="body">Serve un&apos;alleanza per la caccia al Titano.</Txt></Screen>;
  const r = b.run;
  const officer = b.my_role === "leader" || b.my_role === "officer";
  const rules = b.rules;
  const dealt = r ? r.hp_max - Math.max(0, r.hp) : 0;
  const pct = r ? (100 * dealt) / r.hp_max : 0;
  const mine = b.my_attacks_today;
  const left = rules.free_attacks_per_day - mine.free;
  const paidLeft = rules.paid_extra_attacks_cap_per_day - mine.paid;
  const board: any[] = b.leaderboard ?? [];
  const top = board[0]?.damage ?? 1;
  const doAttack = () => attack.mutate({}, { onSuccess: (d: any) => setStrike((s) => ({ tick: s.tick + 1, damage: d.damage })) });
  const equipped: Record<string, any> = {};
  for (const it of profile?.equipped_items ?? []) equipped[it.slot] = it;
  return (
    <Screen title={rules.name} subtitle={r ? `Tier ${r.tier} · ${b.titan_family} · ${r.status === "active" ? `termina in ${fmtDuration(ends)}` : r.status === "killed" ? "abbattuto" : r.status}` : "Nessuna caccia attiva"} testID="boss-screen">
      {r ? (
        <>
          <TitanStage family={b.titan_family} tier={r.tier} hpPct={100 - pct} strikeTick={strike.tick} lastDamage={strike.damage} killed={r.status === "killed"} equipped={equipped} />
          <Panel variant="wood" testID="boss-panel">
            <Progress value={Math.max(0, r.hp)} max={r.hp_max} color={colors.error} height={16} label={`HP ${fmt(Math.max(0, r.hp))} / ${fmt(r.hp_max)} · ${pct.toFixed(1)}% inflitto`} testID="boss-hp" />
            <Row style={{ justifyContent: "space-between", marginTop: 6 }}>
              {rules.alliance_kill_chest_thresholds_pct.map((t: number) => <View key={t} style={{ alignItems: "center" }}><Icon name={r.thresholds_hit?.includes(t) ? "treasure-chest" : "treasure-chest-outline"} size={20} color={r.thresholds_hit?.includes(t) ? colors.goldBright : colors.muted} /><Txt v="small">{t}%</Txt></View>)}
            </Row>
            <Row style={{ justifyContent: "space-between", marginTop: 10 }}>
              <View style={{ flex: 1 }}>
                <Txt v="small">Attacchi oggi: gratis {mine.free}/{rules.free_attacks_per_day} · extra {mine.paid}/{rules.paid_extra_attacks_cap_per_day}</Txt>
                <Txt v="small" color={colors.muted}>Danno = potenza campagna ×4 · +{rules.personal_attack_reward.forge_dust} polvere, +{rules.personal_attack_reward.war_coins} monete a colpo</Txt>
              </View>
              <Btn title={left > 0 ? "Attacca" : paidLeft > 0 ? `Attacca (${rules.extra_attack_rubies})` : "Esaurito"} icon="sword" disabled={r.status !== "active" || (left <= 0 && paidLeft <= 0)} loading={attack.isPending} onPress={doAttack} testID="boss-attack-button" />
            </Row>
            <Txt v="small" color={colors.muted} style={{ marginTop: 6 }}>Il mio danno: {fmt(b.my_damage)} · Cacciatori {r.participants?.length ?? 0} · Ricompensa uccisione: {Object.entries(rules.kill_reward_per_participant).map(([k, v]) => `${v} ${RES_LABEL[k] ?? k}`).join(", ")}</Txt>
          </Panel>
          <Panel testID="titan-leaderboard">
            <Row style={{ justifyContent: "space-between" }}>
              <Txt v="h3">Classifica cacciatori</Txt>
              <Row gap={4}><Icon name="sync" size={12} color={colors.muted} /><Txt v="caption">live</Txt></Row>
            </Row>
            {board.length === 0 ? <Txt v="small" color={colors.muted}>Nessun colpo ancora. Sii il primo a colpire il Titano!</Txt> : null}
            {board.map((h) => {
              const me = h.player_id === b.my_player_id;
              return (
                <View key={h.player_id} style={{ marginTop: 8, gap: 3 }} testID={`hunter-${h.player_id}`}>
                  <Row style={{ justifyContent: "space-between" }}>
                    <Row gap={6}>
                      <View style={{ width: 24, height: 24, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: h.rank === 1 ? colors.gold : h.rank <= 3 ? colors.iron : colors.surfaceTertiary, borderWidth: 1, borderColor: colors.wood }}>
                        <Txt v="small" color={h.rank === 1 ? colors.onBrandSecondary : colors.onSurface} style={{ fontSize: 10 }}>{h.rank}</Txt>
                      </View>
                      <Txt v={me ? "bodyBold" : "body"} color={me ? colors.goldBright : colors.onSurface}>{h.display_name}{h.hero_level ? ` L${h.hero_level}` : ""}{me ? " (tu)" : ""}</Txt>
                    </Row>
                    <Txt v="bodyBold" color={colors.res_gold}>{fmt(h.damage)}</Txt>
                  </Row>
                  <View style={{ height: 8, borderRadius: 4, backgroundColor: colors.scrim, overflow: "hidden", borderWidth: 1, borderColor: colors.wood }}>
                    <View style={{ width: `${Math.max(3, (100 * h.damage) / Math.max(1, top))}%`, height: "100%", backgroundColor: h.rank === 1 ? colors.goldBright : me ? colors.brandPrimary : colors.error }} />
                  </View>
                  <Txt v="caption" color={colors.muted}>{h.attacks} colpi · {h.share_pct}% del danno totale</Txt>
                </View>
              );
            })}
          </Panel>
        </>
      ) : null}
      {(!r || r.status !== "active") && officer ? (
        <Panel testID="boss-start-panel">
          <Txt v="h3">Avvia una caccia (48h)</Txt>
          <Row style={{ marginTop: 8, gap: 12 }}>
            <View style={{ width: 96, height: 96, borderRadius: 8, backgroundColor: colors.surfaceTertiary, borderWidth: 1, borderColor: colors.wood, alignItems: "center", justifyContent: "center" }}>
              {monsterArt(b.tier_families[tier]) ? <Image source={monsterArt(b.tier_families[tier])!} style={{ width: 90, height: 90 }} resizeMode="contain" testID="titan-preview" /> : null}
            </View>
            <View style={{ flex: 1, gap: 6 }}>
              <Txt v="bodyBold">{b.tier_families[tier]}</Txt>
              <Row>
                <Pressable onPress={() => setTier(Math.max(1, tier - 1))} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID="boss-tier-minus"><Icon name="minus" /></Pressable>
                <Txt v="num">Tier {tier}</Txt>
                <Pressable onPress={() => setTier(Math.min(10, tier + 1))} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID="boss-tier-plus"><Icon name="plus" /></Pressable>
              </Row>
              <Txt v="small" color={colors.muted}>HP Titano: {fmt(b.tier_hp[tier])}</Txt>
            </View>
          </Row>
          <Btn title="Inizia la caccia" icon="paw" loading={start.isPending} onPress={() => start.mutate({ tier })} testID="boss-start-button" style={{ marginTop: 8 }} />
        </Panel>
      ) : !r ? <Txt v="small" color={colors.muted}>Solo leader e ufficiali possono avviare la caccia.</Txt> : null}
    </Screen>
  );
}
