// Animated 2.5D auto-battle scene. Authoritative outcome/timeline come from the server; this only animates it.
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PixelRatio, Platform, Text, View, useWindowDimensions } from "react-native";
import Animated, { Easing, FadeIn, ZoomOut, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { fonts, useTheme } from "@/src/theme";
import { fmt } from "@/src/ui";
import { Ambient, BossBar, Burst, Clouds, CoinShower, DamageNumber, Fx, OutcomeBanner, Slash } from "./effects";
import { LordSprite } from "./lord";
import { MonsterSprite } from "./monsters";
import { hashStr, paletteFor } from "./regions";
import { CohortSilhouette, UnitProxy } from "./sprites";

export type Attempt = { id: string; stage: string | number; kind: string; win: boolean; duration: number; created_at: string; resolves_at: string; required_power: number; total_power: number; hero_power: number; army_power: number; timeline: { waves: { wave: number; monsters: { family: string; type: any }[]; cleared: boolean; kill_xp: number; kill_gold: number; t_start: number; t_end: number }[]; total_monsters: number; duration: number; region: { name: string; region: number; boss: string } } };

const isHighTier = Platform.OS === "ios" || Platform.OS === "web" || PixelRatio.get() >= 2.5;
const ORDER = ["dragon", "angel", "demon", "war_elephant", "conquest_wagon", "catapult", "bear", "lion", "cavalry", "wolf", "infantry", "archer", "falcon"];
const CATEGORY: Record<string, string> = { infantry: "regular", archer: "regular", cavalry: "regular", catapult: "siege", conquest_wagon: "siege", wolf: "beast", bear: "beast", lion: "beast", falcon: "beast", war_elephant: "beast", dragon: "mythic", angel: "mythic", demon: "mythic" };

function allocateProxies(formation: Record<string, number>, cap: number): { unit: string; count: number }[] {
  const entries = Object.entries(formation).filter(([, q]) => q > 0);
  const total = entries.reduce((a, [, q]) => a + q, 0);
  if (!total) return [];
  const out = entries.map(([unit, q]) => ({ unit, count: CATEGORY[unit] === "mythic" ? Math.min(3, Math.max(1, Math.round(q / 50))) : Math.max(1, Math.round((q / total) * cap)) }));
  let sum = out.reduce((a, x) => a + x.count, 0);
  while (sum > cap) {
    const big = out.reduce((a, b) => (a.count > b.count ? a : b));
    if (big.count <= 1) break;
    big.count -= 1;
    sum -= 1;
  }
  return out.sort((a, b) => ORDER.indexOf(a.unit) - ORDER.indexOf(b.unit));
}

const OUTCOME_HOLD_MS = 1500;
const haptic = (kind: "light" | "heavy" | "success" | "error") => {
  if (Platform.OS === "web") return;
  if (kind === "light") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
  else if (kind === "heavy") Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy).catch(() => {});
  else Haptics.notificationAsync(kind === "success" ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Error).catch(() => {});
};

export function BattleScene({ attempt, serverTime, formation, equipped, armyTier, heraldicColor, onFinished, skills, firstClear }: {
  attempt: Attempt; serverTime: string; formation: Record<string, number>; equipped: Record<string, any>; armyTier: { tier: number; foreground_proxy_cap: number; background_cohorts: number; name?: string } | undefined; heraldicColor: string; onFinished: (id: string) => void; skills: { key: string; name: string; cooldown_seconds: number }[]; firstClear?: boolean;
}) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const pal = paletteFor(attempt.timeline.region.region);
  const [now, setNow] = useState(() => Date.now());
  const done = useRef(false);
  const offset = useMemo(() => new Date(serverTime).getTime() - Date.now(), [serverTime]);
  const start = new Date(attempt.created_at).getTime();
  const elapsed = Math.max(0, (now + offset - start) / 1000);
  const progress = Math.min(1, elapsed / attempt.duration);
  const finished = progress >= 1;
  const sceneH = Math.min(440, Math.max(320, width * 0.98));
  const [outcome, setOutcome] = useState(false);
  const [fx, setFx] = useState<Fx[]>([]);
  const [hurtTick, setHurtTick] = useState(0);
  const fxId = useRef(0);
  const prevKills = useRef(0);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  // camera shake + full-scene flash
  const shake = useSharedValue(0);
  const flash = useSharedValue(0);
  const [flashColor, setFlashColor] = useState("#FFFFFF");
  const doShake = useCallback((amp: number) => {
    shake.value = withSequence(withTiming(amp, { duration: 40 }), withTiming(-amp, { duration: 60 }), withTiming(amp * 0.5, { duration: 60 }), withTiming(0, { duration: 90 }));
  }, [shake]);
  const doFlash = useCallback((color: string, strength: number, ms: number) => {
    setFlashColor(color);
    flash.value = strength;
    flash.value = withTiming(0, { duration: ms, easing: Easing.out(Easing.quad) });
  }, [flash]);
  const shakeStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }, { translateY: shake.value * 0.6 }] }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: flash.value }));

  const spawn = useCallback((items: Omit<Fx, "id">[], ttl: number) => {
    const withIds = items.map((i) => ({ ...i, id: ++fxId.current }));
    setFx((f) => [...f, ...withIds].slice(-40));
    setTimeout(() => setFx((f) => f.filter((x) => !withIds.some((w) => w.id === x.id))), ttl);
  }, []);

  const waves = attempt.timeline.waves;
  const waveIdx = Math.min(waves.length - 1, waves.findIndex((w) => elapsed < w.t_end) === -1 ? waves.length - 1 : waves.findIndex((w) => elapsed < w.t_end));
  const wave = waves[waveIdx];
  const waveProgress = Math.max(0, Math.min(1, (elapsed - wave.t_start) / Math.max(0.01, wave.t_end - wave.t_start)));
  const alive = wave.cleared ? wave.monsters.length - Math.floor(waveProgress * wave.monsters.length) : Math.max(1, wave.monsters.length - Math.floor(waveProgress * wave.monsters.length * 0.4));
  const kills = waves.slice(0, waveIdx).reduce((a, w) => a + (w.cleared ? w.monsters.length : 0), 0) + (wave.monsters.length - alive);
  const earnedXp = Math.round(waves.slice(0, waveIdx).reduce((a, w) => a + (w.cleared ? w.kill_xp : 0), 0) + wave.kill_xp * (1 - alive / wave.monsters.length));
  const earnedGold = Math.round(waves.slice(0, waveIdx).reduce((a, w) => a + (w.cleared ? w.kill_gold : 0), 0) + wave.kill_gold * (1 - alive / wave.monsters.length));
  const isBossWave = attempt.kind === "boss" && waveIdx === waves.length - 1;
  const bossHp = wave.cleared ? 1 - waveProgress : Math.max(0.35, 1 - waveProgress * 0.4);

  // kill events -> damage numbers, sparks, shake, flash, haptics
  useEffect(() => {
    const fresh = kills - prevKills.current;
    prevKills.current = kills;
    if (fresh <= 0 || finished) return;
    const items: Omit<Fx, "id">[] = [];
    for (let k = 0; k < Math.min(fresh, 4); k++) {
      const h = hashStr(`${attempt.id}:${kills - k}`);
      const crit = h % 4 === 0;
      const x = width * 0.54 + (h % 6) * width * 0.06;
      const y = sceneH * 0.56 + ((h >> 3) % 4) * 14;
      items.push({ kind: "dmg", x, y, value: Math.round(attempt.hero_power * (0.85 + (h % 60) / 100) * (crit ? 2 : 1)), crit, color: crit ? colors.res_gold : colors.onSurface });
      items.push({ kind: "burst", x: x + 10, y: y + 30, color: pal.monster[h % pal.monster.length] });
    }
    spawn(items, 1200);
    const bossKill = isBossWave && alive <= 1;
    doShake(bossKill ? 12 : fresh > 1 ? 7 : 4);
    doFlash(bossKill ? colors.goldBright : "#FFFFFF", bossKill ? 0.5 : 0.16, bossKill ? 500 : 180);
    haptic(bossKill ? "heavy" : "light");
  }, [kills]); // eslint-disable-line react-hooks/exhaustive-deps

  // Lord swing cadence (1.2s) -> slash arc, hit flash on the front monster, small white hit numbers
  useEffect(() => {
    if (finished) return;
    const id = setInterval(() => {
      const h = hashStr(`${attempt.id}:swing:${Math.floor(Date.now() / 1200)}`);
      setHurtTick((t) => t + 1);
      spawn([
        { kind: "slash", x: width * 0.28 + 62, y: sceneH - 150, color: colors.parchment },
        { kind: "dmg", x: width * 0.5 + (h % 4) * 10, y: sceneH * 0.62, value: Math.round(attempt.hero_power * (0.3 + (h % 30) / 100)), color: colors.parchmentDark },
      ], 900);
    }, 1200);
    return () => clearInterval(id);
  }, [attempt.id, attempt.hero_power, finished, spawn, width, sceneH, colors.parchment, colors.parchmentDark]);

  // outcome: hold the banner, then let the parent claim (server-authoritative)
  useEffect(() => {
    if (!finished || done.current) return;
    done.current = true;
    setOutcome(true);
    if (attempt.win) {
      doShake(10);
      doFlash(colors.goldBright, 0.7, 700);
      haptic("success");
    } else {
      doShake(6);
      doFlash(colors.error, 0.55, 600);
      haptic("error");
    }
    const t = setTimeout(() => onFinished(attempt.id), OUTCOME_HOLD_MS);
    return () => clearTimeout(t);
  }, [finished]); // eslint-disable-line react-hooks/exhaustive-deps

  const cap = Math.min(armyTier?.foreground_proxy_cap ?? 0, isHighTier ? 120 : 60);
  const proxies = useMemo(() => allocateProxies(formation, cap), [formation, cap]);
  const bgCohorts = armyTier?.background_cohorts ?? 0;

  // march bob (shared per scene), lord lunge
  const bob = useSharedValue(0);
  const lunge = useSharedValue(0);
  useEffect(() => {
    bob.value = withRepeat(withSequence(withTiming(-3, { duration: 420, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 420, easing: Easing.inOut(Easing.quad) })), -1, true);
    lunge.value = withRepeat(withSequence(withTiming(22, { duration: 240, easing: Easing.out(Easing.cubic) }), withTiming(0, { duration: 560, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 400 })), -1, false);
  }, [bob, lunge]);
  const bobStyle = useAnimatedStyle(() => ({ transform: [{ translateY: bob.value }] }));
  const lungeStyle = useAnimatedStyle(() => ({ transform: [{ translateX: lunge.value }, { translateY: bob.value * 0.6 }] }));
  const bobStyle2 = useAnimatedStyle(() => ({ transform: [{ translateY: -bob.value }] }));

  const skillCycle = skills.map((s) => ({ ...s, frac: ((elapsed % s.cooldown_seconds) / s.cooldown_seconds) }));
  const monsterSize = (type: string) => (type === "boss" ? Math.min(170, width * 0.42) : type === "elite" ? 78 : 56);
  const regionBoss = attempt.timeline.region.boss;

  return (
    <View style={{ height: sceneH, overflow: "hidden", borderBottomWidth: 3, borderColor: colors.gold, backgroundColor: pal.ground }} testID="battle-scene">
      <Animated.View style={[{ position: "absolute", left: -12, right: -12, top: -8, bottom: -8 }, shakeStyle]}>
        <LinearGradient colors={pal.sky} style={{ position: "absolute", left: 0, right: 0, top: 0, height: sceneH * 0.64 }} />
        {/* celestial body + halo, clouds, ambience */}
        <View style={{ position: "absolute", left: width * (0.62 + (attempt.timeline.region.region % 3) * 0.08), top: sceneH * 0.1, width: 64, height: 64, borderRadius: 32, backgroundColor: pal.accent, opacity: 0.18 }} />
        <View style={{ position: "absolute", left: width * (0.62 + (attempt.timeline.region.region % 3) * 0.08) + 12, top: sceneH * 0.1 + 12, width: 40, height: 40, borderRadius: 20, backgroundColor: pal.accent, opacity: 0.6 }} />
        <Clouds width={width} top={sceneH * 0.16} color={pal.fog.replace(/[\d.]+\)$/, "1)")} />
        <Ambient width={width + 24} height={sceneH} color={pal.accent} rise={attempt.timeline.region.region >= 7} />
        {/* far props */}
        <View style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.38, height: sceneH * 0.26, flexDirection: "row", alignItems: "flex-end", justifyContent: "space-around", opacity: 0.55 }}>
          {Array.from({ length: 9 }).map((_, i) => <Prop key={i} kind={pal.props} i={i} color={pal.groundAlt} accent={pal.accent} />)}
        </View>
        <View style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.54, height: sceneH * 0.14, backgroundColor: pal.fog }} />
        {/* ground */}
        <LinearGradient colors={[pal.ground, pal.groundAlt]} style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.62, bottom: 0 }} />
        {isBossWave ? <LinearGradient colors={["rgba(120,0,0,0.45)", "transparent", "rgba(120,0,0,0.45)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} /> : null}
        {/* background cohorts with banners */}
        <View style={{ position: "absolute", left: 20, top: sceneH * 0.58, flexDirection: "row", gap: 10, flexWrap: "wrap", width: width * 0.55 }}>
          {Array.from({ length: Math.min(bgCohorts, 24) }).map((_, i) => <CohortSilhouette key={i} width={34 + (i % 3) * 8} color={i % 4 === 0 ? colors.iron : colors.forest} banner={i % 2 === 0 ? heraldicColor : undefined} />)}
        </View>
        {/* foreground formation */}
        <Animated.View style={[{ position: "absolute", left: 18, bottom: 42, width: width * 0.5, flexDirection: "row", flexWrap: "wrap-reverse", alignItems: "flex-end", gap: 3 }, bobStyle]} testID="formation-proxies">
          {proxies.flatMap((p) => Array.from({ length: p.count }).map((_, i) => <UnitProxy key={`${p.unit}${i}`} unit={p.unit} scale={CATEGORY[p.unit] === "mythic" ? 1.2 : 0.9} banner={i === 0 ? heraldicColor : undefined} />))}
        </Animated.View>
        {/* Lord */}
        <Animated.View style={[{ position: "absolute", left: width * 0.28, bottom: 34 }, lungeStyle]} testID="lord-sprite">
          <LordSprite equipped={equipped} size={78} tier={armyTier?.tier ?? 0} heraldicColor={heraldicColor} swinging={!outcome} />
          <View style={{ position: "absolute", top: -14, alignSelf: "center", paddingHorizontal: 6, backgroundColor: colors.overlay, borderRadius: 3, borderWidth: 1, borderColor: colors.gold }}>
            <Text style={{ fontFamily: fonts.bodyBold, fontSize: 9, color: colors.goldBright }}>LORD</Text>
          </View>
        </Animated.View>
        {/* monsters */}
        <Animated.View style={[{ position: "absolute", right: 16, bottom: 38, width: width * 0.46, flexDirection: "row-reverse", flexWrap: "wrap-reverse", alignItems: "flex-end", gap: 4, justifyContent: "flex-start" }, bobStyle2]} testID="monster-horde">
          {wave.monsters.slice(0, alive).map((m, i) => (
            <Animated.View key={`${waveIdx}-${i}`} entering={FadeIn.duration(250)} exiting={ZoomOut.duration(220)}>
              <MonsterSprite family={m.family} type={m.type} palette={pal.monster} size={monsterSize(m.type)} hurtTick={i === alive - 1 && !outcome ? hurtTick : 0} />
            </Animated.View>
          ))}
        </Animated.View>
        {/* VFX layer */}
        {fx.map((f) => f.kind === "dmg" ? <DamageNumber key={f.id} x={f.x} y={f.y} value={f.value ?? 0} crit={f.crit} color={f.color ?? colors.onSurface} seed={f.id} />
          : f.kind === "slash" ? <Slash key={f.id} x={f.x} y={f.y} color={f.color ?? colors.parchment} />
          : <Burst key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} seed={f.id} />)}
        {outcome && attempt.win ? <CoinShower x={width * 0.5} y={sceneH * 0.5} /> : null}
        {outcome && attempt.win ? <Burst x={width * 0.5} y={sceneH * 0.45} color={colors.goldBright} count={14} big /> : null}
      </Animated.View>
      <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: flashColor }, flashStyle]} />
      {/* HUD */}
      <View style={{ position: "absolute", top: 8, left: 10, right: 10, flexDirection: "row", justifyContent: "space-between" }} pointerEvents="none">
        <View style={{ backgroundColor: colors.overlay, borderColor: colors.gold, borderWidth: 1, borderRadius: 4, paddingHorizontal: 8, paddingVertical: 4 }}>
          <Text style={{ fontFamily: fonts.display, fontSize: 18, color: colors.goldBright }} testID="battle-stage-label">Stage {attempt.stage} · {attempt.kind === "boss" ? "BOSS" : attempt.kind === "elite" ? "ELITE" : attempt.timeline.region.name}</Text>
          <Text style={{ fontFamily: fonts.body, fontSize: 11, color: colors.onSurface }} testID="battle-wave-label">Ondata {wave.wave}/{waves.length} · Uccisioni {kills}/{attempt.timeline.total_monsters}</Text>
        </View>
        <View style={{ backgroundColor: colors.overlay, borderColor: colors.gold, borderWidth: 1, borderRadius: 4, paddingHorizontal: 8, paddingVertical: 4, alignItems: "flex-end" }}>
          <Text style={{ fontFamily: fonts.displaySemi, fontSize: 14, color: colors.res_gold }} testID="battle-kill-gold">+{fmt(earnedGold)} oro</Text>
          <Text style={{ fontFamily: fonts.displaySemi, fontSize: 12, color: colors.res_event_tokens }} testID="battle-kill-xp">+{fmt(earnedXp)} XP</Text>
        </View>
      </View>
      {isBossWave ? <BossBar name={regionBoss} hp={bossHp} width={width} /> : null}
      {/* progress + skills */}
      <View style={{ position: "absolute", bottom: 4, left: 10, right: 10 }} pointerEvents="none">
        <View style={{ height: 6, backgroundColor: colors.scrim, borderRadius: 3, overflow: "hidden", borderWidth: 1, borderColor: colors.gold }}>
          <View style={{ width: `${progress * 100}%`, height: "100%", backgroundColor: attempt.win ? colors.goldBright : colors.error }} />
        </View>
        <View style={{ flexDirection: "row", gap: 6, marginTop: 4 }}>
          {skillCycle.map((s) => (
            <View key={s.key} style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3, backgroundColor: colors.overlay, borderWidth: 1, borderColor: s.frac < 0.08 ? colors.goldBright : colors.iron, overflow: "hidden" }}>
              <View style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${s.frac * 100}%`, backgroundColor: "rgba(184,153,71,0.35)" }} />
              <Text style={{ fontFamily: fonts.bodyMedium, fontSize: 10, color: colors.onSurface }}>{s.name}</Text>
            </View>
          ))}
        </View>
      </View>
      {!attempt.win && !outcome ? (
        <View style={{ position: "absolute", top: sceneH * 0.3, alignSelf: "center", backgroundColor: colors.overlay, borderColor: colors.error, borderWidth: 2, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 4 }}>
          <Text style={{ fontFamily: fonts.display, fontSize: 16, color: colors.onSurface }}>Potenza {fmt(attempt.total_power)} / {fmt(attempt.required_power)} richiesta</Text>
        </View>
      ) : null}
      {outcome ? <OutcomeBanner win={attempt.win} firstClear={!!firstClear} subtitle={attempt.win ? `Stage ${attempt.stage} · ${attempt.timeline.total_monsters} nemici abbattuti` : `Potenza ${fmt(attempt.total_power)} / ${fmt(attempt.required_power)} richiesta`} sceneH={sceneH} /> : null}
    </View>
  );
}

function Prop({ kind, i, color, accent }: { kind: string; i: number; color: string; accent: string }) {
  const h = 20 + ((i * 37) % 40);
  switch (kind) {
    case "trees": return <View style={{ width: 14, height: h, backgroundColor: color, borderTopLeftRadius: 8, borderTopRightRadius: 8 }} />;
    case "swamp": return <View style={{ width: 22, height: h * 0.5, backgroundColor: color, borderRadius: 10 }} />;
    case "ruins": return <View style={{ width: 10, height: h, backgroundColor: color, borderTopWidth: 3, borderColor: accent }} />;
    case "dunes": return <View style={{ width: 40, height: h * 0.5, backgroundColor: color, borderTopLeftRadius: 30, borderTopRightRadius: 30 }} />;
    case "peaks": return <View style={{ width: 0, height: 0, borderLeftWidth: 16, borderRightWidth: 16, borderBottomWidth: h + 14, borderLeftColor: "transparent", borderRightColor: "transparent", borderBottomColor: color }} />;
    case "ice": return <View style={{ width: 8, height: h + 10, backgroundColor: accent, opacity: 0.8, transform: [{ rotate: `${(i % 2 ? 1 : -1) * 8}deg` }] }} />;
    case "graves": return <View style={{ width: 8, height: h * 0.6, backgroundColor: color, borderTopLeftRadius: 4, borderTopRightRadius: 4 }} />;
    case "obsidian": return <View style={{ width: 12, height: h, backgroundColor: color, transform: [{ skewX: "-12deg" }], borderTopWidth: 2, borderColor: accent }} />;
    case "shards": return <View style={{ width: 6, height: h + 16, backgroundColor: accent, opacity: 0.7, transform: [{ rotate: `${(i % 3) * 10 - 10}deg` }] }} />;
    default: return <View style={{ width: 10, height: 10 + (i % 4) * 6, backgroundColor: accent, borderRadius: 10, opacity: 0.5 }} />;
  }
}
