// Animated 2.5D auto-battle scene. Authoritative outcome/timeline come from the server; this only animates it.
// v1.2 choreography: Lord move set (slash / heavy / spin / dash / leap) + periodic SUPER power-up with an ultimate wave,
// enemy move set (lunge / leap / spin / roar / dodge / spit / swoop) with impact FX, combo counter, death dissolves.
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Image, PixelRatio, Platform, Text, View, useWindowDimensions } from "react-native";
import Animated, { Easing, FadeIn, ZoomOut, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";

import { lordArt, regionBackground } from "@/src/art";
import { playRegionMusic } from "@/src/audio";
import { fonts, useTheme } from "@/src/theme";
import { fmt } from "@/src/ui";
import { Ambient, BannerRise, BossBar, Burst, Clouds, CoinShower, ComboText, DamageNumber, DeathDissolve, DustPuff, Flare, Fx, Ghost, LightningBolt, OutcomeBanner, Projectile, ShieldDome, Shockwave, SKILL_FX, SkillBanner, Slash, SpeedLines, SteelRain, SuperAura, UltimateWave } from "./effects";
import { LORD_MOVE_MS, LordMove, LordSprite } from "./lord";
import { EnemyMove, MOVE_HIT_MS, MonsterSprite } from "./monsters";
import { hashStr, paletteFor } from "./regions";
import { CohortSilhouette, UnitProxy } from "./sprites";

export type Attempt = { id: string; stage: string | number; kind: string; win: boolean; duration: number; created_at: string; resolves_at: string; required_power: number; total_power: number; hero_power: number; army_power: number; timeline: { waves: { wave: number; monsters: { family: string; type: any }[]; cleared: boolean; kill_xp: number; kill_gold: number; t_start: number; t_end: number }[]; total_monsters: number; duration: number; region: { name: string; region: number; boss: string } } };

const isHighTier = Platform.OS === "ios" || Platform.OS === "web" || PixelRatio.get() >= 2.5;
const ORDER = ["dragon", "angel", "demon", "war_elephant", "conquest_wagon", "catapult", "bear", "lion", "cavalry", "wolf", "infantry", "archer", "falcon"];
const CATEGORY: Record<string, string> = { infantry: "regular", archer: "regular", cavalry: "regular", catapult: "siege", conquest_wagon: "siege", wolf: "beast", bear: "beast", lion: "beast", falcon: "beast", war_elephant: "beast", dragon: "mythic", angel: "mythic", demon: "mythic" };
const SUPER_COLOR = "#FFC93C";
const LORD_PATTERN: LordMove[] = [1, 1, 2, 1, 3, 1, 5, 1, 2, 4];
const STRIKE_MS = 1300;
const SUPER_FIRST_S = 6, SUPER_EVERY_S = 20;
const MAX_VISIBLE = 4;

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
const monsterSize = (type: string, width: number) => (type === "boss" ? Math.min(200, width * 0.48) : type === "elite" ? 92 : 72);

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
  const [hurtAll, setHurtAll] = useState(0);
  const [lordHurtTick, setLordHurtTick] = useState(0);
  const fxId = useRef(0);
  const prevKills = useRef(0);
  const [skillFx, setSkillFx] = useState<{ id: number; key: string; kind: string; x: number; y: number }[]>([]);
  const [banner, setBanner] = useState<{ id: number; key: string; label?: string; color?: string } | null>(null);
  const skillCycles = useRef<Record<string, number>>({});
  const [superMode, setSuperMode] = useState(false);
  const [ultWave, setUltWave] = useState<number | null>(null);
  const superRef = useRef(false);
  const lastSuper = useRef(-1);
  const [combo, setCombo] = useState(0);
  const lordImg = lordArt(equipped, armyTier?.tier ?? 0);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  // camera shake / flash / zoom / vignette + Lord move channel (kind, progress, dash distance)
  const shake = useSharedValue(0);
  const flash = useSharedValue(0);
  const zoom = useSharedValue(1);
  const vignette = useSharedValue(0);
  const bob = useSharedValue(0);
  const lordKind = useSharedValue(0);
  const lordT = useSharedValue(0);
  const lordDist = useSharedValue(0);
  const lordMove = useMemo(() => ({ kind: lordKind, t: lordT, dist: lordDist }), [lordKind, lordT, lordDist]);
  const [flashColor, setFlashColor] = useState("#FFFFFF");
  const doShake = useCallback((amp: number) => {
    shake.value = withSequence(withTiming(amp, { duration: 40 }), withTiming(-amp, { duration: 60 }), withTiming(amp * 0.5, { duration: 60 }), withTiming(-amp * 0.25, { duration: 60 }), withTiming(0, { duration: 90 }));
  }, [shake]);
  const doFlash = useCallback((color: string, strength: number, ms: number) => {
    setFlashColor(color);
    flash.value = strength;
    flash.value = withTiming(0, { duration: ms, easing: Easing.out(Easing.quad) });
  }, [flash]);
  const playLordMove = useCallback((kind: LordMove) => {
    lordKind.value = kind;
    lordT.value = 0;
    lordT.value = withTiming(1, { duration: LORD_MOVE_MS[kind], easing: kind === 3 ? Easing.inOut(Easing.quad) : kind === 6 ? Easing.linear : Easing.out(Easing.quad) });
  }, [lordKind, lordT]);
  const cameraStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }, { translateY: shake.value * 0.6 }, { scale: zoom.value }] }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: flash.value }));
  const vignetteStyle = useAnimatedStyle(() => ({ opacity: vignette.value }));

  const spawn = useCallback((items: Omit<Fx, "id">[], ttl: number) => {
    const withIds = items.map((i) => ({ ...i, id: ++fxId.current }));
    setFx((f) => [...f, ...withIds].slice(-48));
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
  const visible = Math.min(alive, MAX_VISIBLE);

  // scene geometry (approximate anchors for FX): Lord on the left, horde on the right (row-reverse, wrap-reverse)
  const lordPos = useCallback(() => ({ x: width * 0.22 + 60, y: sceneH - 34 - 66, frontX: width * 0.22 + 118, groundY: sceneH - 36 }), [width, sceneH]);
  const enemyPos = useCallback((i: number, type: string) => {
    const size = monsterSize(type, width);
    const perRow = Math.max(1, Math.floor((width * 0.56) / size));
    const col = i % perRow, row = Math.floor(i / perRow);
    return { x: Math.max(width * 0.42, width - 6 - (col + 0.5) * size), y: sceneH - 38 - size * 0.55 - row * size * 0.8, size };
  }, [width, sceneH]);
  const live = useRef({ wave, visible, finished, alive, isBossWave });
  live.current = { wave, visible, finished, alive, isBossWave };

  // kill events -> damage numbers, sparks, death dissolve, shake, flash, haptics
  useEffect(() => {
    const fresh = kills - prevKills.current;
    prevKills.current = kills;
    if (fresh <= 0 || finished) return;
    const items: Omit<Fx, "id">[] = [];
    const front = enemyPos(Math.max(0, visible - 1), wave.monsters[Math.max(0, visible - 1)]?.type ?? "normal");
    for (let k = 0; k < Math.min(fresh, 4); k++) {
      const h = hashStr(`${attempt.id}:${kills - k}`);
      const crit = h % 4 === 0;
      const x = front.x - 20 + (h % 5) * 12, y = front.y - 20 + ((h >> 3) % 4) * 12;
      items.push({ kind: "dmg", x, y, value: Math.round(attempt.hero_power * (0.85 + (h % 60) / 100) * (crit ? 2 : 1)), crit, color: crit ? colors.res_gold : colors.onSurface });
      items.push({ kind: "burst", x: x + 10, y: y + 30, color: pal.monster[h % pal.monster.length] });
    }
    items.push({ kind: "death", x: front.x, y: front.y, color: pal.accent });
    spawn(items, 1200);
    const bossKill = isBossWave && alive <= 1;
    doShake(bossKill ? 12 : fresh > 1 ? 7 : 4);
    doFlash(bossKill ? colors.goldBright : "#FFFFFF", bossKill ? 0.5 : 0.16, bossKill ? 500 : 180);
    haptic(bossKill ? "heavy" : "light");
  }, [kills]); // eslint-disable-line react-hooks/exhaustive-deps

  // region music
  useEffect(() => {
    playRegionMusic(attempt.timeline.region.region);
  }, [attempt.timeline.region.region]);

  // ---- Lord choreography ---------------------------------------------------------------------------------------
  const strikeCount = useRef(0);
  const lordStrike = useCallback(() => {
    const st = live.current;
    if (st.finished || superRef.current) return;
    strikeCount.current += 1;
    const kind = LORD_PATTERN[strikeCount.current % LORD_PATTERN.length];
    const h = hashStr(`${attempt.id}:swing:${strikeCount.current}`);
    const lp = lordPos();
    const frontIdx = Math.max(0, st.visible - 1);
    const front = enemyPos(frontIdx, st.wave.monsters[frontIdx]?.type ?? "normal");
    const hitX = Math.min(front.x, lp.frontX + 40) + (h % 3) * 8, hitY = front.y - 10;
    setCombo((c) => c + 1);
    if (kind === 4) lordDist.value = Math.max(80, front.x - lp.x - 30);
    playLordMove(kind);
    const dmg = (mult: number, crit = false, x = hitX, y = hitY, color = crit ? colors.goldBright : colors.parchmentDark, huge = false): Omit<Fx, "id"> => ({ kind: "dmg", x, y, value: Math.round(attempt.hero_power * mult * (1 + (h % 30) / 100)), crit, color, size: huge ? 60 : undefined });
    if (kind === 1) {
      setTimeout(() => { setHurtTick((t) => t + 1); spawn([{ kind: "slash", x: hitX - 60, y: hitY - 30, color: colors.parchment, size: 72 }, dmg(0.35)], 900); }, 180);
    } else if (kind === 2) {
      setTimeout(() => {
        setHurtTick((t) => t + 1);
        spawn([{ kind: "slash", x: hitX - 80, y: hitY - 60, color: colors.goldBright, size: 136 }, { kind: "slash", x: hitX - 50, y: hitY - 30, color: "#FFFFFF", size: 84 }, { kind: "flare", x: hitX, y: hitY + 10, size: 70 }, { kind: "speed", x: hitX, y: hitY + 10, color: colors.goldBright }, { kind: "burst", x: hitX, y: hitY + 20, color: colors.goldBright }, dmg(1.3, true)], 1100);
        doShake(6); doFlash("#FFFFFF", 0.16, 160); haptic("light");
      }, 240);
    } else if (kind === 3) {
      [0, 110, 220].forEach((d, i) => setTimeout(() => {
        spawn([{ kind: "slash", x: hitX - 70 + i * 14, y: hitY - 40 + (i % 2) * 16, color: i === 1 ? "#FFFFFF" : colors.goldBright, size: 96 }, dmg(0.6, i === 2, hitX - 10 + i * 16, hitY - i * 10)], 900);
        if (i === 1) setHurtAll((t) => t + 1);
      }, 150 + d));
      setTimeout(() => doShake(4), 300);
    } else if (kind === 4) {
      const d = lordDist.value;
      if (lordImg) spawn([0.2, 0.45, 0.7].map((f, i) => ({ kind: "ghost" as const, x: lp.x - 60 + d * f, y: lp.y - 66, w: 120, h: 130, source: lordImg, color: colors.goldBright, delay: 60 + i * 70 })), 900);
      setTimeout(() => {
        setHurtAll((t) => t + 1);
        spawn([0, 1, 2].map((i) => ({ kind: "slash" as const, x: hitX - 90 + i * 34, y: hitY - 50 + (i % 2) * 22, color: i === 1 ? "#FFFFFF" : colors.parchment, size: 88 })), 800);
        spawn([dmg(0.5, false, hitX - 30, hitY - 20), dmg(0.5, false, hitX + 10, hitY + 6), dmg(0.9, true, hitX + 40, hitY - 30)], 1100);
        doShake(5); doFlash("#FFFFFF", 0.1, 120);
      }, 330);
    } else if (kind === 5) {
      setTimeout(() => {
        setHurtTick((t) => t + 1); setHurtAll((t) => t + 1);
        spawn([{ kind: "dust", x: lp.frontX + 20, y: lp.groundY }, { kind: "shock", x: lp.frontX + 40, y: lp.groundY - 10, color: colors.goldBright }, { kind: "flare", x: hitX, y: hitY + 20, size: 80 }, { kind: "speed", x: hitX, y: hitY + 20, color: "#FFFFFF" }, dmg(1.6, true, hitX, hitY - 10)], 1100);
        doShake(9); doFlash(colors.goldBright, 0.2, 220); haptic("heavy");
      }, 560);
    }
  }, [attempt.id, attempt.hero_power, colors, enemyPos, lordDist, lordImg, lordPos, playLordMove, spawn, doShake, doFlash]);

  useEffect(() => {
    if (finished) return;
    const id = setInterval(lordStrike, STRIKE_MS);
    return () => clearInterval(id);
  }, [finished, lordStrike]);

  // SUPER power-up: charge (aura, vignette, zoom, banner) then release (ultimate wave, white-out, huge numbers on every visible enemy)
  const runSuper = useCallback(() => {
    if (superRef.current || live.current.finished) return;
    superRef.current = true;
    setSuperMode(true);
    const id = ++fxId.current;
    setBanner({ id, key: "__super", label: "POTENZA MASSIMA", color: SUPER_COLOR });
    playLordMove(6);
    vignette.value = withTiming(0.55, { duration: 500 });
    zoom.value = withTiming(1.05, { duration: 1500, easing: Easing.inOut(Easing.quad) });
    doShake(2);
    haptic("light");
    setTimeout(() => {
      if (live.current.finished) { superRef.current = false; setSuperMode(false); vignette.value = withTiming(0, { duration: 300 }); zoom.value = withTiming(1, { duration: 300 }); return; }
      const st = live.current;
      const lp = lordPos();
      playLordMove(7);
      setUltWave(++fxId.current);
      doFlash("#FFFFFF", 0.95, 560);
      doShake(18);
      haptic("heavy");
      zoom.value = withSequence(withTiming(1.12, { duration: 120 }), withTiming(1, { duration: 520, easing: Easing.out(Easing.quad) }));
      vignette.value = withTiming(0, { duration: 700 });
      setBanner((b) => (b?.id === id ? null : b));
      spawn([{ kind: "speed", x: lp.frontX + 30, y: lp.y, color: SUPER_COLOR, size: 160 }, { kind: "flare", x: lp.frontX + 30, y: lp.y, size: 120, color: SUPER_COLOR }], 700);
      const items: Omit<Fx, "id">[] = [];
      for (let i = 0; i < st.visible; i++) {
        const m = st.wave.monsters[i];
        const pos = enemyPos(i, m?.type ?? "normal");
        items.push({ kind: "dmg", x: pos.x - 30, y: pos.y - 30 - i * 6, value: Math.round(attempt.hero_power * (5 + i)), crit: true, color: SUPER_COLOR, size: 60 });
        items.push({ kind: "burst", x: pos.x, y: pos.y, color: SUPER_COLOR });
        items.push({ kind: "flare", x: pos.x, y: pos.y, size: 90 });
      }
      setTimeout(() => { setHurtAll((t) => t + 1); spawn(items, 1500); }, 180);
      setTimeout(() => { setSuperMode(false); superRef.current = false; setUltWave(null); }, 950);
    }, 1650);
  }, [attempt.hero_power, doFlash, doShake, enemyPos, lordPos, playLordMove, spawn, vignette, zoom]);

  useEffect(() => {
    if (finished || elapsed < SUPER_FIRST_S) return;
    const cycle = Math.floor((elapsed - SUPER_FIRST_S) / SUPER_EVERY_S);
    if (cycle > lastSuper.current && elapsed < attempt.duration - 3) {
      lastSuper.current = cycle;
      runSuper();
    }
  }, [Math.floor(elapsed)]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- enemy moves -> impact FX on the scene (roar shockwave, leap dust, spit projectile, melee hits on the Lord) ------
  const lordHit = useCallback((mult: number) => {
    const st = live.current;
    if (st.finished) return;
    const lp = lordPos();
    const h = hashStr(`${attempt.id}:hit:${Date.now() >> 6}`);
    setLordHurtTick((t) => t + 1);
    spawn([{ kind: "dmg", x: lp.x - 30 + (h % 3) * 10, y: lp.y - 40, value: Math.round(Math.max(1, attempt.required_power) * mult * (attempt.win ? 0.5 : 1) * (0.8 + (h % 40) / 100)), color: colors.error }, { kind: "burst", x: lp.x + 10, y: lp.y, color: colors.error, size: 4 }], 900);
    if (!attempt.win) doShake(3);
  }, [attempt.id, attempt.required_power, attempt.win, colors.error, lordPos, spawn, doShake]);

  const onEnemyMove = useCallback((mv: EnemyMove, i: number) => {
    const st = live.current;
    if (st.finished || i >= st.visible) return;
    const m = st.wave.monsters[i];
    if (!m) return;
    const pos = enemyPos(i, m.type);
    const lp = lordPos();
    const isFront = i === st.visible - 1;
    if (mv === 3) {
      spawn([{ kind: "shock", x: pos.x, y: pos.y + pos.size * 0.25, color: m.type === "boss" ? colors.goldBright : pal.accent }], 800);
      if (m.type !== "normal") { doShake(m.type === "boss" ? 7 : 3); doFlash(pal.accent, 0.12, 200); }
    } else if (mv === 1) {
      setTimeout(() => spawn([{ kind: "dust", x: pos.x - pos.size * 0.4, y: pos.y + pos.size * 0.42 }], 700), MOVE_HIT_MS[1]);
      if (isFront) setTimeout(() => lordHit(0.14), MOVE_HIT_MS[1] + 40);
    } else if (mv === 5) {
      setTimeout(() => {
        spawn([{ kind: "proj", x: pos.x - pos.size * 0.35, y: pos.y - pos.size * 0.05, tx: lp.x + 10, ty: lp.y, color: pal.accent }], 520);
        setTimeout(() => { lordHit(0.16); spawn([{ kind: "flare", x: lp.x + 10, y: lp.y, size: 44, color: pal.accent }], 300); }, 470);
      }, MOVE_HIT_MS[5]);
    } else if ((mv === 0 || mv === 2 || mv === 6) && isFront) {
      setTimeout(() => lordHit(mv === 2 ? 0.2 : 0.12), MOVE_HIT_MS[mv]);
    }
  }, [colors.goldBright, enemyPos, lordHit, lordPos, pal.accent, spawn, doShake, doFlash]);

  // auto-skill activations: each cooldown cycle fires the skill's signature effect + flashing name (presentational)
  useEffect(() => {
    if (finished || elapsed < 1) return;
    for (const s of skills) {
      const cycle = Math.floor(elapsed / s.cooldown_seconds);
      const prev = skillCycles.current[s.key];
      skillCycles.current[s.key] = cycle;
      if (prev === undefined || cycle <= prev || !SKILL_FX[s.key] || superRef.current) continue;
      const id = ++fxId.current;
      const color = SKILL_FX[s.key].color;
      const frontX = width * 0.56, frontY = sceneH - 120;
      const lordX = width * 0.28 + 39, lordY = sceneH - 34 - 50;
      setBanner({ id, key: s.key });
      setSkillFx((f) => [...f, { id, key: s.key, kind: s.key, x: s.key === "shield_wall" || s.key === "war_cry" ? lordX : frontX, y: s.key === "shield_wall" || s.key === "war_cry" ? lordY : frontY }]);
      setTimeout(() => setSkillFx((f) => f.filter((x) => x.id !== id)), 1800);
      setTimeout(() => setBanner((b) => (b?.id === id ? null : b)), 1300);
      const h = hashStr(`${attempt.id}:${s.key}:${cycle}`);
      if (s.key === "power_strike") {
        spawn([{ kind: "dmg", x: frontX + 10, y: frontY - 10, value: Math.round(attempt.hero_power * 1.8), crit: true, color }, { kind: "burst", x: frontX + 20, y: frontY + 20, color }, { kind: "speed", x: frontX + 20, y: frontY + 20, color }], 1200);
        doShake(8); doFlash(color, 0.22, 220); haptic("heavy"); setHurtAll((t) => t + 1);
      } else if (s.key === "rain_of_steel") {
        spawn(Array.from({ length: 4 }).map((_, i) => ({ kind: "dmg" as const, x: frontX + (i * 31 + (h % 20)) % (width * 0.36), y: frontY - 20 + (i % 2) * 18, value: Math.round(attempt.hero_power * 1.2), color })), 1300);
        doShake(6); doFlash(color, 0.18, 260); setTimeout(() => setHurtAll((t) => t + 1), 500);
      } else if (s.key === "royal_strike") {
        spawn([{ kind: "dmg", x: frontX + 6, y: frontY - 24, value: Math.round(attempt.hero_power * 3.5), crit: true, color }, { kind: "flare", x: frontX + 24, y: frontY, size: 90, color }], 1400);
        doShake(11); doFlash(color, 0.45, 320); haptic("heavy"); setHurtAll((t) => t + 1);
      } else if (s.key === "war_cry") {
        doShake(4); doFlash(color, 0.2, 320);
      } else if (s.key === "shield_wall") {
        doFlash(color, 0.18, 320);
      } else if (s.key === "dragon_banner") {
        doFlash(color, 0.25, 360); doShake(5);
      }
    }
  }, [Math.floor(elapsed)]); // eslint-disable-line react-hooks/exhaustive-deps

  // outcome: hold the banner, then let the parent claim (server-authoritative)
  useEffect(() => {
    if (!finished || done.current) return;
    done.current = true;
    setOutcome(true);
    lordKind.value = 0;
    vignette.value = withTiming(0, { duration: 200 });
    zoom.value = withTiming(1, { duration: 200 });
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

  const cap = Math.min(armyTier?.foreground_proxy_cap ?? 0, isHighTier ? 12 : 8);
  const proxies = useMemo(() => allocateProxies(formation, cap), [formation, cap]);
  const bgCohorts = armyTier?.background_cohorts ?? 0;

  useEffect(() => {
    bob.value = withRepeat(withSequence(withTiming(-3, { duration: 420, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 420, easing: Easing.inOut(Easing.quad) })), -1, true);
  }, [bob]);
  const bobStyle = useAnimatedStyle(() => ({ transform: [{ translateY: bob.value }] }));
  const bobStyle2 = useAnimatedStyle(() => ({ transform: [{ translateY: -bob.value }] }));

  const skillCycle = skills.map((s) => ({ ...s, frac: ((elapsed % s.cooldown_seconds) / s.cooldown_seconds) }));
  const regionBoss = attempt.timeline.region.boss;
  const bg = regionBackground(attempt.timeline.region.region);
  const lp = lordPos();

  return (
    <View style={{ height: sceneH, overflow: "hidden", borderBottomWidth: 3, borderColor: colors.gold, backgroundColor: pal.ground }} testID="battle-scene">
      <Animated.View style={[{ position: "absolute", left: -12, right: -12, top: -8, bottom: -8 }, cameraStyle]}>
        {bg ? (
          <Image source={bg} style={{ position: "absolute", left: 0, top: -8, width: width + 24, height: sceneH + 16 }} resizeMode="cover" />
        ) : (
          <>
            <LinearGradient colors={pal.sky} style={{ position: "absolute", left: 0, right: 0, top: 0, height: sceneH * 0.64 }} />
            <View style={{ position: "absolute", left: width * (0.62 + (attempt.timeline.region.region % 3) * 0.08), top: sceneH * 0.1, width: 64, height: 64, borderRadius: 32, backgroundColor: pal.accent, opacity: 0.18 }} />
            <View style={{ position: "absolute", left: width * (0.62 + (attempt.timeline.region.region % 3) * 0.08) + 12, top: sceneH * 0.1 + 12, width: 40, height: 40, borderRadius: 20, backgroundColor: pal.accent, opacity: 0.6 }} />
            <Clouds width={width} top={sceneH * 0.16} color={pal.fog.replace(/[\d.]+\)$/, "1)")} />
            <View style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.38, height: sceneH * 0.26, flexDirection: "row", alignItems: "flex-end", justifyContent: "space-around", opacity: 0.55 }}>
              {Array.from({ length: 9 }).map((_, i) => <Prop key={i} kind={pal.props} i={i} color={pal.groundAlt} accent={pal.accent} />)}
            </View>
            <View style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.54, height: sceneH * 0.14, backgroundColor: pal.fog }} />
            <LinearGradient colors={[pal.ground, pal.groundAlt]} style={{ position: "absolute", left: 0, right: 0, top: sceneH * 0.62, bottom: 0 }} />
          </>
        )}
        {/* ground contact shadow + ambience */}
        <LinearGradient colors={["transparent", "rgba(0,0,0,0.45)"]} style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: sceneH * 0.3 }} />
        <Ambient width={width + 24} height={sceneH} color={pal.accent} rise={attempt.timeline.region.region >= 7} />
        {isBossWave ? <LinearGradient colors={["rgba(120,0,0,0.45)", "transparent", "rgba(120,0,0,0.45)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} /> : null}
        {/* vignette during the SUPER charge */}
        <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "#05070C" }, vignetteStyle]} />
        {/* background cohorts with banners */}
        <View style={{ position: "absolute", left: 20, top: sceneH * 0.58, flexDirection: "row", gap: 10, flexWrap: "wrap", width: width * 0.55 }}>
          {Array.from({ length: Math.min(bgCohorts, 24) }).map((_, i) => <CohortSilhouette key={i} width={34 + (i % 3) * 8} color={i % 4 === 0 ? colors.iron : colors.forest} banner={i % 2 === 0 ? heraldicColor : undefined} />)}
        </View>
        {/* foreground formation */}
        <Animated.View style={[{ position: "absolute", left: 4, bottom: 44, width: width * 0.4, flexDirection: "row", flexWrap: "wrap-reverse", alignItems: "flex-end", gap: 0, opacity: 0.95 }, bobStyle]} testID="formation-proxies">
          {proxies.flatMap((p) => Array.from({ length: p.count }).map((_, i) => <UnitProxy key={`${p.unit}${i}`} unit={p.unit} scale={CATEGORY[p.unit] === "mythic" ? 1.3 : 1.05} banner={i === 0 ? heraldicColor : undefined} />))}
        </Animated.View>
        {/* SUPER aura behind the Lord */}
        {superMode ? <SuperAura x={lp.x} y={lp.groundY + 6} width={175} height={185} color={SUPER_COLOR} /> : null}
        {/* Lord */}
        <View style={{ position: "absolute", left: width * 0.22, bottom: 34 }} testID="lord-sprite">
          <LordSprite equipped={equipped} size={104} tier={armyTier?.tier ?? 0} heraldicColor={heraldicColor} swinging={!outcome} move={lordMove} hurtTick={outcome ? 0 : lordHurtTick} superMode={superMode} />
          <View style={{ position: "absolute", top: -14, alignSelf: "center", paddingHorizontal: 6, backgroundColor: colors.overlay, borderRadius: 3, borderWidth: 1, borderColor: superMode ? SUPER_COLOR : colors.gold }}>
            <Text style={{ fontFamily: fonts.bodyBold, fontSize: 9, color: superMode ? SUPER_COLOR : colors.goldBright }}>{superMode ? "SUPER" : "LORD"}</Text>
          </View>
        </View>
        {/* monsters */}
        <Animated.View style={[{ position: "absolute", right: 6, bottom: 38, width: width * 0.56, flexDirection: "row-reverse", flexWrap: "wrap-reverse", alignItems: "flex-end", gap: 0, justifyContent: "flex-start" }, bobStyle2]} testID="monster-horde">
          {alive > MAX_VISIBLE ? <View style={{ position: "absolute", left: 4, top: -18, paddingHorizontal: 6, borderRadius: 3, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }}><Text style={{ fontFamily: fonts.bodyBold, fontSize: 10, color: colors.onSurface }}>+{alive - MAX_VISIBLE} nemici</Text></View> : null}
          {wave.monsters.slice(0, visible).map((m, i) => (
            <Animated.View key={`${waveIdx}-${i}`} entering={FadeIn.duration(250)} exiting={ZoomOut.duration(260)}>
              <MonsterSprite family={m.family} type={m.type} palette={pal.monster} size={monsterSize(m.type, width)} index={i} onMove={onEnemyMove} hurtTick={outcome ? 0 : (i === visible - 1 ? hurtTick : 0) + hurtAll} fighting={!outcome} />
            </Animated.View>
          ))}
        </Animated.View>
        {/* ultimate wave sweeping the horde */}
        {ultWave ? <UltimateWave key={ultWave} x={lp.frontX - 20} y={lp.groundY + 4} width={width - lp.frontX + 40} height={sceneH * 0.62} color={SUPER_COLOR} /> : null}
        {/* VFX layer */}
        {fx.map((f) => {
          switch (f.kind) {
            case "dmg": return <DamageNumber key={f.id} x={f.x} y={f.y} value={f.value ?? 0} crit={f.crit} huge={!!f.size && f.size >= 60} color={f.color ?? colors.onSurface} seed={f.id} />;
            case "slash": return <Slash key={f.id} x={f.x} y={f.y} color={f.color ?? colors.parchment} size={f.size} />;
            case "speed": return <SpeedLines key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} radius={f.size ?? 110} />;
            case "flare": return <Flare key={f.id} x={f.x} y={f.y} size={f.size} color={f.color} />;
            case "dust": return <DustPuff key={f.id} x={f.x} y={f.y} />;
            case "shock": return <Shockwave key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} />;
            case "proj": return <Projectile key={f.id} x={f.x} y={f.y} tx={f.tx ?? f.x} ty={f.ty ?? f.y} color={f.color ?? pal.accent} />;
            case "ghost": return f.source ? <Ghost key={f.id} x={f.x} y={f.y} w={f.w ?? 100} h={f.h ?? 110} source={f.source} tint={f.color ?? colors.goldBright} delay={f.delay} /> : null;
            case "death": return <DeathDissolve key={f.id} x={f.x} y={f.y} color={f.color ?? pal.accent} />;
            default: return <Burst key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} seed={f.id} count={f.size ?? 8} />;
          }
        })}
        {outcome && attempt.win ? <CoinShower x={width * 0.5} y={sceneH * 0.5} /> : null}
        {outcome && attempt.win ? <Burst x={width * 0.5} y={sceneH * 0.45} color={colors.goldBright} count={14} big /> : null}
        {skillFx.map((f) => {
          const color = SKILL_FX[f.key].color;
          if (f.kind === "war_cry") return <Shockwave key={f.id} x={f.x} y={f.y} color={color} />;
          if (f.kind === "shield_wall") return <ShieldDome key={f.id} x={f.x} y={f.y} size={120} color={color} />;
          if (f.kind === "rain_of_steel") return <SteelRain key={f.id} x={width * 0.5} width={width * 0.46} height={sceneH - 60} color={color} />;
          if (f.kind === "royal_strike") return <LightningBolt key={f.id} x={f.x + 24} height={sceneH - 70} color={color} />;
          if (f.kind === "dragon_banner") return <BannerRise key={f.id} x={width * 0.12} y={sceneH * 0.42} color={color} heraldic={heraldicColor} />;
          return <Slash key={f.id} x={f.x - 20} y={f.y - 30} color={color} />;
        })}
      </Animated.View>
      {banner ? <SkillBanner key={banner.id} name={banner.label ?? SKILL_FX[banner.key].label} color={banner.color ?? SKILL_FX[banner.key].color} sceneH={sceneH} /> : null}
      {combo >= 3 && !outcome ? <ComboText n={combo} x={width * 0.5 - 40} y={56} color={combo >= 10 ? SUPER_COLOR : colors.goldBright} /> : null}
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
          <View style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3, backgroundColor: colors.overlay, borderWidth: 1, borderColor: superMode ? SUPER_COLOR : colors.iron, overflow: "hidden" }} testID="super-gauge">
            <View style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${Math.min(100, ((elapsed < SUPER_FIRST_S ? elapsed / SUPER_FIRST_S : ((elapsed - SUPER_FIRST_S) % SUPER_EVERY_S) / SUPER_EVERY_S) * 100))}%`, backgroundColor: "rgba(255,201,60,0.45)" }} />
            <Text style={{ fontFamily: fonts.bodyMedium, fontSize: 10, color: superMode ? SUPER_COLOR : colors.onSurface }}>SUPER</Text>
          </View>
        </View>
      </View>
      {!attempt.win && !outcome ? (
        <View style={{ position: "absolute", top: sceneH * 0.3, alignSelf: "center", backgroundColor: colors.overlay, borderColor: colors.error, borderWidth: 2, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 4 }}>
          <Text style={{ fontFamily: fonts.display, fontSize: 16, color: colors.onSurface }}>Potenza {fmt(attempt.total_power)} / {fmt(attempt.required_power)} richiesta</Text>
        </View>
      ) : null}
      {outcome ? <OutcomeBanner win={attempt.win} firstClear={!!firstClear} subtitle={attempt.win ? `Stage ${attempt.stage} · ${attempt.timeline.total_monsters} nemici abbattuti · combo x${combo}` : `Potenza ${fmt(attempt.total_power)} / ${fmt(attempt.required_power)} richiesta`} sceneH={sceneH} /> : null}
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
