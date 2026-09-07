// Battle VFX: floating damage numbers, slash arcs, spark bursts, coin showers and outcome banners. Purely presentational (server decides the outcome).
import React, { useEffect } from "react";
import { Text, View } from "react-native";
import Animated, { Easing, SharedValue, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { fonts, useTheme } from "@/src/theme";
import { fmt } from "@/src/ui";

export type Fx = { id: number; kind: "dmg" | "slash" | "burst"; x: number; y: number; value?: number; crit?: boolean; color?: string; size?: number };

export function DamageNumber({ x, y, value, crit, color, seed }: { x: number; y: number; value: number; crit?: boolean; color: string; seed: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: crit ? 1100 : 850, easing: Easing.out(Easing.cubic) });
  }, [t, crit]);
  const drift = ((seed % 7) - 3) * 6;
  const style = useAnimatedStyle(() => ({
    opacity: 1 - Math.max(0, (t.value - 0.55) / 0.45),
    transform: [{ translateY: -(crit ? 80 : 56) * t.value }, { translateX: drift * t.value }, { scale: crit ? 1.6 - 0.5 * t.value : 1.15 - 0.25 * t.value }],
  }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: x, top: y }, style]}>
      <Text style={{ fontFamily: fonts.display, fontSize: crit ? 28 : 18, color, textShadowColor: "#000", textShadowOffset: { width: 1, height: 2 }, textShadowRadius: 3 }}>
        {crit ? `${fmt(value)}!` : fmt(value)}
      </Text>
    </Animated.View>
  );
}

export function Slash({ x, y, color, size = 64 }: { x: number; y: number; color: string; size?: number }) {
  const t = useSharedValue(0);
  const big = size > 80;
  useEffect(() => {
    t.value = withTiming(1, { duration: big ? 380 : 280, easing: Easing.out(Easing.quad) });
  }, [t, big]);
  const style = useAnimatedStyle(() => ({ opacity: 1 - t.value, transform: [{ rotate: `${-70 + 130 * t.value}deg` }, { scale: 0.5 + 0.8 * t.value }] }));
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

export function Burst({ x, y, color, count = 8, seed = 0, big }: { x: number; y: number; color: string; count?: number; seed?: number; big?: boolean }) {
  const t = useSharedValue(0);
  useEffect(() => {
    t.value = withTiming(1, { duration: big ? 900 : 520, easing: Easing.out(Easing.quad) });
  }, [t, big]);
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: x, top: y }}>
      {Array.from({ length: count }).map((_, i) => (
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
    <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: sceneH * 0.3, alignItems: "center" }, style]} testID="skill-banner">
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

export function BossBar({ name, hp, width }: { name: string; hp: number; width: number }) {
  const { colors } = useTheme();
  const pulse = useSharedValue(0);
  useEffect(() => {
    pulse.value = withRepeat(withSequence(withTiming(1, { duration: 600 }), withTiming(0, { duration: 600 })), -1, false);
  }, [pulse]);
  const glow = useAnimatedStyle(() => ({ opacity: 0.5 + 0.5 * pulse.value }));
  return (
    <View pointerEvents="none" style={{ position: "absolute", top: 58, left: (width - Math.min(320, width - 24)) / 2, width: Math.min(320, width - 24) }} testID="boss-bar">
      <Text style={{ fontFamily: fonts.display, fontSize: 15, color: colors.goldBright, textAlign: "center", textShadowColor: "#000", textShadowRadius: 4 }}>{name}</Text>
      <View style={{ height: 10, backgroundColor: colors.scrim, borderRadius: 5, overflow: "hidden", borderWidth: 1.5, borderColor: colors.gold }}>
        <Animated.View style={[{ width: `${Math.max(0, Math.min(100, hp * 100))}%`, height: "100%", backgroundColor: colors.error }, glow]} />
      </View>
    </View>
  );
}
