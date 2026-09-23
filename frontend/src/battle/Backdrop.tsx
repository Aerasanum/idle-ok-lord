// Battle backdrop in depth layers (v1.10): painted region art + a scrolling mid skyline + a near foreground strip,
// each moving at its own speed, plus air particles, light shafts and ground fog. The camera shake is fed in so the
// near layers swing more than the far ones — that difference is what sells the 3D.
import { LinearGradient } from "expo-linear-gradient";
import React, { memo, useEffect, useMemo } from "react";
import { Image, View } from "react-native";
import Animated, { Easing, SharedValue, useAnimatedStyle, useSharedValue, withRepeat, withTiming } from "react-native-reanimated";

import { art } from "@/src/art/manifest";
import { regionBackground } from "@/src/art";
import { hashStr, paletteFor } from "./regions";
import { Clouds } from "./effects";

type Mid = "peaks" | "ruins" | "forest";
type Fg = "rocks" | "flora" | "bones";
type Air = "ember" | "snow" | "leaf" | "dust" | "spark";

/** Which silhouettes and which airborne particles each region gets (the tint always comes from the region palette). */
const REGION_LAYERS: Record<number, { mid: Mid; fg: Fg; air: Air }> = {
  1: { mid: "forest", fg: "flora", air: "leaf" },
  2: { mid: "forest", fg: "flora", air: "spark" },
  3: { mid: "ruins", fg: "rocks", air: "dust" },
  4: { mid: "peaks", fg: "rocks", air: "dust" },
  5: { mid: "peaks", fg: "rocks", air: "dust" },
  6: { mid: "peaks", fg: "rocks", air: "snow" },
  7: { mid: "ruins", fg: "bones", air: "spark" },
  8: { mid: "peaks", fg: "rocks", air: "ember" },
  9: { mid: "peaks", fg: "rocks", air: "snow" },
  10: { mid: "ruins", fg: "bones", air: "spark" },
};

const AIR_COUNT = 16;
const MID_LOOP_MS = 78000;
const FG_LOOP_MS = 31000;
const KEN_BURNS_MS = 21000;

/** Rescales the alpha of an `rgba(...)` palette colour: the region fog is tuned for solid bands, the haze needs far less. */
function fade(rgba: string, f: number): string {
  const m = rgba.match(/^rgba\(([^)]+)\)$/);
  if (!m) return rgba;
  const [r, g, b, a = "1"] = m[1].split(",").map((s) => s.trim());
  return `rgba(${r},${g},${b},${(parseFloat(a) * f).toFixed(3)})`;
}

/** Mixes two hex colours; used to push the silhouettes toward the region haze so they read as distance. */
function mix(a: string, b: string, t: number): string {
  const p = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [r1, g1, b1] = p(a);
  const [r2, g2, b2] = p(b);
  const h = (v: number) => Math.round(v).toString(16).padStart(2, "0");
  return `#${h(r1 + (r2 - r1) * t)}${h(g1 + (g2 - g1) * t)}${h(b1 + (b2 - b1) * t)}`;
}

/** One silhouette band scrolling sideways forever: two copies of the strip chase each other. */
const ScrollStrip = memo(function ScrollStrip({ source, width, height, bottom, color, opacity, durationMs, depth, shake, flip }: {
  source: number; width: number; height: number; bottom: number; color: string; opacity: number; durationMs: number; depth: number; shake: SharedValue<number>; flip?: boolean;
}) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = 0;
    t.value = withRepeat(withTiming(1, { duration: durationMs, easing: Easing.linear }), -1, false);
  }, [t, durationMs]);
  const style = useAnimatedStyle(() => ({ transform: [{ translateX: -t.value * width + shake.value * depth }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, bottom, width: width * 2, height, flexDirection: "row", opacity }, style]}>
      <Image source={source} style={{ width, height, tintColor: color }} resizeMode="stretch" />
      <Image source={source} style={{ width, height, tintColor: color, transform: flip ? [{ scaleX: -1 }] : undefined }} resizeMode="stretch" />
    </Animated.View>
  );
});

/** Airborne particle: loops on its own phase so the field never pulses in sync. */
const AirMote = memo(function AirMote({ i, width, height, kind, color, t }: { i: number; width: number; height: number; kind: Air; color: string; t: SharedValue<number> }) {
  const h = hashStr(`air:${kind}:${i}`);
  const phase = (h % 1000) / 1000;
  const lane = ((h >> 7) % 100) / 100;
  const depth = 0.35 + ((h >> 11) % 100) / 154; // 0.35 → ~1.0: far motes are small, dim and slow
  const size = kind === "snow" ? 2 + depth * 3 : kind === "leaf" ? 3 + depth * 5 : 1.5 + depth * 3;
  const drift = kind === "snow" ? 26 : kind === "leaf" ? 70 : 40;
  const style = useAnimatedStyle(() => {
    const p = (t.value + phase) % 1;
    const rising = kind === "ember" || kind === "spark";
    const y = rising ? height * (1 - p) : height * p * 1.05 - height * 0.05;
    const x = lane * width + Math.sin((p + phase) * Math.PI * 2) * drift * depth;
    const fade = Math.sin(Math.PI * p);
    return { opacity: fade * (kind === "dust" ? 0.3 : 0.75) * depth, transform: [{ translateX: x }, { translateY: y }, { scale: depth }] };
  });
  return <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, top: 0, width: size, height: kind === "leaf" ? size * 0.6 : size, borderRadius: size, backgroundColor: color }, style]} />;
});

const AirField = memo(function AirField({ width, height, kind, color }: { width: number; height: number; kind: Air; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withRepeat(withTiming(1, { duration: kind === "snow" ? 14000 : kind === "leaf" ? 11000 : 8000, easing: Easing.linear }), -1, false);
  }, [t, kind]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, width, height, overflow: "hidden" }}>
      {Array.from({ length: AIR_COUNT }).map((_, i) => <AirMote key={i} i={i} width={width} height={height} kind={kind} color={color} t={t} />)}
    </View>
  );
});

/** Volumetric light shafts: slanted bars that breathe, so the sky never looks like a still image. */
const LightShafts = memo(function LightShafts({ width, height, color }: { width: number; height: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withRepeat(withTiming(1, { duration: 9000, easing: Easing.inOut(Easing.quad) }), -1, true);
  }, [t]);
  const style = useAnimatedStyle(() => ({ opacity: 0.05 + t.value * 0.13, transform: [{ translateX: -10 + t.value * 20 }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, top: 0, width, height: height * 0.72 }, style]}>
      {[0.18, 0.42, 0.7].map((x, i) => (
        <LinearGradient key={i} colors={[color, "transparent"]} style={{ position: "absolute", left: width * x, top: -height * 0.1, width: 40 + i * 26, height: height * 0.9, transform: [{ skewX: "-14deg" }] }} />
      ))}
    </Animated.View>
  );
});

export const ParallaxBackdrop = memo(function ParallaxBackdrop({ region, width, height, shake, boss }: {
  region: number; width: number; height: number; shake: SharedValue<number>; boss?: boolean;
}) {
  const pal = paletteFor(region);
  const layers = REGION_LAYERS[Math.max(1, Math.min(10, region))];
  const bg = regionBackground(region);
  const midSrc = art(`parallax/mid_${layers.mid}`);
  const horizon = height * 0.62;
  const midColor = useMemo(() => mix(pal.groundAlt, pal.sky[1], 0.45), [pal]);

  // slow dolly on the painted plate: the far plane keeps breathing even when nothing else moves
  const ken = useSharedValue(0);
  useEffect(() => {
    ken.value = withRepeat(withTiming(1, { duration: KEN_BURNS_MS, easing: Easing.inOut(Easing.quad) }), -1, true);
  }, [ken]);
  const plateStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1.05 + ken.value * 0.04 }, { translateX: -6 + ken.value * 12 - shake.value * 0.75 }, { translateY: -2 + ken.value * 4 }],
  }));

  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, width, height, overflow: "hidden", backgroundColor: pal.ground }}>
      {bg ? (
        <Animated.View style={[{ position: "absolute", left: 0, top: 0, width, height }, plateStyle]}>
          <Image source={bg} style={{ width, height }} resizeMode="cover" />
        </Animated.View>
      ) : (
        <Animated.View style={[{ position: "absolute", left: 0, top: 0, width, height }, plateStyle]}>
          <LinearGradient colors={pal.sky} style={{ position: "absolute", left: 0, right: 0, top: 0, height: horizon }} />
          <LinearGradient colors={[pal.ground, pal.groundAlt]} style={{ position: "absolute", left: 0, right: 0, top: horizon - 8, bottom: 0 }} />
          <Clouds width={width} top={height * 0.16} color={pal.fog.replace(/[\d.]+\)$/, "1)")} />
        </Animated.View>
      )}
      <LightShafts width={width} height={height} color={pal.accent} />
      {midSrc ? <ScrollStrip source={midSrc} width={width * 1.35} height={height * 0.22} bottom={height * 0.38} color={midColor} opacity={0.42} durationMs={MID_LOOP_MS} depth={-0.35} shake={shake} flip /> : null}
      {/* thin haze at the horizon line so the silhouette sinks into the painted plate instead of sitting on top of it */}
      <LinearGradient colors={["transparent", fade(pal.fog, 0.55), "transparent"]} style={{ position: "absolute", left: 0, right: 0, top: horizon - height * 0.16, height: height * 0.24 }} />
      <AirField width={width} height={height} kind={layers.air} color={pal.accent} />
      {boss ? <LinearGradient colors={["rgba(120,0,0,0.5)", "transparent", "rgba(120,0,0,0.5)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} /> : null}
    </View>
  );
});

/** The closest layer: drawn on top of the fighters so they are framed by it. */
export const ForegroundLayer = memo(function ForegroundLayer({ region, width, height, shake }: { region: number; width: number; height: number; shake: SharedValue<number> }) {
  const pal = paletteFor(region);
  const layers = REGION_LAYERS[Math.max(1, Math.min(10, region))];
  const src = art(`parallax/fg_${layers.fg}`);
  const color = useMemo(() => mix(pal.groundAlt, "#000000", 0.62), [pal]);
  if (!src) return null;
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: height * 0.34, overflow: "hidden" }}>
      <ScrollStrip source={src} width={width * 1.9} height={height * 0.3} bottom={-height * 0.09} color={color} opacity={0.95} durationMs={FG_LOOP_MS} depth={0.9} shake={shake} />
    </View>
  );
});
