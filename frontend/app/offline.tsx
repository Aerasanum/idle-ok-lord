import { useRouter } from "expo-router";
import React, { useState } from "react";

import { QK, useAction, useOffline } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Progress, RARITY_LABEL, Res, Row, SLOT_LABEL, Screen, Stat, Txt, fmt } from "@/src/ui";

export default function OfflineScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { data: o, isLoading } = useOffline();
  const [result, setResult] = useState<any>(null);
  const claim = useAction("post", "/offline/claim", [QK.offline, QK.inventory, QK.kingdom], { success: () => "Forziere riscattato" });
  if (isLoading || !o) return <Loading />;
  const loot = o.battle_loot;
  return (
    <Screen title="Forziere offline" subtitle={`${o.hours.toFixed(2)}h accumulate · max ${o.max_hours}h`} testID="offline-screen">
      <Progress value={o.hours} max={o.max_hours} label={o.full ? "Forziere pieno: riscatta per continuare ad accumulare" : `Accumulo in corso (${Math.round((o.hours / o.max_hours) * 100)}%)`} testID="offline-progress" />
      {result ? (
        <Panel variant="parchment" testID="offline-result">
          <Txt v="h2" color={colors.onSurfaceInverse}>Riscattato!</Txt>
          <Txt v="small" color={colors.onSurfaceInverse}>{result.hours.toFixed(2)} ore · {fmt(result.kills)} nemici · {fmt(result.xp)} XP{result.levels_gained ? ` · +${result.levels_gained} livelli` : ""}</Txt>
          <Row style={{ flexWrap: "wrap", gap: 12, marginTop: 6 }}>
            <Res kind="gold" value={result.gold} />
            {Object.entries(result.soft).map(([k, v]) => <Res key={k} kind={k} value={v as number} />)}
          </Row>
          {result.gear?.found?.length ? <Txt v="small" color={colors.onSurfaceInverse}>Equipaggiamento: {result.gear.found.map((g: any) => `${RARITY_LABEL[g.rarity]} ${SLOT_LABEL[g.slot]}`).join(", ")}{result.gear.salvaged.length ? ` (${result.gear.salvaged.length} auto-smantellati)` : ""}</Txt> : null}
          <Btn title="Torna in battaglia" style={{ marginTop: 8 }} onPress={() => router.back()} testID="offline-done-button" />
        </Panel>
      ) : (
        <>
          <Panel testID="offline-battle-loot">
            <Txt v="h3">Bottino di battaglia (70% efficienza)</Txt>
            <Row style={{ justifyContent: "space-around", marginTop: 6 }}>
              <Stat label="XP" value={loot.xp} />
              <Stat label="Oro" value={loot.gold} color={colors.res_gold} />
              <Stat label="Uccisioni" value={loot.kills} />
              <Stat label="Roll equip." value={loot.gear_rolls.toFixed(2)} />
            </Row>
          </Panel>
          <Panel variant="wood" testID="offline-production">
            <Txt v="h3">Produzione del Regno (85%)</Txt>
            <Row style={{ flexWrap: "wrap", gap: 12, marginTop: 6 }}>
              {Object.entries(o.production).map(([k, v]) => <Res key={k} kind={k} value={v as number} />)}
              {!Object.keys(o.production).length ? <Txt v="small" color={colors.muted}>Nessuna produzione offline accumulata (sei stato online).</Txt> : null}
            </Row>
          </Panel>
          {o.completed_timers.length ? (
            <Panel variant="wood" testID="offline-timers">
              <Txt v="h3">Completati mentre eri via</Txt>
              {o.completed_timers.map((t: any, i: number) => <Row key={i}><Icon name="check-circle" size={14} color={colors.success} /><Txt v="small">{t.building ? `${t.building} → Lv ${t.target_level}` : t.node ? `${t.node} → Lv ${t.target_level}` : `${t.quantity} × ${t.unit}`}</Txt></Row>)}
            </Panel>
          ) : null}
          <Btn title="Riscatta il forziere" icon="treasure-chest" disabled={!o.claimable} loading={claim.isPending} onPress={() => claim.mutate({}, { onSuccess: setResult })} testID="offline-claim-button" />
          <Txt v="small" color={colors.muted}>Tempo calcolato dal server: l&apos;orologio del dispositivo non conta. Riscatto singolo e idempotente.</Txt>
        </>
      )}
    </Screen>
  );
}
