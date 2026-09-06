import React, { useMemo, useState } from "react";
import { View } from "react-native";

import { QK, useAction, useProfile, useResearch } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Chip, ChipRow, Icon, Loading, Panel, Res, Row, Screen, Txt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

const BRANCH_LABEL: Record<string, string> = { economy: "Economia", military: "Militare", siege: "Assedio", beasts: "Bestie", mythic: "Mitico", defense: "Difesa", alliance: "Alleanza", idle: "Idle" };

export default function ResearchScreen() {
  const { colors } = useTheme();
  const { data: r, isLoading } = useResearch();
  const { data: profile } = useProfile();
  const [branch, setBranch] = useState("economy");
  const start = useAction("post", "/research/start", [QK.research, QK.kingdom], { success: () => "Ricerca avviata" });
  const nodes = useMemo(() => (r?.nodes ?? []).filter((n: any) => n.branch === branch), [r, branch]);
  if (isLoading || !r || !profile) return <Loading />;
  const canAfford = (cost: Record<string, number>) => Object.entries(cost).every(([k, v]) => (profile.resources[k] ?? 0) >= v);
  const busy = r.queue.length > 0;
  return (
    <Screen title="Ricerca" subtitle={`Università · ${r.queue.length}/1 in corso`} scroll testID="research-screen">
      <View style={{ marginHorizontal: -16 }}>
        <ChipRow>{r.branches.map((b: string) => <Chip key={b} label={BRANCH_LABEL[b] ?? b} selected={branch === b} onPress={() => setBranch(b)} testID={`branch-${b}`} />)}</ChipRow>
      </View>
      {r.queue.map((q: any) => <ActiveResearch key={q.id} q={q} serverTime={r.server_time} />)}
      {nodes.map((n: any) => (
        <Panel key={n.key} variant={n.unlocked ? "iron" : "wood"} testID={`node-${n.key}`}>
          <Row style={{ justifyContent: "space-between" }}>
            <View style={{ flex: 1 }}>
              <Txt v="h3">{n.name} · {n.level}/{n.max_level}</Txt>
              <Txt v="small" color={colors.muted}>{n.effect_key.replace(/_/g, " ")}: +{n.effect_per_level_pct}%/liv · attuale +{n.effect_total_pct}%</Txt>
              {!n.unlocked ? <Txt v="small" color={colors.warning}>Richiede Castello {n.unlock_castle_level}</Txt> : null}
            </View>
            <Row style={{ gap: 3 }}>{Array.from({ length: n.max_level }).map((_, i) => <View key={i} style={{ width: 8, height: 14, borderRadius: 2, backgroundColor: i < n.level ? colors.goldBright : colors.surfaceTertiary }} />)}</Row>
          </Row>
          {n.next ? (
            <Row style={{ justifyContent: "space-between", marginTop: 8 }}>
              <Row style={{ flexWrap: "wrap", flex: 1 }}>
                {Object.entries(n.next.cost).filter(([, v]) => (v as number) > 0).map(([k, v]) => <Res key={k} kind={k} value={v as number} size={12} />)}
                <Row gap={3}><Icon name="clock-outline" size={12} color={colors.muted} /><Txt v="small" color={colors.muted}>{fmtDuration(n.next.time_minutes * 60)}</Txt></Row>
              </Row>
              <Btn title={n.in_queue ? "In corso" : "Avvia"} small disabled={!n.unlocked || busy || !canAfford(n.next.cost)} loading={start.isPending} onPress={() => start.mutate({ node: n.key })} testID={`research-start-${n.key}`} />
            </Row>
          ) : <Txt v="small" color={colors.goldBright}>Massimo</Txt>}
        </Panel>
      ))}
    </Screen>
  );
}

function ActiveResearch({ q, serverTime }: { q: any; serverTime: string }) {
  const left = useCountdown(q.ends_at, serverTime);
  const { colors } = useTheme();
  return (
    <Panel variant="parchment" testID="active-research">
      <Txt v="bodyBold" color={colors.onSurfaceInverse}>In corso: {q.node} → livello {q.target_level}</Txt>
      <Txt v="small" color={colors.onSurfaceInverse}>{left > 0 ? fmtDuration(left) : "completata — aggiornamento…"}</Txt>
    </Panel>
  );
}
