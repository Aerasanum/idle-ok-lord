// The Lord: vector knight whose armor, colors and glow follow the equipped gear rarity (Art Direction v1.1). Sword is a separate layer so it can swing.
import React, { memo, useEffect } from "react";
import { Image, View } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import Svg, { Circle, Defs, Ellipse, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { lordArt } from "@/src/art";
import { rarityColor, useTheme } from "@/src/theme";

type Item = { slot: string; rarity: string; item_level: number } | null | undefined;

const SKIN = "#D9B48F", CLOTH = "#6B5A44", LEATHER = "#5A4632", STEEL = "#9AA1A9", STEEL_D = "#6E7580", HAIR = "#3A2A1E", INK = "#111111";
const RARITY_RANK: Record<string, number> = { common: 0, uncommon: 1, rare: 2, epic: 3, legendary: 4, mythic: 5, ancient: 6 };

export const LordSprite = memo(function LordSprite({ equipped, size = 64, tier = 0, heraldicColor = "#800020", swinging = true }: { equipped: Record<string, Item>; size?: number; tier?: number; heraldicColor?: string; swinging?: boolean }) {
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
  // rendered variant: the whole figure leans into the strike instead of a separate sword layer
  const artStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${(swing.value - 20) * 0.12}deg` }, { scaleX: 1 + Math.max(0, -(swing.value - 20)) * 0.0012 }] }));
  const img = lordArt(equipped, tier);

  if (img) {
    const w = size * 1.15, h = size * 1.25;
    return (
      <View style={{ width: w, height: h, alignItems: "center", justifyContent: "flex-end" }} testID="lord-art">
        {aura ? <View style={{ position: "absolute", bottom: -4, width: w * 0.9, height: h * 0.2, borderRadius: w, backgroundColor: weaponGlow ?? colors.goldBright, opacity: 0.35 }} /> : null}
        <View style={{ position: "absolute", bottom: 2, width: w * 0.7, height: h * 0.1, borderRadius: w, backgroundColor: "#000", opacity: 0.35 }} />
        <Animated.View style={[{ width: w, height: h, transformOrigin: "50% 100%" }, artStyle]}>
          <Image source={img} style={{ width: w, height: h }} resizeMode="contain" />
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
