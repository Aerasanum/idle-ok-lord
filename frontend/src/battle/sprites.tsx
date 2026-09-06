// Representative proxies (Army Visual Progression): stylized silhouettes built from Views. No per-soldier assets.
import React, { memo } from "react";
import { View } from "react-native";

import { rarityColor, useTheme } from "@/src/theme";
import { hashStr } from "./regions";

type Item = { slot: string; rarity: string; item_level: number } | null | undefined;

const CLOTH = "#6B5A44", SKIN = "#D9B48F", POOR = "#7A6B58", STEEL = "#9AA1A9";

export const LordSprite = memo(function LordSprite({ equipped, size = 64, tier = 0, flip }: { equipped: Record<string, Item>; size?: number; tier?: number; flip?: boolean }) {
  const { colors } = useTheme();
  const u = size / 64;
  const col = (slot: string, fallback: string) => (equipped[slot] ? rarityColor(colors, equipped[slot]!.rarity) : fallback);
  const has = (s: string) => !!equipped[s];
  const royal = tier >= 5;
  return (
    <View style={{ width: size, height: size * 1.25, alignItems: "center", justifyContent: "flex-end", transform: [{ scaleX: flip ? -1 : 1 }] }}>
      {/* cloak */}
      {has("cloak") || royal ? <View style={{ position: "absolute", bottom: 4 * u, width: 44 * u, height: 58 * u, backgroundColor: has("cloak") ? col("cloak", CLOTH) : colors.burgundy, borderRadius: 8 * u, opacity: 0.95, left: 4 * u }} /> : null}
      {/* legs / boots */}
      <View style={{ flexDirection: "row", gap: 4 * u, position: "absolute", bottom: 0 }}>
        <View style={{ width: 9 * u, height: 16 * u, backgroundColor: has("boots") ? col("boots", POOR) : POOR, borderRadius: 2 * u }} />
        <View style={{ width: 9 * u, height: 16 * u, backgroundColor: has("boots") ? col("boots", POOR) : POOR, borderRadius: 2 * u }} />
      </View>
      {/* torso */}
      <View style={{ position: "absolute", bottom: 14 * u, width: 30 * u, height: 30 * u, backgroundColor: has("chest") ? col("chest", CLOTH) : CLOTH, borderRadius: 5 * u, borderWidth: has("chest") ? 2 : 0, borderColor: STEEL }}>
        {has("chest") ? <View style={{ position: "absolute", left: 11 * u, top: 6 * u, width: 8 * u, height: 14 * u, backgroundColor: colors.gold, borderRadius: 2 } as any} /> : null}
      </View>
      {/* head + helmet */}
      <View style={{ position: "absolute", bottom: 44 * u, width: 16 * u, height: 16 * u, backgroundColor: SKIN, borderRadius: 8 * u }} />
      {has("helmet") ? (
        <View style={{ position: "absolute", bottom: 50 * u, width: 20 * u, height: 14 * u, backgroundColor: col("helmet", STEEL), borderTopLeftRadius: 10 * u, borderTopRightRadius: 10 * u }}>
          {royal ? <View style={{ position: "absolute", top: -6 * u, left: 3 * u, width: 14 * u, height: 6 * u, backgroundColor: colors.goldBright }} /> : null}
        </View>
      ) : royal ? <View style={{ position: "absolute", bottom: 56 * u, width: 18 * u, height: 6 * u, backgroundColor: colors.goldBright }} /> : null}
      {/* gloves */}
      <View style={{ position: "absolute", bottom: 26 * u, left: 6 * u, width: 8 * u, height: 8 * u, backgroundColor: has("gloves") ? col("gloves", SKIN) : SKIN, borderRadius: 3 * u }} />
      {/* weapon */}
      <View style={{ position: "absolute", bottom: 20 * u, right: 2 * u, width: 5 * u, height: has("weapon") ? 46 * u : 32 * u, backgroundColor: has("weapon") ? col("weapon", STEEL) : POOR, borderRadius: 2 * u, transform: [{ rotate: "-12deg" }] }}>
        <View style={{ position: "absolute", bottom: 8 * u, left: -5 * u, width: 15 * u, height: 4 * u, backgroundColor: has("weapon") ? colors.gold : POOR }} />
      </View>
      {/* offhand shield */}
      {has("offhand") ? <View style={{ position: "absolute", bottom: 20 * u, left: 0, width: 16 * u, height: 22 * u, backgroundColor: col("offhand", STEEL), borderRadius: 6 * u, borderWidth: 2, borderColor: colors.gold }} /> : null}
      {/* amulet / ring glow */}
      {has("amulet") ? <View style={{ position: "absolute", bottom: 40 * u, width: 6 * u, height: 6 * u, borderRadius: 3 * u, backgroundColor: col("amulet", colors.gold) }} /> : null}
    </View>
  );
});

const UNIT_STYLE: Record<string, { body: string; accent: string; w: number; h: number; kind: "foot" | "mount" | "siege" | "beast" | "flyer" | "mythic" }> = {
  infantry: { body: "#5C6470", accent: "#B89947", w: 12, h: 22, kind: "foot" },
  archer: { body: "#3E5B3A", accent: "#D9C9A3", w: 11, h: 21, kind: "foot" },
  cavalry: { body: "#6B4A2B", accent: "#B89947", w: 20, h: 22, kind: "mount" },
  catapult: { body: "#4A3B2C", accent: "#8C929C", w: 26, h: 22, kind: "siege" },
  conquest_wagon: { body: "#2E241B", accent: "#800020", w: 30, h: 24, kind: "siege" },
  wolf: { body: "#5A5A5A", accent: "#E5E4E2", w: 18, h: 12, kind: "beast" },
  bear: { body: "#4A3222", accent: "#2A1A10", w: 22, h: 20, kind: "beast" },
  lion: { body: "#B8863B", accent: "#7A4E1B", w: 22, h: 16, kind: "beast" },
  falcon: { body: "#7A5A3A", accent: "#E6D8B8", w: 16, h: 8, kind: "flyer" },
  war_elephant: { body: "#6E6E6E", accent: "#B89947", w: 36, h: 34, kind: "beast" },
  dragon: { body: "#8B1A1A", accent: "#FF7A2F", w: 56, h: 40, kind: "mythic" },
  angel: { body: "#E6F4FF", accent: "#E3C16F", w: 30, h: 46, kind: "mythic" },
  demon: { body: "#3B0F0C", accent: "#B0361D", w: 34, h: 44, kind: "mythic" },
};

export const UnitProxy = memo(function UnitProxy({ unit, scale = 1, banner }: { unit: string; scale?: number; banner?: string }) {
  const st = UNIT_STYLE[unit] ?? UNIT_STYLE.infantry;
  const w = st.w * scale, h = st.h * scale;
  if (st.kind === "foot") {
    return (
      <View style={{ width: w, height: h, alignItems: "center", justifyContent: "flex-end" }}>
        <View style={{ width: w * 0.45, height: w * 0.45, borderRadius: w, backgroundColor: st.accent, marginBottom: 1 }} />
        <View style={{ width: w * 0.8, height: h * 0.55, backgroundColor: st.body, borderRadius: 2 }} />
        <View style={{ position: "absolute", right: -1, top: 0, width: 2 * scale, height: h * 0.9, backgroundColor: unit === "archer" ? st.accent : "#C9CED6" }} />
        {banner ? <View style={{ position: "absolute", left: -2, top: -6 * scale, width: 6 * scale, height: 8 * scale, backgroundColor: banner }} /> : null}
      </View>
    );
  }
  if (st.kind === "mount") {
    return (
      <View style={{ width: w, height: h, justifyContent: "flex-end" }}>
        <View style={{ position: "absolute", top: 0, left: w * 0.35, width: w * 0.3, height: h * 0.5, backgroundColor: "#5C6470", borderRadius: 2 }} />
        <View style={{ width: w, height: h * 0.5, backgroundColor: st.body, borderRadius: 4 }} />
        <View style={{ position: "absolute", right: -2, top: h * 0.2, width: w * 0.28, height: h * 0.28, backgroundColor: st.body, borderRadius: 3 }} />
        <View style={{ position: "absolute", left: w * 0.6, top: -2, width: 2 * scale, height: h * 0.8, backgroundColor: st.accent }} />
      </View>
    );
  }
  if (st.kind === "siege") {
    return (
      <View style={{ width: w, height: h, justifyContent: "flex-end" }}>
        <View style={{ width: w, height: h * 0.45, backgroundColor: st.body, borderRadius: 3, borderWidth: 1, borderColor: st.accent }} />
        <View style={{ position: "absolute", top: 0, left: w * 0.3, width: 3 * scale, height: h * 0.7, backgroundColor: st.accent, transform: [{ rotate: unit === "catapult" ? "-35deg" : "0deg" }] }} />
        <View style={{ position: "absolute", bottom: -2, left: 2, width: w * 0.25, height: w * 0.25, borderRadius: w, backgroundColor: "#2A2A35" }} />
        <View style={{ position: "absolute", bottom: -2, right: 2, width: w * 0.25, height: w * 0.25, borderRadius: w, backgroundColor: "#2A2A35" }} />
      </View>
    );
  }
  if (st.kind === "flyer") {
    return (
      <View style={{ width: w, height: h, flexDirection: "row", alignItems: "center" }}>
        <View style={{ width: w * 0.45, height: 3 * scale, backgroundColor: st.body, transform: [{ rotate: "-20deg" }] }} />
        <View style={{ width: w * 0.15, height: w * 0.15, backgroundColor: st.accent, borderRadius: w }} />
        <View style={{ width: w * 0.45, height: 3 * scale, backgroundColor: st.body, transform: [{ rotate: "20deg" }] }} />
      </View>
    );
  }
  if (st.kind === "beast") {
    return (
      <View style={{ width: w, height: h, justifyContent: "flex-end" }}>
        <View style={{ width: w, height: h * 0.6, backgroundColor: st.body, borderRadius: h * 0.3 }} />
        <View style={{ position: "absolute", right: -3, top: 0, width: w * 0.35, height: h * 0.45, backgroundColor: st.body, borderRadius: 4 }} />
        {unit === "war_elephant" ? <View style={{ position: "absolute", right: -6, top: h * 0.3, width: 4 * scale, height: h * 0.55, backgroundColor: st.body, borderRadius: 2 }} /> : null}
        {unit === "war_elephant" ? <View style={{ position: "absolute", top: -8 * scale, left: w * 0.25, width: w * 0.5, height: 10 * scale, backgroundColor: st.accent, borderRadius: 2 }} /> : null}
      </View>
    );
  }
  // mythic: hero-scale representative
  return (
    <View style={{ width: w, height: h, justifyContent: "flex-end", alignItems: "center" }}>
      {unit === "dragon" ? (
        <>
          <View style={{ position: "absolute", top: 0, left: 0, width: w * 0.5, height: h * 0.5, backgroundColor: st.body, borderTopLeftRadius: w, opacity: 0.9 }} />
          <View style={{ position: "absolute", top: 0, right: 0, width: w * 0.5, height: h * 0.5, backgroundColor: st.body, borderTopRightRadius: w, opacity: 0.9 }} />
          <View style={{ width: w * 0.5, height: h * 0.55, backgroundColor: st.body, borderRadius: h * 0.2 }} />
          <View style={{ position: "absolute", right: 0, bottom: h * 0.4, width: w * 0.3, height: h * 0.2, backgroundColor: st.accent, borderRadius: 4 }} />
        </>
      ) : unit === "angel" ? (
        <>
          <View style={{ position: "absolute", top: h * 0.1, left: -w * 0.2, width: w * 0.5, height: h * 0.7, backgroundColor: st.body, borderRadius: w, opacity: 0.85, transform: [{ rotate: "-15deg" }] }} />
          <View style={{ position: "absolute", top: h * 0.1, right: -w * 0.2, width: w * 0.5, height: h * 0.7, backgroundColor: st.body, borderRadius: w, opacity: 0.85, transform: [{ rotate: "15deg" }] }} />
          <View style={{ width: w * 0.35, height: h * 0.7, backgroundColor: "#D9C9A3", borderRadius: 6 }} />
          <View style={{ position: "absolute", top: 0, width: w * 0.3, height: 3 * scale, backgroundColor: st.accent, borderRadius: 2 }} />
        </>
      ) : (
        <>
          <View style={{ position: "absolute", top: 0, left: w * 0.15, width: 4 * scale, height: h * 0.25, backgroundColor: st.accent, transform: [{ rotate: "-25deg" }] }} />
          <View style={{ position: "absolute", top: 0, right: w * 0.15, width: 4 * scale, height: h * 0.25, backgroundColor: st.accent, transform: [{ rotate: "25deg" }] }} />
          <View style={{ width: w * 0.55, height: h * 0.75, backgroundColor: st.body, borderRadius: 8 }} />
          <View style={{ position: "absolute", bottom: h * 0.45, width: w * 0.3, height: h * 0.08, backgroundColor: st.accent }} />
        </>
      )}
    </View>
  );
});

export const MonsterProxy = memo(function MonsterProxy({ family, type, palette, scale = 1 }: { family: string; type: "normal" | "elite" | "boss"; palette: string[]; scale?: number }) {
  const h = hashStr(family);
  const color = palette[h % palette.length];
  const shape = h % 4; // blob, tall, wide, flyer
  const base = type === "boss" ? 96 : type === "elite" ? 40 : 26;
  const size = base * scale;
  const eye = type === "boss" ? "#FFD700" : "#E63946";
  return (
    <View style={{ width: size, height: size * (shape === 1 ? 1.5 : shape === 2 ? 0.7 : 1), justifyContent: "flex-end", alignItems: "center" }}>
      <View style={{ width: size * (shape === 2 ? 1 : 0.8), height: "100%", backgroundColor: color, borderRadius: shape === 0 ? size / 2 : shape === 3 ? size : 6, borderWidth: type === "boss" ? 3 : 1, borderColor: type === "boss" ? "#FFD700" : "rgba(0,0,0,0.4)" }}>
        <View style={{ position: "absolute", top: "25%", left: "20%", width: size * 0.12, height: size * 0.12, backgroundColor: eye, borderRadius: size }} />
        <View style={{ position: "absolute", top: "25%", right: "20%", width: size * 0.12, height: size * 0.12, backgroundColor: eye, borderRadius: size }} />
        {type !== "normal" ? <View style={{ position: "absolute", top: -size * 0.15, left: "35%", width: size * 0.3, height: size * 0.2, backgroundColor: type === "boss" ? "#FFD700" : "#C9CED6", transform: [{ rotate: "180deg" }] }} /> : null}
      </View>
    </View>
  );
});

export function CohortSilhouette({ width, color, rows = 2, banner }: { width: number; color: string; rows?: number; banner?: string }) {
  const cols = Math.max(4, Math.floor(width / 7));
  return (
    <View style={{ width, opacity: 0.55 }}>
      {banner ? <View style={{ width: 4, height: 14, backgroundColor: banner, alignSelf: "flex-start", marginLeft: width * 0.4 }} /> : null}
      {Array.from({ length: rows }).map((_, r) => (
        <View key={r} style={{ flexDirection: "row", gap: 2, marginLeft: r * 3 }}>
          {Array.from({ length: cols }).map((_, i) => (
            <View key={i} style={{ width: 4, height: 9, backgroundColor: color, borderRadius: 1 }} />
          ))}
        </View>
      ))}
    </View>
  );
}
