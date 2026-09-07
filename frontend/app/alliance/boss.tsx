import React, { useState } from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useBoss } from "@/src/api/hooks";
import { MonsterSprite } from "@/src/battle/monsters";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Progress, Row, Screen, Txt, fmt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

export default function BossScreen() {
  const { colors } = useTheme();
  const { data: b, isLoading } = useBoss();
  const [tier, setTier] = useState(1);
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
  return (
    <Screen title={rules.name} subtitle={r ? `Tier ${r.tier} · ${r.status === "active" ? `termina in ${fmtDuration(ends)}` : r.status}` : "Nessuna caccia attiva"} testID="boss-screen">
      {r ? (
        <Panel variant="wood" testID="boss-panel">
          <View style={{ alignItems: "center", paddingVertical: 8 }}>
            <MonsterSprite family="Ancient Titan" type="boss" palette={["#3B0F0C", "#800020", "#B0361D"]} size={140} />
          </View>
          <Progress value={Math.max(0, r.hp)} max={r.hp_max} color={colors.error} height={16} label={`HP ${fmt(Math.max(0, r.hp))} / ${fmt(r.hp_max)} · ${pct.toFixed(1)}% inflitto`} testID="boss-hp" />
          <Row style={{ justifyContent: "space-between", marginTop: 6 }}>
            {rules.alliance_kill_chest_thresholds_pct.map((t: number) => <View key={t} style={{ alignItems: "center" }}><Icon name={r.thresholds_hit?.includes(t) ? "treasure-chest" : "treasure-chest-outline"} size={20} color={r.thresholds_hit?.includes(t) ? colors.goldBright : colors.muted} /><Txt v="small">{t}%</Txt></View>)}
          </Row>
          <Row style={{ justifyContent: "space-between", marginTop: 10 }}>
            <View>
              <Txt v="small">Attacchi oggi: gratis {mine.free}/{rules.free_attacks_per_day} · extra {mine.paid}/{rules.paid_extra_attacks_cap_per_day}</Txt>
              <Txt v="small" color={colors.muted}>Danno = potenza campagna ×4 · +{rules.personal_attack_reward.forge_dust} polvere, +{rules.personal_attack_reward.war_coins} monete a colpo</Txt>
            </View>
            <Btn title={left > 0 ? "Attacca" : paidLeft > 0 ? `Attacca (${rules.extra_attack_rubies})` : "Esaurito"} icon="sword" disabled={r.status !== "active" || (left <= 0 && paidLeft <= 0)} loading={attack.isPending} onPress={() => attack.mutate({})} testID="boss-attack-button" />
          </Row>
          <Txt v="small" color={colors.muted} style={{ marginTop: 6 }}>Il mio danno totale: {fmt(b.my_damage)} · Partecipanti {r.participants?.length ?? 0} · Ricompensa uccisione: {Object.entries(rules.kill_reward_per_participant).map(([k, v]) => `${v} ${k}`).join(", ")}</Txt>
          {r.log?.length ? <View style={{ marginTop: 6 }}>{[...r.log].reverse().slice(0, 8).map((l: any, i: number) => <Txt key={i} v="small" color={colors.muted}>{l.name}: {fmt(l.damage)}</Txt>)}</View> : null}
        </Panel>
      ) : null}
      {(!r || r.status !== "active") && officer ? (
        <Panel testID="boss-start-panel">
          <Txt v="h3">Avvia una caccia (48h)</Txt>
          <Row style={{ justifyContent: "space-between", marginTop: 6 }}>
            <Row>
              <Pressable onPress={() => setTier(Math.max(1, tier - 1))} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID="boss-tier-minus"><Icon name="minus" /></Pressable>
              <Txt v="num">Tier {tier}</Txt>
              <Pressable onPress={() => setTier(Math.min(10, tier + 1))} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID="boss-tier-plus"><Icon name="plus" /></Pressable>
            </Row>
            <Btn title="Inizia" small loading={start.isPending} onPress={() => start.mutate({ tier })} testID="boss-start-button" />
          </Row>
          <Txt v="small" color={colors.muted}>HP Titano tier {tier}: {fmt(b.tier_hp[tier])}</Txt>
        </Panel>
      ) : !r ? <Txt v="small" color={colors.muted}>Solo leader e ufficiali possono avviare la caccia.</Txt> : null}
    </Screen>
  );
}
