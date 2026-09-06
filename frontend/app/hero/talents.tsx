import React, { useState } from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useHero } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Row, Screen, Stat, Txt, fmt } from "@/src/ui";

const BRANCH_LABEL: Record<string, string> = { warrior: "Guerriero", guardian: "Guardiano", commander: "Comandante", fortune: "Fortuna" };

export default function TalentsScreen() {
  const { colors } = useTheme();
  const { data: h, isLoading } = useHero();
  const alloc = useAction("post", "/hero/talents", [QK.hero], { success: () => "Talento assegnato" });
  const respec = useAction("post", "/hero/talents/respec", [QK.hero], { success: (d) => `Talenti azzerati (-${d.rubies_spent} Rubini)` });
  const setSkills = useAction("put", "/hero/skills", [QK.hero], { success: () => "Abilità aggiornate" });
  const [picking, setPicking] = useState<number | null>(null);
  if (isLoading || !h) return <Loading />;
  const free = h.talent_points_total - h.talent_points_spent;
  const slots: (string | null)[] = h.hero.skill_slots ?? [null, null, null];
  return (
    <Screen title="Talenti & Abilità" subtitle={`Lord livello ${h.hero.level}`} testID="talents-screen">
      <Panel testID="hero-stats">
        <Row style={{ justifyContent: "space-around" }}>
          <Stat label="Attacco" value={h.stats.attack} testID="stat-attack" />
          <Stat label="Difesa" value={h.stats.defense} testID="stat-defense" />
          <Stat label="Salute" value={h.stats.hp} testID="stat-hp" />
          <Stat label="Potenza" value={h.stats.power} color={colors.goldBright} testID="stat-power" />
        </Row>
        <Txt v="small" color={colors.muted} style={{ textAlign: "center", marginTop: 6 }}>Potenza = Attacco×2 + Difesa×1.5 + Salute×0.15 (stat base + equipaggiamento forgiato, poi talenti e affissi %).</Txt>
      </Panel>
      <Row style={{ justifyContent: "space-between" }}>
        <Txt v="h2">Talenti · {free} punti liberi</Txt>
        <Btn title="Reset (50 Rubini)" small variant="ghost" onPress={() => respec.mutate({})} disabled={!h.talent_points_spent} testID="respec-button" />
      </Row>
      <Txt v="small" color={colors.muted}>1 punto ogni 5 livelli (max 20). Nessuna vendita di potere: i talenti si guadagnano giocando.</Txt>
      {Object.entries(h.talents.branches).map(([key, br]: any) => {
        const rank = h.hero.talents[key] ?? 0;
        return (
          <Panel key={key} variant="wood" testID={`talent-${key}`}>
            <Row style={{ justifyContent: "space-between" }}>
              <View style={{ flex: 1 }}>
                <Txt v="h3">{BRANCH_LABEL[key]} · {rank}/{br.max_ranks}</Txt>
                <Txt v="small" color={colors.muted}>{br.effect_per_rank} · totale attuale {(rank * parseFloat(String(br.effect_per_rank).split("+").pop() ?? "0")).toFixed(1)}%</Txt>
              </View>
              <Btn title="+1" small disabled={free <= 0 || rank >= br.max_ranks} loading={alloc.isPending} onPress={() => alloc.mutate({ branch: key })} testID={`talent-add-${key}`} />
            </Row>
            <Row style={{ marginTop: 6, gap: 3 }}>{Array.from({ length: br.max_ranks }).map((_, i) => <View key={i} style={{ flex: 1, height: 6, borderRadius: 2, backgroundColor: i < rank ? colors.goldBright : colors.surfaceTertiary }} />)}</Row>
          </Panel>
        );
      })}
      <Txt v="h2">Abilità automatiche</Txt>
      <Txt v="small" color={colors.muted}>Slot sbloccati: {h.skill_slots_unlocked}/3 (livelli 1, 10, 25). Le abilità si attivano da sole con i loro tempi di ricarica.</Txt>
      <Row>
        {slots.map((k, i) => {
          const sk = h.all_skills.find((s: any) => s.key === k);
          const locked = i >= h.skill_slots_unlocked;
          return (
            <Pressable key={i} testID={`skill-slot-${i}`} disabled={locked} onPress={() => setPicking(picking === i ? null : i)} style={{ flex: 1, minHeight: 72, borderWidth: 2, borderColor: picking === i ? colors.goldBright : locked ? colors.iron : colors.gold, borderRadius: 6, backgroundColor: colors.surfaceSecondary, alignItems: "center", justifyContent: "center", padding: 6, opacity: locked ? 0.5 : 1 }}>
              <Icon name={locked ? "lock" : sk ? "flash" : "plus"} size={22} color={colors.goldBright} />
              <Txt v="small" style={{ textAlign: "center" }}>{locked ? `Lv ${h.all_skills && [1, 10, 25][i]}` : sk ? sk.name : "Scegli"}</Txt>
            </Pressable>
          );
        })}
      </Row>
      {picking !== null ? (
        <Panel variant="parchment" testID="skill-picker">
          {h.all_skills.map((s: any) => {
            const unlocked = s.unlock_level <= h.hero.level;
            const used = slots.includes(s.key) && slots[picking] !== s.key;
            return (
              <Row key={s.key} style={{ justifyContent: "space-between", paddingVertical: 6, borderBottomWidth: 1, borderColor: colors.parchmentDark }}>
                <View style={{ flex: 1 }}>
                  <Txt v="bodyBold" color={colors.onSurfaceInverse}>{s.name} {unlocked ? "" : `(Lv ${s.unlock_level})`}</Txt>
                  <Txt v="small" color={colors.onSurfaceInverse}>{s.effect} · ricarica {s.cooldown_seconds}s</Txt>
                </View>
                <Btn title="Usa" small disabled={!unlocked || used} onPress={() => { const next = [...slots]; next[picking] = s.key; setSkills.mutate({ slots: next }); setPicking(null); }} testID={`skill-pick-${s.key}`} />
              </Row>
            );
          })}
          <Btn title="Svuota slot" small variant="ghost" onPress={() => { const next = [...slots]; next[picking] = null; setSkills.mutate({ slots: next }); setPicking(null); }} testID="skill-clear" />
        </Panel>
      ) : null}
      <Txt v="small" color={colors.muted}>XP al prossimo livello: {fmt(h.hero.xp)} / {fmt(h.xp_to_next)}</Txt>
    </Screen>
  );
}
