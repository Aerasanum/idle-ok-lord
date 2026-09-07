// Fixed premium 2.5D kingdom view. Seven canonical visual tiers drive walls, density, banners and landmarks.
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect, useMemo, useState } from "react";
import { Image, Pressable, Text, View, useWindowDimensions } from "react-native";

import { buildingArt, kingdomGround } from "@/src/art";
import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName } from "@/src/ui";
import { ConstructionSite, Flag, Peasant, Smoke } from "./life";
import { ZoomPan } from "@/src/ui/ZoomPan";

const SMOKING = new Set(["castle", "farm", "lumberyard", "workshop", "barracks", "iron_mine", "gold_mine", "temple", "university"]);

const BUILDING_ICON: Record<string, IconName> = { castle: "castle", farm: "barley", lumberyard: "pine-tree", clay_pit: "cube", iron_mine: "pickaxe", gold_mine: "gold", warehouse: "warehouse", barracks: "sword-cross", stable: "horse", workshop: "hammer-wrench", university: "school", walls: "wall", alliance_hall: "account-group", bestiary: "paw", temple: "church", mythic_sanctuary: "star-four-points" };
const LAYOUT: Record<string, [number, number]> = { castle: [0.5, 0.4], walls: [0.5, 0.9], farm: [0.14, 0.74], lumberyard: [0.86, 0.74], clay_pit: [0.17, 0.54], iron_mine: [0.83, 0.52], gold_mine: [0.86, 0.32], warehouse: [0.32, 0.62], barracks: [0.68, 0.62], stable: [0.72, 0.84], workshop: [0.28, 0.84], university: [0.14, 0.32], alliance_hall: [0.32, 0.2], bestiary: [0.68, 0.2], temple: [0.5, 0.1], mythic_sanctuary: [0.5, 0.63] };

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
  const ground = kingdomGround();
  const sizeOf = (key: string, level: number) => (key === "castle" ? Math.min(width * 0.34, 92 + t * 8) : key === "walls" ? width * 0.5 : Math.min(width * 0.22, 54 + Math.min(level, 20) * 1.2));
  return (
    <View style={{ height: h, overflow: "hidden", borderBottomWidth: 3, borderColor: colors.gold }} testID="kingdom-scene">
    <ZoomPan width={width} height={h} testID="kingdom-zoom">
      {ground ? (
        <Image source={ground} style={{ position: "absolute", left: 0, right: 0, top: 0, height: h, width }} resizeMode="cover" />
      ) : (
        <>
          <LinearGradient colors={[skyTop, "#6E7C99"]} style={{ position: "absolute", left: 0, right: 0, top: 0, height: h * 0.4 }} />
          <LinearGradient colors={["#4F6B3A", "#3C5230"]} style={{ position: "absolute", left: 0, right: 0, top: h * 0.38, bottom: 0 }} />
          <View style={{ position: "absolute", left: width * 0.5 - 6, top: h * 0.5, width: 12, height: h * 0.5, backgroundColor: "rgba(120,100,70,0.55)", transform: [{ skewX: "8deg" }] }} />
          <View style={{ position: "absolute", left: width * 0.1, top: h * 0.68, width: width * 0.8, height: 8, backgroundColor: "rgba(120,100,70,0.5)" }} />
        </>
      )}
      {/* soft vignette + dwellings density hint (tier growth) */}
      <LinearGradient colors={["rgba(0,0,0,0.25)", "transparent", "rgba(0,0,0,0.3)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} pointerEvents="none" />
      {(() => {
        const wb = buildings.find((b) => b.key === "walls");
        return wb ? <WallRing width={width} h={h} level={wb.level} unlocked={wb.unlocked} tier={t} color={wallColor} heraldic={heraldicColor} queued={queued.walls ? progressOf(queued.walls) : null} onPress={() => onSelect("walls")} /> : null;
      })()}
      <View style={{ position: "absolute", left: width * 0.36, right: width * 0.36, top: h * 0.58, flexDirection: "row", flexWrap: "wrap", gap: 4, justifyContent: "center" }} pointerEvents="none">
        {Array.from({ length: Math.min(houses, 14) }).map((_, i) => (
          <View key={i} style={{ width: 8 + (i % 3) * 2, height: 6 + (i % 2) * 3, backgroundColor: i % 5 === 0 ? colors.parchmentDark : colors.wood, borderTopWidth: 3, borderColor: t >= 5 ? colors.gold : t >= 3 ? "#7A4E3B" : "#5A4A3A", opacity: 0.85 }} />
        ))}
      </View>
      {/* villagers on the roads */}
      {Array.from({ length: peasants }).map((_, i) => (i % 3 === 2
        ? <Peasant key={`v${i}`} x0={width * 0.5 - 4 + (i % 2) * 6} y0={h * 0.5} x1={width * 0.5 - 4 + (i % 2) * 6} y1={h * 0.96} seed={i * 7 + castleLevel} size={10} />
        : <Peasant key={`p${i}`} x0={width * (0.06 + (i % 4) * 0.05)} y0={h * 0.62 - 6 + (i % 2) * 5} x1={width * (0.94 - (i % 3) * 0.06)} y1={h * 0.62 - 6 + (i % 2) * 5} seed={i * 13 + t} size={10 + (i % 2)} />))}
      {/* chimney smoke on working buildings */}
      {buildings.filter((b) => b.level > 0 && SMOKING.has(b.key) && !queued[b.key] && LAYOUT[b.key]).map((b) => {
        const pos = LAYOUT[b.key];
        const size = sizeOf(b.key, b.level);
        return <Smoke key={`s${b.key}`} x={width * pos[0] + size * 0.18} y={h * pos[1] - size / 2 + 4} />;
      })}
      {/* buildings (walls are drawn as the perimeter ring above) */}
      {buildings.filter((b) => b.key !== "walls").map((b) => {
        const pos = LAYOUT[b.key];
        if (!pos) return null;
        const size = sizeOf(b.key, b.level);
        const locked = !b.unlocked;
        const built = b.level > 0;
        const img = buildingArt(b.key, t);
        return (
          <Pressable key={b.key} testID={`building-${b.key}`} onPress={() => onSelect(b.key)} style={{ position: "absolute", left: width * pos[0] - size / 2, top: h * pos[1] - size / 2, width: size, height: size + 14, alignItems: "center", opacity: locked ? 0.5 : 1 }}>
            {img ? (
              <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
                <View style={{ position: "absolute", bottom: size * 0.06, width: size * 0.8, height: size * 0.22, borderRadius: size, backgroundColor: "#000", opacity: 0.28 }} />
                <Image source={img} style={{ width: size, height: size, opacity: built ? 1 : 0.55 }} resizeMode="contain" />
                {!built ? <View style={{ position: "absolute", width: Math.min(34, size * 0.42), height: Math.min(34, size * 0.42), borderRadius: 20, backgroundColor: colors.overlay, borderWidth: 1.5, borderColor: locked ? colors.iron : colors.gold, alignItems: "center", justifyContent: "center" }}><Icon name={locked ? "lock" : "hammer"} size={Math.min(18, size * 0.22)} color={locked ? colors.muted : colors.goldBright} /></View> : null}
                {b.key === "castle" ? <View style={{ position: "absolute", top: size * 0.12, left: size * 0.5 }}><Flag color={heraldicColor} height={18} /></View> : null}
                {queued[b.key] ? <ConstructionSite size={size} progress={progressOf(queued[b.key])} /> : null}
              </View>
            ) : (
              <View style={{ width: size, height: size, borderRadius: b.key === "castle" ? 8 : 6, backgroundColor: built ? (b.key === "castle" ? wallColor : colors.woodDark) : "rgba(0,0,0,0.35)", borderWidth: 2, borderColor: locked ? colors.iron : b.key === "castle" ? colors.gold : colors.wood, alignItems: "center", justifyContent: "center", borderStyle: built ? "solid" : "dashed" }}>
                <Icon name={locked ? "lock" : BUILDING_ICON[b.key]} size={size * 0.5} color={locked ? colors.muted : b.key === "castle" ? colors.goldBright : colors.parchment} />
                {b.key === "castle" ? <Flag color={heraldicColor} height={18} /> : null}
                {queued[b.key] ? <ConstructionSite size={size} progress={progressOf(queued[b.key])} /> : null}
              </View>
            )}
            <Text style={{ fontFamily: fonts.bodyBold, fontSize: 9, color: colors.onSurface, backgroundColor: colors.overlay, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 3, marginTop: -6, borderWidth: 1, borderColor: b.key === "castle" ? colors.gold : colors.wood }} numberOfLines={1}>{built ? `${size >= 84 ? `${b.name.split(" /")[0]} · ` : ""}Lv ${b.level}` : locked ? "Bloccato" : "Costruisci"}</Text>
          </Pressable>
        );
      })}
      <View style={{ position: "absolute", left: 10, top: 8, backgroundColor: colors.overlay, borderColor: colors.gold, borderWidth: 1, borderRadius: 4, paddingHorizontal: 8, paddingVertical: 4 }} pointerEvents="none">
        <Text style={{ fontFamily: fonts.display, fontSize: 18, color: colors.goldBright }} testID="kingdom-tier-label">{tier.name}</Text>
        <Text style={{ fontFamily: fonts.body, fontSize: 11, color: colors.onSurface }}>Castello {castleLevel} · Tier {t} · {tier.landmark}</Text>
      </View>
    </ZoomPan>
    </View>
  );
}

/** City walls: a real perimeter (thickness, towers and gatehouse grow with the wall level) instead of a small building icon. */
function WallRing({ width, h, level, unlocked, tier, color, heraldic, queued, onPress }: { width: number; h: number; level: number; unlocked: boolean; tier: number; color: string; heraldic: string; queued: number | null; onPress: () => void }) {
  const { colors } = useTheme();
  const built = level > 0;
  const lv = Math.min(30, level);
  const thick = built ? 10 + Math.round(lv * 0.5) : 4; // 10..25px
  const towerR = built ? 14 + Math.round(lv * 0.6) : 0; // corner towers 14..32
  const gate = built ? Math.min(width * 0.4, 84 + lv * 2.4) : 72; // gatehouse art 84..156
  const left = width * 0.05, right = width * 0.05, top = h * 0.17, bottom = h * 0.02;
  const dark = "rgba(0,0,0,0.35)", light = "rgba(255,255,255,0.22)";
  const img = buildingArt("walls", tier);
  const corners = [{ x: left, y: top }, { x: width - right, y: top }, { x: left, y: h - bottom }, { x: width - right, y: h - bottom }];
  return (
    <>
      {built ? (
        <View pointerEvents="none" style={{ position: "absolute", left, right, top, bottom }} testID="kingdom-walls">
          {/* wall body + crenellations (dashed cap) + shading */}
          <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, borderWidth: thick, borderColor: color, borderRadius: 40 + thick }} />
          <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, borderWidth: Math.max(3, thick * 0.38), borderColor: dark, borderStyle: "dashed", borderRadius: 40 + thick }} />
          <View style={{ position: "absolute", left: thick * 0.55, right: thick * 0.55, top: thick * 0.55, bottom: thick * 0.55, borderWidth: 1.5, borderColor: light, borderRadius: 40 }} />
          <View style={{ position: "absolute", left: thick, right: thick, top: thick, bottom: thick, borderTopWidth: thick * 0.5, borderColor: dark, borderRadius: 34 }} />
          {/* corner towers with roofs and pennants */}
          {corners.map((c, i) => (
            <View key={i} style={{ position: "absolute", left: c.x - left - towerR, top: c.y - top - towerR * 1.3, width: towerR * 2, height: towerR * 2.3, alignItems: "center" }}>
              <View style={{ width: 0, height: 0, borderLeftWidth: towerR * 0.95, borderRightWidth: towerR * 0.95, borderBottomWidth: towerR * 0.9, borderLeftColor: "transparent", borderRightColor: "transparent", borderBottomColor: tier >= 5 ? colors.gold : "#3C4A66" }} />
              <View style={{ width: towerR * 2, height: towerR * 1.5, borderRadius: towerR * 0.5, backgroundColor: color, borderWidth: 2, borderColor: dark }}>
                <View style={{ position: "absolute", left: towerR * 0.35, right: towerR * 0.35, top: towerR * 0.25, height: towerR * 0.35, borderRadius: 2, backgroundColor: dark }} />
              </View>
              <View style={{ position: "absolute", top: -towerR * 0.7, alignItems: "center" }}><View style={{ width: 2, height: towerR * 0.9, backgroundColor: "#5A4A3A" }} /><View style={{ position: "absolute", top: 0, left: 2, width: 0, height: 0, borderTopWidth: towerR * 0.25, borderBottomWidth: towerR * 0.25, borderLeftWidth: towerR * 0.6, borderTopColor: "transparent", borderBottomColor: "transparent", borderLeftColor: heraldic }} /></View>
            </View>
          ))}
        </View>
      ) : (
        <View pointerEvents="none" style={{ position: "absolute", left, right, top, bottom, borderWidth: thick, borderColor: unlocked ? color : colors.iron, borderStyle: "dashed", borderRadius: 50, opacity: 0.45 }} testID="kingdom-walls-unbuilt" />
      )}
      {/* gatehouse (tap target for the walls building) */}
      <Pressable testID="building-walls" onPress={onPress} style={{ position: "absolute", left: width * 0.5 - gate / 2, top: h - bottom - gate * 0.82, width: gate, height: gate + 14, alignItems: "center", opacity: unlocked ? 1 : 0.5 }}>
        <View style={{ width: gate, height: gate, alignItems: "center", justifyContent: "center" }}>
          <View style={{ position: "absolute", bottom: gate * 0.08, width: gate * 0.85, height: gate * 0.2, borderRadius: gate, backgroundColor: "#000", opacity: 0.3 }} />
          {img ? <Image source={img} style={{ width: gate, height: gate, opacity: built ? 1 : 0.5 }} resizeMode="contain" /> : <Icon name="wall" size={gate * 0.5} color={colors.parchment} />}
          {!built ? <View style={{ position: "absolute", width: 34, height: 34, borderRadius: 20, backgroundColor: colors.overlay, borderWidth: 1.5, borderColor: unlocked ? colors.gold : colors.iron, alignItems: "center", justifyContent: "center" }}><Icon name={unlocked ? "hammer" : "lock"} size={18} color={unlocked ? colors.goldBright : colors.muted} /></View> : null}
          {queued !== null ? <ConstructionSite size={gate} progress={queued} /> : null}
        </View>
        <Text style={{ fontFamily: fonts.bodyBold, fontSize: 9, color: colors.onSurface, backgroundColor: colors.overlay, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 3, marginTop: -gate * 0.16, borderWidth: 1, borderColor: colors.wood }} numberOfLines={1}>{built ? `Mura · Lv ${level}` : unlocked ? "Costruisci le mura" : "Bloccato"}</Text>
      </Pressable>
    </>
  );
}
