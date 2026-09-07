import { useRouter } from "expo-router";
import React, { useMemo, useRef, useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { QK, useAction, useKingdom, useProfile } from "@/src/api/hooks";
import { KingdomScene } from "@/src/kingdom/KingdomScene";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Res, ResourceBar, Row, Txt, fmt, fmtDuration } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";
import { useCountdown } from "@/src/ui/useCountdown";
import { TutorialTarget } from "@/src/tutorial/Tutorial";
import { playSfx } from "@/src/audio";

export default function KingdomTab() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data: k, isLoading } = useKingdom();
  const { data: profile } = useProfile();
  const sheet = useRef<SheetRef>(null);
  const [sel, setSel] = useState<string | null>(null);
  const upgrade = useAction("post", "/kingdom/upgrade", [QK.kingdom], { success: (d) => (d.instant ? "Costruito!" : "Costruzione avviata") });
  const speed = useAction("post", "/kingdom/speedup", [QK.kingdom, QK.research, QK.army], { success: (d) => `Accelerato per ${d.rubies_spent} Rubini` });
  const b = useMemo(() => k?.buildings?.find((x: any) => x.key === sel), [k, sel]);
  const queued = useMemo(() => Object.fromEntries((k?.queues?.construction_queue ?? []).map((q: any) => [q.building, q])), [k]);
  if (isLoading || !k || !profile) return <Loading label="Il Regno si sveglia..." />;
  const canAfford = (cost: Record<string, number>) => Object.entries(cost).every(([r, v]) => (k.resources[r] ?? 0) >= v);
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="kingdom-screen">
      <View style={{ paddingTop: insets.top, backgroundColor: colors.surfaceSecondary }}>
        <ResourceBar resources={k.resources} />
      </View>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }} showsVerticalScrollIndicator={false}>
        <TutorialTarget id="kingdom-scene">
          <KingdomScene buildings={k.buildings} castleLevel={k.castle_level} tier={k.visual_tier} heraldicColor={profile.heraldic_color} queued={queued} serverTime={k.server_time} onSelect={(key) => { setSel(key); sheet.current?.present(); }} />
        </TutorialTarget>
        <Row style={{ paddingHorizontal: 12, paddingTop: 12, gap: 8 }}>
          <Btn title="Ricerca" icon="flask" variant="gold" onPress={() => router.push("/kingdom/research")} style={{ flex: 1 }} testID="open-research-button" />
          <Btn title="Esercito" icon="account-group" variant="secondary" onPress={() => router.push("/(tabs)/army")} style={{ flex: 1 }} testID="open-army-button" />
        </Row>
        <TutorialTarget id="production-panel">
        <Panel style={{ margin: 12 }} testID="production-panel">
          <Row style={{ justifyContent: "space-between" }}>
            <Txt v="h3">Produzione / ora</Txt>
            <Txt v="caption">Magazzino {fmt(k.warehouse_capacity)}</Txt>
          </Row>
          <Row style={{ flexWrap: "wrap", gap: 12, marginTop: 6 }}>
            {Object.entries(k.production_per_hour).map(([r, v]) => <Res key={r} kind={r} value={v as number} testID={`prod-${r}`} />)}
          </Row>
        </Panel>
        </TutorialTarget>
        <TutorialTarget id="queues-panel">
        <Panel variant="wood" style={{ marginHorizontal: 12, marginBottom: 12 }} testID="queues-panel">
          <Row style={{ justifyContent: "space-between" }}>
            <Txt v="h3">Code</Txt>
            <Txt v="caption">Costruzione {k.queues.construction_queue.length}/{k.queue_caps.construction} · Reclut. {k.queues.recruit_queue.length}/{k.queue_caps.recruit} · Ricerca {k.queues.research_queue.length}/{k.queue_caps.research}</Txt>
          </Row>
          {(["construction_queue", "recruit_queue", "research_queue"] as const).flatMap((q) => k.queues[q].map((item: any) => <QueueRow key={item.id} queue={q} item={item} serverTime={k.server_time} onSpeed={() => speed.mutate({ queue: q, item_id: item.id })} />))}
          {!k.queues.construction_queue.length && !k.queues.recruit_queue.length && !k.queues.research_queue.length ? <Txt v="small" color={colors.muted}>Nessun lavoro in corso. Tocca un edificio per potenziarlo.</Txt> : null}
        </Panel>
        </TutorialTarget>
      </ScrollView>
      <Sheet ref={sheet} title={b?.name} testID="building-sheet">
        {b ? (
          <View style={{ gap: 10 }}>
            <Row style={{ justifyContent: "space-between" }}>
              <Txt v="h3">Livello {b.level} / {b.max_level}</Txt>
              {!b.unlocked ? <Txt v="small" color={colors.warning}>Richiede Castello {b.unlock_castle_level}</Txt> : null}
            </Row>
            {b.current?.production_per_hour ? <Row style={{ flexWrap: "wrap" }}>{Object.entries(b.current.production_per_hour).map(([r, v]) => <Res key={r} kind={r} value={`${fmt(v as number)}/h`} />)}</Row> : null}
            {b.current?.capacity_each_resource ? <Txt v="small">Capacità: {fmt(b.current.capacity_each_resource)} per risorsa</Txt> : null}
            {b.key === "castle" ? <Txt v="small" color={colors.muted}>Il Castello sblocca edifici, ricerche, unità, slot formazione e code aggiuntive. Livello {b.level}: {k.visual_tier.name}.</Txt> : null}
            {b.key === "university" ? (
              <View style={{ gap: 6 }}>
                <Txt v="small" color={colors.muted}>L&apos;Università ospita le 48 ricerche (8 rami × 5 livelli). Le ricerche sono sbloccate dal livello del Castello; una ricerca alla volta.</Txt>
                <Btn title="Apri Ricerca" icon="flask" variant="gold" onPress={() => { sheet.current?.dismiss(); router.push("/kingdom/research"); }} testID="sheet-open-research-button" />
              </View>
            ) : null}
            {b.key === "barracks" || b.key === "stable" || b.key === "bestiary" || b.key === "mythic_sanctuary" ? <Btn title="Recluta unità" icon="account-group" variant="secondary" onPress={() => { sheet.current?.dismiss(); router.push("/(tabs)/army"); }} testID="sheet-open-army-button" /> : null}
            {b.next ? (
              <Panel variant="parchment">
                <Txt v="h3" color={colors.onSurfaceInverse}>Prossimo livello {b.next.level}</Txt>
                {b.next.production_per_hour ? <Row style={{ flexWrap: "wrap" }}>{Object.entries(b.next.production_per_hour).map(([r, v]) => <Txt key={r} v="small" color={colors.onSurfaceInverse}>{r}: {fmt(v as number)}/h</Txt>)}</Row> : null}
                {b.next.capacity_each_resource ? <Txt v="small" color={colors.onSurfaceInverse}>Capacità {fmt(b.next.capacity_each_resource)}</Txt> : null}
                <Row style={{ flexWrap: "wrap", gap: 10, marginVertical: 6 }}>
                  {Object.entries(b.next.cost).filter(([, v]) => (v as number) > 0).map(([r, v]) => <Res key={r} kind={r} value={v as number} />)}
                  <Row gap={4}><Icon name="clock-outline" size={14} color={colors.onSurfaceInverse} /><Txt v="small" color={colors.onSurfaceInverse}>{b.next.minutes <= 0 ? "istantaneo" : fmtDuration(b.next.minutes * 60)}</Txt></Row>
                </Row>
                {b.in_queue ? <Txt v="small" color={colors.onSurfaceInverse}>In costruzione…</Txt> : (
                  <Btn title={b.level === 0 ? "Costruisci" : "Potenzia"} icon="hammer" disabled={!b.unlocked || !canAfford(b.next.cost) || k.queues.construction_queue.length >= k.queue_caps.construction} loading={upgrade.isPending} onPress={() => upgrade.mutate({ building: b.key }, { onSuccess: () => { playSfx("build"); sheet.current?.dismiss(); } })} testID="building-upgrade-button" />
                )}
                {!canAfford(b.next.cost) ? <Txt v="small" color={colors.burgundy}>Risorse insufficienti</Txt> : null}
              </Panel>
            ) : <Txt v="small" color={colors.goldBright}>Livello massimo raggiunto</Txt>}
          </View>
        ) : null}
      </Sheet>
    </View>
  );
}

function QueueRow({ queue, item, serverTime, onSpeed }: { queue: string; item: any; serverTime: string; onSpeed: () => void }) {
  const { colors } = useTheme();
  const left = useCountdown(item.ends_at, serverTime);
  const label = queue === "construction_queue" ? `${item.building} → Lv ${item.target_level}` : queue === "research_queue" ? `${item.node} → Lv ${item.target_level}` : `${item.quantity} × ${item.unit}`;
  const rubies = Math.max(5, Math.ceil(left / 60 / 3));
  return (
    <Row style={{ justifyContent: "space-between", paddingVertical: 6, borderBottomWidth: 1, borderColor: colors.divider }} testID={`queue-item-${item.id}`}>
      <View style={{ flex: 1 }}>
        <Txt v="bodyBold">{label}</Txt>
        <Txt v="small" color={colors.muted}>{left > 0 ? fmtDuration(left) : "Completato — aggiornamento…"}</Txt>
      </View>
      {left > 0 ? <Pressable onPress={onSpeed} style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 10, minHeight: 44 }} testID={`speedup-${item.id}`}><Icon name="diamond-stone" size={14} color={colors.res_rubies} /><Txt v="small">{rubies}</Txt></Pressable> : null}
    </Row>
  );
}
