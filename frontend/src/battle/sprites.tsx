// Representative proxies (Army Visual Progression): stylized silhouettes built from Views. No per-soldier assets.
import React, { memo } from "react";
import { View } from "react-native";

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
