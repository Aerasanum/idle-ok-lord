import React, { useRef, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import { Pressable, View } from "react-native";

import { QK, useAction, useMyAlliance, useWar, useWarMap, useWars } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Row, Screen, Txt, fmt, fmtDuration } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";
import { useCountdown, useSecondsUntil } from "@/src/ui/useCountdown";
import { NODE_LABEL, WarMap, allianceColor } from "@/src/war/WarMap";
import { WarEnlist } from "@/src/war/WarEnlist";
import { WarReplay } from "@/src/war/WarReplay";

const STATUS_LABEL: Record<string, string> = { prep: "Preparazione", locking: "Blocco roster", locked: "Roster bloccato", resolving: "Risoluzione", resolved: "Risolta", cancelled: "Annullata" };

const ATTACK_REASON: Record<string, string> = {
  officer_required: "Solo il leader e gli ufficiali possono dichiarare guerra.",
  displaced: "L'alleanza si sta ricollocando dopo aver perso il castello: attendi 12 ore.",
  min_members: "Servono almeno 10 membri per attaccare.",
  attack_cooldown: "Un solo attacco ogni 24 ore per alleanza.",
  war_active: "La tua alleanza è già impegnata in una guerra: aspetta che si risolva.",
};

export default function WarScreen({ inTab = false }: { inTab?: boolean }) {
  const { colors } = useTheme();
  const params = useLocalSearchParams<{ section?: string }>();
  const rosterOnly = params.section === "roster"; // opened from the Alleanza tab: only wars + enlistment/formation
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
  // Opening another war, or the server returning a different roster, discards the picks
  // in progress. Adjusting here rather than in an effect avoids rendering the stale list once.
  const rosterKey = `${detail?.war?.id ?? ""}:${currentRoster?.length ?? 0}`;
  const [syncedRoster, setSyncedRoster] = useState(rosterKey);
  if (syncedRoster !== rosterKey) {
    setSyncedRoster(rosterKey);
    setPicked(currentRoster ?? []);
  }
  const seasonEnds = useSecondsUntil(m?.season?.ends_at);
  const infirmaryIn = useSecondsUntil(detail?.my_casualties?.infirmary?.ready_at);
  const attackCooldownIn = useSecondsUntil(m?.attack_state?.cooldown_ends_at);
  if (isLoading || !m) return <Loading label="Carico la mappa del territorio..." />;
  const a = mine?.alliance;
  const officer = a?.my_role === "leader" || a?.my_role === "officer";
  const contested = new Set<number>(m.active_wars.map((w: any) => w.node_id));
  return (
    <Screen title={rosterOnly ? "Guerra 10v10" : "Territori"} back={!inTab} subtitle={`Stagione ${m.season.key} · termina in ${fmtDuration(seasonEnds)} · shard ${m.shard_id.slice(-6)}`} testID="war-screen">
      {!a ? <Txt v="small" color={colors.warning}>Entra in un&apos;alleanza (scheda Alleanza, Castello 8) per partecipare alle guerre. La mappa è visibile a tutti.</Txt> : null}
      {!rosterOnly ? (
        <>
          <WarMap nodes={m.nodes} myAlliance={m.my_alliance_id} selected={sel?.node_id} contested={contested} alliances={m.alliances} attackable={new Set<number>(m.attack_state?.attackable_node_ids ?? [])} onSelect={(n) => { setSel(n); sheet.current?.present(); }} />
          <Panel testID="territory-bonus">
            <Txt v="h3">Bonus territorio della tua alleanza</Txt>
            {Object.keys(m.territory_bonus).length ? Object.entries(m.territory_bonus).map(([k, v]) => <Txt key={k} v="small">{k.replace(/_/g, " ")}: +{Number(v).toFixed(1)}%</Txt>) : <Txt v="small" color={colors.muted}>Nessun nodo con bonus conquistato.</Txt>}
            <Txt v="small" color={colors.muted} style={{ marginTop: 6 }}>Regole: prep {m.rules.prep_hours}h, roster bloccato {m.rules.roster_lock_minutes_before_resolution} min prima, 10 corsie 1v1 sullo snapshot congelato, 1 attacco/24h, min {m.rules.minimum_members_to_attack} membri, bersaglio adiacente. Perdite permanenti su entrambi i lati (v1.5).</Txt>
          </Panel>
        </>
      ) : (
        <Txt v="small" color={colors.muted}>Arruolati nelle guerre in preparazione: i primi 10 per potenza formano lo schieramento, gli altri restano in riserva. Per dichiarare una guerra usa la mappa nella scheda Guerra.</Txt>
      )}
      <Txt v="h2">Guerre</Txt>
      {(wars?.wars ?? []).map((w: any) => <WarRow key={w.id} w={w} mine={a?.id} serverTime={wars.server_time} onOpen={() => setWarId(warId === w.id ? undefined : w.id)} open={warId === w.id} />)}
      {!wars?.wars?.length ? <Txt v="small" color={colors.muted}>Nessuna guerra. Seleziona un nodo adiacente al tuo territorio per dichiararla.</Txt> : null}
      {detail ? (
        <Panel variant="parchment" testID="war-detail">
          <Txt v="h3" color={colors.onSurfaceInverse}>Nodo {detail.war.node_id} · {NODE_LABEL[detail.war.node_type]} · {STATUS_LABEL[detail.war.status] ?? detail.war.status}</Txt>
          <Txt v="small" color={colors.onSurfaceInverse}>Attaccante {detail.alliances[detail.war.attacker_id]?.name} vs {detail.war.defender_id ? detail.alliances[detail.war.defender_id]?.name : "Guarnigione neutrale"}</Txt>
          {detail.war.status === "prep" ? <WarEnlist detail={detail} myAllianceId={myId} /> : null}
          {detail.war.status === "prep" && officer ? (
            <View style={{ gap: 6, marginTop: 10, borderTopWidth: 1, borderColor: colors.wood, paddingTop: 8 }}>
              <Txt v="caption" style={{ color: colors.onSurfaceInverse }}>Gestione ufficiali: sostituisci il roster ({picked.length}/10) — tocca i membri</Txt>
              <Row style={{ flexWrap: "wrap" }}>
                {(a?.members ?? []).map((mem: any) => {
                  const on = picked.includes(mem.player_id);
                  return <Pressable key={mem.player_id} onPress={() => setPicked(on ? picked.filter((x) => x !== mem.player_id) : picked.length < 10 ? [...picked, mem.player_id] : picked)} style={{ paddingHorizontal: 8, height: 36, justifyContent: "center", borderRadius: 999, borderWidth: 1, borderColor: on ? colors.forest : colors.wood, backgroundColor: on ? colors.forest : colors.parchment }} testID={`roster-pick-${mem.player_id}`}><Txt v="small" color={on ? colors.onBrandTertiary : colors.onSurfaceInverse}>{mem.display_name} L{mem.hero_level}</Txt></Pressable>;
                })}
              </Row>
              <Btn title="Salva roster" small onPress={() => roster.mutate({ war_id: detail.war.id, player_ids: picked })} loading={roster.isPending} testID="save-roster-button" />
              <Txt v="small" color={colors.onSurfaceInverse}>Attacco: {detail.war.attack_roster.length}/10 · Difesa: {detail.war.defense_roster.length}/10 (difesa: NPC al 70% della mediana nei posti vuoti · attacco: corsie vuote perse)</Txt>
            </View>
          ) : null}
          {detail.war.result?.lanes ? (
            <View style={{ marginTop: 8, gap: 8 }}>
              <Txt v="h3" color={colors.onSurfaceInverse}>{detail.war.result.attacker_won ? "Attaccante vince" : "Difensore vince"} {detail.war.result.attacker_points}-{detail.war.result.defender_points}{detail.war.result.tie_break_used ? " (spareggio margini)" : ""}{detail.war.result.captured ? " · nodo conquistato" : ""}</Txt>
              <WarReplay
                key={detail.war.id}
                lanes={detail.war.result.lanes}
                attackerName={`[${detail.alliances[detail.war.attacker_id]?.tag ?? "?"}] ${detail.alliances[detail.war.attacker_id]?.name ?? "Attaccante"}`}
                defenderName={detail.war.defender_id ? `[${detail.alliances[detail.war.defender_id]?.tag ?? "?"}] ${detail.alliances[detail.war.defender_id]?.name ?? "Difensore"}` : "Guarnigione neutrale"}
                attackerWon={detail.war.result.attacker_won}
                points={[detail.war.result.attacker_points, detail.war.result.defender_points]}
                captured={!!detail.war.result.captured}
                mineIsAttacker={myId ? detail.war.attacker_id === myId : null}
              />
              {detail.team_casualties ? (
                <View style={{ gap: 4, padding: 8, borderRadius: 8, backgroundColor: colors.parchment, borderWidth: 1, borderColor: colors.wood }} testID="war-casualties">
                  <Txt v="bodyBold" color={colors.onSurfaceInverse}>⚰ Perdite della squadra: {fmt(detail.team_casualties.lost)} unità cadute su {fmt(detail.team_casualties.deployed)} schierate · {fmt(detail.team_casualties.deployed - detail.team_casualties.lost)} superstiti</Txt>
                  {detail.team_casualties.players.map((c: any) => (
                    <Row key={c.player_id} style={{ justifyContent: "space-between" }} testID={`war-casualty-${c.player_id}`}>
                      <Txt v="small" color={colors.onSurfaceInverse}>Corsia {c.lane} · {c.display_name ?? c.player_id} · {c.won ? "vinta" : "persa"} ({c.rate_pct}%)</Txt>
                      <Txt v="small" color={c.lost ? colors.error : colors.onSurfaceInverse}>−{fmt(c.lost)} / {fmt(c.deployed)}</Txt>
                    </Row>
                  ))}
                  {detail.my_casualties ? (
                    <Txt v="small" color={colors.onSurfaceInverse} testID="war-my-casualties">
                      Le tue truppe: {Object.entries(detail.my_casualties.units).map(([k, v]: any) => `${k} −${fmt(v.lost)} (${fmt(v.survived)} superstiti)`).join(" · ")}
                    </Txt>
                  ) : null}
                  {detail.my_casualties?.infirmary?.total ? (
                    <Txt v="small" color={colors.success} testID="war-infirmary">
                      🏥 Infermeria: {fmt(detail.my_casualties.infirmary.total)} unità tornano {infirmaryIn > 0 ? `tra ${fmtDuration(infirmaryIn)}` : "(già rientrate)"} · {Object.entries(detail.my_casualties.infirmary.units).map(([k, v]: any) => `${k} +${fmt(v)}`).join(" · ")}
                    </Txt>
                  ) : null}
                  <Txt v="small" color={colors.muted}>Regola v1.5: vincitore 5% + 20%×r, sconfitto 30% + 30%×(1−r); difensore ×0,85; bestie ×0,9, assedio ×0,8, mitiche ×0,6. Almeno un superstite per tipo; l&apos;Infermeria restituisce il 40% dei caduti dopo 8 ore. Il PvE non causa perdite.</Txt>
                </View>
              ) : null}
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
            {!sel.owner && m.attack_state?.garrison_lane_power ? <Txt v="small" color={colors.muted} testID="garrison-power">Guarnigione: 10 difensori NPC da ~{fmt(m.attack_state.garrison_lane_power)} potenza ciascuno ({m.attack_state.garrison_pct_of_median}% della potenza mediana dei tuoi membri).</Txt> : null}
            {sel.bonus ? <Txt v="small" color={colors.muted}>Bonus: {Object.entries(sel.bonus).map(([k, v]) => `${k.replace(/_/g, " ")} +${v}%`).join(", ")}</Txt> : <Txt v="small" color={colors.muted}>Nessun bonus.</Txt>}
            {contested.has(sel.node_id) ? <Txt v="small" color={colors.error}>Guerra in corso su questo nodo.</Txt> : null}
            {officer && sel.owner !== m.my_alliance_id ? (
              <DeclareBlock attackState={m.attack_state ?? {}} nodeId={sel.node_id} contested={contested.has(sel.node_id)} cooldownIn={attackCooldownIn} declare={declare} onDeclared={() => sheet.current?.dismiss()} />
            ) : null}
            {!officer ? <Txt v="small" color={colors.muted}>Solo leader e ufficiali dichiarano guerra.</Txt> : null}
          </View>
        ) : null}
      </Sheet>
    </Screen>
  );
}

function DeclareBlock({ attackState, nodeId, contested, cooldownIn, declare, onDeclared }: { attackState: any; nodeId: number; contested: boolean; cooldownIn: number; declare: any; onDeclared: () => void }) {
  const { colors } = useTheme();
  const st = attackState;
  const attackable = (st.attackable_node_ids ?? []).includes(nodeId);
  const reason = !st.can_attack ? ATTACK_REASON[st.reason] ?? st.reason : !attackable ? (contested ? "Su questo nodo c'è già una guerra in corso." : "Puoi attaccare solo i nodi adiacenti al tuo territorio (bordo dorato) il cui proprietario non è già in guerra.") : null;
  const cd = st.reason === "attack_cooldown" && st.cooldown_ends_at ? ` Prossimo attacco tra ${fmtDuration(cooldownIn)}.` : "";
  return (
    <View style={{ gap: 6 }}>
      {reason ? <Txt v="small" color={colors.warning} testID="declare-blocked-reason">⚠ {reason}{cd}</Txt> : <Txt v="small" color={colors.success}>Bersaglio valido: preparazione 8 ore, poi 10 corsie 1v1.</Txt>}
      <Btn title="Dichiara guerra" icon="sword-cross" disabled={!!reason} loading={declare.isPending} onPress={() => declare.mutate({ node_id: nodeId }, { onSuccess: onDeclared })} testID="declare-war-button" />
    </View>
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
