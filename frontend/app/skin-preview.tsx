// Full-screen animated skin preview: the Lord performs his special move (SUPER aura → dash → slash/burst/shockwave → ultimate wave),
// castles get fireworks + ambience, army banners get a marching row of troops in the skin's heraldic colour. Buy / equip from here.
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import { Image, Pressable, useWindowDimensions, View } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { QK, useAction, useCosmetics } from "@/src/api/hooks";
import { regionBackground, skinArt } from "@/src/art";
import { Ambient, Burst, Flare, FloatText, Ghost, Shockwave, SkillBanner, Slash, SpeedLines, SuperAura, UltimateWave } from "@/src/battle/effects";
import { UnitProxy } from "@/src/battle/sprites";
import { fonts, rarityColor, useTheme } from "@/src/theme";
import { Btn, Icon, RARITY_LABEL, Res, Row, Txt } from "@/src/ui";

const KEYS = [QK.cosmetics, QK.profile, QK.store];
const SUPER = "#FFC93C";
const REGION_BY_KIND: Record<string, number> = { lord: 4, castle: 2, army: 1 };

export default function SkinPreviewScreen() {
  const { key } = useLocalSearchParams<{ key: string }>();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width, height } = useWindowDimensions();
  const { data: c } = useCosmetics();
  const buy = useAction("post", "/store/cosmetics/buy", KEYS, { success: () => "Skin acquistata e indossata!" });
  const equip = useAction("post", "/store/cosmetics/equip", KEYS, { success: () => "Skin indossata" });
  const skin = c?.catalog.find((x: any) => x.key === key);
  const stageH = Math.round(height * 0.6);
  // special-move loop: 0 idle · 1 charge (aura + banner) · 2 strike (dash + slash/burst/shockwave) · 3 ultimate wave
  const [phase, setPhase] = useState(0);
  const [cycle, setCycle] = useState(0);
  useEffect(() => {
    if (!skin || skin.kind !== "lord") return;
    const t1 = setTimeout(() => setPhase(1), 1500);
    const t2 = setTimeout(() => setPhase(2), 2600);
    const t3 = setTimeout(() => setPhase(3), 3300);
    const t4 = setTimeout(() => { setPhase(0); setCycle((n) => n + 1); }, 4600);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, [cycle, skin]);
  const [fw, setFw] = useState(0);
  useEffect(() => {
    if (!skin || skin.kind === "lord") return;
    const id = setInterval(() => setFw((n) => n + 1), skin.kind === "castle" ? 700 : 1800);
    return () => clearInterval(id);
  }, [skin]);
  if (!c || !skin) return <View style={{ flex: 1, backgroundColor: colors.surface }} />;
  const col = rarityColor(colors, skin.rarity);
  const price = skin.rubies_now ?? skin.rubies;
  const onDeal = price !== skin.rubies;
  const bg = regionBackground(REGION_BY_KIND[skin.kind] ?? 1);
  const groundY = stageH * 0.86;
  const lordX = width * 0.16;
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="skin-preview-screen">
      <View style={{ height: stageH, overflow: "hidden", backgroundColor: colors.surfaceTertiary }} testID="skin-preview-stage">
        {bg ? <Image source={bg} style={{ position: "absolute", left: 0, top: 0, width, height: stageH }} resizeMode="cover" /> : null}
        <LinearGradient colors={["rgba(0,0,0,0.55)", "rgba(0,0,0,0)", "rgba(0,0,0,0.15)", "rgba(9,11,16,1)"]} locations={[0, 0.25, 0.8, 1]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
        <Ambient width={width} height={stageH} color={skin.kind === "army" ? skin.glow : col} rise={skin.kind !== "castle"} />
        {skin.kind === "lord" ? <LordStage key={key} img={skinArt(skin.key)} phase={phase} cycle={cycle} x={lordX} groundY={groundY} width={width} stageH={stageH} color={col} /> : null}
        {skin.kind === "castle" ? <CastleStage img={skinArt(skin.key)} fw={fw} width={width} stageH={stageH} color={col} /> : null}
        {skin.kind === "army" ? <ArmyStage img={skinArt(skin.key)} fw={fw} width={width} stageH={stageH} color={skin.color} glow={skin.glow} /> : null}
        <Pressable onPress={() => router.back()} style={{ position: "absolute", top: insets.top + 8, left: 10, width: 40, height: 40, borderRadius: 20, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold, alignItems: "center", justifyContent: "center" }} testID="skin-preview-close" hitSlop={8}>
          <Icon name="close" size={20} color={colors.goldBright} />
        </Pressable>
        <View style={{ position: "absolute", top: insets.top + 12, right: 10, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, backgroundColor: col }}>
          <Txt v="caption" color={colors.onBrandPrimary}>{RARITY_LABEL[skin.rarity] ?? skin.rarity}</Txt>
        </View>
        <View style={{ position: "absolute", left: 12, right: 12, bottom: 10 }}>
          <Txt v="h1" color={colors.goldBright} style={{ textShadowColor: "#000", textShadowRadius: 6 }} testID="skin-preview-name">{skin.name}</Txt>
          <Txt v="caption" color={colors.onSurface}>{skin.kind === "lord" ? "Anteprima con mossa speciale" : skin.kind === "castle" ? "Anteprima del Regno" : "Anteprima in battaglia"}{skin.equipped ? " · indossata" : skin.owned ? " · posseduta" : ""}</Txt>
        </View>
      </View>
      <View style={{ flex: 1, padding: 14, gap: 10, paddingBottom: insets.bottom + 14 }}>
        <Txt v="body">{skin.desc}</Txt>
        <Txt v="small" color={colors.muted}>Solo estetica: nessun bonus a potenza, difesa o ricompense. Si applica subito ovunque compare {skin.kind === "lord" ? "il Lord" : skin.kind === "castle" ? "il Castello" : "l'esercito"}.</Txt>
        <View style={{ marginTop: "auto", gap: 8 }}>
          {onDeal && !skin.owned ? (
            <Row style={{ gap: 8 }}>
              <View style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.error }}><Txt v="caption" color={colors.onSurface} style={{ fontFamily: fonts.bodyBold }}>Offerta del giorno −{c.deal.discount_pct}%</Txt></View>
              <Txt v="small" color={colors.muted} style={{ textDecorationLine: "line-through" }}>{skin.rubies} Rubini</Txt>
            </Row>
          ) : null}
          {skin.owned ? (
            <Btn title={skin.equipped ? "Indossata" : "Indossa"} variant={skin.equipped ? "secondary" : "gold"} disabled={skin.equipped} loading={equip.isPending} onPress={() => equip.mutate({ kind: skin.kind, key: skin.key })} testID="skin-preview-equip" />
          ) : (
            <Pressable onPress={() => c.rubies >= price && buy.mutate({ key: skin.key })} disabled={c.rubies < price || buy.isPending} style={{ height: 48, borderRadius: 8, backgroundColor: c.rubies >= price ? colors.brandPrimary : colors.surfaceTertiary, borderWidth: 1.5, borderColor: c.rubies >= price ? colors.goldBright : colors.iron, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 }} testID="skin-preview-buy">
              <Res kind="rubies" value={price} size={16} />
              <Txt v="bodyBold" color={c.rubies >= price ? colors.onBrandPrimary : colors.muted}>{c.rubies >= price ? "Acquista e indossa" : `Rubini insufficienti (hai ${c.rubies})`}</Txt>
            </Pressable>
          )}
          <Btn title="Chiudi" variant="ghost" onPress={() => router.back()} testID="skin-preview-back" />
        </View>
      </View>
    </View>
  );
}

function LordStage({ img, phase, cycle, x, groundY, width, stageH, color }: { img?: number; phase: number; cycle: number; x: number; groundY: number; width: number; stageH: number; color: string }) {
  const h = Math.min(stageH * 0.55, 260), w = h * 0.9;
  const bob = useSharedValue(0);
  const dash = useSharedValue(0);
  useEffect(() => {
    bob.value = withRepeat(withSequence(withTiming(1, { duration: 900, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 900, easing: Easing.inOut(Easing.sin) })), -1, false);
  }, [bob]);
  useEffect(() => {
    if (phase === 2) dash.value = withSequence(withTiming(1, { duration: 180, easing: Easing.out(Easing.cubic) }), withDelay(380, withTiming(0, { duration: 400, easing: Easing.inOut(Easing.quad) })));
  }, [phase, dash]);
  const style = useAnimatedStyle(() => ({ transform: [{ translateX: dash.value * width * 0.2 }, { translateY: -3 * bob.value - (phase === 1 ? 6 : 0) }, { scale: 1 + 0.03 * bob.value + (phase === 1 ? 0.06 : 0) }] }));
  const impactX = x + w * 0.5 + width * 0.2, impactY = groundY - h * 0.5;
  return (
    <>
      {phase >= 1 ? <SuperAura x={x + w * 0.5} y={groundY + 4} width={w * 1.3} height={h * 1.05} color={SUPER} /> : null}
      {phase === 1 ? <SpeedLines key={`sl${cycle}`} x={x + w * 0.5} y={groundY - h * 0.5} color={SUPER} /> : null}
      {phase === 2 ? <Ghost x={x} y={groundY - h} w={w} h={h} source={img ?? 0} tint={SUPER} /> : null}
      <Animated.View style={[{ position: "absolute", left: x, top: groundY - h, width: w, height: h }, style]} testID="skin-preview-lord">
        <View style={{ position: "absolute", bottom: -4, left: w * 0.15, width: w * 0.7, height: 14, borderRadius: 999, backgroundColor: "#000", opacity: 0.35 }} />
        {img ? <Image source={img} style={{ width: w, height: h }} resizeMode="contain" /> : null}
      </Animated.View>
      {phase === 2 ? (
        <>
          <Slash key={`s${cycle}`} x={impactX} y={impactY} color={SUPER} size={h * 0.7} />
          <Burst key={`b${cycle}`} x={impactX + 10} y={impactY} color={color} count={12} big />
          <Shockwave key={`w${cycle}`} x={impactX} y={groundY} color={SUPER} />
          <Flare key={`f${cycle}`} x={impactX} y={impactY} size={90} color="#FFF3B0" />
        </>
      ) : null}
      {phase === 3 ? <UltimateWave key={`u${cycle}`} x={x + w * 0.6} y={groundY} width={width} height={stageH} color={SUPER} /> : null}
      {phase === 1 ? <SkillBanner key={`k${cycle}`} name="MOSSA SPECIALE" color={SUPER} sceneH={stageH} /> : null}
      {phase === 3 ? <FloatText key={`t${cycle}`} x={impactX - 20} y={impactY - 30} text="COLPO REALE!" color={SUPER} size={22} /> : null}
    </>
  );
}

function CastleStage({ img, fw, width, stageH, color }: { img?: number; fw: number; width: number; stageH: number; color: string }) {
  const h = Math.min(stageH * 0.7, 320), w = Math.min(width * 0.9, h * 1.2);
  const pulse = useSharedValue(0);
  useEffect(() => {
    pulse.value = withRepeat(withSequence(withTiming(1, { duration: 1600, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 1600, easing: Easing.inOut(Easing.sin) })), -1, false);
  }, [pulse]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: 1 + 0.02 * pulse.value }] }));
  const seeds = [0.2, 0.75, 0.5, 0.35, 0.65];
  const fx = seeds[fw % seeds.length];
  return (
    <>
      <View style={{ position: "absolute", left: width * 0.05, top: stageH * 0.82, width: width * 0.9, height: 24, borderRadius: 999, backgroundColor: color, opacity: 0.25 }} />
      <Animated.View style={[{ position: "absolute", left: (width - w) / 2, top: stageH * 0.86 - h, width: w, height: h }, style]} testID="skin-preview-castle">
        {img ? <Image source={img} style={{ width: w, height: h }} resizeMode="contain" /> : null}
      </Animated.View>
      <Burst key={`fw${fw}`} x={width * fx} y={stageH * (0.18 + 0.12 * ((fw * 7) % 3))} color={fw % 2 ? color : "#FFF3B0"} count={14} seed={fw} big fire={fw % 3 === 0} />
      <Flare key={`fl${fw}`} x={width * fx} y={stageH * (0.18 + 0.12 * ((fw * 7) % 3))} size={70} color={fw % 2 ? color : "#FFFFFF"} />
    </>
  );
}

function ArmyStage({ img, fw, width, stageH, color, glow }: { img?: number; fw: number; width: number; stageH: number; color: string; glow: string }) {
  const h = Math.min(stageH * 0.7, 300), w = h * 0.42;
  const sway = useSharedValue(0);
  const march = useSharedValue(0);
  useEffect(() => {
    sway.value = withRepeat(withSequence(withTiming(1, { duration: 1400, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 1400, easing: Easing.inOut(Easing.sin) })), -1, false);
    march.value = withRepeat(withSequence(withTiming(1, { duration: 420 }), withTiming(0, { duration: 420 })), -1, false);
  }, [sway, march]);
  const swayStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${-3 + 6 * sway.value}deg` }] }));
  const marchStyle = useAnimatedStyle(() => ({ transform: [{ translateY: -3 * march.value }] }));
  const troops = ["infantry", "archer", "cavalry", "infantry", "archer", "infantry"];
  return (
    <>
      <View style={{ position: "absolute", left: width * 0.08, top: stageH * 0.8, width: width * 0.84, height: 26, borderRadius: 999, backgroundColor: glow, opacity: 0.35 }} />
      <Animated.View style={[{ position: "absolute", left: width * 0.1, top: stageH * 0.86 - h, width: w, height: h, transformOrigin: "bottom" }, swayStyle]} testID="skin-preview-banner">
        {img ? <Image source={img} style={{ width: w, height: h }} resizeMode="contain" /> : null}
      </Animated.View>
      <Animated.View style={[{ position: "absolute", left: width * 0.3, bottom: stageH * 0.14, width: width * 0.66, flexDirection: "row", flexWrap: "wrap-reverse", alignItems: "flex-end" }, marchStyle]}>
        {troops.map((u, i) => <UnitProxy key={i} unit={u} scale={2} banner={i % 2 === 0 ? color : undefined} />)}
      </Animated.View>
      <Shockwave key={`sw${fw}`} x={width * 0.6} y={stageH * 0.86} color={glow} />
      <Burst key={`ab${fw}`} x={width * 0.18} y={stageH * 0.86 - h * 0.9} color={glow} count={8} seed={fw} />
    </>
  );
}
