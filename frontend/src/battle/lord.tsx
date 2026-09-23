// The Lord: vector knight whose armor, colors and glow follow the equipped gear rarity (Art Direction v1.1). Sword is a separate layer so it can swing.
import React, { memo, useEffect } from "react";
import { Image, View } from "react-native";
import Animated, { Easing, SharedValue, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import Svg, { Circle, Defs, Ellipse, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { lordArt } from "@/src/art";
import { rarityColor, useTheme } from "@/src/theme";

type Item = { slot: string; rarity: string; item_level: number } | null | undefined;

const SKIN = "#D9B48F", CLOTH = "#6B5A44", LEATHER = "#5A4632", STEEL = "#9AA1A9", STEEL_D = "#6E7580", HAIR = "#3A2A1E", INK = "#111111";
const RARITY_RANK: Record<string, number> = { common: 0, uncommon: 1, rare: 2, epic: 3, legendary: 4, mythic: 5, ancient: 6 };
const SHADOW = [{ w: 0.82, h: 0.085, o: 0.18 }, { w: 0.66, h: 0.07, o: 0.22 }, { w: 0.48, h: 0.055, o: 0.28 }];
const RIM_OFFSET = 2.5;

// ---- Lord move set (v1.2): 1 slash · 2 heavy · 3 rising slash · 4 dash · 5 leap · 6 super charge · 7 super release · 8 dodge (back-dash) ----
export type LordMove = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;
export const LORD_MOVE_MS: Record<LordMove, number> = { 0: 0, 1: 760, 2: 820, 3: 700, 4: 760, 5: 820, 6: 1700, 7: 620, 8: 640 };

export const LordSprite = memo(function LordSprite({ equipped, size = 64, tier = 0, heraldicColor = "#800020", swinging = true, move, hurtTick = 0, superMode = false }: { equipped: Record<string, Item>; size?: number; tier?: number; heraldicColor?: string; swinging?: boolean; move?: { kind: SharedValue<number>; t: SharedValue<number>; dist: SharedValue<number> }; hurtTick?: number; superMode?: boolean }) {
  const { colors } = useTheme();
  const u = size / 80;
  const has = (s: string) => !!equipped[s];
  const col = (slot: string, fallback: string) => (equipped[slot] ? rarityColor(colors, equipped[slot]!.rarity) : fallback);
  const rank = (slot: string) => (equipped[slot] ? RARITY_RANK[equipped[slot]!.rarity] ?? 0 : -1);
  const royal = tier >= 5;
  const armored = has("chest");
  const plate = armored ? (rank("chest") >= 4 ? "#C9B26A" : rank("chest") >= 2 ? "#B4BCC6" : STEEL) : CLOTH;
  const trim = armored ? col("chest", STEEL_D) : LEATHER;
  const weaponGlow = rank("weapon") >= 2 ? col("weapon", colors.gold) : null;
  const aura = tier >= 3 || rank("weapon") >= 4;

  const swing = useSharedValue(20);
  useEffect(() => {
    if (!swinging) {
      swing.value = 20;
      return;
    }
    swing.value = withRepeat(withSequence(withTiming(-80, { duration: 170, easing: Easing.out(Easing.cubic) }), withTiming(-70, { duration: 130 }), withTiming(20, { duration: 480, easing: Easing.inOut(Easing.quad) }), withTiming(20, { duration: 420 })), -1, false);
  }, [swing, swinging]);
  const swordStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${swing.value}deg` }] }));
  // rendered variant: whole-figure choreography driven by the scene's move (kind + progress) and recoil when hit
  const hurt = useSharedValue(0);
  useEffect(() => {
    if (!hurtTick) return;
    hurt.value = 1;
    hurt.value = withTiming(0, { duration: 320, easing: Easing.out(Easing.quad) });
  }, [hurtTick, hurt]);
  const glow = useSharedValue(0);
  useEffect(() => {
    if (superMode) glow.value = withRepeat(withSequence(withTiming(1, { duration: 140 }), withTiming(0.45, { duration: 140 })), -1, true);
    else glow.value = withTiming(0, { duration: 300 });
  }, [superMode, glow]);
  const artStyle = useAnimatedStyle(() => {
    const k = move ? move.kind.value : 0, t = move ? move.t.value : 0, d = move ? move.dist.value : 0, hv = hurt.value;
    const s = Math.sin(Math.PI * Math.min(1, Math.max(0, t)));
    let tx = -8 * hv, ty = 0, rot = 5 * hv, sx = 1, sy = 1;
    if (k === 1) { tx += 24 * s; rot += -11 * s; sx = 1 + 0.05 * s; sy = 1 - 0.03 * s; }
    else if (k === 2) { tx += 54 * s; rot += -17 * s; sx = 1 + 0.1 * s; sy = 1 - 0.05 * s; }
    else if (k === 3) { tx += 36 * s; ty = -26 * Math.sin(Math.PI * Math.min(1, t * 1.3)); rot += -14 * s; sx = 1 + 0.06 * s; }
    else if (k === 4) { const p = t < 0.5 ? 1 - (1 - t * 2) * (1 - t * 2) : 1 - (t - 0.5) * 2; tx += d * p; sx = 1 + 0.15 * s; rot += -8 * s; }
    else if (k === 5) { const up = Math.min(1, t / 0.7); tx += 44 * Math.sin((Math.PI / 2) * up); ty = -78 * Math.sin(Math.PI * up); rot += -12 * Math.sin(Math.PI * up); sy = t > 0.7 ? 1 - 0.18 * Math.sin(Math.PI * ((t - 0.7) / 0.3)) : 1 + 0.06 * Math.sin(Math.PI * up); sx = t > 0.7 ? 1 + 0.12 * Math.sin(Math.PI * ((t - 0.7) / 0.3)) : 1; }
    else if (k === 6) { ty = -14 * Math.min(1, t * 1.4); tx += Math.sin(t * 90) * 2.2 * Math.min(1, t * 2); sx = sy = 1 + 0.08 * Math.min(1, t * 1.2); }
    else if (k === 7) { tx += 70 * s; sx = 1.12; sy = 1.12; rot += -6 * s; }
    else if (k === 8) { const p = t < 0.35 ? 1 - Math.pow(1 - t / 0.35, 2) : 1 - (t - 0.35) / 0.65; tx += -d * p; ty = -18 * Math.sin(Math.PI * Math.min(1, t / 0.5)); rot += 10 * p; sx = 1 - 0.08 * p; }
    return { transform: [{ translateX: tx }, { translateY: ty }, { rotate: `${rot}deg` }, { scaleX: sx }, { scaleY: sy }] };
  });
  // idle breathing: the render is a still image, so the chest lift has to come from a tiny squash/stretch
  const breath = useSharedValue(0);
  useEffect(() => {
    breath.value = withRepeat(withTiming(1, { duration: 1700, easing: Easing.inOut(Easing.quad) }), -1, true);
  }, [breath]);
  const breathStyle = useAnimatedStyle(() => ({ transform: [{ translateY: -breath.value * 1.6 }, { scaleY: 1 + breath.value * 0.014 }, { scaleX: 1 - breath.value * 0.008 }] }));
  const hurtStyle = useAnimatedStyle(() => ({ opacity: 0.55 * hurt.value }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: 0.85 * glow.value, transform: [{ scale: 1.06 + 0.05 * glow.value }] }));
  const img = lordArt(equipped, tier);

  if (img) {
    const w = size * 1.18, h = size * 1.3;
    const rim = weaponGlow ?? colors.goldBright;
    return (
      <View style={{ width: w, height: h, alignItems: "center", justifyContent: "flex-end" }} testID="lord-art">
        {aura ? <View style={{ position: "absolute", bottom: -4, width: w * 0.9, height: h * 0.2, borderRadius: w, backgroundColor: rim, opacity: 0.35 }} /> : null}
        {/* contact shadow: three stacked ellipses stand in for a blur, so the Lord sits on the ground instead of floating */}
        {SHADOW.map((s, i) => <View key={i} style={{ position: "absolute", bottom: 1 + i, width: w * s.w, height: h * s.h, borderRadius: w, backgroundColor: "#000", opacity: s.o }} />)}
        <Animated.View style={[{ width: w, height: h, transformOrigin: "50% 100%" }, artStyle]}>
          <Animated.View style={[{ width: w, height: h }, breathStyle]}>
            {/* rim light: a tinted copy nudged toward the key light draws a lit edge along the silhouette */}
            <Image source={img} style={{ position: "absolute", left: RIM_OFFSET, top: -RIM_OFFSET, width: w, height: h, tintColor: rim, opacity: 0.5 }} resizeMode="contain" />
            <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, top: 0, width: w, height: h }, glowStyle]}>
              <Image source={img} style={{ width: w, height: h, tintColor: "#FFD84A" }} resizeMode="contain" />
            </Animated.View>
            <Image source={img} style={{ width: w, height: h }} resizeMode="contain" />
            <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, top: 0, width: w, height: h }, hurtStyle]}>
              <Image source={img} style={{ width: w, height: h, tintColor: colors.error }} resizeMode="contain" />
            </Animated.View>
          </Animated.View>
        </Animated.View>
      </View>
    );
  }

  return (
    <View style={{ width: size, height: size * 1.25 }}>
      <Svg viewBox="0 0 80 100" width={size} height={size * 1.25}>
        <Defs>
          <LinearGradient id="lordPlate" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={plate} />
            <Stop offset="1" stopColor={armored ? STEEL_D : "#4E4030"} />
          </LinearGradient>
        </Defs>
        {aura ? <Ellipse cx={42} cy={62} rx={36} ry={40} fill={weaponGlow ?? colors.goldBright} opacity={0.14} /> : null}
        <Ellipse cx={42} cy={95} rx={22} ry={4.5} fill="#000" opacity={0.35} />
        {/* cape */}
        {has("cloak") || royal ? <Path d="M22 34 Q12 60 10 92 L44 92 Q40 60 44 36Z" fill={has("cloak") ? col("cloak", colors.burgundy) : colors.burgundy} /> : null}
        {has("cloak") || royal ? <Path d="M26 40 Q18 64 18 90" stroke="#000" strokeWidth={2} opacity={0.2} fill="none" /> : null}
        {/* legs + boots */}
        <Path d="M32 66 L28 92 L38 92 L40 68Z" fill={armored ? STEEL_D : "#3A2F26"} />
        <Path d="M44 68 L46 92 L56 92 L52 66Z" fill={armored ? STEEL_D : "#3A2F26"} />
        <Path d="M26 82 L40 82 L40 92 L26 92Z" fill={has("boots") ? col("boots", LEATHER) : LEATHER} />
        <Path d="M44 82 L58 82 L58 92 L44 92Z" fill={has("boots") ? col("boots", LEATHER) : LEATHER} />
        {/* torso */}
        <Path d="M26 38 Q42 32 58 38 L56 70 L28 70Z" fill="url(#lordPlate)" />
        {armored ? <Path d="M42 40 L42 70 M30 50 L54 50" stroke={trim} strokeWidth={1.5} /> : <Path d="M34 40 L42 56 L50 40" stroke="#4E4030" strokeWidth={1.5} fill="none" />}
        {armored ? <Path d="M36 46 L48 46 L48 56 Q42 62 36 56Z" fill={heraldicColor} stroke={colors.goldBright} strokeWidth={1.2} /> : null}
        <Rect x={28} y={62} width={28} height={4} fill="#8A6A3A" />
        <Rect x={40} y={61} width={5} height={6} fill={colors.goldBright} />
        <Circle cx={28} cy={42} r={armored ? 7 : 5.5} fill={armored ? trim : LEATHER} stroke={armored ? colors.gold : "#3A2F26"} strokeWidth={1} />
        <Circle cx={56} cy={42} r={armored ? 7 : 5.5} fill={armored ? trim : LEATHER} stroke={armored ? colors.gold : "#3A2F26"} strokeWidth={1} />
        {!armored ? <Path d="M36 48 L48 48 L48 56 Q42 61 36 56Z" fill={heraldicColor} opacity={0.9} /> : null}
        {/* back arm + shield */}
        <Path d="M28 44 L18 60 L24 64 L34 50Z" fill={armored ? STEEL_D : CLOTH} />
        {has("offhand") ? <Path d="M6 42 L28 42 L28 64 Q17 76 6 64Z" fill={col("offhand", STEEL)} stroke={colors.goldBright} strokeWidth={2} /> : <Circle cx={20} cy={62} r={4} fill={has("gloves") ? col("gloves", SKIN) : SKIN} />}
        {has("offhand") ? <Path d="M14 46 L20 46 L20 62 L14 62Z" fill={heraldicColor} /> : null}
        {/* front arm */}
        <Path d="M56 44 L68 56 L64 62 L52 52Z" fill={armored ? STEEL_D : CLOTH} />
        {has("ring") ? <Circle cx={66} cy={59} r={7} fill={col("ring", colors.gold)} opacity={0.4} /> : null}
        <Circle cx={66} cy={59} r={4.2} fill={has("gloves") ? col("gloves", SKIN) : SKIN} />
        {/* head */}
        <Circle cx={42} cy={26} r={10} fill={SKIN} />
        <Circle cx={46} cy={26} r={1.4} fill={INK} />
        <Path d="M43 22 L49 23" stroke={HAIR} strokeWidth={1.4} strokeLinecap="round" />
        <Path d="M36 30 Q42 38 48 30 Q46 34 42 34 Q38 34 36 30Z" fill={HAIR} />
        {!has("helmet") ? <Path d="M32 24 Q42 8 52 24 Q48 17 42 17 Q36 17 32 24Z" fill={HAIR} /> : null}
        {has("helmet") ? <Path d="M30 26 Q30 8 42 8 Q54 8 54 26 L54 32 L30 32Z" fill={col("helmet", STEEL)} /> : null}
        {has("helmet") ? <Rect x={32} y={22} width={22} height={4} fill={INK} /> : null}
        {has("helmet") ? <Path d="M42 12 L42 32" stroke={colors.goldBright} strokeWidth={1.5} /> : null}
        {has("helmet") ? <Path d="M42 8 Q52 -2 62 6 Q52 4 44 12Z" fill={heraldicColor} /> : null}
        {royal ? <Path d="M32 12 L36 2 L42 9 L48 2 L52 12Z" fill={colors.goldBright} /> : null}
        {royal ? <Circle cx={42} cy={6} r={1.5} fill={colors.burgundy} /> : null}
        {/* amulet */}
        {has("amulet") ? <Path d="M36 38 Q42 44 48 38" stroke={colors.goldBright} strokeWidth={1} fill="none" /> : null}
        {has("amulet") ? <Circle cx={42} cy={43} r={3} fill={col("amulet", colors.gold)} /> : null}
      </Svg>
      {/* sword layer: pivot at the hand (66,59 in body space) */}
      <Animated.View style={[{ position: "absolute", left: 60 * u, top: 3 * u, width: 30 * u, height: 60 * u, transformOrigin: `${6 * u}px ${56 * u}px` }, swordStyle]} pointerEvents="none">
        <Svg viewBox="0 0 30 60" width={30 * u} height={60 * u}>
          {weaponGlow ? <Path d="M2 52 L20 2 L28 6 L10 56Z" fill={weaponGlow} opacity={0.45} /> : null}
          <Path d="M5 52 L20 4 L25 6 L10 54Z" fill={has("weapon") ? "#E6ECF2" : "#8C929C"} />
          <Path d="M20 4 L22 5 L8 52" stroke="#FFFFFF" strokeWidth={1} opacity={0.7} />
          <Path d="M0 50 L16 58" stroke={has("weapon") ? colors.goldBright : LEATHER} strokeWidth={3.5} strokeLinecap="round" />
          <Path d="M6 56 L2 66" stroke="#4A3B2C" strokeWidth={3} strokeLinecap="round" />
        </Svg>
      </Animated.View>
    </View>
  );
});
