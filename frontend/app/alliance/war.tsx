import React, { useEffect, useRef, useState } from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useMyAlliance, useWar, useWarMap, useWars } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Row, Screen, Txt, fmt, fmtDuration } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";
import { useCountdown } from "@/src/ui/useCountdown";
import { NODE_LABEL, WarMap, allianceColor } from "@/src/war/WarMap";

const STATUS_LABEL: Record<string, string> = { prep: "Preparazione", locking: "Blocco roster", locked: "Roster bloccato", resolving: "Risoluzione", resolved: "Risolta", cancelled: "Annullata" };

export default function WarScreen() {
  const { colors } = useTheme();
  const { data: m, isLoading } = useWarMap();
  const { data: wars } = useWars();
  const { data: mine } = useMyAlliance();
  const [sel, setSel] = useState<any>(null);
  const [warId, setWarId] = useState<string | undefined>();
  const sheet = useRef<SheetRef>(null);
  const { data: detail } = useWar(warId);
  const declare = useAction("post", "/wars/declare", [QK.warMap, QK.wars], { success: () => "Guerra dichiarata! Preparazione 8h." });
  const roster = useAction("post", "/wars/roster", [QK.wars], { success: () => "Roster aggiornato" });
  const [picked, setPicked] = useState<string[]>([]);
  const myId = mine?.alliance?.id;
  const currentRoster: string[] | undefined = detail ? (detail.war.attacker_id === myId ? detail.war.attack_roster : detail.war.defense_roster) : undefined;
  useEffect(() => { setPicked(currentRoster ?? []); }, [detail?.war?.id, currentRoster?.length]); // eslint-disable-line react-hooks/exhaustive-deps
  if (isLoading || !m) return <Loading label="Carico la mappa del territorio..." />;
  const a = mine?.alliance;
  const officer = a?.my_role === "leader" || a?.my_role === "officer";
  const contested = new Set<number>(m.active_wars.map((w: any) => w.node_id));
  const seasonEnds = new Date(m.season.ends_at).getTime() - Date.now();
  return (
    <Screen title="Territorio" subtitle={`Stagione ${m.season.key} · termina in ${fmtDuration(seasonEnds / 1000)} · shard ${m.shard_id.slice(-6)}`} testID="war-screen">
      {!a ? <Txt v="small" color={colors.warning}>Entra in un&apos;alleanza per partecipare alle guerre. La mappa è visibile a tutti.</Txt> : null}
      <WarMap nodes={m.nodes} myAlliance={m.my_alliance_id} selected={sel?.node_id} contested={contested} alliances={m.alliances} onSelect={(n) => { setSel(n); sheet.current?.present(); }} />
      <Panel testID="territory-bonus">
        <Txt v="h3">Bonus territorio della tua alleanza</Txt>
        {Object.keys(m.territory_bonus).length ? Object.entries(m.territory_bonus).map(([k, v]) => <Txt key={k} v="small">{k.replace(/_/g, " ")}: +{Number(v).toFixed(1)}%</Txt>) : <Txt v="small" color={colors.muted}>Nessun nodo con bonus conquistato.</Txt>}
        <Txt v="small" color={colors.muted} style={{ marginTop: 6 }}>Regole: prep {m.rules.prep_hours}h, roster bloccato {m.rules.roster_lock_minutes_before_resolution} min prima, 10 corsie 1v1 sullo snapshot congelato, 1 attacco/24h, min {m.rules.minimum_members_to_attack} membri, bersaglio adiacente.</Txt>
      </Panel>
      <Txt v="h2">Guerre</Txt>
      {(wars?.wars ?? []).map((w: any) => <WarRow key={w.id} w={w} mine={a?.id} serverTime={wars.server_time} onOpen={() => setWarId(warId === w.id ? undefined : w.id)} open={warId === w.id} />)}
      {!wars?.wars?.length ? <Txt v="small" color={colors.muted}>Nessuna guerra. Seleziona un nodo adiacente al tuo territorio per dichiararla.</Txt> : null}
      {detail ? (
        <Panel variant="parchment" testID="war-detail">
          <Txt v="h3" color={colors.onSurfaceInverse}>Nodo {detail.war.node_id} · {NODE_LABEL[detail.war.node_type]} · {STATUS_LABEL[detail.war.status] ?? detail.war.status}</Txt>
          <Txt v="small" color={colors.onSurfaceInverse}>Attaccante {detail.alliances[detail.war.attacker_id]?.name} vs {detail.war.defender_id ? detail.alliances[detail.war.defender_id]?.name : "Guarnigione neutrale"}</Txt>
          {detail.war.status === "prep" && officer ? (
            <View style={{ gap: 6, marginTop: 6 }}>
              <Txt v="caption" style={{ color: colors.onSurfaceInverse }}>Roster ({picked.length}/10) — tocca i membri</Txt>
              <Row style={{ flexWrap: "wrap" }}>
                {(a?.members ?? []).map((mem: any) => {
                  const on = picked.includes(mem.player_id);
                  return <Pressable key={mem.player_id} onPress={() => setPicked(on ? picked.filter((x) => x !== mem.player_id) : picked.length < 10 ? [...picked, mem.player_id] : picked)} style={{ paddingHorizontal: 8, height: 36, justifyContent: "center", borderRadius: 999, borderWidth: 1, borderColor: on ? colors.forest : colors.wood, backgroundColor: on ? colors.forest : colors.parchment }} testID={`roster-pick-${mem.player_id}`}><Txt v="small" color={on ? colors.onBrandTertiary : colors.onSurfaceInverse}>{mem.display_name} L{mem.hero_level}</Txt></Pressable>;
                })}
              </Row>
              <Btn title="Salva roster" small onPress={() => roster.mutate({ war_id: detail.war.id, player_ids: picked })} loading={roster.isPending} testID="save-roster-button" />
              <Txt v="small" color={colors.onSurfaceInverse}>Attacco attuale: {detail.war.attack_roster.length}/10 · Difesa: {detail.war.defense_roster.length}/10 (NPC al 70% della mediana per i posti vuoti)</Txt>
            </View>
          ) : null}
          {detail.war.result?.lanes ? (
            <View style={{ marginTop: 6 }}>
              <Txt v="h3" color={colors.onSurfaceInverse}>{detail.war.result.attacker_won ? "Attaccante vince" : "Difensore vince"} {detail.war.result.attacker_points}-{detail.war.result.defender_points}{detail.war.result.tie_break_used ? " (spareggio margini)" : ""}{detail.war.result.captured ? " · nodo conquistato" : ""}</Txt>
              {detail.war.result.lanes.map((l: any) => <Txt key={l.lane} v="small" color={colors.onSurfaceInverse}>Corsia {l.lane}: {l.attacker} {fmt(l.attacker_power)} vs {l.defender} {fmt(l.defender_power)} → {l.attacker_wins ? "A" : "D"}</Txt>)}
            </View>
          ) : null}
        </Panel>
      ) : null}
      <Txt v="h2">Classifica stagione</Txt>
      {m.leaderboard.map((l: any, i: number) => <Row key={l.alliance_id} style={{ justifyContent: "space-between" }}><Txt v="body">{i + 1}. [{l.tag}] {l.name}</Txt><Txt v="bodyBold" color={colors.goldBright}>{fmt(l.season_points)}</Txt></Row>)}
      <Sheet ref={sheet} title={sel ? `Nodo ${sel.node_id} · ${NODE_LABEL[sel.type]}` : ""} snap={["40%"]} testID="node-sheet">
        {sel ? (
          <View style={{ gap: 8 }}>
            <Row><View style={{ width: 14, height: 14, backgroundColor: allianceColor(sel.owner, m.my_alliance_id), borderWidth: 1, borderColor: colors.gold }} /><Txt v="body">{sel.owner ? `Controllato da [${m.alliances[sel.owner]?.tag}] ${m.alliances[sel.owner]?.name}` : "Neutrale (guarnigione)"}</Txt></Row>
            {sel.bonus ? <Txt v="small" color={colors.muted}>Bonus: {Object.entries(sel.bonus).map(([k, v]) => `${k.replace(/_/g, " ")} +${v}%`).join(", ")}</Txt> : <Txt v="small" color={colors.muted}>Nessun bonus.</Txt>}
            {contested.has(sel.node_id) ? <Txt v="small" color={colors.error}>Guerra in corso su questo nodo.</Txt> : null}
            {officer && sel.owner !== m.my_alliance_id ? <Btn title="Dichiara guerra" icon="sword-cross" loading={declare.isPending} onPress={() => declare.mutate({ node_id: sel.node_id }, { onSuccess: () => sheet.current?.dismiss() })} testID="declare-war-button" /> : null}
            {!officer ? <Txt v="small" color={colors.muted}>Solo leader e ufficiali dichiarano guerra.</Txt> : null}
          </View>
        ) : null}
      </Sheet>
    </Screen>
  );
}

function WarRow({ w, mine, serverTime, onOpen, open }: { w: any; mine?: string; serverTime: string; onOpen: () => void; open: boolean }) {
  const { colors } = useTheme();
  const lock = useCountdown(w.lock_at, serverTime);
  const res = useCountdown(w.resolves_at, serverTime);
  const role = w.attacker_id === mine ? "Attacco" : "Difesa";
  return (
    <Pressable onPress={onOpen} testID={`war-row-${w.id}`}>
      <Panel variant={open ? "parchment" : "iron"}>
        <Row style={{ justifyContent: "space-between" }}>
          <View>
            <Txt v="h3" color={open ? colors.onSurfaceInverse : colors.onSurface}>{role} · nodo {w.node_id} · {NODE_LABEL[w.node_type]}</Txt>
            <Txt v="small" color={open ? colors.onSurfaceInverse : colors.muted}>{w.status === "prep" ? `Roster si blocca in ${fmtDuration(lock)} · risoluzione in ${fmtDuration(res)}` : w.status === "locked" ? `Snapshot congelato · risoluzione in ${fmtDuration(res)}` : w.status === "resolved" && w.result ? `${STATUS_LABEL.resolved} · ${w.result.attacker_won ? "attaccante" : "difensore"} vince ${w.result.attacker_points}-${w.result.defender_points}` : STATUS_LABEL[w.status] ?? w.status}</Txt>
          </View>
          <Icon name={open ? "chevron-up" : "chevron-down"} color={open ? colors.onSurfaceInverse : colors.goldBright} />
        </Row>
      </Panel>
    </Pressable>
  );
}
