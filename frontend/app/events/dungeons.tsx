import React, { useState } from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useDungeons } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, IconName, Loading, Panel, Row, Screen, Txt, fmt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

const ICON: Record<string, IconName> = { treasury_vault: "treasure-chest", forge_depths: "anvil", ancient_ruins: "pillar", monster_hunt: "paw" };

export default function DungeonsScreen() {
  const { colors } = useTheme();
  const { data: d, isLoading } = useDungeons();
  const [tier, setTier] = useState<Record<string, number>>({});
  const start = useAction("post", "/dungeons/start", [QK.dungeons], { success: () => "Spedizione nel dungeon avviata" });
  const claim = useAction("post", "/dungeons/claim", [QK.dungeons, QK.inventory], { success: (r) => `Bottino: ${Object.entries(r.granted).map(([k, v]) => `${v} ${k}`).join(", ")}${r.xp ? ` · ${fmt(r.xp)} XP` : ""}` });
  const speed = useAction("post", "/dungeons/speedup", [QK.dungeons], { success: (r) => `Completato (-${r.rubies_spent} Rubini)` });
  if (isLoading || !d) return <Loading />;
  return (
    <Screen title="Dungeon" subtitle={d.unlocked ? `Tier max ${d.max_tier}/${d.tiers} · run ${d.run_minutes} min · reset ${d.daily_reset}` : `Si sbloccano allo stage ${d.unlock_stage}`} testID="dungeons-screen">
      {d.active_runs.map((r: any) => <Run key={r.id} r={r} onClaim={() => claim.mutate({ id: r.id })} onSpeed={() => speed.mutate({ id: r.id })} />)}
      {d.dungeons.map((x: any) => {
        const t = tier[x.key] ?? Math.max(1, d.max_tier);
        return (
          <Panel key={x.key} variant={d.unlocked ? "iron" : "wood"} testID={`dungeon-${x.key}`}>
            <Row style={{ gap: 12 }}>
              <Icon name={ICON[x.key]} size={30} color={colors.goldBright} />
              <View style={{ flex: 1 }}>
                <Txt v="h3">{x.name}</Txt>
                <Txt v="small" color={colors.muted}>{x.rewards}</Txt>
                <Txt v="small" color={colors.muted}>{x.formula}</Txt>
              </View>
            </Row>
            <Row style={{ justifyContent: "space-between", marginTop: 8 }}>
              <Row>
                <Pressable onPress={() => setTier({ ...tier, [x.key]: Math.max(1, t - 1) })} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID={`tier-minus-${x.key}`}><Icon name="minus" /></Pressable>
                <Txt v="num">Tier {t}</Txt>
                <Pressable onPress={() => setTier({ ...tier, [x.key]: Math.min(d.max_tier, t + 1) })} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID={`tier-plus-${x.key}`}><Icon name="plus" /></Pressable>
              </Row>
              <View style={{ alignItems: "flex-end" }}>
                <Btn title={x.free_left > 0 ? `Entra (gratis ${x.free_left})` : x.paid_left > 0 ? `Entra (${d.paid_entry_rubies} Rubini)` : "Esaurito"} small disabled={!d.unlocked || d.max_tier < 1 || (x.free_left <= 0 && x.paid_left <= 0) || d.active_runs.length > 0} loading={start.isPending} onPress={() => start.mutate({ key: x.key, tier: t })} testID={`dungeon-start-${x.key}`} />
                <Txt v="small" color={colors.muted}>Gratis {x.free_used}/2 · Extra {x.paid_used}/3</Txt>
              </View>
            </Row>
          </Panel>
        );
      })}
    </Screen>
  );
}

function Run({ r, onClaim, onSpeed }: { r: any; onClaim: () => void; onSpeed: () => void }) {
  const { colors } = useTheme();
  const left = useCountdown(r.ends_at);
  return (
    <Panel variant="parchment" testID={`dungeon-run-${r.id}`}>
      <Row style={{ justifyContent: "space-between" }}>
        <View>
          <Txt v="h3" color={colors.onSurfaceInverse}>{r.dungeon.replace("_", " ")} · Tier {r.tier}</Txt>
          <Txt v="small" color={colors.onSurfaceInverse}>{left > 0 ? `In corso: ${fmtDuration(left)}` : "Completato: riscatta"}</Txt>
        </View>
        {left > 0 ? <Btn title={`Subito (${Math.max(5, Math.ceil(left / 60 / 3))})`} small variant="ghost" icon="diamond-stone" onPress={onSpeed} testID="dungeon-speedup-button" /> : <Btn title="Riscatta" small onPress={onClaim} testID="dungeon-claim-button" />}
      </Row>
    </Panel>
  );
}
