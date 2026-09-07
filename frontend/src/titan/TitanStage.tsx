// Titan Hunt showcase: the Titan's 3D illustration on its region backdrop, idle breathing, hurt flash and a Lord strike
// animation when the player attacks. Presentational — damage/HP come from the server.
import React, { useEffect, useRef, useState } from "react";
import { Image, Text, View, useWindowDimensions } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { lordArt, monsterArt, regionBackground } from "@/src/art";
import { Burst, DamageNumber, Flare, Fx, Shockwave, Slash, SpeedLines } from "@/src/battle/effects";
import { fonts, useTheme } from "@/src/theme";
import { ZoomPan } from "@/src/ui/ZoomPan";

export function TitanStage({ family, tier, hpPct, strikeTick, lastDamage, killed, equipped }: { family: string; tier: number; hpPct: number; strikeTick: number; lastDamage?: number; killed?: boolean; equipped?: Record<string, any> }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const W = width - 24, H = Math.min(300, W * 0.78);
  const titan = Math.min(H * 0.82, W * 0.55);
  const lordSize = Math.min(110, W * 0.28);
  const [fx, setFx] = useState<Fx[]>([]);
  const fxId = useRef(0);
  const breath = useSharedValue(0);
  const hurt = useSharedValue(0);
  const roar = useSharedValue(0);
  const lordX = useSharedValue(-lordSize * 1.4);
  const lordRot = useSharedValue(0);
  const shake = useSharedValue(0);
  const flash = useSharedValue(0);
  useEffect(() => {
    breath.value = withRepeat(withSequence(withTiming(1, { duration: 1400, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 1400, easing: Easing.inOut(Easing.quad) })), -1, false);
  }, [breath]);
  // strike choreography: Lord dashes in, slashes, Titan flashes + roars, Lord retreats
  useEffect(() => {
    if (!strikeTick) return;
    const spawn = (items: Omit<Fx, "id">[], ttl: number) => {
      const withIds = items.map((i) => ({ ...i, id: ++fxId.current }));
      setFx((f) => [...f, ...withIds]);
      setTimeout(() => setFx((f) => f.filter((x) => !withIds.some((w) => w.id === x.id))), ttl);
    };
    const hitX = W * 0.62 - titan * 0.2, hitY = H * 0.55;
    lordX.value = withSequence(withTiming(W * 0.34 - lordSize * 0.5, { duration: 320, easing: Easing.out(Easing.cubic) }), withTiming(W * 0.34 - lordSize * 0.3, { duration: 160 }), withTiming(W * 0.34 - lordSize * 0.5, { duration: 600 }), withTiming(-lordSize * 1.4, { duration: 420, easing: Easing.in(Easing.quad) }));
    lordRot.value = withSequence(withTiming(0, { duration: 320 }), withTiming(-16, { duration: 160 }), withTiming(0, { duration: 400 }));
    const t1 = setTimeout(() => {
      hurt.value = 1; hurt.value = withTiming(0, { duration: 420 });
      roar.value = withSequence(withTiming(1, { duration: 180, easing: Easing.out(Easing.back(2)) }), withTiming(0, { duration: 500 }));
      shake.value = withSequence(withTiming(10, { duration: 40 }), withTiming(-10, { duration: 60 }), withTiming(5, { duration: 60 }), withTiming(0, { duration: 90 }));
      flash.value = 0.5; flash.value = withTiming(0, { duration: 360 });
      spawn([
        { kind: "slash", x: hitX - 70, y: hitY - 70, color: colors.goldBright, size: 140 }, { kind: "slash", x: hitX - 40, y: hitY - 40, color: "#FFFFFF", size: 90 },
        { kind: "flare", x: hitX, y: hitY, size: 100 }, { kind: "speed", x: hitX, y: hitY, color: colors.goldBright }, { kind: "burst", x: hitX, y: hitY + 10, color: colors.error },
        { kind: "shock", x: W * 0.62, y: H - 30, color: colors.error },
        ...(lastDamage ? [{ kind: "dmg" as const, x: hitX - 30, y: hitY - 60, value: lastDamage, crit: true, color: colors.goldBright }] : []),
      ], 1400);
    }, 460);
    return () => clearTimeout(t1);
  }, [strikeTick]); // eslint-disable-line react-hooks/exhaustive-deps

  const titanStyle = useAnimatedStyle(() => ({
    opacity: killed ? 0.35 : 1,
    transform: [{ translateY: -4 * breath.value }, { scaleX: 1 + 0.03 * breath.value + 0.1 * roar.value }, { scaleY: 1 + 0.02 * breath.value + 0.14 * roar.value }, { translateX: 12 * hurt.value }, { rotate: `${-4 * hurt.value}deg` }],
  }));
  const hurtStyle = useAnimatedStyle(() => ({ opacity: 0.8 * hurt.value }));
  const lordStyle = useAnimatedStyle(() => ({ transform: [{ translateX: lordX.value }, { rotate: `${lordRot.value}deg` }] }));
  const camStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }, { translateY: shake.value * 0.5 }] }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: flash.value }));
  const bg = regionBackground(Math.max(1, Math.min(10, tier)));
  const img = monsterArt(family);
  const lord = lordArt(equipped ?? {}, 0);

  return (
    <ZoomPan width={W} height={H} testID="titan-zoom" style={{ borderRadius: 8, borderWidth: 2, borderColor: colors.gold, backgroundColor: "#1B1410" }} controlsStyle={{ top: 6, right: 6 }}>
    <Animated.View style={[{ width: W, height: H, overflow: "hidden" }, camStyle]} testID="titan-stage">
      {bg ? <Image source={bg} style={{ position: "absolute", left: -10, top: -10, width: W + 20, height: H + 20 }} resizeMode="cover" /> : null}
      <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "rgba(40,0,0,0.35)" }} />
      <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: H * 0.3, backgroundColor: "rgba(0,0,0,0.45)" }} />
      {/* Titan */}
      <Animated.View style={[{ position: "absolute", left: W * 0.62 - titan / 2, bottom: 18, width: titan, height: titan, transformOrigin: "50% 100%" }, titanStyle]} testID="titan-art">
        <View style={{ position: "absolute", bottom: 0, left: titan * 0.1, width: titan * 0.8, height: titan * 0.14, borderRadius: titan, backgroundColor: "#000", opacity: 0.4 }} />
        <View style={{ position: "absolute", bottom: -6, left: titan * 0.05, width: titan * 0.9, height: titan * 0.22, borderRadius: titan, borderWidth: 3, borderColor: colors.goldBright, opacity: 0.55 }} />
        {img ? <Image source={img} style={{ width: titan, height: titan }} resizeMode="contain" /> : null}
        {img ? <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, top: 0 }, hurtStyle]}><Image source={img} style={{ width: titan, height: titan, tintColor: "#FFFFFF" }} resizeMode="contain" /></Animated.View> : null}
      </Animated.View>
      {/* Lord striking */}
      {lord ? (
        <Animated.View style={[{ position: "absolute", left: 0, bottom: 14, width: lordSize, height: lordSize * 1.1, transformOrigin: "50% 100%" }, lordStyle]}>
          <Image source={lord} style={{ width: lordSize, height: lordSize * 1.1 }} resizeMode="contain" />
        </Animated.View>
      ) : null}
      {fx.map((f) => {
        switch (f.kind) {
          case "dmg": return <DamageNumber key={f.id} x={f.x} y={f.y} value={f.value ?? 0} crit={f.crit} color={f.color ?? colors.parchment} seed={f.id} />;
          case "slash": return <Slash key={f.id} x={f.x} y={f.y} color={f.color ?? colors.parchment} size={f.size} />;
          case "speed": return <SpeedLines key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} radius={120} />;
          case "flare": return <Flare key={f.id} x={f.x} y={f.y} size={f.size} />;
          case "shock": return <Shockwave key={f.id} x={f.x} y={f.y} color={f.color ?? colors.error} />;
          default: return <Burst key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} seed={f.id} count={12} big />;
        }
      })}
      <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "#FFFFFF" }, flashStyle]} />
      {/* name plate */}
      <View style={{ position: "absolute", left: 10, top: 8, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }}>
        <Text style={{ fontFamily: fonts.display, fontSize: 18, color: colors.goldBright }} testID="titan-name">{family}</Text>
        <Text style={{ fontFamily: fonts.body, fontSize: 11, color: colors.onSurface }}>Titano tier {tier} · {killed ? "ABBATTUTO" : `${hpPct.toFixed(1)}% HP`}</Text>
      </View>
    </Animated.View>
    </ZoomPan>
  );
}
