// Pinch-to-zoom + pan container for visual scenes (battle, kingdom, domain map, war map, titan). Double-tap resets.
// Also exposes +/−/reset buttons (touch and web friendly), an optional D-pad and an imperative `focus(cx, cy, scale)`.
// Content may be larger than the viewport (contentWidth/Height): minScale then fits it, panning is clamped to the content bounds.
// Pan is only enabled once zoomed (relative to the fit scale) so vertical page scrolling keeps working.
import React, { forwardRef, useImperativeHandle, useState } from "react";
import { Pressable, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";

import { useTheme } from "@/src/theme";
import { Icon, IconName } from "@/src/ui";

export type ZoomPanRef = { focus: (cx: number, cy: number, scale?: number) => void; reset: () => void; panBy: (dx: number, dy: number) => void };

export const ZoomPan = forwardRef<ZoomPanRef, { width: number; height: number; children: React.ReactNode; testID?: string; controls?: boolean; dpad?: boolean; style?: any; controlsStyle?: any; contentWidth?: number; contentHeight?: number; minScale?: number; maxScale?: number }>(
  function ZoomPan({ width, height, children, testID, controls = true, dpad = false, style, controlsStyle, contentWidth, contentHeight, minScale, maxScale = 3 }, ref) {
    const { colors } = useTheme();
    const cw = contentWidth ?? width, ch = contentHeight ?? height;
    const MIN = minScale ?? Math.min(1, width / cw, height / ch);
    const MAX = maxScale;
    const scale = useSharedValue(MIN);
    const saved = useSharedValue(MIN);
    const tx = useSharedValue(0), ty = useSharedValue(0);
    const stx = useSharedValue(0), sty = useSharedValue(0);
    const [zoomed, setZoomed] = useState(false);

    const clamp = (v: number, s: number, content: number, viewport: number) => {
      "worklet";
      const max = Math.max(0, (content * s - viewport) / 2);
      return Math.max(-max, Math.min(max, v));
    };
    const setZoomedJS = (z: boolean) => setZoomed(z);

    const pinch = Gesture.Pinch()
      .onUpdate((e) => {
        const s = Math.max(MIN, Math.min(MAX, saved.value * e.scale));
        scale.value = s;
        tx.value = clamp(tx.value, s, cw, width);
        ty.value = clamp(ty.value, s, ch, height);
      })
      .onEnd(() => {
        saved.value = scale.value;
        runOnJS(setZoomedJS)(scale.value > MIN * 1.02);
      });
    const pan = Gesture.Pan()
      .enabled(zoomed)
      .onStart(() => {
        stx.value = tx.value;
        sty.value = ty.value;
      })
      .onUpdate((e) => {
        tx.value = clamp(stx.value + e.translationX, scale.value, cw, width);
        ty.value = clamp(sty.value + e.translationY, scale.value, ch, height);
      });
    const reset = () => {
      scale.value = withTiming(MIN, { duration: 220 });
      saved.value = MIN;
      tx.value = withTiming(0, { duration: 220 });
      ty.value = withTiming(0, { duration: 220 });
      setZoomed(false);
    };
    const zoomTo = (s: number) => {
      const next = Math.max(MIN, Math.min(MAX, s));
      scale.value = withTiming(next, { duration: 200 });
      saved.value = next;
      tx.value = withTiming(clamp(tx.value, next, cw, width), { duration: 200 });
      ty.value = withTiming(clamp(ty.value, next, ch, height), { duration: 200 });
      setZoomed(next > MIN * 1.02);
    };
    /** Center the viewport on content coordinates (cx, cy). */
    const focus = (cx: number, cy: number, s?: number) => {
      const next = Math.max(MIN, Math.min(MAX, s ?? Math.max(saved.value, 2)));
      scale.value = withTiming(next, { duration: 320 });
      saved.value = next;
      tx.value = withTiming(clamp(-(cx - cw / 2) * next, next, cw, width), { duration: 320 });
      ty.value = withTiming(clamp(-(cy - ch / 2) * next, next, ch, height), { duration: 320 });
      setZoomed(next > MIN * 1.02);
    };
    const panBy = (dx: number, dy: number) => {
      let s = saved.value;
      if (s <= MIN * 1.02) { s = Math.min(MAX, MIN * 2); scale.value = withTiming(s, { duration: 200 }); saved.value = s; setZoomed(true); }
      tx.value = withTiming(clamp(tx.value + dx, s, cw, width), { duration: 180 });
      ty.value = withTiming(clamp(ty.value + dy, s, ch, height), { duration: 180 });
    };
    useImperativeHandle(ref, () => ({ focus, reset, panBy }));
    const doubleTap = Gesture.Tap().numberOfTaps(2).onEnd(() => {
      runOnJS(zoomed ? reset : zoomTo)(zoomed ? MIN : MIN * 1.8);
    });
    const gesture = Gesture.Simultaneous(pinch, pan, doubleTap);
    const style2 = useAnimatedStyle(() => ({ transform: [{ translateX: tx.value }, { translateY: ty.value }, { scale: scale.value }] }));
    const btn = { width: 30, height: 30, borderRadius: 6, alignItems: "center" as const, justifyContent: "center" as const, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold };
    const id = (k: string) => (testID ? `${testID}-${k}` : k);
    const Arrow = ({ k, icon, dx, dy }: { k: string; icon: IconName; dx: number; dy: number }) => (
      <Pressable onPress={() => panBy(dx, dy)} style={btn} testID={id(k)} hitSlop={4}><Icon name={icon} size={18} color={colors.goldBright} /></Pressable>
    );
    const step = Math.round(width * 0.3);
    return (
      <View style={[{ width, height, overflow: "hidden" }, style]} testID={testID}>
        <GestureDetector gesture={gesture}>
          <Animated.View style={[{ position: "absolute", left: (width - cw) / 2, top: (height - ch) / 2, width: cw, height: ch }, style2]}>{children}</Animated.View>
        </GestureDetector>
        {controls ? (
          <View style={[{ position: "absolute", right: 6, top: 6, gap: 4 }, controlsStyle]} testID={id("zoom-controls")}>
            <Pressable onPress={() => zoomTo(saved.value + MIN * 0.5)} style={btn} testID={id("zoom-in")} hitSlop={6}><Icon name="magnify-plus-outline" size={18} color={colors.goldBright} /></Pressable>
            <Pressable onPress={() => zoomTo(saved.value - MIN * 0.5)} style={btn} testID={id("zoom-out")} hitSlop={6}><Icon name="magnify-minus-outline" size={18} color={colors.goldBright} /></Pressable>
            {zoomed ? <Pressable onPress={reset} style={btn} testID={id("zoom-reset")} hitSlop={6}><Icon name="fit-to-screen-outline" size={18} color={colors.goldBright} /></Pressable> : null}
          </View>
        ) : null}
        {dpad ? (
          <View style={{ position: "absolute", left: 6, bottom: 6, width: 98, height: 98 }} testID={id("dpad")}>
            <View style={{ position: "absolute", left: 34, top: 0 }}><Arrow k="pan-up" icon="chevron-up" dx={0} dy={step} /></View>
            <View style={{ position: "absolute", left: 0, top: 34 }}><Arrow k="pan-left" icon="chevron-left" dx={step} dy={0} /></View>
            <View style={{ position: "absolute", left: 68, top: 34 }}><Arrow k="pan-right" icon="chevron-right" dx={-step} dy={0} /></View>
            <View style={{ position: "absolute", left: 34, top: 68 }}><Arrow k="pan-down" icon="chevron-down" dx={0} dy={-step} /></View>
          </View>
        ) : null}
      </View>
    );
  },
);
