// Fixed premium 2.5D kingdom view. Seven canonical visual tiers drive walls, density, banners and landmarks.
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useMemo, useState } from "react";
import { Pressable, Text, View, useWindowDimensions } from "react-native";

import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName } from "@/src/ui";
import { ConstructionSite, Flag, Peasant, Smoke } from "./life";

const SMOKING = new Set(["castle", "farm", "lumberyard", "workshop", "barracks", "iron_mine", "gold_mine", "temple", "university"]);

const BUILDING_ICON: Record<string, IconName> = { castle: "castle", farm: "barley", lumberyard: "pine-tree", clay_pit: "cube", iron_mine: "pickaxe", gold_mine: "gold", warehouse: "warehouse", barracks: "sword-cross", stable: "horse", workshop: "hammer-wrench", university: "school", walls: "wall", alliance_hall: "account-group", bestiary: "paw", temple: "church", mythic_sanctuary: "star-four-points" };
const LAYOUT: Record<string, [number, number]> = { castle: [0.5, 0.42], walls: [0.5, 0.86], farm: [0.16, 0.7], lumberyard: [0.84, 0.7], clay_pit: [0.2, 0.52], iron_mine: [0.8, 0.5], gold_mine: [0.86, 0.34], warehouse: [0.34, 0.62], barracks: [0.66, 0.62], stable: [0.7, 0.78], workshop: [0.3, 0.78], university: [0.16, 0.34], alliance_hall: [0.34, 0.26], bestiary: [0.66, 0.26], temple: [0.5, 0.14], mythic_sanctuary: [0.5, 0.66] };

export function KingdomScene({ buildings, castleLevel, tier, heraldicColor, onSelect, queued, serverTime }: { buildings: { key: string; name: string; level: number; unlocked: boolean }[]; castleLevel: number; tier: { tier: number; name: string; walls: string; roofs: string; banners: string; landmark: string; density?: string }; heraldicColor: string; onSelect: (key: string) => void; queued: Record<string, any>; serverTime?: string }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const h = Math.min(400, width * 0.95);
  const t = tier.tier;
  // construction progress ticks once per second on server-anchored time
  const offset = useMemo(() => (serverTime ? new Date(serverTime).getTime() - Date.now() : 0), [serverTime]);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!Object.keys(queued).length) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [queued]);
  const progressOf = (q: any) => {
    const a = new Date(q.started_at).getTime(), b = new Date(q.ends_at).getTime();
    return b > a ? Math.max(0, Math.min(1, (now + offset - a) / (b - a))) : 1;
  };
  const peasants = 2 + Math.min(7, t + Math.floor(castleLevel / 3));
  const wallColor = t <= 1 ? colors.wood : t <= 2 ? colors.woodDark : t <= 4 ? colors.iron : t <= 6 ? "#7C8592" : "#E6D8B8";
  const skyTop = t >= 7 ? "#2B1A4A" : t >= 5 ? "#1B2A44" : "#2E3A55";
  const houses = Math.min(40, 2 + t * 5 + Math.floor(castleLevel * 1.5));
  return (
    <View style={{ height: h, overflow: "hidden", borderBottomWidth: 3, borderColor: colors.gold }} testID="kingdom-scene">
      <LinearGradient colors={[skyTop, "#6E7C99"]} style={{ position: "absolute", left: 0, right: 0, top: 0, height: h * 0.4 }} />
      <LinearGradient colors={["#4F6B3A", "#3C5230"]} style={{ position: "absolute", left: 0, right: 0, top: h * 0.38, bottom: 0 }} />
      {/* roads */}
      <View style={{ position: "absolute", left: width * 0.5 - 6, top: h * 0.5, width: 12, height: h * 0.5, backgroundColor: "rgba(120,100,70,0.55)", transform: [{ skewX: "8deg" }] }} />
      <View style={{ position: "absolute", left: width * 0.1, top: h * 0.68, width: width * 0.8, height: 8, backgroundColor: "rgba(120,100,70,0.5)" }} />
      {/* walls */}
      <View style={{ position: "absolute", left: width * 0.08, right: width * 0.08, top: h * 0.3, bottom: h * 0.06, borderWidth: t <= 1 ? 3 : 8 + t, borderColor: wallColor, borderRadius: t <= 1 ? 4 : 40, borderStyle: t <= 1 ? "dashed" : "solid", opacity: t === 0 ? 0 : 0.85 }} />
      {t >= 3 ? [0.08, 0.92].map((x, i) => <View key={i} style={{ position: "absolute", left: width * x - 12, top: h * 0.28, width: 24, height: 44, backgroundColor: wallColor, borderRadius: 3 }}><View style={{ position: "absolute", top: -10, left: 10, width: 3, height: 12, backgroundColor: heraldicColor }} /></View>) : null}
      {/* dwellings */}
      <View style={{ position: "absolute", left: width * 0.14, right: width * 0.14, top: h * 0.46, flexDirection: "row", flexWrap: "wrap", gap: 5, justifyContent: "center" }} pointerEvents="none">
        {Array.from({ length: houses }).map((_, i) => (
          <View key={i} style={{ width: 10 + (i % 3) * 2, height: 8 + (i % 2) * 3, backgroundColor: i % 5 === 0 ? colors.parchmentDark : colors.wood, borderTopWidth: 4, borderColor: t >= 5 ? colors.gold : t >= 3 ? "#7A4E3B" : "#5A4A3A", opacity: 0.9 }} />
        ))}
      </View>
      {/* villagers on the roads */}
      {Array.from({ length: peasants }).map((_, i) => (i % 3 === 2
        ? <Peasant key={`v${i}`} x0={width * 0.5 - 4 + (i % 2) * 6} y0={h * 0.52} x1={width * 0.5 - 4 + (i % 2) * 6} y1={h * 0.94} seed={i * 7 + castleLevel} size={9} />
        : <Peasant key={`p${i}`} x0={width * (0.1 + (i % 4) * 0.05)} y0={h * 0.66 - 6 + (i % 2) * 4} x1={width * (0.9 - (i % 3) * 0.06)} y1={h * 0.66 - 6 + (i % 2) * 4} seed={i * 13 + t} size={9 + (i % 2)} />))}
      {/* chimney smoke on working buildings */}
      {buildings.filter((b) => b.level > 0 && SMOKING.has(b.key) && !queued[b.key] && LAYOUT[b.key]).map((b) => {
        const pos = LAYOUT[b.key];
        const size = b.key === "castle" ? 56 + t * 6 : 36 + Math.min(b.level, 20) * 0.8;
        return <Smoke key={`s${b.key}`} x={width * pos[0] + size * 0.22} y={h * pos[1] - size / 2 - 4} />;
      })}
      {/* buildings */}
      {buildings.map((b) => {
        const pos = LAYOUT[b.key];
        if (!pos) return null;
        const size = b.key === "castle" ? 56 + t * 6 : 36 + Math.min(b.level, 20) * 0.8;
        const locked = !b.unlocked;
        const built = b.level > 0;
        return (
          <Pressable key={b.key} testID={`building-${b.key}`} onPress={() => onSelect(b.key)} style={{ position: "absolute", left: width * pos[0] - size / 2, top: h * pos[1] - size / 2, width: size, height: size + 14, alignItems: "center", opacity: locked ? 0.45 : 1 }}>
            <View style={{ width: size, height: size, borderRadius: b.key === "castle" ? 8 : 6, backgroundColor: built ? (b.key === "castle" ? wallColor : colors.woodDark) : "rgba(0,0,0,0.35)", borderWidth: 2, borderColor: locked ? colors.iron : b.key === "castle" ? colors.gold : colors.wood, alignItems: "center", justifyContent: "center", borderStyle: built ? "solid" : "dashed" }}>
              <Icon name={locked ? "lock" : BUILDING_ICON[b.key]} size={size * 0.5} color={locked ? colors.muted : b.key === "castle" ? colors.goldBright : colors.parchment} />
              {b.key === "castle" ? <Flag color={heraldicColor} height={18} /> : null}
              {queued[b.key] ? <ConstructionSite size={size} progress={progressOf(queued[b.key])} /> : null}
            </View>
            <Text style={{ fontFamily: fonts.bodyBold, fontSize: 9, color: colors.onSurface, backgroundColor: colors.overlay, paddingHorizontal: 4, borderRadius: 2, marginTop: 2 }} numberOfLines={1}>{built ? `Lv ${b.level}` : locked ? "Bloccato" : "Costruisci"}</Text>
          </Pressable>
        );
      })}
      <View style={{ position: "absolute", left: 10, top: 8, backgroundColor: colors.overlay, borderColor: colors.gold, borderWidth: 1, borderRadius: 4, paddingHorizontal: 8, paddingVertical: 4 }} pointerEvents="none">
        <Text style={{ fontFamily: fonts.display, fontSize: 18, color: colors.goldBright }} testID="kingdom-tier-label">{tier.name}</Text>
        <Text style={{ fontFamily: fonts.body, fontSize: 11, color: colors.onSurface }}>Castello {castleLevel} · Tier {t} · {tier.landmark}</Text>
      </View>
    </View>
  );
}
