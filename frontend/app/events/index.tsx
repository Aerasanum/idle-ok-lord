import { useRouter } from "expo-router";
import React from "react";
import { View } from "react-native";

import { QK, useAction, useEvents } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Progress, Res, Row, Screen, Txt, fmt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

export default function EventsScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { data: e, isLoading } = useEvents();
  const deploy = useAction("post", "/events/deploy", [QK.events], { success: () => "Spedizione partita" });
  const claim = useAction("post", "/events/claim", [QK.events, QK.inventory], { success: (d) => `+${d.event_tokens} gettoni, +${fmt(d.gold)} oro` });
  const instant = useAction("post", "/events/instant-finish", [QK.events], { success: (d) => `Completata (-${d.rubies_spent} Rubini)` });
  const refill = useAction("post", "/events/refill", [QK.events], { success: (d) => `Energia ${d.energy}` });
  const booster = useAction("post", "/events/booster", [QK.events], { success: () => "Booster PvE attivo 24h" });
  const track = useAction("post", "/events/track/claim", [QK.events, QK.inventory], { success: () => "Ricompensa riscattata" });
  const ends = useCountdown(e?.event?.ends_at);
  if (isLoading || !e) return <Loading />;
  const t = e.track;
  return (
    <Screen title={e.event.archetype} subtitle={`Evento settimanale · termina in ${fmtDuration(ends)}`} testID="events-screen" right={<Btn title="Dungeon" small variant="ghost" onPress={() => router.push("/events/dungeons")} testID="events-dungeons-link" />}>
      <Panel testID="energy-panel">
        <Row style={{ justifyContent: "space-between" }}>
          <Txt v="h3">Energia {e.energy}/{e.energy_max}</Txt>
          <Row>
            <Btn title={`Ricarica ${e.refill.rubies}`} small variant="ghost" icon="diamond-stone" disabled={e.paid_refills_today >= e.refill.paid_refill_daily_cap} onPress={() => refill.mutate({})} testID="refill-button" />
            <Btn title={e.booster_until && new Date(e.booster_until) > new Date() ? "Booster ON" : `Booster ${e.booster.rubies}`} small variant={e.booster_until && new Date(e.booster_until) > new Date() ? "gold" : "ghost"} onPress={() => booster.mutate({})} testID="booster-button" />
          </Row>
        </Row>
        <Progress value={e.energy} max={e.energy_max} label={`+1 ogni ${e.regen_minutes} min · ricariche pagate oggi ${e.paid_refills_today}/${e.refill.paid_refill_daily_cap}`} />
      </Panel>
      {e.active_deployments.map((d: any) => <Deployment key={d.id} d={d} onClaim={() => claim.mutate({ id: d.id })} onInstant={() => instant.mutate({ id: d.id })} />)}
      <Txt v="h2">Spedizioni</Txt>
      {e.deployments_catalog.map((d: any, i: number) => (
        <Panel key={i} variant="wood" testID={`deployment-${i}`}>
          <Row style={{ justifyContent: "space-between" }}>
            <View>
              <Txt v="h3">{d.energy} energia · {fmtDuration(d.duration_minutes * 60)}</Txt>
              <Txt v="small" color={colors.muted}>Ricompense ×{d.reward_multiplier} (gettoni, oro, risorse, roll equipaggiamento)</Txt>
            </View>
            <Btn title="Parti" small disabled={e.energy < d.energy || e.active_deployments.some((x: any) => x.status === "running")} loading={deploy.isPending} onPress={() => deploy.mutate({ index: i })} testID={`deploy-${i}`} />
          </Row>
        </Panel>
      ))}
      <Txt v="h2">Percorso evento · {t.points} punti · tier {t.tier_reached}/{t.tiers}</Txt>
      <Progress value={t.points % t.points_per_tier} max={t.points_per_tier} label={`${t.points_per_tier} gettoni per tier · Event Pass ${e.event_pass_active ? "attivo" : "non attivo"}`} />
      {!e.event_pass_active ? <Btn title="Event Pass nel Negozio" small variant="ghost" onPress={() => router.push("/shop")} testID="event-pass-link" /> : null}
      {Object.entries(t.rewards).map(([tier, rw]) => {
        const r = rw as { free: Record<string, any>; premium: Record<string, any> };
        const n = Number(tier);
        const reached = n <= t.tier_reached;
        return (
          <Row key={tier} style={{ justifyContent: "space-between", paddingVertical: 6, borderBottomWidth: 1, borderColor: colors.divider, opacity: reached ? 1 : 0.6 }} testID={`track-tier-${tier}`}>
            <Txt v="bodyBold" style={{ width: 44 }}>T{tier}</Txt>
            <View style={{ flex: 1 }}>
              <Row style={{ flexWrap: "wrap" }}>{Object.entries(r.free).map(([k, v]) => k === "soft_hours" ? <Txt key={k} v="small">{String(v)}h risorse</Txt> : <Res key={k} kind={k} value={Number(v)} size={12} />)}</Row>
              <Row style={{ flexWrap: "wrap" }}><Icon name="crown" size={12} color={colors.goldBright} />{Object.entries(r.premium).map(([k, v]) => k === "gear_min_rarity" ? (v ? <Txt key={k} v="small" color={colors.goldBright}>equip. {String(v)}+</Txt> : null) : <Res key={k} kind={k} value={Number(v)} size={12} />)}</Row>
            </View>
            <View style={{ gap: 4 }}>
              <Btn title={t.claimed_free.includes(n) ? "✓" : "Free"} small variant="secondary" disabled={!reached || t.claimed_free.includes(n)} onPress={() => track.mutate({ tier: n, premium: false })} testID={`claim-free-${tier}`} />
              <Btn title={t.claimed_premium.includes(n) ? "✓" : "Pass"} small variant="gold" disabled={!reached || !e.event_pass_active || t.claimed_premium.includes(n)} onPress={() => track.mutate({ tier: n, premium: true })} testID={`claim-premium-${tier}`} />
            </View>
          </Row>
        );
      })}
    </Screen>
  );
}

function Deployment({ d, onClaim, onInstant }: { d: any; onClaim: () => void; onInstant: () => void }) {
  const { colors } = useTheme();
  const left = useCountdown(d.ends_at);
  return (
    <Panel variant="parchment" testID={`active-deployment-${d.id}`}>
      <Row style={{ justifyContent: "space-between" }}>
        <View>
          <Txt v="h3" color={colors.onSurfaceInverse}>Spedizione ×{d.multiplier}</Txt>
          <Txt v="small" color={colors.onSurfaceInverse}>{left > 0 ? `Rientro in ${fmtDuration(left)}` : "Rientrata: riscatta il bottino"} · {d.rewards.event_tokens} gettoni · {fmt(d.rewards.gold)} oro</Txt>
        </View>
        {left > 0 ? <Btn title={`Subito (${Math.max(5, Math.ceil(left / 60 / 3))})`} small variant="ghost" icon="diamond-stone" onPress={onInstant} testID="instant-finish-button" /> : <Btn title="Riscatta" small onPress={onClaim} testID="claim-deployment-button" />}
      </Row>
    </Panel>
  );
}
