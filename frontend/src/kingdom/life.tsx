// Kingdom life: walking peasants, chimney smoke and animated construction sites. Presentational only (timers are server-authoritative).
import React, { memo, useEffect } from "react";
import { View } from "react-native";
import Animated, { Easing, SharedValue, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { useTheme } from "@/src/theme";
import { Icon } from "@/src/ui";

const SKIN = "#D9B48F";
const TUNICS = ["#6B5A44", "#5A6B44", "#7A4E3B", "#4E5A6B", "#8A6A3A"];

/** Tiny villager walking back and forth along a segment (horizontal or vertical). */
export const Peasant = memo(function Peasant({ x0, y0, x1, y1, seed, size = 10 }: { x0: number; y0: number; x1: number; y1: number; seed: number; size?: number }) {
  const p = useSharedValue((seed % 7) / 7 * 2);
  useEffect(() => {
    const dur = 9000 + (seed % 5) * 1800;
    p.value = withRepeat(withTiming(2, { duration: dur * 2, easing: Easing.linear }), -1, false);
  }, [p, seed]);
  const style = useAnimatedStyle(() => {
    const q = p.value <= 1 ? p.value : 2 - p.value; // 0..1 then back
    const forward = p.value <= 1;
    return {
      transform: [
        { translateX: x0 + (x1 - x0) * q },
        { translateY: y0 + (y1 - y0) * q - Math.abs(Math.sin(p.value * 60)) * 1.6 },
        { scaleX: x1 !== x0 ? (forward ? 1 : -1) : 1 },
      ],
    };
  });
  const tunic = TUNICS[seed % TUNICS.length];
  const carry = seed % 3 === 0;
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, top: 0, width: size, height: size * 1.9, alignItems: "center" }, style]}>
      <View style={{ width: size * 0.5, height: size * 0.5, borderRadius: size, backgroundColor: SKIN }} />
      <View style={{ width: size * 0.6, height: size * 0.9, backgroundColor: tunic, borderRadius: 1 }} />
      <View style={{ flexDirection: "row", gap: size * 0.12 }}>
        <View style={{ width: size * 0.22, height: size * 0.45, backgroundColor: "#3A2F26" }} />
        <View style={{ width: size * 0.22, height: size * 0.45, backgroundColor: "#3A2F26" }} />
      </View>
      {carry ? <View style={{ position: "absolute", right: -size * 0.35, top: size * 0.45, width: size * 0.5, height: size * 0.45, backgroundColor: "#8A6A3A", borderRadius: 1 }} /> : null}
    </Animated.View>
  );
});

function Puff({ t, i, color, rise, spread }: { t: SharedValue<number>; i: number; color: string; rise: number; spread: number }) {
  const style = useAnimatedStyle(() => {
    const q = (t.value + i / 3) % 1;
    return { opacity: (1 - q) * 0.85, transform: [{ translateY: -rise * q }, { translateX: Math.sin(q * 5 + i) * spread }, { scale: 0.5 + q }] };
  });
  return <Animated.View style={[{ position: "absolute", width: 8, height: 8, borderRadius: 4, backgroundColor: color }, style]} />;
}

/** Looping chimney smoke (or construction dust when `dust`). */
export const Smoke = memo(function Smoke({ x, y, dust }: { x: number; y: number; dust?: boolean }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withRepeat(withTiming(1, { duration: dust ? 1400 : 2600, easing: Easing.linear }), -1, false);
  }, [t, dust]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {[0, 1, 2].map((i) => <Puff key={i} t={t} i={i} color={dust ? "#C9B892" : "#EDEDED"} rise={dust ? 14 : 34} spread={dust ? 10 : 6} />)}
    </View>
  );
});

/** Scaffolding, swinging hammer, dust and server-time progress for a queued upgrade. */
export const ConstructionSite = memo(function ConstructionSite({ size, progress }: { size: number; progress: number }) {
  const { colors } = useTheme();
  const swing = useSharedValue(0);
  useEffect(() => {
    swing.value = withRepeat(withSequence(withTiming(1, { duration: 260, easing: Easing.in(Easing.quad) }), withTiming(0, { duration: 340, easing: Easing.out(Easing.quad) })), -1, false);
  }, [swing]);
  const hammer = useAnimatedStyle(() => ({ transform: [{ rotate: `${-35 + 60 * swing.value}deg` }] }));
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, width: size, height: size }} testID="construction-site">
      <View style={{ position: "absolute", left: 2, right: 2, top: 2, bottom: 2, borderWidth: 2, borderColor: "#8A6A3A", borderRadius: 4, opacity: 0.9 }} />
      <View style={{ position: "absolute", left: size * 0.1, top: size * 0.5, width: size * 0.8, height: 2, backgroundColor: "#8A6A3A", transform: [{ rotate: "30deg" }] }} />
      <View style={{ position: "absolute", left: size * 0.1, top: size * 0.5, width: size * 0.8, height: 2, backgroundColor: "#8A6A3A", transform: [{ rotate: "-30deg" }] }} />
      <View style={{ position: "absolute", left: size * 0.15, top: -6, width: 3, height: size * 0.4, backgroundColor: "#8A6A3A" }} />
      <View style={{ position: "absolute", left: size * 0.15, top: -6, width: size * 0.6, height: 3, backgroundColor: "#8A6A3A" }} />
      <View style={{ position: "absolute", left: size * 0.72, top: -6, width: 2, height: size * 0.28, backgroundColor: "#6E5A44" }} />
      <Animated.View style={[{ position: "absolute", right: -8, top: -10, backgroundColor: colors.warning, borderRadius: 11, padding: 4, transformOrigin: "bottom left" }, hammer]}>
        <Icon name="hammer" size={12} color={colors.onWarning} />
      </Animated.View>
      <Smoke x={size * 0.2} y={size * 0.55} dust />
      <View style={{ position: "absolute", left: 4, right: 4, bottom: -3, height: 4, backgroundColor: colors.scrim, borderRadius: 2, overflow: "hidden" }}>
        <View style={{ width: `${Math.round(Math.max(2, Math.min(100, progress * 100)))}%`, height: "100%", backgroundColor: colors.goldBright }} />
      </View>
    </View>
  );
});

/** Heraldic flag waving on top of the castle. */
export const Flag = memo(function Flag({ color, height = 16 }: { color: string; height?: number }) {
  const w = useSharedValue(0);
  useEffect(() => {
    w.value = withRepeat(withSequence(withTiming(1, { duration: 420, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 420, easing: Easing.inOut(Easing.quad) })), -1, false);
  }, [w]);
  const style = useAnimatedStyle(() => ({ transform: [{ skewY: `${-8 + 16 * w.value}deg` }, { scaleX: 0.92 + 0.08 * w.value }] }));
  return (
    <View pointerEvents="none" style={{ position: "absolute", top: -height, alignItems: "flex-start" }}>
      <View style={{ width: 3, height: height + 6, backgroundColor: "#4A3B2C" }} />
      <Animated.View style={[{ position: "absolute", left: 3, top: 0, width: height * 0.9, height: height * 0.55, backgroundColor: color, borderRightWidth: 2, borderColor: "#E3C16F", transformOrigin: "left center" }, style]} />
    </View>
  );
});
