// Battle VFX: floating damage numbers, slash arcs, spark bursts, coin showers and outcome banners. Purely presentational (server decides the outcome).
import { LinearGradient } from "expo-linear-gradient";
import React, { useEffect } from "react";
import { Image, Text, View } from "react-native";
import Animated, { Easing, FadeOut, SharedValue, useAnimatedStyle, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { vfxArt } from "@/src/art";
import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName, fmt } from "@/src/ui";

export type Fx = { id: number; kind: "dmg" | "slash" | "burst" | "speed" | "flare" | "dust" | "shock" | "proj" | "ghost" | "death" | "sprite" | "text"; x: number; y: number; value?: number; crit?: boolean; color?: string; size?: number; tx?: number; ty?: number; source?: number; w?: number; h?: number; delay?: number; sprite?: string; text?: string; opts?: Record<string, any> };

export function DamageNumber({ x, y, value, crit, color, seed, huge }: { x: number; y: number; value: number; crit?: boolean; color: string; seed: number; huge?: boolean }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: huge ? 1400 : crit ? 1100 : 850, easing: Easing.out(Easing.cubic) });
  }, [t, crit, huge]);
  const drift = ((seed % 7) - 3) * 6;
  const style = useAnimatedStyle(() => ({
    opacity: 1 - Math.max(0, (t.value - 0.55) / 0.45),
    transform: [{ translateY: -(huge ? 96 : crit ? 80 : 56) * t.value }, { translateX: drift * t.value }, { scale: huge ? 2.1 - 0.7 * t.value : crit ? 1.6 - 0.5 * t.value : 1.15 - 0.25 * t.value }, { rotate: `${crit ? ((seed % 2) ? 6 : -6) : 0}deg` }],
  }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y }, style]}>
      <Text style={{ fontFamily: fonts.display, fontSize: huge ? 34 : crit ? 28 : 18, color, textShadowColor: huge ? color : "#000", textShadowOffset: { width: 1, height: 2 }, textShadowRadius: huge ? 12 : 3 }}>
        {crit || huge ? `${fmt(value)}!` : fmt(value)}
      </Text>
    </Animated.View>
  );
}

/** Generic sprite VFX (light-on-black render with alpha): grows from `from` to `to`, fades out, optional rotation/flip. */
export function SpriteFx({ x, y, sprite, size, from = 0.45, to = 1.15, rotate = 0, duration = 420, delay = 0, flipX = false, flipY = false, fadeIn = 0.12, anchor = "center", opacity = 1, aspect = 1, drift = 0, hold = 0 }: {
  x: number; y: number; sprite: string; size: number; from?: number; to?: number; rotate?: number; duration?: number; delay?: number; flipX?: boolean; flipY?: boolean; fadeIn?: number; anchor?: "center" | "bottom"; opacity?: number; aspect?: number; drift?: number; hold?: number;
}) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withDelay(delay, withTiming(1, { duration, easing: Easing.out(Easing.quad) }));
  }, [t, delay, duration]);
  const style = useAnimatedStyle(() => {
    const p = t.value;
    const grow = from + (to - from) * Math.min(1, p * 1.25);
    const fadeStart = fadeIn + hold;
    const o = p < fadeIn ? p / Math.max(0.001, fadeIn) : p < fadeStart ? 1 : 1 - Math.pow((p - fadeStart) / Math.max(0.001, 1 - fadeStart), 1.4);
    return { opacity: opacity * Math.max(0, o), transform: [{ translateY: -drift * p }, { rotate: `${rotate}deg` }, { scaleX: grow * (flipX ? -1 : 1) }, { scaleY: grow * (flipY ? -1 : 1) }] };
  });
  const img = vfxArt(sprite);
  if (!img) return null;
  const h = size * aspect;
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x - size / 2, top: anchor === "bottom" ? y - h : y - h / 2, width: size, height: h, transformOrigin: anchor === "bottom" ? "50% 100%" : "50% 50%" }, style]}>
      <Image source={img} style={{ width: size, height: h }} resizeMode="contain" />
    </Animated.View>
  );
}

/** Light blade slash: sprite (gold or white) sweeping with a slight rotation; falls back to a vector arc without assets. */
export function Slash({ x, y, color, size = 64 }: { x: number; y: number; color: string; size?: number }) {
  const t = useSharedValue(0);
  const big = size > 80;
  const white = color === "#FFFFFF" || /D9C9A3|E6D8B8|F3E7C9/i.test(color);
  useEffect(() => {
    t.value = withTiming(1, { duration: big ? 380 : 280, easing: Easing.out(Easing.quad) });
  }, [t, big]);
  const style = useAnimatedStyle(() => ({ opacity: 1 - t.value, transform: [{ rotate: `${-70 + 130 * t.value}deg` }, { scale: 0.5 + 0.8 * t.value }] }));
  if (vfxArt("slash_gold")) {
    const seed = Math.round(x + y);
    return <SpriteFx x={x + size / 2} y={y + size / 2} sprite={white ? "slash_white" : "slash_gold"} size={size * 1.7} from={0.55} to={1.25} rotate={-25 + (seed % 5) * 12} flipX={seed % 2 === 0} duration={big ? 420 : 320} fadeIn={0.08} />;
  }
  const bw = big ? 9 : 5;
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y, width: size, height: size }, style]}>
      <View style={{ width: size, height: size, borderRadius: size / 2, borderTopWidth: bw, borderRightWidth: bw, borderColor: color, borderLeftColor: "transparent", borderBottomColor: "transparent" }} />
      {big ? <View style={{ position: "absolute", left: size * 0.12, top: size * 0.12, width: size * 0.76, height: size * 0.76, borderRadius: size, borderTopWidth: 3, borderRightWidth: 3, borderColor: "#FFFFFF", borderLeftColor: "transparent", borderBottomColor: "transparent", opacity: 0.8 }} /> : null}
    </Animated.View>
  );
}

function Particle({ t, angle, dist, color, size, gravity }: { t: SharedValue<number>; angle: number; dist: number; color: string; size: number; gravity: number }) {
  const style = useAnimatedStyle(() => ({
    opacity: 1 - Math.max(0, (t.value - 0.5) / 0.5),
    transform: [{ translateX: Math.cos(angle) * dist * t.value }, { translateY: Math.sin(angle) * dist * t.value * 0.7 - 30 * t.value + gravity * t.value * t.value }, { rotate: `${t.value * 540}deg` }],
  }));
  return <Animated.View style={[{ position: "absolute", width: size, height: size, borderRadius: size / 3, backgroundColor: color }, style]} />;
}

/** Impact burst: explosion sprite (fire when `big`) plus a few flying sparks in the hit colour. */
export function Burst({ x, y, color, count = 8, seed = 0, big, fire }: { x: number; y: number; color: string; count?: number; seed?: number; big?: boolean; fire?: boolean }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: big ? 900 : 520, easing: Easing.out(Easing.quad) });
  }, [t, big]);
  const hasSprite = !!vfxArt("impact_burst");
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {hasSprite ? <SpriteFx x={0} y={0} sprite={fire || big ? "fire_burst" : "impact_burst"} size={big ? 190 : 96} from={0.3} to={big ? 1.3 : 1.1} rotate={(seed * 47) % 360} duration={big ? 620 : 380} fadeIn={0.1} /> : null}
      {Array.from({ length: hasSprite ? Math.min(count, 6) : count }).map((_, i) => (
        <Particle key={i} t={t} angle={((i + (seed % 3) * 0.37) / count) * Math.PI * 2} dist={(big ? 70 : 34) + ((seed * 7 + i * 13) % 20)} color={color} size={big ? 8 : 5} gravity={big ? 120 : 40} />
      ))}
    </View>
  );
}

function Coin({ t, angle, dist, size }: { t: SharedValue<number>; angle: number; dist: number; size: number }) {
  const { colors } = useTheme();
  const style = useAnimatedStyle(() => ({
    opacity: 1 - Math.max(0, (t.value - 0.7) / 0.3),
    transform: [{ translateX: Math.cos(angle) * dist * t.value }, { translateY: Math.sin(angle) * dist * 0.5 * t.value - 140 * t.value + 260 * t.value * t.value }, { scaleX: Math.abs(Math.cos(t.value * 9)) * 0.7 + 0.3 }],
  }));
  return <Animated.View style={[{ position: "absolute", width: size, height: size, borderRadius: size / 2, backgroundColor: colors.res_gold, borderWidth: 1.5, borderColor: colors.gold }, style]} />;
}

export function CoinShower({ x, y, count = 16 }: { x: number; y: number; count?: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 1300, easing: Easing.out(Easing.quad) });
  }, [t]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {Array.from({ length: count }).map((_, i) => <Coin key={i} t={t} angle={Math.PI + (i / (count - 1)) * Math.PI} dist={60 + ((i * 37) % 90)} size={8 + (i % 3) * 3} />)}
    </View>
  );
}

export function OutcomeBanner({ win, firstClear, subtitle, sceneH }: { win: boolean; firstClear?: boolean; subtitle: string; sceneH: number }) {
  const { colors } = useTheme();
  const s = useSharedValue(0);
  const rot = useSharedValue(0);
  useEffect(() => {
    s.value = withSequence(withTiming(1.18, { duration: 320, easing: Easing.out(Easing.back(2)) }), withTiming(1, { duration: 220 }));
    rot.value = withRepeat(withTiming(360, { duration: 9000, easing: Easing.linear }), -1, false);
  }, [s, rot]);
  const bannerStyle = useAnimatedStyle(() => ({ opacity: Math.min(1, s.value), transform: [{ scale: s.value }] }));
  const rayStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${rot.value}deg` }] }));
  const color = win ? colors.goldBright : colors.error;
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, right: 0, top: 0, height: sceneH, alignItems: "center", justifyContent: "center" }} testID="battle-outcome-banner">
      {win ? (
        <Animated.View style={[{ position: "absolute", width: 300, height: 300, alignItems: "center", justifyContent: "center" }, rayStyle]}>
          {Array.from({ length: 12 }).map((_, i) => <View key={i} style={{ position: "absolute", width: 6, height: 300, backgroundColor: colors.goldBright, opacity: 0.16, transform: [{ rotate: `${i * 30}deg` }] }} />)}
        </Animated.View>
      ) : null}
      <Animated.View style={[{ alignItems: "center", paddingHorizontal: 22, paddingVertical: 10, backgroundColor: colors.overlay, borderWidth: 2, borderColor: color, borderRadius: 6 }, bannerStyle]}>
        <Text style={{ fontFamily: fonts.display, fontSize: win ? 40 : 34, letterSpacing: 2, color, textShadowColor: "#000", textShadowOffset: { width: 0, height: 2 }, textShadowRadius: 6 }}>
          {win ? (firstClear ? "STAGE CONQUISTATO" : "VITTORIA") : "SCONFITTA"}
        </Text>
        <Text style={{ fontFamily: fonts.bodyMedium, fontSize: 12, color: colors.onSurface, marginTop: 2 }}>{subtitle}</Text>
      </Animated.View>
    </View>
  );
}

function Mote({ t, i, width, height, color, rise }: { t: SharedValue<number>; i: number; width: number; height: number; color: string; rise: boolean }) {
  const phase = i / 12;
  const x0 = (i * 97) % Math.max(1, width);
  const style = useAnimatedStyle(() => {
    const p = (t.value + phase) % 1;
    return { opacity: 0.2 + 0.5 * Math.sin(p * Math.PI), transform: [{ translateX: x0 + Math.sin(p * 6.28 + i) * 18 }, { translateY: rise ? height - p * height : p * height }] };
  });
  return <Animated.View style={[{ position: "absolute", width: 3 + (i % 3), height: 3 + (i % 3), borderRadius: 3, backgroundColor: color }, style]} />;
}

/** Region ambience: falling leaves/snow/dust or rising embers/sparks. */
export function Ambient({ width, height, color, rise }: { width: number; height: number; color: string; rise: boolean }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withRepeat(withTiming(1, { duration: 7000, easing: Easing.linear }), -1, false);
  }, [t]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, width, height }}>
      {Array.from({ length: 12 }).map((_, i) => <Mote key={i} t={t} i={i} width={width} height={height} color={color} rise={rise} />)}
    </View>
  );
}

export function Clouds({ width, top, color }: { width: number; top: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withRepeat(withTiming(1, { duration: 26000, easing: Easing.linear }), -1, false);
  }, [t]);
  const a = useAnimatedStyle(() => ({ transform: [{ translateX: -120 + ((t.value * (width + 240)) % (width + 240)) }] }));
  const b = useAnimatedStyle(() => ({ transform: [{ translateX: -120 + (((t.value + 0.5) * (width + 240)) % (width + 240)) }] }));
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, right: 0, top }}>
      <Animated.View style={[{ position: "absolute", width: 120, height: 26, borderRadius: 13, backgroundColor: color, opacity: 0.22 }, a]} />
      <Animated.View style={[{ position: "absolute", top: 34, width: 90, height: 20, borderRadius: 10, backgroundColor: color, opacity: 0.16 }, b]} />
    </View>
  );
}

// ---- Lord auto-skills: one signature effect each + flashing name banner (canon hero.auto_skills) ----
export const SKILL_FX: Record<string, { color: string; label: string }> = {
  power_strike: { color: "#FF7A2F", label: "COLPO POTENTE" },
  war_cry: { color: "#FFD166", label: "GRIDO DI GUERRA" },
  shield_wall: { color: "#7FE3FF", label: "MURO DI SCUDI" },
  rain_of_steel: { color: "#DDE3EA", label: "PIOGGIA D'ACCIAIO" },
  royal_strike: { color: "#FFE97A", label: "COLPO REALE" },
  dragon_banner: { color: "#FF3B3B", label: "VESSILLO DEL DRAGO" },
};

export function SkillBanner({ name, color, sceneH }: { name: string; color: string; sceneH: number }) {
  const s = useSharedValue(0);
  const blink = useSharedValue(1);
  useEffect(() => {
    s.value = withSequence(withTiming(1.1, { duration: 220, easing: Easing.out(Easing.back(2.5)) }), withTiming(1, { duration: 160 }));
    blink.value = withRepeat(withSequence(withTiming(0.25, { duration: 110 }), withTiming(1, { duration: 110 })), 4, false);
  }, [s, blink]);
  const style = useAnimatedStyle(() => ({ opacity: blink.value * Math.min(1, s.value), transform: [{ scale: s.value }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: sceneH * 0.44, alignItems: "center" }, style]} testID="skill-banner">
      <Text style={{ fontFamily: fonts.display, fontSize: 24, letterSpacing: 3, color, textShadowColor: "#000", textShadowOffset: { width: 0, height: 2 }, textShadowRadius: 6 }}>{name}</Text>
    </Animated.View>
  );
}

/** war_cry: expanding shockwave ring from the Lord. */
export function Shockwave({ x, y, color }: { x: number; y: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 700, easing: Easing.out(Easing.cubic) });
  }, [t]);
  const style = useAnimatedStyle(() => ({ opacity: 1 - t.value, transform: [{ scale: 0.2 + 3.2 * t.value }] }));
  if (vfxArt("shockwave_ring")) return <SpriteFx x={x} y={y} sprite="shockwave_ring" size={150} aspect={0.5} from={0.15} to={1.9} duration={620} fadeIn={0.05} />;
  return <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x - 40, top: y - 40, width: 80, height: 80, borderRadius: 40, borderWidth: 5, borderColor: color }, style]} />;
}

/** shield_wall: translucent dome over the Lord that pulses then fades. */
export function ShieldDome({ x, y, size, color }: { x: number; y: number; size: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withSequence(withTiming(1, { duration: 220, easing: Easing.out(Easing.quad) }), withRepeat(withSequence(withTiming(0.7, { duration: 260 }), withTiming(1, { duration: 260 })), 3, false), withTiming(0, { duration: 400 }));
  }, [t]);
  const style = useAnimatedStyle(() => ({ opacity: 0.55 * t.value, transform: [{ scale: 0.6 + 0.4 * Math.min(1, t.value) }] }));
  return <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size, borderRadius: size / 2, backgroundColor: color, borderWidth: 3, borderColor: "#FFFFFF" }, style]} />;
}

function Blade({ t, i, x, height, color }: { t: SharedValue<number>; i: number; x: number; height: number; color: string }) {
  const delay = (i % 5) * 0.12;
  const style = useAnimatedStyle(() => {
    const p = Math.max(0, Math.min(1, (t.value - delay) / (1 - delay)));
    return { opacity: p < 0.9 ? 1 : 1 - (p - 0.9) / 0.1, transform: [{ translateY: -60 + (height + 60) * p }, { rotate: "18deg" }] };
  });
  return <Animated.View style={[{ position: "absolute", left: x, width: 4, height: 34, borderRadius: 2, backgroundColor: color, borderLeftWidth: 1.5, borderLeftColor: "#FFFFFF" }, style]} />;
}

/** rain_of_steel: blades falling over the horde. */
export function SteelRain({ x, width, height, color }: { x: number; width: number; height: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 900, easing: Easing.in(Easing.quad) });
  }, [t]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: 0, width, height }}>
      {Array.from({ length: 12 }).map((_, i) => <Blade key={i} t={t} i={i} x={(i * 37) % Math.max(1, width - 6)} height={height} color={color} />)}
    </View>
  );
}

/** royal_strike: lightning column striking the front monster. */
export function LightningBolt({ x, height, color }: { x: number; height: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withSequence(withTiming(1, { duration: 60 }), withTiming(0.3, { duration: 60 }), withTiming(1, { duration: 60 }), withTiming(0.5, { duration: 80 }), withTiming(0, { duration: 260 }));
  }, [t]);
  const core = useAnimatedStyle(() => ({ opacity: t.value }));
  const halo = useAnimatedStyle(() => ({ opacity: 0.35 * t.value, transform: [{ scaleX: 1 + t.value }] }));
  if (vfxArt("lightning")) {
    return (
      <View pointerEvents="none" style={{ position: "absolute", left: x - height * 0.3, top: 0, width: height * 0.6, height }}>
        <SpriteFx x={height * 0.3} y={height} sprite="lightning" size={height * 0.6} aspect={1.7} anchor="bottom" from={0.9} to={1.05} duration={520} fadeIn={0.04} hold={0.3} />
        <SpriteFx x={height * 0.3} y={height - 10} sprite="impact_burst" size={height * 0.5} from={0.3} to={1} duration={420} delay={60} />
      </View>
    );
  }
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x - 14, top: 0, width: 28, height, alignItems: "center" }}>
      <Animated.View style={[{ position: "absolute", top: 0, width: 20, height, backgroundColor: color }, halo]} />
      <Animated.View style={[{ position: "absolute", top: 0, width: 5, height: height * 0.45, backgroundColor: "#FFFFFF", transform: [{ translateX: 4 }, { skewX: "12deg" }] }, core]} />
      <Animated.View style={[{ position: "absolute", top: height * 0.42, width: 5, height: height * 0.58, backgroundColor: "#FFFFFF", transform: [{ translateX: -4 }, { skewX: "-14deg" }] }, core]} />
    </View>
  );
}

function Ember({ t, i, color }: { t: SharedValue<number>; i: number; color: string }) {
  const style = useAnimatedStyle(() => {
    const p = (t.value + i / 10) % 1;
    return { opacity: 1 - p, transform: [{ translateX: (i % 5) * 14 - 28 + Math.sin(p * 8 + i) * 8 }, { translateY: -90 * p }] };
  });
  return <Animated.View style={[{ position: "absolute", width: 4, height: 4, borderRadius: 2, backgroundColor: color }, style]} />;
}

/** dragon_banner: crimson standard rising with embers over the army. */
export function BannerRise({ x, y, color, heraldic }: { x: number; y: number; color: string; heraldic: string }) {
  const t = useSharedValue(0);
  const wave = useSharedValue(0);
  const ember = useSharedValue(0);
  useEffect(() => {
    t.value = withSequence(withTiming(1, { duration: 500, easing: Easing.out(Easing.back(1.5)) }), withTiming(1, { duration: 900 }), withTiming(0, { duration: 300 }));
    wave.value = withRepeat(withSequence(withTiming(1, { duration: 300 }), withTiming(0, { duration: 300 })), -1, false);
    ember.value = withRepeat(withTiming(1, { duration: 900, easing: Easing.linear }), -1, false);
  }, [t, wave, ember]);
  const pole = useAnimatedStyle(() => ({ opacity: Math.min(1, t.value * 2), transform: [{ translateY: 40 * (1 - t.value) }] }));
  const flag = useAnimatedStyle(() => ({ transform: [{ skewY: `${-6 + 12 * wave.value}deg` }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y, alignItems: "flex-start" }, pole]}>
      <View style={{ width: 4, height: 90, backgroundColor: "#4A3B2C", borderRadius: 2 }} />
      <Animated.View style={[{ position: "absolute", left: 4, top: 4, width: 44, height: 30, backgroundColor: heraldic, borderWidth: 1.5, borderColor: color }, flag]}>
        <View style={{ position: "absolute", left: 14, top: 7, width: 16, height: 16, borderRadius: 8, borderWidth: 3, borderColor: color }} />
      </Animated.View>
      <View style={{ position: "absolute", left: 20, top: 30 }}>{Array.from({ length: 10 }).map((_, i) => <Ember key={i} t={ember} i={i} color={color} />)}</View>
    </Animated.View>
  );
}

// Game HUD health colours (identical in every theme, like the VFX palette above)
export const HP_COLORS = { high: ["#4FB35B", "#A6E06A"], mid: ["#E3C16F", "#F6E29A"], low: ["#C62D3F", "#FF7A6B"], boss: ["#8B1A2B", "#FF4D3D"] } as const;
export const hpColors = (hp: number): readonly [string, string] => (hp < 0.3 ? HP_COLORS.low : hp < 0.55 ? HP_COLORS.mid : HP_COLORS.high);

/** Duel-HUD health bar (presentational): lagging white "recent damage" ghost, flash on hit, pulse when low. `hp` in 0..1.
 * `align="right"` mirrors the bar (fill anchored on the right) for the enemy side. */
export function HpBar({ hp, name, sub, tag, icon, palette, align = "left", hitTick = 0, testID, style }: {
  hp: number; name: string; sub?: string; tag?: string; icon: IconName; palette: readonly [string, string]; align?: "left" | "right"; hitTick?: number; testID?: string; style?: any;
}) {
  const { colors } = useTheme();
  const v = Math.max(0, Math.min(1, hp));
  const fill = useSharedValue(v);
  const ghost = useSharedValue(v);
  const flash = useSharedValue(0);
  const pulse = useSharedValue(1);
  const low = v < 0.3;
  useEffect(() => {
    fill.value = withTiming(v, { duration: 260, easing: Easing.out(Easing.quad) });
    ghost.value = withDelay(340, withTiming(v, { duration: 620, easing: Easing.out(Easing.quad) }));
  }, [v, fill, ghost]);
  useEffect(() => {
    if (!hitTick) return;
    flash.value = 1;
    flash.value = withTiming(0, { duration: 340, easing: Easing.out(Easing.quad) });
  }, [hitTick, flash]);
  useEffect(() => {
    pulse.value = low ? withRepeat(withSequence(withTiming(0.5, { duration: 280 }), withTiming(1, { duration: 280 })), -1, true) : withTiming(1, { duration: 200 });
  }, [low, pulse]);
  const fillStyle = useAnimatedStyle(() => ({ width: `${fill.value * 100}%`, opacity: pulse.value }));
  const ghostStyle = useAnimatedStyle(() => ({ width: `${ghost.value * 100}%` }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: flash.value }));
  const right = align === "right";
  const pct = Math.round(v * 100);
  return (
    <View style={[{ flex: 1 }, style]} testID={testID}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 5, marginBottom: 2 }}>
        <Icon name={icon} size={13} color={palette[1]} />
        {tag ? (
          <View style={{ paddingHorizontal: 4, borderRadius: 3, backgroundColor: palette[0], borderWidth: 1, borderColor: palette[1] }}>
            <Text style={{ fontFamily: fonts.bodyBold, fontSize: 8, color: "#FFFFFF", letterSpacing: 1 }}>{tag}</Text>
          </View>
        ) : null}
        <Text numberOfLines={1} style={{ flex: 1, fontFamily: fonts.display, fontSize: 13, color: colors.goldBright, textShadowColor: "#000", textShadowRadius: 3 }} testID={testID ? `${testID}-name` : undefined}>{name}</Text>
        <Text style={{ fontFamily: fonts.displaySemi, fontSize: 13, color: low ? HP_COLORS.low[1] : "#FFFFFF", textShadowColor: "#000", textShadowRadius: 3 }} testID={testID ? `${testID}-pct` : undefined}>{pct}%</Text>
      </View>
      {sub ? <Text numberOfLines={1} style={{ fontFamily: fonts.bodyMedium, fontSize: 10, color: colors.onSurface, marginBottom: 2, textShadowColor: "#000", textShadowRadius: 3 }} testID={testID ? `${testID}-sub` : undefined}>{sub}</Text> : null}
      <View style={{ height: 11, borderRadius: 6, backgroundColor: colors.scrim, borderWidth: 1.5, borderColor: colors.gold, overflow: "hidden", flexDirection: right ? "row-reverse" : "row" }}>
        <Animated.View style={[{ position: "absolute", top: 0, bottom: 0, backgroundColor: "#FFFFFF", opacity: 0.55 }, right ? { right: 0 } : { left: 0 }, ghostStyle]} />
        <Animated.View style={[{ height: "100%", overflow: "hidden" }, fillStyle]}>
          <LinearGradient colors={[palette[0], palette[1]]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ flex: 1 }} />
          <View style={{ position: "absolute", left: 0, right: 0, top: 0, height: 4, backgroundColor: "#FFFFFF", opacity: 0.22 }} />
        </Animated.View>
        <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "#FFFFFF" }, flashStyle]} />
      </View>
    </View>
  );
}

// ==== v1.2 "wow" layer: impact language, enemy moves support, Super power-up and ultimate ================================

function SpeedLine({ t, angle, radius, color }: { t: SharedValue<number>; angle: number; radius: number; color: string }) {
  const style = useAnimatedStyle(() => ({
    opacity: (1 - t.value) * 0.9,
    transform: [{ rotate: `${angle}rad` }, { translateX: radius * 0.25 + radius * 0.75 * t.value }, { scaleX: 0.4 + 1.2 * t.value }],
  }));
  return <Animated.View style={[{ position: "absolute", width: 34, height: 3, borderRadius: 2, backgroundColor: color }, style]} />;
}

/** Radial speed lines bursting from an impact point (heavy hits, ultimate). */
export function SpeedLines({ x, y, color, count = 14, radius = 110 }: { x: number; y: number; color: string; count?: number; radius?: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 380, easing: Easing.out(Easing.cubic) });
  }, [t]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {Array.from({ length: count }).map((_, i) => <SpeedLine key={i} t={t} angle={(i / count) * Math.PI * 2 + 0.2} radius={radius} color={color} />)}
    </View>
  );
}

/** White-hot impact flare (scales up and fades). */
export function Flare({ x, y, size = 60, color = "#FFFFFF" }: { x: number; y: number; size?: number; color?: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 260, easing: Easing.out(Easing.quad) });
  }, [t]);
  const style = useAnimatedStyle(() => ({ opacity: 0.9 * (1 - t.value), transform: [{ scale: 0.3 + 1.4 * t.value }] }));
  return <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size, borderRadius: size / 2, backgroundColor: color }, style]} />;
}

function Puff({ t, i, color }: { t: SharedValue<number>; i: number; color: string }) {
  const dir = i % 2 ? 1 : -1;
  const style = useAnimatedStyle(() => ({
    opacity: 0.8 * (1 - t.value),
    transform: [{ translateX: dir * (10 + (i * 13) % 40) * t.value }, { translateY: -(6 + (i * 7) % 18) * t.value }, { scale: 0.6 + 1.6 * t.value }],
  }));
  return <Animated.View style={[{ position: "absolute", width: 14, height: 10, borderRadius: 7, backgroundColor: color }, style]} />;
}

/** Ground dust puff (landings, slams): dust cloud sprite spreading sideways + a few puffs. */
export function DustPuff({ x, y, color = "rgba(214,190,150,0.75)", count = 8 }: { x: number; y: number; color?: string; count?: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 620, easing: Easing.out(Easing.quad) });
  }, [t]);
  const hasSprite = !!vfxArt("dust_cloud");
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {hasSprite ? <SpriteFx x={0} y={6} sprite="dust_cloud" size={130} aspect={0.55} from={0.35} to={1.35} duration={680} fadeIn={0.08} drift={10} /> : null}
      {Array.from({ length: hasSprite ? 3 : count }).map((_, i) => <Puff key={i} t={t} i={i} color={color} />)}
    </View>
  );
}

function TrailDot({ t, lag, dx, dy, color, size }: { t: SharedValue<number>; lag: number; dx: number; dy: number; color: string; size: number }) {
  const style = useAnimatedStyle(() => {
    const p = Math.max(0, t.value - lag);
    return { opacity: p > 0 && t.value < 0.98 ? 0.7 - lag * 3 : 0, transform: [{ translateX: dx * p }, { translateY: dy * p - Math.sin(Math.PI * p) * 42 }] };
  });
  return <Animated.View style={[{ position: "absolute", width: size, height: size, borderRadius: size / 2, backgroundColor: color, left: -size / 2, top: -size / 2 }, style]} />;
}

/** Projectile flying from (x,y) to (tx,ty) along an arc. `sprite` "energy_orb" (magic, tail on the right → flies left; flipped when
 * flying right) or "arrow_volley" (arrows fly right natively). Falls back to glowing trail dots. */
export function Projectile({ x, y, tx, ty, color, duration = 460, sprite = "energy_orb", size = 70 }: { x: number; y: number; tx: number; ty: number; color: string; duration?: number; sprite?: "energy_orb" | "arrow_volley" | "none"; size?: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration, easing: sprite === "arrow_volley" ? Easing.linear : Easing.in(Easing.quad) });
  }, [t, duration, sprite]);
  const dx = tx - x, dy = ty - y;
  const img = sprite !== "none" ? vfxArt(sprite) : undefined;
  const toRight = dx > 0;
  const flip = sprite === "energy_orb" ? toRight : !toRight;
  const arc = sprite === "arrow_volley" ? 26 : 42;
  const head = useAnimatedStyle(() => {
    const p = t.value;
    const ang = Math.atan2(dy - Math.cos(Math.PI * p) * Math.PI * arc, dx) * (180 / Math.PI);
    return { opacity: p < 0.97 ? 1 : 0, transform: [{ translateX: dx * p }, { translateY: dy * p - Math.sin(Math.PI * p) * arc }, { rotate: `${ang}deg` }, { scaleX: flip ? -1 : 1 }] };
  });
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {img ? (
        <Animated.View style={[{ position: "absolute", left: -size / 2, top: -size / 4, width: size, height: size / 2 }, head]}>
          <Image source={img} style={{ width: size, height: size / 2 }} resizeMode="contain" />
        </Animated.View>
      ) : (
        <>
          <TrailDot t={t} lag={0.16} dx={dx} dy={dy} color={color} size={7} />
          <TrailDot t={t} lag={0.1} dx={dx} dy={dy} color={color} size={9} />
          <TrailDot t={t} lag={0.05} dx={dx} dy={dy} color={color} size={11} />
          <TrailDot t={t} lag={0} dx={dx} dy={dy} color="#FFFFFF" size={12} />
        </>
      )}
    </View>
  );
}

/** Afterimage ghost left behind by a dash (fades + stretches). */
export function Ghost({ x, y, w, h, source, tint, delay = 0 }: { x: number; y: number; w: number; h: number; source: number; tint: string; delay?: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withDelay(delay, withTiming(1, { duration: 420, easing: Easing.out(Easing.quad) }));
  }, [t, delay]);
  const style = useAnimatedStyle(() => ({ opacity: t.value === 0 ? 0 : 0.55 * (1 - t.value), transform: [{ scaleX: 1 + 0.25 * t.value }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y, width: w, height: h }, style]}>
      <Image source={source} style={{ width: w, height: h, tintColor: tint }} resizeMode="contain" />
    </Animated.View>
  );
}

function Flame({ i, width, height, color, core }: { i: number; width: number; height: number; color: string; core: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    const d = 260 + (i * 53) % 160;
    t.value = withRepeat(withSequence(withTiming(1, { duration: d, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: d, easing: Easing.inOut(Easing.quad) })), -1, false);
  }, [t, i]);
  const n = 9;
  const off = (i - (n - 1) / 2) / ((n - 1) / 2); // -1..1
  const w = width * (0.15 - 0.05 * Math.abs(off));
  const hgt = height * (0.42 + 0.52 * (1 - Math.abs(off))) * (0.72 + 0.14 * ((i * 37) % 3));
  const lean = off * -14;
  const style = useAnimatedStyle(() => ({
    opacity: 0.6 + 0.35 * t.value,
    transform: [{ translateX: off * width * 0.4 }, { skewX: `${lean + (t.value - 0.5) * 12}deg` }, { scaleY: 0.8 + 0.4 * t.value }, { scaleX: 0.85 + 0.25 * (1 - t.value) }],
  }));
  return (
    <Animated.View style={[{ position: "absolute", bottom: 0, left: width / 2 - w / 2, width: w, height: hgt, borderTopLeftRadius: off <= 0 ? w * 0.35 : w, borderTopRightRadius: off <= 0 ? w : w * 0.35, borderBottomLeftRadius: w / 3, borderBottomRightRadius: w / 3, backgroundColor: color, transformOrigin: "50% 100%" }, style]}>
      <View style={{ position: "absolute", bottom: 0, left: w * 0.28, width: w * 0.44, height: hgt * 0.55, borderTopLeftRadius: w, borderTopRightRadius: w, backgroundColor: core, opacity: 0.9 }} />
    </Animated.View>
  );
}

function Spark({ i, width, height, color }: { i: number; width: number; height: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withDelay((i * 97) % 600, withRepeat(withTiming(1, { duration: 700 + (i * 61) % 400, easing: Easing.out(Easing.quad) }), -1, false));
  }, [t, i]);
  const x0 = ((i * 53) % 100) / 100;
  const style = useAnimatedStyle(() => ({ opacity: (1 - t.value) * 0.95, transform: [{ translateX: (x0 - 0.5) * width * 0.9 + Math.sin(t.value * 7 + i) * 8 }, { translateY: -t.value * height * 1.1 }] }));
  return <Animated.View style={[{ position: "absolute", bottom: 0, left: width / 2, width: 4 + (i % 3), height: 4 + (i % 3), borderRadius: 3, backgroundColor: i % 3 ? color : "#FFFFFF" }, style]} />;
}

function Arc({ i, width, height }: { i: number; width: number; height: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withDelay(i * 130, withRepeat(withSequence(withTiming(1, { duration: 60 }), withTiming(0, { duration: 90 }), withTiming(0, { duration: 260 + (i * 71) % 300 })), -1, false));
  }, [t, i]);
  const style = useAnimatedStyle(() => ({ opacity: t.value }));
  return <Animated.View style={[{ position: "absolute", left: width * (0.15 + ((i * 37) % 70) / 100), top: height * (0.1 + ((i * 53) % 70) / 100), width: 26 + (i % 3) * 10, height: 2, backgroundColor: "#FFFFFF", transform: [{ rotate: `${(i * 47) % 180}deg` }] }, style]} />;
}

/** "Super" power-up aura around the Lord: rising golden flames, sparks, electric arcs and a ground glow. */
export function SuperAura({ x, y, width = 150, height = 200, color = "#FFC93C", core = "#FFF3B0" }: { x: number; y: number; width?: number; height?: number; color?: string; core?: string }) {
  const s = useSharedValue(0);
  const pulse = useSharedValue(0);
  useEffect(() => {
    s.value = withTiming(1, { duration: 360, easing: Easing.out(Easing.back(1.4)) });
    pulse.value = withRepeat(withSequence(withTiming(1, { duration: 160 }), withTiming(0, { duration: 160 })), -1, true);
  }, [s, pulse]);
  const style = useAnimatedStyle(() => ({ opacity: Math.min(1, s.value), transform: [{ scale: 0.4 + 0.6 * s.value }] }));
  const auraStyle = useAnimatedStyle(() => ({ opacity: 0.8 + 0.2 * pulse.value, transform: [{ scaleX: 1 + 0.06 * pulse.value }, { scaleY: 1 + 0.04 * pulse.value }] }));
  const aura = vfxArt("energy_aura");
  return (
    <Animated.View pointerEvents="none" exiting={FadeOut.duration(420)} style={[{ position: "absolute", left: x - width / 2, top: y - height, width, height, transformOrigin: "50% 100%" }, style]} testID="super-aura">
      <View style={{ position: "absolute", bottom: -10, left: width * 0.05, width: width * 0.9, height: 34, borderRadius: width, backgroundColor: color, opacity: 0.55 }} />
      {aura ? (
        <Animated.View style={[{ position: "absolute", bottom: -8, left: -width * 0.1, width: width * 1.2, height: height * 1.12, transformOrigin: "50% 100%" }, auraStyle]}>
          <Image source={aura} style={{ width: width * 1.2, height: height * 1.12 }} resizeMode="stretch" />
        </Animated.View>
      ) : (
        <>
          <View style={{ position: "absolute", bottom: 0, left: width * 0.1, width: width * 0.8, height: height * 0.9, borderTopLeftRadius: width, borderTopRightRadius: width, backgroundColor: color, opacity: 0.22 }} />
          {Array.from({ length: 9 }).map((_, i) => <Flame key={i} i={i} width={width} height={height} color={color} core={core} />)}
        </>
      )}
      {Array.from({ length: 14 }).map((_, i) => <Spark key={i} i={i} width={width} height={height} color={color} />)}
      {Array.from({ length: 5 }).map((_, i) => <Arc key={i} i={i} width={width} height={height} />)}
    </Animated.View>
  );
}

function Pillar({ t, i, x, height, color }: { t: SharedValue<number>; i: number; x: number; height: number; color: string }) {
  const delay = 0.25 + i * 0.09;
  const style = useAnimatedStyle(() => {
    const p = Math.max(0, Math.min(1, (t.value - delay) / (1 - delay)));
    return { opacity: p === 0 ? 0 : 0.9 * (1 - p), transform: [{ scaleX: 0.3 + 1.8 * p }, { scaleY: 0.2 + 0.8 * Math.min(1, p * 3) }] };
  });
  return <Animated.View style={[{ position: "absolute", left: x, bottom: 0, width: 16, height, borderRadius: 8, backgroundColor: color, transformOrigin: "50% 100%" }, style]} />;
}

/** Ultimate release: a wall of light sweeps across the horde, followed by holy light pillars erupting from the ground. */
export function UltimateWave({ x, y, width, height, color = "#FFD84A" }: { x: number; y: number; width: number; height: number; color?: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 900, easing: Easing.out(Easing.quad) });
  }, [t]);
  const wall = useAnimatedStyle(() => ({ opacity: 1 - t.value * t.value, transform: [{ translateX: width * 0.85 * Math.min(1, t.value * 1.6) }, { scaleY: 0.5 + 0.7 * Math.min(1, t.value * 2) }, { skewX: "-18deg" }] }));
  const glow = useAnimatedStyle(() => ({ opacity: 0.6 * (1 - t.value) }));
  const beams = !!vfxArt("holy_beam");
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y - height, width, height }} testID="ultimate-wave">
      <Animated.View style={[{ position: "absolute", left: 0, right: 0, bottom: 0, height, backgroundColor: color }, glow]} />
      <Animated.View style={[{ position: "absolute", left: 0, bottom: 0, width: 46, height, borderRadius: 20, backgroundColor: "#FFFFFF", shadowColor: color, shadowOpacity: 1, shadowRadius: 30, transformOrigin: "50% 100%" }, wall]}>
        <View style={{ position: "absolute", left: -18, top: 0, bottom: 0, width: 24, borderRadius: 12, backgroundColor: color, opacity: 0.9 }} />
        <View style={{ position: "absolute", right: -30, top: 0, bottom: 0, width: 40, borderRadius: 12, backgroundColor: color, opacity: 0.55 }} />
      </Animated.View>
      {beams
        ? Array.from({ length: 5 }).map((_, i) => <SpriteFx key={i} x={width * (0.28 + i * 0.15)} y={height} sprite="holy_beam" size={height * 0.5} aspect={2} anchor="bottom" from={0.6} to={1.1} duration={700} delay={220 + i * 80} fadeIn={0.1} hold={0.25} />)
        : Array.from({ length: 6 }).map((_, i) => <Pillar key={i} t={t} i={i} x={width * (0.25 + i * 0.13)} height={height * 0.95} color={i % 2 ? "#FFFFFF" : color} />)}
      <SpriteFx x={width * 0.5} y={height * 0.55} sprite="impact_burst" size={Math.min(width, 320)} from={0.4} to={1.4} duration={520} delay={120} />
    </View>
  );
}

/** Combo counter pop. */
export function ComboText({ n, x, y, color }: { n: number; x: number; y: number; color: string }) {
  const s = useSharedValue(0);
  useEffect(() => {
    s.value = 0;
    s.value = withSequence(withTiming(1.25, { duration: 140, easing: Easing.out(Easing.back(3)) }), withTiming(1, { duration: 160 }));
  }, [s, n]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: s.value }, { rotate: "-6deg" }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y, alignItems: "center" }, style]} testID="combo-counter">
      <Text style={{ fontFamily: fonts.display, fontSize: 13, letterSpacing: 2, color, textShadowColor: "#000", textShadowRadius: 4 }}>COMBO</Text>
      <Text style={{ fontFamily: fonts.display, fontSize: 30, color: "#FFFFFF", marginTop: -6, textShadowColor: color, textShadowRadius: 10 }}>x{n}</Text>
    </Animated.View>
  );
}

/** Floating word (e.g. "SCHIVATA!"). */
export function FloatText({ x, y, text, color, size = 20 }: { x: number; y: number; text: string; color: string; size?: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 900, easing: Easing.out(Easing.cubic) });
  }, [t]);
  const style = useAnimatedStyle(() => ({ opacity: 1 - Math.max(0, (t.value - 0.5) / 0.5), transform: [{ translateY: -50 * t.value }, { scale: 1.3 - 0.3 * t.value }, { rotate: "-4deg" }] }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y }, style]} testID="float-text">
      <Text style={{ fontFamily: fonts.display, fontSize: size, letterSpacing: 1, color, textShadowColor: "#000", textShadowOffset: { width: 1, height: 2 }, textShadowRadius: 4 }}>{text}</Text>
    </Animated.View>
  );
}

/** Boss telegraph: flashing red warning strip across the scene. */
export function WarningBanner({ text, sceneH }: { text: string; sceneH: number }) {
  const { colors } = useTheme();
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withRepeat(withSequence(withTiming(1, { duration: 180 }), withTiming(0.35, { duration: 180 })), -1, true);
  }, [p]);
  const style = useAnimatedStyle(() => ({ opacity: p.value }));
  const stripe = useAnimatedStyle(() => ({ opacity: 0.25 + 0.35 * p.value }));
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.56, alignItems: "center" }} testID="boss-warning">
      <Animated.View style={[{ position: "absolute", left: 0, right: 0, top: -6, height: 44, backgroundColor: colors.error }, stripe]} />
      <Animated.View style={[{ flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 14, paddingVertical: 4, borderRadius: 4, backgroundColor: colors.overlay, borderWidth: 2, borderColor: colors.error }, style]}>
        <Text style={{ fontFamily: fonts.display, fontSize: 16, color: colors.error }}>⚠ MOSSA SPECIALE: </Text>
        <Text style={{ fontFamily: fonts.display, fontSize: 16, color: "#FFFFFF", textShadowColor: colors.error, textShadowRadius: 8 }}>{text}</Text>
      </Animated.View>
    </View>
  );
}

export type BossFxKind = "slam" | "breath" | "shards" | "vortex" | "beam" | "wave" | "void" | "roots" | "quake";
/** Unique boss special move (sprite based). `x,y` = Lord ground anchor, `bx,by` = boss anchor, `width` = scene width. */
export function BossMoveFx({ kind, x, y, bx, by, width, height }: { kind: BossFxKind; x: number; y: number; bx: number; by: number; width: number; height: number }) {
  switch (kind) {
    case "breath": {
      const w = Math.max(160, bx - x + 40);
      return (
        <>
          <SpriteFx x={bx - w / 2} y={by - 20} sprite="fire_breath" size={w} aspect={0.42} from={0.5} to={1.15} duration={900} fadeIn={0.1} hold={0.35} />
          <SpriteFx x={x + 20} y={y - 40} sprite="fire_burst" size={150} from={0.3} to={1.3} duration={650} delay={380} />
        </>
      );
    }
    case "slam":
      return (
        <>
          <SpriteFx x={x + 30} y={y} sprite="rock_slam" size={Math.min(320, width * 0.8)} aspect={0.55} anchor="center" from={0.3} to={1.2} duration={820} fadeIn={0.08} hold={0.3} />
          <SpriteFx x={x + 30} y={y} sprite="dust_cloud" size={220} aspect={0.55} from={0.4} to={1.5} duration={800} delay={80} drift={16} />
        </>
      );
    case "quake":
      return (
        <>
          <SpriteFx x={width * 0.45} y={y} sprite="rock_slam" size={Math.min(360, width * 0.95)} aspect={0.5} from={0.5} to={1.25} duration={900} fadeIn={0.08} hold={0.35} />
          {Array.from({ length: 4 }).map((_, i) => <SpriteFx key={i} x={x - 30 + i * 60} y={y - 10} sprite="dust_cloud" size={120} aspect={0.6} from={0.3} to={1.3} duration={700} delay={i * 90} drift={14} />)}
        </>
      );
    case "roots":
      return (
        <>
          <SpriteFx x={x + 20} y={y + 4} sprite="dust_cloud" size={200} aspect={0.5} from={0.4} to={1.3} duration={700} drift={8} />
          {Array.from({ length: 3 }).map((_, i) => <SpriteFx key={i} x={x - 30 + i * 40} y={y} sprite="soul_wisp" size={110} aspect={1.2} anchor="bottom" from={0.3} to={1.2} duration={900} delay={100 + i * 120} fadeIn={0.1} hold={0.2} />)}
        </>
      );
    case "shards":
      return (
        <>
          <SpriteFx x={x + 10} y={y - 60} sprite="ice_shards" size={220} from={0.3} to={1.4} duration={800} fadeIn={0.08} />
          <SpriteFx x={bx} y={by - 30} sprite="ice_shards" size={160} from={0.6} to={1.1} duration={500} />
        </>
      );
    case "vortex":
      return <SpriteFx x={x + 10} y={y + 6} sprite="sand_vortex" size={230} aspect={1.25} anchor="bottom" from={0.35} to={1.15} duration={1100} fadeIn={0.12} hold={0.3} drift={6} />;
    case "beam":
      return (
        <>
          <SpriteFx x={x + 10} y={y + 4} sprite="holy_beam" size={140} aspect={2.2} anchor="bottom" from={0.5} to={1.1} duration={900} fadeIn={0.06} hold={0.35} />
          <SpriteFx x={x + 10} y={y - 30} sprite="impact_burst" size={160} from={0.3} to={1.2} duration={500} delay={150} />
        </>
      );
    case "wave":
      return <SpriteFx x={(x + bx) / 2} y={y - 30} sprite="water_wave" size={Math.max(240, bx - x + 80)} aspect={0.55} from={0.5} to={1.2} duration={1000} fadeIn={0.1} hold={0.3} />;
    case "void":
    default:
      return (
        <>
          <SpriteFx x={x + 10} y={y - 50} sprite="void_burst" size={230} from={0.2} to={1.4} duration={900} fadeIn={0.1} hold={0.2} />
          <SpriteFx x={bx} y={by} sprite="void_burst" size={140} from={0.8} to={1.1} duration={600} />
        </>
      );
  }
}

/** Enemy death: soul wisp sprite rising + expanding ring. */
export function DeathDissolve({ x, y, color }: { x: number; y: number; color: string }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: 800, easing: Easing.out(Easing.quad) });
  }, [t]);
  const ring = useAnimatedStyle(() => ({ opacity: 0.8 * (1 - t.value), transform: [{ scale: 0.2 + 2.2 * t.value }, { scaleY: 0.45 }] }));
  const hasSprite = !!vfxArt("soul_wisp");
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      <Animated.View style={[{ position: "absolute", left: -30, top: -12, width: 60, height: 60, borderRadius: 30, borderWidth: 3, borderColor: color }, ring]} />
      {hasSprite ? <SpriteFx x={0} y={20} sprite="soul_wisp" size={90} aspect={1.15} anchor="bottom" from={0.5} to={1.2} duration={900} fadeIn={0.1} drift={70} /> : null}
      {Array.from({ length: hasSprite ? 4 : 9 }).map((_, i) => <Wisp key={i} t={t} i={i} color={i % 3 ? color : "#FFFFFF"} />)}
    </View>
  );
}

function Wisp({ t, i, color }: { t: SharedValue<number>; i: number; color: string }) {
  const style = useAnimatedStyle(() => ({
    opacity: (1 - t.value) * 0.9,
    transform: [{ translateX: ((i % 5) - 2) * 12 + Math.sin(t.value * 6 + i) * 10 }, { translateY: -110 * t.value - (i % 3) * 10 }, { scale: 1 - 0.5 * t.value }],
  }));
  return <Animated.View style={[{ position: "absolute", width: 7, height: 7, borderRadius: 4, backgroundColor: color }, style]} />;
}

/** Army-skin war banner planted behind the formation: gentle sway + heraldic glow pool under the troops. */
export function WarBanner({ x, y, h, source, glow, width }: { x: number; y: number; h: number; source?: number; glow: string; width: number }) {
  const sway = useSharedValue(0);
  const pulse = useSharedValue(0);
  useEffect(() => {
    sway.value = withRepeat(withSequence(withTiming(1, { duration: 1400, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 1400, easing: Easing.inOut(Easing.sin) })), -1, false);
    pulse.value = withRepeat(withSequence(withTiming(1, { duration: 1100 }), withTiming(0, { duration: 1100 })), -1, false);
  }, [sway, pulse]);
  const swayStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${-3 + 6 * sway.value}deg` }] }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: 0.22 + 0.16 * pulse.value }));
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, right: 0, bottom: 0 }} testID="army-banner">
      <Animated.View style={[{ position: "absolute", left: x, bottom: 40, width, height: 22, borderRadius: 999, backgroundColor: glow }, glowStyle]} />
      {source ? (
        <Animated.View style={[{ position: "absolute", left: x + 4, top: y - h * 0.15, width: h * 0.42, height: h, transformOrigin: "bottom" }, swayStyle]}>
          <Image source={source} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
        </Animated.View>
      ) : null}
    </View>
  );
}
