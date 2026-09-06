// Alliance territory 19x19 map with ownership colors, node types, wars in progress.
import React from "react";
import { Pressable, ScrollView, Text, View, useWindowDimensions } from "react-native";

import { fonts, useTheme } from "@/src/theme";
import { hashStr } from "@/src/battle/regions";

const NODE_COLOR: Record<string, string> = { wilderness: "#3C5230", village: "#6F8A46", town: "#8A7A50", mine: "#6E5A4A", fortress: "#5C6470", city: "#B89947", home_castle: "#800020" };
export const NODE_LABEL: Record<string, string> = { wilderness: "Terre selvagge", village: "Villaggio", town: "Borgo", mine: "Miniera", fortress: "Fortezza", city: "Città", home_castle: "Castello" };

export function allianceColor(id: string | null | undefined, mine: string | null | undefined): string {
  if (!id) return "transparent";
  if (id === mine) return "#E3C16F";
  const h = hashStr(id);
  return `hsl(${h % 360}, 55%, 55%)`;
}

export function WarMap({ nodes, myAlliance, onSelect, selected, contested }: { nodes: { node_id: number; x: number; y: number; type: string; owner: string | null }[]; myAlliance: string | null; onSelect: (n: any) => void; selected?: number | null; contested: Set<number> }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const cell = Math.max(22, Math.floor((width - 32) / 19));
  const size = cell * 19;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ padding: 0 }}>
      <View style={{ width: size, height: size, borderWidth: 3, borderColor: colors.gold, backgroundColor: "#2E3A2A", borderRadius: 4, overflow: "hidden" }} testID="war-map">
        {nodes.map((n) => {
          const own = allianceColor(n.owner, myAlliance);
          return (
            <Pressable key={n.node_id} testID={`war-node-${n.node_id}`} onPress={() => onSelect(n)} style={{ position: "absolute", left: n.x * cell, top: n.y * cell, width: cell, height: cell, backgroundColor: NODE_COLOR[n.type], borderWidth: 0.5, borderColor: "rgba(0,0,0,0.3)", alignItems: "center", justifyContent: "center" }}>
              {n.owner ? <View style={{ position: "absolute", inset: 0, backgroundColor: own, opacity: n.owner === myAlliance ? 0.6 : 0.45 } as any} /> : null}
              {n.type === "home_castle" ? <Text style={{ fontFamily: fonts.bodyBold, fontSize: cell * 0.5, color: colors.parchment }}>♜</Text> : n.type === "city" ? <Text style={{ fontSize: cell * 0.45, color: colors.onSurfaceInverse }}>◆</Text> : n.type === "fortress" ? <Text style={{ fontSize: cell * 0.45, color: colors.parchment }}>▲</Text> : n.type === "mine" ? <Text style={{ fontSize: cell * 0.4, color: colors.parchment }}>⛏</Text> : n.type === "town" ? <Text style={{ fontSize: cell * 0.4, color: colors.parchment }}>■</Text> : n.type === "village" ? <Text style={{ fontSize: cell * 0.35, color: colors.parchment }}>▪</Text> : null}
              {contested.has(n.node_id) ? <View style={{ position: "absolute", inset: 1, borderWidth: 2, borderColor: colors.error } as any} /> : null}
              {selected === n.node_id ? <View style={{ position: "absolute", inset: 0, borderWidth: 2, borderColor: colors.goldBright } as any} /> : null}
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}
