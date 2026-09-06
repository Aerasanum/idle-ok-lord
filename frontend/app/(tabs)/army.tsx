import React, { useMemo, useRef, useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { QK, useAction, useArmy, useProfile } from "@/src/api/hooks";
import { UnitProxy } from "@/src/battle/sprites";
import { useTheme } from "@/src/theme";
import { Btn, Chip, ChipRow, Icon, Loading, Panel, Progress, Res, ResourceBar, Row, Txt, fmt, fmtDuration } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";
import { useCountdown } from "@/src/ui/useCountdown";

const CATS = [["all", "Tutte"], ["regular", "Regolari"], ["siege", "Assedio"], ["beast", "Bestie"], ["mythic", "Mitiche"]];

export default function ArmyTab() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { data: a, isLoading } = useArmy();
  const { data: profile } = useProfile();
  const [cat, setCat] = useState("all");
  const [sel, setSel] = useState<any>(null);
  const [qty, setQty] = useState(10);
  const [formation, setFormation] = useState<Record<string, number> | null>(null);
  const sheet = useRef<SheetRef>(null);
  const recruit = useAction("post", "/army/recruit", [QK.army, QK.kingdom], { success: () => "Reclutamento avviato" });
  const setForm = useAction("put", "/army/formation", [QK.army], { success: () => "Formazione aggiornata" });
  const units = useMemo(() => (a?.units ?? []).filter((u: any) => cat === "all" || u.category === cat), [a, cat]);
  if (isLoading || !a || !profile) return <Loading label="Passo in rassegna le truppe..." />;
  const f = formation ?? a.formation;
  const cmdUsed = Object.entries(f).reduce((s, [k, q]) => s + (a.units.find((u: any) => u.key === k)?.command_cost ?? 0) * (q as number), 0);
  const types = Object.values(f).filter((q) => (q as number) > 0).length;
  const setDeploy = (key: string, v: number) => setFormation({ ...f, [key]: Math.max(0, v) });
  const canAfford = (cost: Record<string, number>, n: number) => Object.entries(cost).every(([r, v]) => (profile.resources[r] ?? 0) >= v * n);
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="army-screen">
      <View style={{ paddingTop: insets.top, backgroundColor: colors.surfaceSecondary }}>
        <ResourceBar resources={profile.resources} />
        <ChipRow>{CATS.map(([k, l]) => <Chip key={k} label={l} selected={cat === k} onPress={() => setCat(k)} testID={`army-filter-${k}`} />)}</ChipRow>
      </View>
      <ScrollView contentContainerStyle={{ padding: 12, paddingBottom: 24, gap: 12 }} showsVerticalScrollIndicator={false}>
        <Panel testID="formation-panel">
          <Row style={{ justifyContent: "space-between" }}>
            <Txt v="h3">Formazione · Potenza esercito {fmt(a.army_power)}</Txt>
            <Txt v="caption">{a.visual_tier?.name}</Txt>
          </Row>
          <Progress value={cmdUsed} max={a.command_capacity} color={cmdUsed > a.command_capacity ? colors.error : undefined} label={`Comando ${cmdUsed}/${a.command_capacity} · Tipi ${types}/${a.formation_slots} (Castello ${profile.kingdom.castle_level})`} testID="command-bar" />
          {a.formation_slots === 0 ? <Txt v="small" color={colors.warning}>Gli slot formazione si sbloccano al Castello 3. L&apos;esercito combatte dallo stage {a.campaign_army_unlock_stage}.</Txt> : null}
          {formation ? (
            <Row style={{ marginTop: 8 }}>
              <Btn title="Salva formazione" small icon="content-save" loading={setForm.isPending} disabled={cmdUsed > a.command_capacity || types > a.formation_slots} onPress={() => setForm.mutate({ formation: f }, { onSuccess: () => setFormation(null) })} testID="save-formation-button" />
              <Btn title="Annulla" small variant="ghost" onPress={() => setFormation(null)} testID="cancel-formation-button" />
            </Row>
          ) : null}
        </Panel>
        {a.queue.length ? (
          <Panel variant="wood" testID="recruit-queue">
            <Txt v="h3">Reclutamento in corso</Txt>
            {a.queue.map((q: any) => <QueueLine key={q.id} q={q} serverTime={a.server_time} />)}
          </Panel>
        ) : null}
        {units.map((u: any) => (
          <Panel key={u.key} variant={u.unlocked ? "iron" : "wood"} testID={`unit-${u.key}`}>
            <Row style={{ gap: 12 }}>
              <View style={{ width: 64, height: 56, alignItems: "center", justifyContent: "flex-end", backgroundColor: colors.surfaceTertiary, borderRadius: 6, borderWidth: 1, borderColor: colors.wood, opacity: u.unlocked ? 1 : 0.5 }}>
                <UnitProxy unit={u.key} scale={u.category === "mythic" ? 1 : 1.6} />
              </View>
              <View style={{ flex: 1 }}>
                <Row style={{ justifyContent: "space-between" }}>
                  <Txt v="h3">{u.name}</Txt>
                  <Txt v="caption">{u.role}</Txt>
                </Row>
                <Txt v="small" color={colors.muted}>Potenza {u.base_power} · Comando {u.command_cost} · {u.recruit_minutes_each}m/unità</Txt>
                <Txt v="small">Possedute {fmt(u.owned)} · Schierate {fmt(u.deployed)}{a.army_per_unit[u.key] ? ` · ${fmt(a.army_per_unit[u.key])} pot.` : ""}</Txt>
                {!u.unlocked ? (
                  <Txt v="small" color={colors.warning}>
                    {[!u.gates.castle && `Castello ${u.unlock_castle_level}`, !u.gates.campaign && `Stage ${u.unlock_campaign_stage}`, !u.gates.research && `Ricerca ${u.required_research}`].filter(Boolean).join(" · ")}
                  </Txt>
                ) : null}
              </View>
            </Row>
            <Row style={{ marginTop: 8, justifyContent: "space-between" }}>
              <Row>
                <Pressable testID={`deploy-minus-${u.key}`} onPress={() => setDeploy(u.key, (f[u.key] ?? 0) - Math.max(1, Math.round(u.owned / 10)))} disabled={!u.owned} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }}><Icon name="minus" /></Pressable>
                <Txt v="num" testID={`deploy-value-${u.key}`}>{fmt(Math.min(f[u.key] ?? 0, u.owned))}</Txt>
                <Pressable testID={`deploy-plus-${u.key}`} onPress={() => setDeploy(u.key, Math.min(u.owned, (f[u.key] ?? 0) + Math.max(1, Math.round(u.owned / 10))))} disabled={!u.owned} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }}><Icon name="plus" /></Pressable>
                <Pressable testID={`deploy-max-${u.key}`} onPress={() => setDeploy(u.key, u.owned)} disabled={!u.owned} style={{ paddingHorizontal: 8, height: 40, justifyContent: "center" }}><Txt v="small" color={colors.goldBright}>MAX</Txt></Pressable>
              </Row>
              <Btn title="Recluta" small icon="account-plus" disabled={!u.unlocked} onPress={() => { setSel(u); setQty(10); sheet.current?.present(); }} testID={`recruit-open-${u.key}`} />
            </Row>
          </Panel>
        ))}
      </ScrollView>
      <Sheet ref={sheet} title={sel ? `Recluta ${sel.name}` : ""} snap={["55%"]} testID="recruit-sheet">
        {sel ? (
          <View style={{ gap: 10 }}>
            <Row style={{ justifyContent: "center", gap: 16 }}>
              {[-100, -10, -1].map((d) => <Pressable key={d} onPress={() => setQty(Math.max(1, qty + d))} style={{ minWidth: 44, height: 44, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID={`qty-${d}`}><Txt v="small">{d}</Txt></Pressable>)}
              <Txt v="h1" testID="recruit-qty">{qty}</Txt>
              {[1, 10, 100].map((d) => <Pressable key={d} onPress={() => setQty(Math.min(5000, qty + d))} style={{ minWidth: 44, height: 44, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID={`qty-${d}`}><Txt v="small">+{d}</Txt></Pressable>)}
            </Row>
            <Row style={{ flexWrap: "wrap", gap: 12, justifyContent: "center" }}>
              {Object.entries(sel.recruit_cost).map(([r, v]) => <Res key={r} kind={r} value={(v as number) * qty} />)}
              <Row gap={4}><Icon name="clock-outline" size={14} /><Txt v="small">{fmtDuration(sel.recruit_minutes_each * qty * 60)}</Txt></Row>
            </Row>
            <Btn title="Conferma reclutamento" icon="account-plus" loading={recruit.isPending} disabled={!canAfford(sel.recruit_cost, qty)} onPress={() => recruit.mutate({ unit: sel.key, quantity: qty }, { onSuccess: () => sheet.current?.dismiss() })} testID="recruit-confirm-button" />
            {!canAfford(sel.recruit_cost, qty) ? <Txt v="small" color={colors.error} style={{ textAlign: "center" }}>Risorse insufficienti</Txt> : null}
          </View>
        ) : null}
      </Sheet>
    </View>
  );
}

function QueueLine({ q, serverTime }: { q: any; serverTime: string }) {
  const left = useCountdown(q.ends_at, serverTime);
  const { colors } = useTheme();
  return <Txt v="small" color={colors.muted}>{q.quantity} × {q.unit} · {left > 0 ? fmtDuration(left) : "pronti"}</Txt>;
}
