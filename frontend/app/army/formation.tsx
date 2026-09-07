// Formation area: battlefield preview of the deployed army vs the next stage's enemy mix, steppers per unit, one-tap suggestion.
import { useQueryClient } from "@tanstack/react-query";
import React, { useMemo, useState } from "react";
import { Image, Pressable, View, useWindowDimensions } from "react-native";

import { api } from "@/src/api/client";
import { QK, useAction, useArmy, useProfile } from "@/src/api/hooks";
import { lordArt, regionBackground } from "@/src/art";
import { CATEGORY, allocateProxies } from "@/src/battle/BattleScene";
import { UnitProxy } from "@/src/battle/sprites";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Progress, Row, Screen, Txt, fmt } from "@/src/ui";
import { useToast } from "@/src/ui/Toast";
import { ZoomPan } from "@/src/ui/ZoomPan";

const REGION_INDEX: Record<string, number> = { "Green Marches": 1, Blackwood: 2, "Iron Hills": 3, "Ashen Plains": 4, "Frost Crown": 5, "Sunscar Desert": 6, "Drowned Coast": 7, "Dragon Spine": 8, "Celestial Ruins": 9, "Abyssal Gate": 10 };
const ROW_OF: Record<string, number> = { infantry: 0, cavalry: 0, bear: 0, lion: 0, wolf: 0, war_elephant: 0, conquest_wagon: 0, dragon: 1, angel: 1, demon: 1, falcon: 1, archer: 2, catapult: 2 };

export default function FormationScreen() {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const { data: a, isLoading } = useArmy();
  const { data: profile } = useProfile();
  const qc = useQueryClient();
  const toast = useToast();
  const [draft, setDraft] = useState<Record<string, number> | null>(null);
  const [sug, setSug] = useState<any>(null);
  const [loadingSug, setLoadingSug] = useState(false);
  const save = useAction("put", "/army/formation", [QK.army, QK.profile], { success: () => "Formazione schierata" });
  if (isLoading || !a || !profile) return <Loading label="Preparo il campo..." />;
  const f: Record<string, number> = draft ?? a.formation;
  const unitOf = (k: string) => a.units.find((u: any) => u.key === k);
  const cmdUsed = Object.entries(f).reduce((s, [k, q]) => s + (unitOf(k)?.command_cost ?? 0) * (q as number), 0);
  const types = Object.values(f).filter((q) => (q as number) > 0).length;
  const over = cmdUsed > a.command_capacity || types > a.formation_slots;
  const rc = a.region_counter;
  const pct = (k: string) => rc?.unit_pct?.[k] ?? 0;
  const owned = a.units.filter((u: any) => u.owned > 0);
  const setQ = (k: string, v: number) => setDraft({ ...f, [k]: Math.max(0, Math.min(unitOf(k)?.owned ?? 0, v)) });
  const canAdd = (k: string) => {
    const u = unitOf(k);
    if (!u || (f[k] ?? 0) >= u.owned) return false;
    if (cmdUsed + u.command_cost > a.command_capacity) return false;
    return (f[k] ?? 0) > 0 || types < a.formation_slots;
  };
  const suggest = async () => {
    setLoadingSug(true);
    try {
      const d = await api.get("/army/suggest");
      setSug(d);
    } catch (e: any) {
      toast.show(e?.message ?? "Suggerimento non disponibile", "error");
    } finally {
      setLoadingSug(false);
    }
  };
  const apply = (formation: Record<string, number>) => save.mutate({ formation }, { onSuccess: () => { setDraft(null); setSug(null); qc.invalidateQueries({ queryKey: QK.army }); } });
  const W = width - 24, H = 200;
  const proxies = allocateProxies(f, 12);
  const region = REGION_INDEX[rc?.region] ?? 1;
  const bg = regionBackground(region);
  const lord = lordArt(profile.equipped_items ? Object.fromEntries((profile.equipped_items as any[]).map((i) => [i.slot, i])) : {}, a.visual_tier?.tier ?? 0);
  const rows: { unit: string; count: number }[][] = [[], [], []];
  for (const p of proxies) rows[ROW_OF[p.unit] ?? 0].push(p);
  const previewPower = Object.entries(f).reduce((s, [k, q]) => {
    const per = a.army_per_unit[k] && a.formation[k] ? a.army_per_unit[k] / a.formation[k] : (unitOf(k)?.base_power ?? 0);
    return s + per * (q as number) * (1 + pct(k) / 100);
  }, 0);

  return (
    <Screen title="Formazione" subtitle={rc ? `Prossimo stage ${rc.stage} · ${rc.region}` : "Schiera l'esercito"} testID="formation-screen">
      {/* battlefield preview */}
      <ZoomPan width={W} height={H} testID="formation-preview" style={{ alignSelf: "center", borderRadius: 8, borderWidth: 2, borderColor: colors.gold, backgroundColor: "#2A2A1C" }}>
        {bg ? <Image source={bg} style={{ position: "absolute", left: 0, top: 0, width: W, height: H }} resizeMode="cover" /> : null}
        <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: H * 0.35, backgroundColor: "rgba(0,0,0,0.35)" }} />
        {lord ? <Image source={lord} style={{ position: "absolute", left: 8, bottom: 14, width: 70, height: 78 }} resizeMode="contain" /> : null}
        <View style={{ position: "absolute", left: 76, right: W * 0.34, bottom: 10, gap: 2 }}>
          {[2, 1, 0].map((r) => (
            <View key={r} style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "flex-end", gap: 2, minHeight: 28, paddingLeft: (2 - r) * 10 }}>
              {rows[r].flatMap((p) => Array.from({ length: p.count }).map((_, i) => <UnitProxy key={`${p.unit}${i}`} unit={p.unit} scale={CATEGORY[p.unit] === "mythic" ? 1.1 : 0.85} />))}
            </View>
          ))}
        </View>
        {proxies.length === 0 ? <View style={{ position: "absolute", left: 90, bottom: 40 }}><Txt v="small" color={colors.parchment}>Nessuna truppa schierata</Txt></View> : null}
        {/* enemy mix */}
        <View style={{ position: "absolute", right: 8, bottom: 12, alignItems: "flex-end", gap: 4 }}>
          <Txt v="caption" color={colors.parchment}>Nemici stage {rc?.stage}</Txt>
          {Object.entries(rc?.enemy_mix ?? {}).map(([c, s]) => (
            <View key={c} style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.error }}>
              <Txt v="small" color={colors.onSurface} style={{ fontSize: 10 }}>{a.counters.class_labels[c]} {Math.round((s as number) * 100)}%</Txt>
            </View>
          ))}
        </View>
      </ZoomPan>
      <Panel testID="formation-stats">
        <Row style={{ justifyContent: "space-between" }}>
          <View><Txt v="caption">Potenza esercito (vs stage)</Txt><Txt v="num" testID="formation-power">{fmt(Math.round(previewPower))}</Txt></View>
          <View style={{ alignItems: "flex-end" }}><Txt v="caption">Tipi schierati</Txt><Txt v="num" color={types > a.formation_slots ? colors.error : colors.onSurface} testID="formation-types">{types}/{a.formation_slots}</Txt></View>
        </Row>
        <Progress value={cmdUsed} max={a.command_capacity} color={cmdUsed > a.command_capacity ? colors.error : undefined} label={`Comando ${cmdUsed}/${a.command_capacity}`} testID="formation-command" />
        <Row style={{ marginTop: 8, flexWrap: "wrap" }}>
          <Btn title="Suggerisci formazione" icon="lightbulb-on" variant="gold" loading={loadingSug} onPress={suggest} testID="suggest-formation-button" />
          {draft ? <Btn title="Schiera" icon="content-save" loading={save.isPending} disabled={over} onPress={() => apply(f)} testID="apply-formation-button" /> : null}
          {draft ? <Btn title="Annulla" variant="ghost" onPress={() => setDraft(null)} testID="reset-formation-button" /> : null}
        </Row>
        {over ? <Txt v="small" color={colors.error}>Supera il comando o gli slot disponibili.</Txt> : null}
      </Panel>
      {sug ? (
        <Panel variant="parchment" testID="suggestion-panel">
          <Row style={{ justifyContent: "space-between" }}>
            <Txt v="h3" color={colors.onSurfaceInverse}>Consiglio per lo stage {sug.stage}</Txt>
            <Pressable onPress={() => setSug(null)} hitSlop={8} testID="close-suggestion"><Icon name="close" size={18} color={colors.onSurfaceInverse} /></Pressable>
          </Row>
          <Txt v="small" color={colors.onSurfaceInverse}>{sug.region} · {sug.kind === "boss" ? "BOSS" : sug.kind === "elite" ? "ELITE" : "normale"} · potenza esercito {fmt(sug.army_power)} (ora {fmt(sug.current_army_power)}) · comando {sug.command_used}/{sug.command_capacity}</Txt>
          <View style={{ marginTop: 6, gap: 4 }}>
            {sug.picks.filter((p: any) => p.quantity > 0).map((p: any) => (
              <Row key={p.key} style={{ justifyContent: "space-between" }}>
                <Row gap={6}><UnitProxy unit={p.key} scale={0.7} /><Txt v="body" color={colors.onSurfaceInverse}>{p.name} × {p.quantity}</Txt></Row>
                <Txt v="small" color={p.counter_pct > 0 ? colors.success : p.counter_pct < 0 ? colors.error : colors.onSurfaceInverse}>{p.counter_pct > 0 ? "+" : ""}{p.counter_pct}% · {p.per_command} pot./cmd</Txt>
              </Row>
            ))}
            {sug.picks.filter((p: any) => p.quantity === 0).length ? <Txt v="caption" color={colors.onSurfaceInverse}>Lasciati a casa: {sug.picks.filter((p: any) => p.quantity === 0).map((p: any) => `${p.name} (${p.counter_pct > 0 ? "+" : ""}${p.counter_pct}%)`).join(", ")}</Txt> : null}
          </View>
          <Row style={{ marginTop: 8 }}>
            <Btn title="Applica consiglio" icon="check" loading={save.isPending} onPress={() => apply(sug.formation)} testID="apply-suggestion-button" />
            <Btn title="Modifica prima" variant="secondary" onPress={() => { setDraft(sug.formation); setSug(null); }} testID="edit-suggestion-button" />
          </Row>
          <Txt v="caption" color={colors.onSurfaceInverse} style={{ marginTop: 4 }}>Il consiglio massimizza la potenza per punto comando usando i bonus contro il mix nemico dello stage.</Txt>
        </Panel>
      ) : null}
      <Panel testID="formation-units">
        <Txt v="h3">Truppe disponibili</Txt>
        {owned.length === 0 ? <Txt v="small" color={colors.muted}>Recluta truppe nella scheda Esercito.</Txt> : null}
        {owned.map((u: any) => {
          const q = f[u.key] ?? 0;
          const p = pct(u.key);
          return (
            <View key={u.key} style={{ marginTop: 10, gap: 4 }} testID={`formation-unit-${u.key}`}>
              <Row style={{ justifyContent: "space-between" }}>
                <Row gap={8}>
                  <UnitProxy unit={u.key} scale={0.9} />
                  <View>
                    <Txt v="bodyBold">{u.name}</Txt>
                    <Txt v="small" color={colors.muted}>Possedute {fmt(u.owned)} · comando {u.command_cost}/unità · <Txt v="small" color={p > 0 ? colors.success : p < 0 ? colors.error : colors.muted}>{p > 0 ? "+" : ""}{p}% qui</Txt></Txt>
                  </View>
                </Row>
                <Txt v="num" testID={`formation-qty-${u.key}`}>{q}</Txt>
              </Row>
              <Row>
                <Pressable onPress={() => setQ(u.key, 0)} style={{ height: 40, paddingHorizontal: 10, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6 }} testID={`formation-zero-${u.key}`}><Txt v="small">0</Txt></Pressable>
                <Pressable onPress={() => setQ(u.key, q - (q >= 10 ? 10 : 1))} disabled={q <= 0} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6, opacity: q <= 0 ? 0.4 : 1 }} testID={`formation-minus-${u.key}`}><Icon name="minus" /></Pressable>
                <Pressable onPress={() => setQ(u.key, q + 1)} disabled={!canAdd(u.key)} style={{ width: 40, height: 40, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6, opacity: canAdd(u.key) ? 1 : 0.4 }} testID={`formation-plus-${u.key}`}><Icon name="plus" /></Pressable>
                <Pressable onPress={() => setQ(u.key, q + 10)} disabled={!canAdd(u.key)} style={{ height: 40, paddingHorizontal: 10, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.iron, borderRadius: 6, opacity: canAdd(u.key) ? 1 : 0.4 }} testID={`formation-plus10-${u.key}`}><Txt v="small">+10</Txt></Pressable>
                <Pressable onPress={() => { const free = a.command_capacity - (cmdUsed - q * u.command_cost); setQ(u.key, (q > 0 || types < a.formation_slots) ? Math.min(u.owned, Math.floor(free / u.command_cost)) : 0); }} style={{ height: 40, paddingHorizontal: 10, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.gold, borderRadius: 6 }} testID={`formation-max-${u.key}`}><Txt v="small" color={colors.goldBright}>MAX</Txt></Pressable>
              </Row>
              <Txt v="caption" color={colors.muted}>Forte contro {a.counters.table[u.key].strong_vs.map((c: string) => a.counters.class_labels[c]).join(", ")} · Debole contro {a.counters.table[u.key].weak_vs.map((c: string) => a.counters.class_labels[c]).join(", ")}</Txt>
            </View>
          );
        })}
      </Panel>
    </Screen>
  );
}
