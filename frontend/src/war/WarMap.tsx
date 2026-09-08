// Alliance territory map (19x19): illustrated 3D-tilted tiles, calm palette (gold = yours, crimson = rivals, stone = free),
// banners on home castles, pulsing war rings, D-pad + zoom and a "go to my territory" button.
import React, { useEffect, useMemo, useRef } from "react";
import { Image, Pressable, Text, View, useWindowDimensions } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { hashStr } from "@/src/battle/regions";
import { ART } from "@/src/art/manifest";
import { useProfile } from "@/src/api/hooks";
import { skinArt } from "@/src/art";
import { fonts, useTheme } from "@/src/theme";
import { Btn, Txt } from "@/src/ui";
import { ZoomPan, ZoomPanRef } from "@/src/ui/ZoomPan";

export const NODE_LABEL: Record<string, string> = { wilderness: "Terre selvagge", village: "Villaggio", town: "Borgo", mine: "Miniera", fortress: "Fortezza", city: "Città", home_castle: "Castello" };
const OWN = "#E3C16F", RIVAL = "#B3162B", WAR = "#FF4D3D";
const TILE_FOR: Record<string, string[]> = { wilderness: ["plains", "forest", "hills", "plains", "forest", "mountains", "river"], village: ["village"], town: ["village"], mine: ["mine"], fortress: ["fort"], city: ["city"], home_castle: ["fort"] };
const CELL = 40;
const GRID = 19;

export function allianceColor(id: string | null | undefined, mine: string | null | undefined): string {
  if (!id) return "transparent";
  return id === mine ? OWN : RIVAL;
}

type Node = { node_id: number; x: number; y: number; type: string; owner: string | null };

export function WarMap({ nodes, myAlliance, onSelect, selected, contested, alliances, attackable }: { nodes: Node[]; myAlliance: string | null; onSelect: (n: any) => void; selected?: number | null; contested: Set<number>; alliances?: Record<string, { name: string; tag: string; home_node?: number | null }>; attackable?: Set<number> }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const { data: profile } = useProfile();
  const zoom = useRef<ZoomPanRef>(null);
  const vw = width - 24, vh = Math.round(vw * 0.92);
  const size = CELL * GRID;
  const mine = useMemo(() => nodes.filter((n) => n.owner && n.owner === myAlliance), [nodes, myAlliance]);
  const centroid = useMemo(() => {
    if (!mine.length) return null;
    return { x: (mine.reduce((s, n) => s + n.x, 0) / mine.length + 0.5) * CELL, y: (mine.reduce((s, n) => s + n.y, 0) / mine.length + 0.5) * CELL };
  }, [mine]);
  const goMine = () => centroid && zoom.current?.focus(centroid.x, centroid.y, 1.6);
  useEffect(() => { const t = setTimeout(goMine, 350); return () => clearTimeout(t); }, [centroid?.x, centroid?.y]); // eslint-disable-line react-hooks/exhaustive-deps
  const banner = profile?.cosmetics?.army ? skinArt(profile.cosmetics.army.key) : undefined;
  const rivals = Object.entries(alliances ?? {}).filter(([id]) => id !== myAlliance);
  return (
    <View style={{ gap: 8 }}>
      <View style={{ borderWidth: 3, borderColor: colors.gold, borderRadius: 8, overflow: "hidden", backgroundColor: "#141a12", alignSelf: "center" }}>
        <ZoomPan ref={zoom} width={vw} height={vh} contentWidth={size} contentHeight={size} maxScale={3.2} dpad testID="war-zoom">
          <View style={{ width: size, height: size, backgroundColor: "#2a3a26" }} testID="war-map">
            {nodes.map((n) => <Tile key={n.node_id} n={n} mine={myAlliance} selected={selected === n.node_id} contested={contested.has(n.node_id)} attackable={!!attackable?.has(n.node_id)} onSelect={onSelect} tag={n.owner ? alliances?.[n.owner]?.tag : undefined} banner={n.owner === myAlliance ? banner : undefined} />)}
          </View>
        </ZoomPan>
        {myAlliance && centroid ? (
          <View style={{ position: "absolute", right: 6, bottom: 6 }}>
            <Btn title="Il mio territorio" small variant="gold" icon="crosshairs-gps" onPress={goMine} testID="war-goto-mine" />
          </View>
        ) : null}
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10, alignItems: "center" }} testID="war-map-legend">
        {myAlliance ? <Legend color={OWN} label={`Tuo territorio · ${mine.length} nodi`} /> : null}
        {rivals.length ? <Legend color={RIVAL} label={`Rivali: ${rivals.map(([, a]) => `[${a.tag}]`).join(" ")}`} /> : null}
        <Legend color="transparent" border={WAR} label="Guerra in corso" />
        {attackable?.size ? <Legend color="transparent" border={colors.goldBright} label="Attaccabile" /> : null}
        <Legend color="transparent" border={colors.parchment} label="Libero" />
      </View>
      <Txt v="caption" color={colors.muted}>Trascina o usa le frecce per muoverti · pizzica o usa +/− per lo zoom · tocca un nodo per i dettagli</Txt>
    </View>
  );
}

function Tile({ n, mine, selected, contested, attackable, onSelect, tag, banner }: { n: Node; mine: string | null; selected: boolean; contested: boolean; attackable?: boolean; onSelect: (n: any) => void; tag?: string; banner?: number }) {
  const { colors } = useTheme();
  const variants = TILE_FOR[n.type] ?? TILE_FOR.wilderness;
  const tile = n.type === "home_castle" && !n.owner ? "ruins" : variants[hashStr(`${n.node_id}`) % variants.length];
  const img = ART[`tiles/${tile}`];
  const own = n.owner ? (n.owner === mine ? OWN : RIVAL) : null;
  // unowned base sites stay quiet ruins; buildings only where there is something to conquer
  const castle = n.type === "home_castle" ? (n.owner ? ART["buildings/castle_fortress"] ?? ART["buildings/castle"] : undefined) : n.type === "city" ? ART["buildings/alliance_hall"] : n.type === "fortress" ? ART["buildings/walls"] : n.type === "mine" ? ART["buildings/iron_mine"] : n.type === "town" ? ART["buildings/warehouse"] : undefined;
  return (
    <Pressable testID={`war-node-${n.node_id}`} onPress={() => onSelect(n)} style={{ position: "absolute", left: n.x * CELL, top: n.y * CELL, width: CELL, height: CELL, alignItems: "center", justifyContent: "center" }}>
      {img ? <Image source={img} style={{ position: "absolute", width: CELL, height: CELL }} resizeMode="cover" /> : null}
      {/* bevel: light top edge + dark bottom edge give the tiles a raised, 3D feel */}
      <View style={{ position: "absolute", top: 0, left: 0, width: CELL, height: 2, backgroundColor: "rgba(255,255,255,0.28)" }} />
      <View style={{ position: "absolute", bottom: 0, left: 0, width: CELL, height: 3, backgroundColor: "rgba(0,0,0,0.42)" }} />
      {own ? <View style={{ position: "absolute", width: CELL, height: CELL, backgroundColor: own, opacity: own === OWN ? 0.42 : 0.32 }} /> : null}
      <View style={{ position: "absolute", width: CELL, height: CELL, borderWidth: own ? 3 : 0.5, borderColor: own ?? "rgba(0,0,0,0.25)" }} />
      {own === OWN ? <View style={{ position: "absolute", top: 3, right: 3, width: 9, height: 9, borderRadius: 5, backgroundColor: OWN, borderWidth: 1, borderColor: "#11151C" }} testID={`war-own-${n.node_id}`} /> : null}
      {castle ? <Image source={castle} style={{ width: CELL * (n.type === "home_castle" ? 0.9 : 0.6), height: CELL * (n.type === "home_castle" ? 0.9 : 0.6), marginTop: -CELL * 0.08 }} resizeMode="contain" /> : null}
      {n.type === "home_castle" && n.owner ? (
        banner ? <Image source={banner} style={{ position: "absolute", left: 1, top: -CELL * 0.35, width: CELL * 0.45, height: CELL * 0.8 }} resizeMode="contain" /> : (
          <View style={{ position: "absolute", left: 2, top: -8, paddingHorizontal: 2, backgroundColor: own ?? colors.iron, borderWidth: 1, borderColor: "#11151C", borderRadius: 2 }}>
            <Text style={{ fontFamily: fonts.bodyBold, fontSize: 7, color: own === OWN ? "#11151C" : "#FFFFFF" }}>{tag ?? "?"}</Text>
          </View>
        )
      ) : null}
      {contested ? <WarRing /> : null}
      {attackable && !contested ? <View pointerEvents="none" style={{ position: "absolute", width: CELL - 2, height: CELL - 2, margin: 1, borderWidth: 2, borderStyle: "dashed", borderColor: colors.goldBright, borderRadius: 3 }} testID={`war-attackable-${n.node_id}`} /> : null}
      {selected ? <View style={{ position: "absolute", width: CELL, height: CELL, borderWidth: 2.5, borderColor: "#FFFFFF" }} /> : null}
    </Pressable>
  );
}

function WarRing() {
  const p = useSharedValue(0);
  useEffect(() => { p.value = withRepeat(withSequence(withTiming(1, { duration: 600, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 600, easing: Easing.inOut(Easing.quad) })), -1, false); }, [p]);
  const st = useAnimatedStyle(() => ({ opacity: 0.55 + 0.45 * p.value, transform: [{ scale: 1 + 0.06 * p.value }] }));
  return <Animated.View pointerEvents="none" style={[{ position: "absolute", width: CELL - 4, height: CELL - 4, borderWidth: 2.5, borderColor: WAR, borderRadius: 4 }, st]} testID="war-ring" />;
}

function Legend({ color, label, border }: { color: string; label: string; border?: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
      <View style={{ width: 12, height: 12, backgroundColor: color, borderWidth: 2, borderColor: border ?? "rgba(0,0,0,0.4)", borderRadius: 2 }} />
      <Text style={{ fontFamily: fonts.body, fontSize: 11, color: colors.muted }}>{label}</Text>
    </View>
  );
}
