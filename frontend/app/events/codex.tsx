import React from "react";
import { View } from "react-native";

import { QK, useAction, useCodex } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Loading, Panel, Progress, Row, Screen, Txt } from "@/src/ui";

const TRACK: Record<string, string> = { regions: "Regioni", monster_families: "Famiglie di mostri", bosses: "Boss", units: "Unità", gear_rarities: "Rarità" };

export default function CodexScreen() {
  const { colors } = useTheme();
  const { data: c, isLoading } = useCodex();
  const claim = useAction("post", "/codex/claim", [QK.codex], { success: (d) => `+${d.rubies} Rubini` });
  if (isLoading || !c) return <Loading />;
  return (
    <Screen title="Codex" subtitle={`Completamento ${c.completion_pct}%`} testID="codex-screen">
      <Progress value={c.completion_pct} max={100} />
      <Row style={{ justifyContent: "space-between" }}>
        {c.milestones.map((m: any) => <Btn key={m.pct} title={m.claimed ? `${m.pct}% ✓` : `${m.pct}% · ${m.rubies}`} small variant={m.unlocked && !m.claimed ? "gold" : "secondary"} disabled={!m.unlocked || m.claimed} onPress={() => claim.mutate({ pct: m.pct })} testID={`codex-claim-${m.pct}`} />)}
      </Row>
      {Object.entries(c.tracks).map(([k, t]: any) => (
        <Panel key={k} testID={`codex-${k}`}>
          <Txt v="h3">{TRACK[k]} · {t.discovered.length}/{t.entries.length}</Txt>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
            {t.entries.map((e: string) => {
              const found = t.discovered.includes(e);
              return <View key={e} style={{ paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, borderWidth: 1, borderColor: found ? colors.gold : colors.iron, backgroundColor: found ? colors.surfaceTertiary : "transparent" }}><Txt v="small" color={found ? colors.onSurface : colors.muted}>{found ? e : "???"}</Txt></View>;
            })}
          </View>
        </Panel>
      ))}
    </Screen>
  );
}
