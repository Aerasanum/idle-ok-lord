// Guided first-play tutorial: coach-mark overlay driven by measured targets. Completion is stored server-side (settings.tutorial_done).
import { useRouter } from "expo-router";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { StyleSheet, View, useWindowDimensions } from "react-native";
import Animated, { Easing, FadeIn, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api/client";
import { QK } from "@/src/api/hooks";
import { queryClient } from "@/src/query-client";
import { useTheme } from "@/src/theme";
import { Btn, Icon, IconName, Panel, Row, Txt } from "@/src/ui";

export type TutorialStep = { id: string; title: string; text: string; icon: IconName; target?: string; route?: string };

export const TUTORIAL_STEPS: TutorialStep[] = [
  { id: "welcome", icon: "crown", title: "Benvenuto, Lord!", text: "In IDLE 1 il tuo esercito combatte da solo, anche quando non ci sei. In un minuto ti mostro come funziona." },
  { id: "stage", icon: "sword-cross", target: "stage-panel", route: "/(tabs)/battle", title: "Lo Stage", text: "Qui vedi lo stage attuale, la tua Potenza e quella Richiesta. Se la tua è più alta vinci: la battaglia si decide sul server, tu la vedi animata." },
  { id: "auto", icon: "play-circle", target: "auto-battle-toggle", title: "Auto-battaglia", text: "Con Auto ON il Lord ripete gli stage e avanza dopo ogni vittoria. Ogni stage conquistato dà bottino, XP e una nuova tessera del Dominio." },
  { id: "hero", icon: "shield-star", target: "hero-card", title: "Il tuo Lord", text: "Equipaggia gli oggetti trovati e spendi i punti Talento: ne guadagni uno ogni 5 livelli. Nessun potere a pagamento." },
  { id: "kingdom", icon: "castle", target: "production-panel", route: "/(tabs)/kingdom", title: "Il Regno produce", text: "Fattorie, segherie e miniere generano risorse ogni ora, anche offline. Il Castello sblocca nuovi edifici." },
  { id: "build", icon: "hammer", target: "kingdom-scene", title: "Costruisci e potenzia", text: "Tocca un edificio nella scena per vedere costi e tempi. Le costruzioni entrano in coda e proseguono anche con l'app chiusa." },
  { id: "queues", icon: "timer-sand", target: "queues-panel", title: "Code e accelerazioni", text: "Qui segui costruzioni, reclutamenti e ricerche. Puoi accelerare con Rubini: il costo è sempre mostrato prima." },
  { id: "offline", icon: "treasure-chest", target: "quick-offline", route: "/(tabs)/battle", title: "Forziere offline", text: "Quando torni, il Forziere contiene fino a 12 ore di bottino, XP e oggetti: riscattalo da qui." },
  { id: "done", icon: "flag-checkered", title: "Buona conquista!", text: "Espandi il Dominio, unisciti a un'Alleanza e affronta le Guerre 10v10. Puoi rivedere questa guida dal Profilo." },
];

type Rect = { x: number; y: number; w: number; h: number };
// `hasAutoStarted` is a getter, not a flag: the auto-start happens once per app session and
// is only ever read from an effect, so it must not force a re-render of the whole tree.
type Ctx = { active: boolean; index: number; step: TutorialStep | null; targets: Record<string, Rect>; start: () => void; next: () => void; skip: () => void; report: (id: string, r: Rect) => void; hasAutoStarted: () => boolean; markAutoStarted: () => void };

const TutorialCtx = createContext<Ctx>({ active: false, index: 0, step: null, targets: {}, start: () => {}, next: () => {}, skip: () => {}, report: () => {}, hasAutoStarted: () => false, markAutoStarted: () => {} });

export function useTutorial() {
  return useContext(TutorialCtx);
}

export function TutorialProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(0);
  const [targets, setTargets] = useState<Record<string, Rect>>({});
  const autoStarted = useRef(false);

  const go = useCallback((i: number) => {
    const s = TUTORIAL_STEPS[i];
    if (s?.route) router.navigate(s.route as any);
    setIndex(i);
  }, [router]);
  const finish = useCallback(() => {
    setActive(false);
    api.patch("/account/settings", { tutorial_done: true }).then(() => queryClient.invalidateQueries({ queryKey: QK.profile })).catch(() => {});
  }, []);
  const start = useCallback(() => {
    autoStarted.current = true;
    setTargets({});
    setIndex(0);
    setActive(true);
    router.navigate("/(tabs)/battle" as any);
  }, [router]);
  const next = useCallback(() => (index + 1 >= TUTORIAL_STEPS.length ? finish() : go(index + 1)), [index, finish, go]);
  const report = useCallback((id: string, r: Rect) => {
    setTargets((t) => {
      const c = t[id];
      if (c && Math.abs(c.x - r.x) < 1 && Math.abs(c.y - r.y) < 1 && Math.abs(c.w - r.w) < 1 && Math.abs(c.h - r.h) < 1) return t;
      return { ...t, [id]: r };
    });
  }, []);

  const value = useMemo<Ctx>(() => ({ active, index, step: active ? TUTORIAL_STEPS[index] : null, targets, start, next, skip: finish, report, hasAutoStarted: () => autoStarted.current, markAutoStarted: () => { autoStarted.current = true; } }), [active, index, targets, start, next, finish, report]);
  return <TutorialCtx.Provider value={value}>{children}</TutorialCtx.Provider>;
}

/** Wrap any element so the overlay can spotlight it when the current step targets `id`. */
export function TutorialTarget({ id, children, style, onLayout }: { id: string; children: React.ReactNode; style?: any; onLayout?: (y: number) => void }) {
  const { step, report, active } = useTutorial();
  const ref = useRef<View>(null);
  const isTarget = active && step?.target === id;
  useEffect(() => {
    if (!isTarget) return;
    const measure = () => ref.current?.measureInWindow((x, y, w, h) => {
      if (w > 0 && h > 0) report(id, { x, y, w, h });
    });
    measure();
    const iv = setInterval(measure, 350);
    return () => clearInterval(iv);
  }, [isTarget, id, report]);
  return (
    <View ref={ref} style={style} collapsable={false} onLayout={(e) => onLayout?.(e.nativeEvent.layout.y)}>
      {children}
    </View>
  );
}

export function TutorialOverlay() {
  const { active, step, index, targets, next, skip } = useTutorial();
  const { colors } = useTheme();
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const pulse = useSharedValue(0);
  useEffect(() => {
    pulse.value = withRepeat(withSequence(withTiming(1, { duration: 700, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: 700, easing: Easing.inOut(Easing.quad) })), -1, false);
  }, [pulse]);
  const ringStyle = useAnimatedStyle(() => ({ opacity: 0.55 + 0.45 * pulse.value, transform: [{ scale: 1 + 0.015 * pulse.value }] }));
  if (!active || !step) return null;

  const raw = step.target ? targets[step.target] : undefined;
  const pad = 8;
  const visible = raw && raw.y + raw.h > insets.top + 40 && raw.y < height - insets.bottom - 120;
  const hole = visible && raw ? { x: Math.max(0, raw.x - pad), y: raw.y - pad, w: Math.min(width, raw.w + pad * 2), h: raw.h + pad * 2 } : null;
  const CARD_H = 250;
  const below = hole ? hole.y + hole.h + 12 + CARD_H < height - insets.bottom : false;
  const cardTop = hole ? (below ? hole.y + hole.h + 12 : Math.max(insets.top + 12, hole.y - 12 - CARD_H)) : undefined;
  const last = index === TUTORIAL_STEPS.length - 1;
  const dim = "rgba(0,0,0,0.72)";

  return (
    <View style={[StyleSheet.absoluteFill, { zIndex: 1000 }]} testID="tutorial-overlay">
      {hole ? (
        <>
          <View style={{ position: "absolute", left: 0, right: 0, top: 0, height: Math.max(0, hole.y), backgroundColor: dim }} />
          <View style={{ position: "absolute", left: 0, right: 0, top: hole.y + hole.h, bottom: 0, backgroundColor: dim }} />
          <View style={{ position: "absolute", left: 0, width: hole.x, top: hole.y, height: hole.h, backgroundColor: dim }} />
          <View style={{ position: "absolute", left: hole.x + hole.w, right: 0, top: hole.y, height: hole.h, backgroundColor: dim }} />
          <Animated.View pointerEvents="none" style={[{ position: "absolute", left: hole.x, top: hole.y, width: hole.w, height: hole.h, borderWidth: 2.5, borderColor: colors.goldBright, borderRadius: 8 }, ringStyle]} />
        </>
      ) : (
        <View style={[StyleSheet.absoluteFill, { backgroundColor: dim }]} />
      )}
      <Animated.View key={step.id} entering={FadeIn.duration(220)} style={{ position: "absolute", left: 12, right: 12, top: cardTop, ...(cardTop === undefined ? { top: undefined, bottom: undefined, alignSelf: "center", marginTop: height * 0.3 } : {}) }} testID="tutorial-card">
        <Panel variant="wood" style={{ gap: 8 }}>
          <Row>
            <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.burgundy, alignItems: "center", justifyContent: "center", borderWidth: 2, borderColor: colors.gold }}>
              <Icon name={step.icon} size={22} color={colors.goldBright} />
            </View>
            <View style={{ flex: 1 }}>
              <Txt v="h2" testID="tutorial-title">{step.title}</Txt>
              <Txt v="caption" color={colors.muted}>Passo {index + 1} di {TUTORIAL_STEPS.length}</Txt>
            </View>
          </Row>
          <Txt v="body" testID="tutorial-text">{step.text}</Txt>
          <Row style={{ justifyContent: "space-between", marginTop: 4 }}>
            <Row gap={4}>{TUTORIAL_STEPS.map((s, i) => <View key={s.id} style={{ width: i === index ? 14 : 6, height: 6, borderRadius: 3, backgroundColor: i <= index ? colors.goldBright : colors.iron }} />)}</Row>
            <Row>
              {!last ? <Btn title="Salta" small variant="ghost" onPress={skip} testID="tutorial-skip-button" /> : null}
              <Btn title={last ? "Inizia!" : index === 0 ? "Andiamo" : "Avanti"} small icon={last ? "sword" : "chevron-right"} onPress={next} testID="tutorial-next-button" />
            </Row>
          </Row>
        </Panel>
      </Animated.View>
    </View>
  );
}
