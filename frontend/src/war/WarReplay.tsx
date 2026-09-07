// Animated replay of a resolved 10-lane alliance war: each lane is a duel between the two Lords (attacker left, defender right).
// Purely presentational — lane winners/powers come from the server snapshot resolution.
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Image, Pressable, Text, View, useWindowDimensions } from "react-native";
import Animated, { Easing, FadeIn, FadeOut, useAnimatedStyle, useSharedValue, withSequence, withTiming } from "react-native-reanimated";

import { lordArt, monsterArt } from "@/src/art";
import { Burst, DamageNumber, Flare, Fx, Shockwave, Slash, SpeedLines } from "@/src/battle/effects";
import { fonts, useTheme } from "@/src/theme";
import { Icon, Txt, fmt } from "@/src/ui";

export type Lane = { lane: number; attacker: string; defender: string; attacker_power: number; defender_power: number; attacker_wins: boolean; attacker_level?: number; defender_level?: number; attacker_npc?: boolean; defender_npc?: boolean; attacker_counter_pct?: number; defender_counter_pct?: number };

const LANE_MS = 2300;
const tierFor = (level?: number) => (level && level >= 40 ? 5 : level && level >= 20 ? 3 : 0);
const artFor = (level?: number, npc?: boolean) => (npc ? monsterArt("Fallen Knight") ?? lordArt({}, 0) : lordArt(tierFor(level) >= 3 ? { chest: true } : {}, tierFor(level)));

export function WarReplay({ lanes, attackerName, defenderName, attackerWon, points, captured, mineIsAttacker, testID }: { lanes: Lane[]; attackerName: string; defenderName: string; attackerWon: boolean; points: [number, number]; captured: boolean; mineIsAttacker: boolean | null; testID?: string }) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const W = Math.min(width - 56, 420), H = 210;
  const [step, setStep] = useState(0);
  const [phase, setPhase] = useState<"idle" | "enter" | "clash" | "result" | "summary">("idle");
  const [playing, setPlaying] = useState(true);
  const [fx, setFx] = useState<Fx[]>([]);
  const fxId = useRef(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const lane = lanes[Math.min(step, lanes.length - 1)];
  const scoreA = lanes.slice(0, phase === "summary" ? lanes.length : step + (phase === "result" ? 1 : 0)).filter((l) => l.attacker_wins).length;
  const scoreD = lanes.slice(0, phase === "summary" ? lanes.length : step + (phase === "result" ? 1 : 0)).filter((l) => !l.attacker_wins).length;

  const ax = useSharedValue(-W * 0.6), dx = useSharedValue(W * 0.6);
  const aRot = useSharedValue(0), dRot = useSharedValue(0);
  const aOp = useSharedValue(1), dOp = useSharedValue(1);
  const aScale = useSharedValue(1), dScale = useSharedValue(1);
  const shake = useSharedValue(0);
  const flash = useSharedValue(0);

  const spawn = useCallback((items: Omit<Fx, "id">[], ttl: number) => {
    const withIds = items.map((i) => ({ ...i, id: ++fxId.current }));
    setFx((f) => [...f, ...withIds]);
    const t = setTimeout(() => setFx((f) => f.filter((x) => !withIds.some((w) => w.id === x.id))), ttl);
    timers.current.push(t);
  }, []);
  const later = useCallback((fn: () => void, ms: number) => {
    const t = setTimeout(fn, ms);
    timers.current.push(t);
  }, []);

  const lordSize = Math.min(104, W * 0.28);
  const cx = W / 2, groundY = H - 26;
  const aHome = W * 0.22 - lordSize / 2, dHome = W * 0.78 - lordSize / 2;

  const playLane = useCallback((i: number) => {
    const l = lanes[i];
    if (!l) return;
    setPhase("enter");
    ax.value = -W * 0.6; dx.value = W * 0.6; aOp.value = 1; dOp.value = 1; aRot.value = 0; dRot.value = 0; aScale.value = 1; dScale.value = 1;
    ax.value = withTiming(0, { duration: 420, easing: Easing.out(Easing.cubic) });
    dx.value = withTiming(0, { duration: 420, easing: Easing.out(Easing.cubic) });
    later(() => {
      setPhase("clash");
      const reach = cx - lordSize / 2 - aHome - 8;
      ax.value = withSequence(withTiming(reach, { duration: 220, easing: Easing.in(Easing.quad) }), withTiming(reach - 30, { duration: 160 }), withTiming(0, { duration: 500, easing: Easing.out(Easing.quad) }));
      dx.value = withSequence(withTiming(-reach, { duration: 220, easing: Easing.in(Easing.quad) }), withTiming(-reach + 30, { duration: 160 }), withTiming(0, { duration: 500, easing: Easing.out(Easing.quad) }));
      aRot.value = withSequence(withTiming(-14, { duration: 220 }), withTiming(0, { duration: 500 }));
      dRot.value = withSequence(withTiming(14, { duration: 220 }), withTiming(0, { duration: 500 }));
      later(() => {
        shake.value = withSequence(withTiming(8, { duration: 40 }), withTiming(-8, { duration: 60 }), withTiming(4, { duration: 60 }), withTiming(0, { duration: 80 }));
        flash.value = 0.7; flash.value = withTiming(0, { duration: 320 });
        spawn([
          { kind: "flare", x: cx, y: groundY - lordSize * 0.55, size: 90 },
          { kind: "speed", x: cx, y: groundY - lordSize * 0.55, color: colors.goldBright },
          { kind: "slash", x: cx - 60, y: groundY - lordSize * 0.9, color: colors.parchment, size: 96 },
          { kind: "slash", x: cx - 40, y: groundY - lordSize * 0.7, color: l.attacker_wins ? colors.goldBright : colors.error, size: 80 },
          { kind: "burst", x: cx, y: groundY - lordSize * 0.5, color: colors.goldBright },
          { kind: "dmg", x: cx - 70, y: groundY - lordSize * 1.1, value: l.attacker_power, crit: l.attacker_wins, color: l.attacker_wins ? colors.goldBright : colors.parchment },
          { kind: "dmg", x: cx + 20, y: groundY - lordSize * 1.15, value: l.defender_power, crit: !l.attacker_wins, color: !l.attacker_wins ? colors.goldBright : colors.parchment },
        ], 1300);
      }, 210);
      later(() => {
        setPhase("result");
        if (l.attacker_wins) {
          dx.value = withTiming(W * 0.28, { duration: 420, easing: Easing.out(Easing.quad) });
          dRot.value = withTiming(70, { duration: 420 }); dOp.value = withTiming(0.15, { duration: 520 });
          aScale.value = withSequence(withTiming(1.18, { duration: 220 }), withTiming(1.08, { duration: 300 }));
        } else {
          ax.value = withTiming(-W * 0.28, { duration: 420, easing: Easing.out(Easing.quad) });
          aRot.value = withTiming(-70, { duration: 420 }); aOp.value = withTiming(0.15, { duration: 520 });
          dScale.value = withSequence(withTiming(1.18, { duration: 220 }), withTiming(1.08, { duration: 300 }));
        }
        spawn([{ kind: "shock", x: l.attacker_wins ? W * 0.78 : W * 0.22, y: groundY - 6, color: l.attacker_wins ? colors.error : colors.error }], 800);
      }, 520);
    }, 460);
  }, [lanes, W, cx, aHome, lordSize, groundY, colors, ax, dx, aRot, dRot, aOp, dOp, aScale, dScale, shake, flash, spawn, later]);

  // sequencer
  useEffect(() => {
    if (!playing || phase === "summary") return;
    if (phase === "idle") {
      playLane(step);
      return;
    }
    if (phase === "result") {
      const t = setTimeout(() => {
        if (step + 1 >= lanes.length) setPhase("summary");
        else { setStep(step + 1); playLane(step + 1); }
      }, LANE_MS - 1200);
      timers.current.push(t);
    }
  }, [playing, phase, step]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const restart = () => { timers.current.forEach(clearTimeout); timers.current = []; setFx([]); setStep(0); setPhase("idle"); setPlaying(true); };
  const skip = () => { timers.current.forEach(clearTimeout); timers.current = []; setFx([]); setPhase("summary"); };

  const aStyle = useAnimatedStyle(() => ({ opacity: aOp.value, transform: [{ translateX: ax.value }, { rotate: `${aRot.value}deg` }, { scale: aScale.value }] }));
  const dStyle = useAnimatedStyle(() => ({ opacity: dOp.value, transform: [{ translateX: dx.value }, { rotate: `${dRot.value}deg` }, { scale: dScale.value }, { scaleX: -1 }] }));
  const camStyle = useAnimatedStyle(() => ({ transform: [{ translateX: shake.value }] }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: flash.value }));
  const mineWon = mineIsAttacker === null ? null : mineIsAttacker === attackerWon;

  return (
    <View style={{ gap: 8 }} testID={testID ?? "war-replay"}>
      {/* scoreboard */}
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ flex: 1 }}><Txt v="bodyBold" color={colors.onSurfaceInverse} numberOfLines={1}>⚔️ {attackerName}</Txt></View>
        <View style={{ paddingHorizontal: 12, paddingVertical: 4, borderRadius: 6, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }} testID="war-replay-score">
          <Text style={{ fontFamily: fonts.display, fontSize: 22, color: colors.goldBright }}>{scoreA} – {scoreD}</Text>
        </View>
        <View style={{ flex: 1, alignItems: "flex-end" }}><Txt v="bodyBold" color={colors.onSurfaceInverse} numberOfLines={1}>{defenderName} 🛡️</Txt></View>
      </View>
      {/* lane dots */}
      <View style={{ flexDirection: "row", gap: 4, justifyContent: "center" }} testID="war-replay-lanes">
        {lanes.map((l, i) => {
          const done = phase === "summary" || i < step || (i === step && phase === "result");
          return <View key={l.lane} style={{ width: 22, height: 8, borderRadius: 4, backgroundColor: done ? (l.attacker_wins ? colors.goldBright : colors.error) : i === step ? colors.parchmentDark : colors.iron, opacity: done || i === step ? 1 : 0.5 }} />;
        })}
      </View>
      {/* arena */}
      <Animated.View style={[{ width: W, height: H, alignSelf: "center", borderRadius: 8, overflow: "hidden", backgroundColor: "#2B2419", borderWidth: 2, borderColor: colors.wood }, camStyle]} testID="war-replay-arena">
        <View style={{ position: "absolute", left: 0, right: 0, top: 0, height: H * 0.62, backgroundColor: "#3B3A55" }} />
        <View style={{ position: "absolute", left: 0, right: 0, top: H * 0.62, bottom: 0, backgroundColor: "#4A3E2C" }} />
        <View style={{ position: "absolute", left: 0, right: 0, top: groundY, height: 2, backgroundColor: "rgba(0,0,0,0.4)" }} />
        {phase !== "summary" ? (
          <>
            <View style={{ position: "absolute", left: 8, top: 6, maxWidth: W * 0.44 }}>
              <Txt v="small" color={colors.parchment} numberOfLines={1}>{lane.attacker_npc ? "Guarnigione" : lane.attacker}{lane.attacker_level ? ` L${lane.attacker_level}` : ""}</Txt>
              <Text style={{ fontFamily: fonts.displaySemi, fontSize: 13, color: colors.goldBright }}>{fmt(lane.attacker_power)}{lane.attacker_counter_pct ? <Text style={{ color: lane.attacker_counter_pct > 0 ? colors.success : colors.error, fontSize: 11 }}> {lane.attacker_counter_pct > 0 ? "+" : ""}{lane.attacker_counter_pct}%</Text> : null}</Text>
            </View>
            <View style={{ position: "absolute", right: 8, top: 6, maxWidth: W * 0.44, alignItems: "flex-end" }}>
              <Txt v="small" color={colors.parchment} numberOfLines={1}>{lane.defender_npc ? "Guarnigione" : lane.defender}{lane.defender_level ? ` L${lane.defender_level}` : ""}</Txt>
              <Text style={{ fontFamily: fonts.displaySemi, fontSize: 13, color: colors.goldBright }}>{fmt(lane.defender_power)}{lane.defender_counter_pct ? <Text style={{ color: lane.defender_counter_pct > 0 ? colors.success : colors.error, fontSize: 11 }}> {lane.defender_counter_pct > 0 ? "+" : ""}{lane.defender_counter_pct}%</Text> : null}</Text>
            </View>
            <View style={{ position: "absolute", top: 8, alignSelf: "center", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }}>
              <Text style={{ fontFamily: fonts.display, fontSize: 14, color: colors.goldBright }} testID="war-replay-lane-label">Corsia {lane.lane}/{lanes.length}</Text>
            </View>
            <Animated.View style={[{ position: "absolute", left: aHome, top: groundY - lordSize, width: lordSize, height: lordSize, transformOrigin: "50% 100%" }, aStyle]}>
              <View style={{ position: "absolute", bottom: 0, left: lordSize * 0.15, width: lordSize * 0.7, height: lordSize * 0.12, borderRadius: lordSize, backgroundColor: "#000", opacity: 0.35 }} />
              <Image source={artFor(lane.attacker_level, lane.attacker_npc)} style={{ width: lordSize, height: lordSize, tintColor: lane.attacker_npc ? "#9AA1AD" : undefined }} resizeMode="contain" />
            </Animated.View>
            <Animated.View style={[{ position: "absolute", left: dHome, top: groundY - lordSize, width: lordSize, height: lordSize, transformOrigin: "50% 100%" }, dStyle]}>
              <View style={{ position: "absolute", bottom: 0, left: lordSize * 0.15, width: lordSize * 0.7, height: lordSize * 0.12, borderRadius: lordSize, backgroundColor: "#000", opacity: 0.35 }} />
              <Image source={artFor(lane.defender_level, lane.defender_npc)} style={{ width: lordSize, height: lordSize, tintColor: lane.defender_npc ? "#9AA1AD" : undefined }} resizeMode="contain" />
            </Animated.View>
            {phase === "result" ? (
              <Animated.View entering={FadeIn.duration(200)} exiting={FadeOut.duration(150)} style={{ position: "absolute", bottom: 4, alignSelf: "center", paddingHorizontal: 10, paddingVertical: 3, borderRadius: 4, backgroundColor: colors.overlay, borderWidth: 1, borderColor: lane.attacker_wins ? colors.goldBright : colors.error }}>
                <Text style={{ fontFamily: fonts.display, fontSize: 13, color: lane.attacker_wins ? colors.goldBright : colors.error }} testID="war-replay-lane-result">{lane.attacker_wins ? `${lane.attacker_npc ? "Guarnigione" : lane.attacker} vince la corsia` : `${lane.defender_npc ? "Guarnigione" : lane.defender} tiene la corsia`}</Text>
              </Animated.View>
            ) : null}
          </>
        ) : (
          <Animated.View entering={FadeIn.duration(400)} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, alignItems: "center", justifyContent: "center", gap: 6 }} testID="war-replay-summary">
            <Icon name={mineWon === false ? "skull" : "trophy"} size={40} color={mineWon === false ? colors.error : colors.goldBright} />
            <Text style={{ fontFamily: fonts.display, fontSize: 26, color: mineWon === false ? colors.error : colors.goldBright, textShadowColor: "#000", textShadowRadius: 6 }}>{mineWon === null ? (attackerWon ? "ATTACCO RIUSCITO" : "DIFESA RIUSCITA") : mineWon ? "VITTORIA" : "SCONFITTA"}</Text>
            <Text style={{ fontFamily: fonts.displaySemi, fontSize: 16, color: colors.parchment }}>{attackerWon ? attackerName : defenderName} vince {points[0]}–{points[1]}{captured ? " · nodo conquistato" : ""}</Text>
            <Pressable onPress={restart} style={{ marginTop: 8, flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, height: 40, borderRadius: 6, borderWidth: 1, borderColor: colors.gold, backgroundColor: colors.overlay }} testID="war-replay-restart">
              <Icon name="replay" size={16} color={colors.goldBright} /><Txt v="small" color={colors.goldBright}>Rivedi la battaglia</Txt>
            </Pressable>
          </Animated.View>
        )}
        {fx.map((f) => {
          switch (f.kind) {
            case "dmg": return <DamageNumber key={f.id} x={f.x} y={f.y} value={f.value ?? 0} crit={f.crit} color={f.color ?? colors.parchment} seed={f.id} />;
            case "slash": return <Slash key={f.id} x={f.x} y={f.y} color={f.color ?? colors.parchment} size={f.size} />;
            case "speed": return <SpeedLines key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} radius={90} />;
            case "flare": return <Flare key={f.id} x={f.x} y={f.y} size={f.size} />;
            case "shock": return <Shockwave key={f.id} x={f.x} y={f.y} color={f.color ?? colors.error} />;
            default: return <Burst key={f.id} x={f.x} y={f.y} color={f.color ?? colors.goldBright} seed={f.id} />;
          }
        })}
        <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "#FFFFFF" }, flashStyle]} />
      </Animated.View>
      {phase !== "summary" ? (
        <View style={{ flexDirection: "row", justifyContent: "center", gap: 10 }}>
          <Pressable onPress={() => setPlaying((p) => !p)} style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, height: 40, borderRadius: 6, borderWidth: 1, borderColor: colors.wood }} testID="war-replay-toggle">
            <Icon name={playing ? "pause" : "play"} size={16} color={colors.onSurfaceInverse} /><Txt v="small" color={colors.onSurfaceInverse}>{playing ? "Pausa" : "Riprendi"}</Txt>
          </Pressable>
          <Pressable onPress={skip} style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 12, height: 40, borderRadius: 6, borderWidth: 1, borderColor: colors.wood }} testID="war-replay-skip">
            <Icon name="skip-forward" size={16} color={colors.onSurfaceInverse} /><Txt v="small" color={colors.onSurfaceInverse}>Vai al risultato</Txt>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}
