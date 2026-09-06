import React, { useMemo, useRef, useState } from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useForgeCosts, useInventory, useProfile } from "@/src/api/hooks";
import { rarityColor, useTheme } from "@/src/theme";
import { Btn, Chip, ChipRow, Icon, Loading, Panel, RARITY_LABEL, RarityFrame, Row, SLOT_ICON, SLOT_LABEL, Screen, Txt, fmt } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";

const AFFIX_LABEL: Record<string, string> = { crit_chance_pct: "Crit %", crit_damage_pct: "Danno crit %", attack_speed_pct: "Vel. attacco %", lifesteal_pct: "Rubavita %", dodge_pct: "Schivata %", gold_find_pct: "Oro trovato %", gear_find_pct: "Equip. trovato %", army_power_pct: "Potenza esercito %", boss_damage_pct: "Danno boss %" };

export default function GearScreen() {
  const { colors } = useTheme();
  const { data: inv, isLoading } = useInventory();
  const { data: profile } = useProfile();
  const { data: forge } = useForgeCosts();
  const [filter, setFilter] = useState("all");
  const [sel, setSel] = useState<any>(null);
  const sheet = useRef<SheetRef>(null);
  const equip = useAction("post", "/gear/equip", [QK.inventory, QK.forge], { success: () => "Equipaggiato" });
  const unequip = useAction("post", "/gear/unequip", [QK.inventory, QK.forge]);
  const autoEquip = useAction("post", "/gear/auto-equip", [QK.inventory, QK.forge], { success: (d) => `Auto-equip: ${d.changed} cambi` });
  const salvage = useAction("post", "/gear/salvage", [QK.inventory], { success: (d) => `Smantellati ${d.salvaged.length}: ${Object.entries(d.materials).map(([k, v]) => `${v} ${k}`).join(", ")}` });
  const forgeUp = useAction("post", "/forge/upgrade", [QK.inventory, QK.forge], { success: (d) => `Forgia ${SLOT_LABEL[d.slot]} +${d.forge_level}` });
  const reforge = useAction("post", "/gear/reforge", [QK.inventory], { success: () => "Affisso riforgiato" });
  const expand = useAction("post", "/gear/expand", [QK.inventory], { success: (d) => `Inventario: ${d.inventory_capacity} slot` });
  const setAuto = useAction("put", "/gear/auto-salvage", [QK.inventory], { success: () => "Auto-smantellamento aggiornato" });
  const items = useMemo(() => (inv?.items ?? []).filter((i: any) => filter === "all" || (filter === "equipped" ? !!i.equipped_slot : i.slot === filter)), [inv, filter]);
  if (isLoading || !inv || !profile) return <Loading />;
  const eqById: Record<string, any> = Object.fromEntries(inv.items.filter((i: any) => i.equipped_slot).map((i: any) => [i.slot, i]));
  const junk = inv.items.filter((i: any) => !i.equipped_slot && ["common", "uncommon"].includes(i.rarity)).map((i: any) => i.id);
  const auto = inv.auto_salvage ?? { enabled: false, max_rarity: "common", below_equipped: false, slots: [] };
  return (
    <Screen title="Equipaggiamento" subtitle={`${inv.count}/${inv.capacity} nell'inventario`} testID="gear-screen" right={<Btn title="Auto-equip" small variant="ghost" onPress={() => autoEquip.mutate({})} testID="auto-equip-button" />}>
      <Panel testID="equipped-grid">
        <Row style={{ flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
          {Object.keys(inv.equipped).map((slot) => {
            const it = eqById[slot];
            const fc = forge?.[slot];
            return (
              <Pressable key={slot} testID={`slot-${slot}`} onPress={() => { if (it) { setSel(it); sheet.current?.present(); } }} style={{ alignItems: "center", width: 96, gap: 2 }}>
                <RarityFrame rarity={it?.rarity ?? "common"} size={60}>
                  <Icon name={SLOT_ICON[slot]} size={26} color={it ? rarityColor(colors, it.rarity) : colors.muted} />
                  {inv.forge[slot] ? <View style={{ position: "absolute", bottom: -2, right: -2, backgroundColor: colors.gold, borderRadius: 3, paddingHorizontal: 3 }}><Txt v="small" color={colors.onBrandSecondary} style={{ fontSize: 9 }}>+{inv.forge[slot]}</Txt></View> : null}
                </RarityFrame>
                <Txt v="small">{SLOT_LABEL[slot]}</Txt>
                <Txt v="small" color={colors.muted} style={{ fontSize: 10 }}>{it ? `Lv ${it.item_level} · ${fmt(it.score_forged)}` : "vuoto"}</Txt>
                {fc?.next_cost ? (
                  <Pressable testID={`forge-${slot}`} onPress={() => forgeUp.mutate({ slot })} style={{ flexDirection: "row", gap: 4, alignItems: "center", paddingVertical: 4, paddingHorizontal: 6, borderWidth: 1, borderColor: colors.gold, borderRadius: 4, minHeight: 28 }}>
                    <Icon name="anvil" size={12} color={colors.goldBright} /><Txt v="small" style={{ fontSize: 10 }}>{fmt(fc.next_cost.gold)} / {fc.next_cost.forge_dust}</Txt>
                  </Pressable>
                ) : null}
              </Pressable>
            );
          })}
        </Row>
        <Txt v="small" color={colors.muted} style={{ textAlign: "center", marginTop: 6 }}>Forgia: +4%/livello (+0.2% quadratico) sulle statistiche dello slot, max +20. Costo in Oro e Polvere di Forgia.</Txt>
      </Panel>
      <Row style={{ justifyContent: "space-between" }}>
        <Txt v="h2">Inventario</Txt>
        <Row>
          <Btn title={`Smantella comuni (${junk.length})`} small variant="secondary" disabled={!junk.length} onPress={() => salvage.mutate({ item_ids: junk })} testID="salvage-junk-button" />
          <Btn title="Espandi" small variant="ghost" onPress={() => expand.mutate({})} testID="expand-inventory-button" />
        </Row>
      </Row>
      <View style={{ marginHorizontal: -16 }}>
        <ChipRow>
          <Chip label="Tutti" selected={filter === "all"} onPress={() => setFilter("all")} testID="filter-all" />
          <Chip label="Equipaggiati" selected={filter === "equipped"} onPress={() => setFilter("equipped")} testID="filter-equipped" />
          {Object.keys(SLOT_LABEL).map((s) => <Chip key={s} label={SLOT_LABEL[s]} selected={filter === s} onPress={() => setFilter(s)} testID={`filter-${s}`} />)}
        </ChipRow>
      </View>
      {items.length === 0 ? <Txt v="small" color={colors.muted}>Nessun oggetto. Vinci stage, dungeon ed eventi per trovare equipaggiamento.</Txt> : null}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {items.map((it: any) => (
          <Pressable key={it.id} testID={`item-${it.id}`} onPress={() => { setSel(it); sheet.current?.present(); }} style={{ width: "22%", flexGrow: 1, maxWidth: 96, alignItems: "center", gap: 2 }}>
            <RarityFrame rarity={it.rarity} size={58}>
              <Icon name={SLOT_ICON[it.slot]} size={24} color={rarityColor(colors, it.rarity)} />
              {it.equipped_slot ? <View style={{ position: "absolute", top: -6, right: -6, backgroundColor: colors.success, borderRadius: 8, padding: 2 }}><Icon name="check" size={10} color={colors.onSuccess} /></View> : null}
            </RarityFrame>
            <Txt v="small" style={{ fontSize: 10 }}>Lv {it.item_level} · {fmt(it.score)}</Txt>
          </Pressable>
        ))}
      </View>
      {inv.auto_salvage_unlocked ? (
        <Panel variant="wood" testID="auto-salvage-panel">
          <Row style={{ justifyContent: "space-between" }}>
            <Txt v="h3">Auto-smantellamento</Txt>
            <Btn title={auto.enabled ? "Attivo" : "Disattivo"} small variant={auto.enabled ? "gold" : "secondary"} onPress={() => setAuto.mutate({ ...auto, enabled: !auto.enabled })} testID="auto-salvage-toggle" />
          </Row>
          <Txt v="small" color={colors.muted}>Smantella automaticamente i drop fino a: {RARITY_LABEL[auto.max_rarity]}{auto.below_equipped ? " · sotto il livello equipaggiato" : ""}</Txt>
          <Row style={{ flexWrap: "wrap", marginTop: 6 }}>
            {["common", "uncommon", "rare", "epic"].map((r) => <Chip key={r} label={RARITY_LABEL[r]} selected={auto.max_rarity === r} onPress={() => setAuto.mutate({ ...auto, max_rarity: r })} testID={`auto-salvage-${r}`} />)}
            <Chip label="Sotto equip." selected={auto.below_equipped} onPress={() => setAuto.mutate({ ...auto, below_equipped: !auto.below_equipped })} testID="auto-salvage-below" />
          </Row>
        </Panel>
      ) : <Txt v="small" color={colors.muted}>Auto-smantellamento: si sblocca allo stage 20.</Txt>}
      <Sheet ref={sheet} title={sel ? `${RARITY_LABEL[sel.rarity]} ${SLOT_LABEL[sel.slot]}` : ""} testID="item-sheet">
        {sel ? <ItemDetail item={sel} equipped={eqById[sel.slot]} forgeLevel={inv.forge[sel.slot]} onEquip={() => equip.mutate({ item_id: sel.id }, { onSuccess: () => sheet.current?.dismiss() })} onUnequip={() => unequip.mutate({ slot: sel.slot }, { onSuccess: () => sheet.current?.dismiss() })} onSalvage={() => salvage.mutate({ item_ids: [sel.id] }, { onSuccess: () => sheet.current?.dismiss() })} onReforge={(i: number) => reforge.mutate({ item_id: sel.id, affix_index: i }, { onSuccess: (d: any) => setSel({ ...sel, affixes: d.affixes }) })} busy={equip.isPending || salvage.isPending || reforge.isPending} rubiesStones={profile.resources.reforge_stone} /> : null}
      </Sheet>
    </Screen>
  );
}

function ItemDetail({ item, equipped, forgeLevel, onEquip, onUnequip, onSalvage, onReforge, busy, rubiesStones }: any) {
  const { colors } = useTheme();
  const isEq = !!item.equipped_slot;
  const cmp = equipped && equipped.id !== item.id ? equipped : null;
  const mult = 1 + 0.04 * (forgeLevel ?? 0) + 0.002 * (forgeLevel ?? 0) ** 2;
  return (
    <View style={{ gap: 10 }}>
      <Row style={{ gap: 12 }}>
        <RarityFrame rarity={item.rarity} size={72}><Icon name={SLOT_ICON[item.slot]} size={34} color={rarityColor(colors, item.rarity)} /></RarityFrame>
        <View style={{ flex: 1 }}>
          <Txt v="h3">Livello oggetto {item.item_level}</Txt>
          <Txt v="small" color={colors.muted}>Origine: {item.source} · Punteggio {fmt(item.score)}{forgeLevel ? ` → ${fmt(item.score * mult)} con forgia +${forgeLevel}` : ""}</Txt>
        </View>
      </Row>
      <Panel variant="parchment">
        {Object.entries(item.stats).map(([k, v]) => {
          const other = cmp?.stats?.[k] ?? 0;
          const d = (v as number) - other;
          return (
            <Row key={k} style={{ justifyContent: "space-between" }}>
              <Txt v="bodyBold" color={colors.onSurfaceInverse}>{k === "attack" ? "Attacco" : k === "defense" ? "Difesa" : "Salute"}</Txt>
              <Row><Txt v="body" color={colors.onSurfaceInverse}>{fmt(v as number)}</Txt>{cmp ? <Txt v="small" color={d >= 0 ? colors.forest : colors.burgundy}>({d >= 0 ? "+" : ""}{fmt(d)})</Txt> : null}</Row>
            </Row>
          );
        })}
        {cmp ? <Txt v="small" color={colors.onSurfaceInverse} style={{ marginTop: 4 }}>Confronto con l&apos;oggetto equipaggiato (Lv {cmp.item_level}, {RARITY_LABEL[cmp.rarity]}): punteggio {fmt(item.score)} vs {fmt(cmp.score)}</Txt> : null}
      </Panel>
      {item.affixes?.length ? (
        <View style={{ gap: 6 }}>
          <Txt v="caption">Affissi secondari</Txt>
          {item.affixes.map((a: any, i: number) => (
            <Row key={i} style={{ justifyContent: "space-between" }} testID={`affix-${i}`}>
              <Txt v="body">{AFFIX_LABEL[a.key] ?? a.key}: <Txt v="bodyBold" color={colors.goldBright}>{a.value}%</Txt></Txt>
              <Btn title={`Riforgia (${{ common: 0, uncommon: 0, rare: 1, epic: 2, legendary: 3, mythic: 4, ancient: 5 }[item.rarity as string] ?? 1} pietre)`} small variant="ghost" onPress={() => onReforge(i)} disabled={busy} testID={`reforge-${i}`} />
            </Row>
          ))}
          <Txt v="small" color={colors.muted}>Pietre di Riforgia disponibili: {rubiesStones}</Txt>
        </View>
      ) : null}
      <Row>
        {isEq ? <Btn title="Rimuovi" variant="secondary" onPress={onUnequip} disabled={busy} style={{ flex: 1 }} testID="unequip-button" /> : <Btn title="Equipaggia" onPress={onEquip} disabled={busy} style={{ flex: 1 }} testID="equip-button" />}
        {!isEq ? <Btn title="Smantella" variant="danger" onPress={onSalvage} disabled={busy} style={{ flex: 1 }} testID="salvage-button" /> : null}
      </Row>
    </View>
  );
}
