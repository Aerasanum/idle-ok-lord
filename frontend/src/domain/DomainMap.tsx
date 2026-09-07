// Personal Domain 10x10: illustrated top-down terrain tiles (fog variant until conquered), 3D table tilt, conquest reveal animation.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import React, { memo, useEffect, useRef, useState } from "react";
import { Image, Pressable, Text, View, useWindowDimensions } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { ART } from "@/src/art/manifest";
import { playSfx } from "@/src/audio";
import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName } from "@/src/ui";

const TERRAIN: Record<string, { color: string; icon?: IconName }> = { plains: { color: "#6F8A46" }, forest: { color: "#3E5B3A", icon: "pine-tree" }, hills: { color: "#7A7050" }, river: { color: "#3F6E9E", icon: "waves" }, mountains: { color: "#5B5B60", icon: "image-filter-hdr" }, village: { color: "#8A7A50", icon: "home-group" }, mine: { color: "#6E5A4A", icon: "pickaxe" }, ruins: { color: "#7B7462", icon: "pillar" }, fort: { color: "#5C6470", icon: "chess-rook" }, city: { color: "#B89947", icon: "city-variant" } };
const SEEN_KEY = "idle1.domain.seenOwned";

type Tile = { index: number; x: number; y: number; terrain: string; owned: boolean; order: number; unlock_stage: number };

const TileView = memo(function TileView({ t, cell, heraldicColor, isNext, selected, reveal, growth, onSelect }: { t: Tile; cell: number; heraldicColor: string; isNext: boolean; selected: boolean; reveal: number; growth: string; onSelect: (t: Tile) => void }) {
  const { colors } = useTheme();
  const ter = TERRAIN[t.terrain] ?? TERRAIN.plains;
  const img = ART[`tiles/${t.terrain}`] ?? ART["tiles/plains"];
  const fog = ART[`tiles/${t.terrain}_fog`] ?? ART["tiles/plains_fog"];
  const pop = useSharedValue(0);
  const glow = useSharedValue(0);
  useEffect(() => {
    if (!reveal) return;
    pop.value = withDelay(reveal, withSequence(withTiming(1, { duration: 260, easing: Easing.out(Easing.back(2)) }), withTiming(0, { duration: 500 })));
  }, [reveal, pop]);
  useEffect(() => {
    if (!isNext) return;
    glow.value = withRepeat(withSequence(withTiming(1, { duration: 700 }), withTiming(0, { duration: 700 })), -1, false);
  }, [isNext, glow]);
  const popStyle = useAnimatedStyle(() => ({ transform: [{ scale: 1 + 0.18 * pop.value }], zIndex: pop.value > 0 ? 10 : 0 }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: 0.85 * pop.value }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: 0.45 + 0.55 * glow.value }));
  return (
    <Animated.View style={[{ position: "absolute", left: t.x * cell, top: t.y * cell, width: cell, height: cell }, popStyle]}>
      <Pressable testID={`domain-tile-${t.index}`} onPress={() => onSelect(t)} style={{ width: cell, height: cell, backgroundColor: ter.color, alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
        {img ? <Image source={t.owned ? img : fog} style={{ position: "absolute", width: cell + 1, height: cell + 1 }} resizeMode="cover" /> : null}
        {!img && !t.owned ? <View style={{ position: "absolute", inset: 0, backgroundColor: "rgba(20,26,40,0.55)" } as any} /> : null}
        {t.owned ? <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 3, backgroundColor: heraldicColor, opacity: 0.9 }} /> : null}
        {!img && ter.icon ? <Icon name={ter.icon} size={cell * 0.45} color={t.owned ? colors.parchment : "rgba(255,255,255,0.45)"} /> : null}
        {t.owned && !ter.icon && growth !== "camp" && !img ? <View style={{ width: cell * 0.28, height: cell * 0.22, backgroundColor: colors.parchmentDark, borderTopWidth: 3, borderColor: growth === "imperial" || growth === "cities" ? colors.gold : colors.wood }} /> : null}
        {t.order === 0 ? <View style={{ position: "absolute", bottom: 2, paddingHorizontal: 3, backgroundColor: colors.overlay, borderRadius: 2 }}><Text style={{ fontFamily: fonts.bodyBold, fontSize: 7, color: colors.goldBright }}>SEDE</Text></View> : null}
        {selected ? <View style={{ position: "absolute", inset: 0, borderWidth: 2, borderColor: colors.onSurface } as any} /> : null}
        <Animated.View pointerEvents="none" style={[{ position: "absolute", inset: 0, backgroundColor: "#FFFFFF" } as any, flashStyle]} />
      </Pressable>
      {isNext ? <Animated.View pointerEvents="none" style={[{ position: "absolute", inset: 1, borderWidth: 2, borderColor: colors.goldBright, borderStyle: "dashed", borderRadius: 3 } as any, glowStyle]} testID={`domain-next-tile`} /> : null}
    </Animated.View>
  );
});

export function DomainMap({ tiles, ownedCount, heraldicColor, growth, onSelect, selected }: { tiles: Tile[]; ownedCount: number; heraldicColor: string; growth: string; onSelect: (t: Tile) => void; selected?: number | null }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const size = Math.min(width - 32, 420);
  const cell = size / 10;
  const [revealFrom, setRevealFrom] = useState<number | null>(null);
  const seenLoaded = useRef(false);
  // conquest reveal: tiles owned since the last visit pop in one after another
  useEffect(() => {
    if (seenLoaded.current) return;
    seenLoaded.current = true;
    AsyncStorage.getItem(SEEN_KEY).then((raw) => {
      const seen = raw ? Number(raw) : ownedCount;
      if (ownedCount > seen) {
        setRevealFrom(seen);
        setTimeout(() => playSfx("coin"), 200);
      }
      AsyncStorage.setItem(SEEN_KEY, String(ownedCount)).catch(() => {});
    }).catch(() => {});
  }, [ownedCount]);
  useEffect(() => {
    if (seenLoaded.current) AsyncStorage.setItem(SEEN_KEY, String(ownedCount)).catch(() => {});
  }, [ownedCount]);
  return (
    <View style={{ alignSelf: "center", width: size, paddingTop: 10 }} testID="domain-map-stage">
      <View style={{ position: "absolute", left: size * 0.05, right: size * 0.05, bottom: -6, height: size * 0.08, borderRadius: size, backgroundColor: "#000", opacity: 0.45 }} />
      <View style={{ width: size, height: size, borderWidth: 3, borderColor: colors.gold, backgroundColor: "#2E3A2A", borderRadius: 6, overflow: "hidden", transform: [{ perspective: 900 }, { rotateX: "26deg" }, { scale: 1.06 }] }} testID="domain-map">
        {tiles.map((t) => (
          <TileView key={t.index} t={t} cell={cell} heraldicColor={heraldicColor} isNext={t.order === ownedCount} selected={selected === t.index} growth={growth} onSelect={onSelect} reveal={revealFrom !== null && t.owned && t.order >= revealFrom ? 200 + (t.order - revealFrom) * 180 : 0} />
        ))}
        <LinearGradient colors={["rgba(0,0,0,0.25)", "transparent", "transparent", "rgba(0,0,0,0.2)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} pointerEvents="none" />
      </View>
    </View>
  );
}
