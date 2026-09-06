// Personal Domain 10x10 painted strategic map with ownership colors, roads and settlements by growth stage.
import React from "react";
import { Pressable, Text, View, useWindowDimensions } from "react-native";

import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName } from "@/src/ui";

const TERRAIN: Record<string, { color: string; icon?: IconName }> = { plains: { color: "#6F8A46" }, forest: { color: "#3E5B3A", icon: "pine-tree" }, hills: { color: "#7A7050" }, river: { color: "#3F6E9E", icon: "waves" }, mountains: { color: "#5B5B60", icon: "image-filter-hdr" }, village: { color: "#8A7A50", icon: "home-group" }, mine: { color: "#6E5A4A", icon: "pickaxe" }, ruins: { color: "#7B7462", icon: "pillar" }, fort: { color: "#5C6470", icon: "chess-rook" }, city: { color: "#B89947", icon: "city-variant" } };

export function DomainMap({ tiles, ownedCount, heraldicColor, growth, onSelect, selected }: { tiles: { index: number; x: number; y: number; terrain: string; owned: boolean; order: number; unlock_stage: number }[]; ownedCount: number; heraldicColor: string; growth: string; onSelect: (t: any) => void; selected?: number | null }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const size = Math.min(width - 32, 420);
  const cell = size / 10;
  const owned = new Set(tiles.filter((t) => t.owned).map((t) => t.index));
  return (
    <View style={{ width: size, height: size, alignSelf: "center", borderWidth: 3, borderColor: colors.gold, backgroundColor: "#2E3A2A", borderRadius: 6, overflow: "hidden" }} testID="domain-map">
      {tiles.map((t) => {
        const ter = TERRAIN[t.terrain] ?? TERRAIN.plains;
        const isNext = t.order === ownedCount;
        const roadRight = t.owned && owned.has(t.index + 1) && t.x < 9;
        const roadDown = t.owned && owned.has(t.index + 10) && t.y < 9;
        return (
          <Pressable key={t.index} testID={`domain-tile-${t.index}`} onPress={() => onSelect(t)} style={{ position: "absolute", left: t.x * cell, top: t.y * cell, width: cell, height: cell, backgroundColor: ter.color, borderWidth: 0.5, borderColor: "rgba(0,0,0,0.25)", alignItems: "center", justifyContent: "center", opacity: t.owned ? 1 : 0.55 }}>
            {t.owned ? <View style={{ position: "absolute", inset: 0, backgroundColor: heraldicColor, opacity: 0.28 } as any} /> : null}
            {roadRight ? <View style={{ position: "absolute", right: -cell * 0.25, top: cell * 0.45, width: cell * 0.5, height: 3, backgroundColor: "#C9B48A", opacity: 0.8 }} /> : null}
            {roadDown ? <View style={{ position: "absolute", bottom: -cell * 0.25, left: cell * 0.45, width: 3, height: cell * 0.5, backgroundColor: "#C9B48A", opacity: 0.8 }} /> : null}
            {ter.icon ? <Icon name={ter.icon} size={cell * 0.45} color={t.owned ? colors.parchment : "rgba(255,255,255,0.45)"} /> : t.owned && growth !== "camp" ? <View style={{ width: cell * 0.28, height: cell * 0.22, backgroundColor: colors.parchmentDark, borderTopWidth: 3, borderColor: growth === "imperial" || growth === "cities" ? colors.gold : colors.wood }} /> : null}
            {isNext ? <View style={{ position: "absolute", inset: 2, borderWidth: 2, borderColor: colors.goldBright, borderStyle: "dashed", borderRadius: 3 } as any} /> : null}
            {selected === t.index ? <View style={{ position: "absolute", inset: 0, borderWidth: 2, borderColor: colors.onSurface } as any} /> : null}
            {t.order === 0 ? <Text style={{ position: "absolute", bottom: 1, fontFamily: fonts.bodyBold, fontSize: 7, color: colors.onSurfaceInverse }}>SEDE</Text> : null}
          </Pressable>
        );
      })}
    </View>
  );
}
