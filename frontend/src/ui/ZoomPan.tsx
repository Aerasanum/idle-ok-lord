// Pinch-to-zoom + pan container for visual scenes (battle, kingdom, domain map, war map, titan). Double-tap resets.
// Also exposes +/−/reset buttons (touch and web friendly). Pan is only enabled once zoomed so vertical page scrolling keeps working.
import React, { useState } from "react";
import { Pressable, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withTiming } from "react-native-reanimated";

import { useTheme } from "@/src/theme";
import { Icon } from "@/src/ui";

const MIN = 1, MAX = 3;

export function ZoomPan({ width, height, children, testID, controls = true, style, controlsStyle }: { width: number; height: number; children: React.ReactNode; testID?: string; controls?: boolean; style?: any; controlsStyle?: any }) {
  const { colors } = useTheme();
  const scale = useSharedValue(1);
  const saved = useSharedValue(1);
  const tx = useSharedValue(0), ty = useSharedValue(0);
  const stx = useSharedValue(0), sty = useSharedValue(0);
  const [zoomed, setZoomed] = useState(false);

  const clamp = (v: number, s: number, size: number) => {
    "worklet";
    const max = (size * (s - 1)) / 2;
    return Math.max(-max, Math.min(max, v));
  };
  const setZoomedJS = (z: boolean) => setZoomed(z);

  const pinch = Gesture.Pinch()
    .onUpdate((e) => {
      const s = Math.max(MIN, Math.min(MAX, saved.value * e.scale));
      scale.value = s;
      tx.value = clamp(tx.value, s, width);
      ty.value = clamp(ty.value, s, height);
    })
    .onEnd(() => {
      saved.value = scale.value;
      runOnJS(setZoomedJS)(scale.value > 1.02);
    });
  const pan = Gesture.Pan()
    .enabled(zoomed)
    .onStart(() => {
      stx.value = tx.value;
      sty.value = ty.value;
    })
    .onUpdate((e) => {
      tx.value = clamp(stx.value + e.translationX, scale.value, width);
      ty.value = clamp(sty.value + e.translationY, scale.value, height);
    });
  const reset = () => {
    scale.value = withTiming(1, { duration: 220 });
    saved.value = 1;
    tx.value = withTiming(0, { duration: 220 });
    ty.value = withTiming(0, { duration: 220 });
    setZoomed(false);
  };
  const zoomTo = (s: number) => {
    const next = Math.max(MIN, Math.min(MAX, s));
    scale.value = withTiming(next, { duration: 200 });
    saved.value = next;
    tx.value = withTiming(clamp(tx.value, next, width), { duration: 200 });
    ty.value = withTiming(clamp(ty.value, next, height), { duration: 200 });
    setZoomed(next > 1.02);
  };
  const doubleTap = Gesture.Tap().numberOfTaps(2).onEnd(() => {
    runOnJS(zoomed ? reset : zoomTo)(zoomed ? 1 : 1.8);
  });
  const gesture = Gesture.Simultaneous(pinch, pan, doubleTap);
  const style2 = useAnimatedStyle(() => ({ transform: [{ translateX: tx.value }, { translateY: ty.value }, { scale: scale.value }] }));

  return (
    <View style={[{ width, height, overflow: "hidden" }, style]} testID={testID}>
      <GestureDetector gesture={gesture}>
        <Animated.View style={[{ width, height }, style2]}>{children}</Animated.View>
      </GestureDetector>
      {controls ? (
        <View style={[{ position: "absolute", right: 6, top: 6, gap: 4 }, controlsStyle]} testID={testID ? `${testID}-zoom-controls` : "zoom-controls"}>
          <Pressable onPress={() => zoomTo(saved.value + 0.5)} style={{ width: 30, height: 30, borderRadius: 6, alignItems: "center", justifyContent: "center", backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }} testID={testID ? `${testID}-zoom-in` : "zoom-in"} hitSlop={6}>
            <Icon name="magnify-plus-outline" size={18} color={colors.goldBright} />
          </Pressable>
          <Pressable onPress={() => zoomTo(saved.value - 0.5)} style={{ width: 30, height: 30, borderRadius: 6, alignItems: "center", justifyContent: "center", backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }} testID={testID ? `${testID}-zoom-out` : "zoom-out"} hitSlop={6}>
            <Icon name="magnify-minus-outline" size={18} color={colors.goldBright} />
          </Pressable>
          {zoomed ? (
            <Pressable onPress={reset} style={{ width: 30, height: 30, borderRadius: 6, alignItems: "center", justifyContent: "center", backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }} testID={testID ? `${testID}-zoom-reset` : "zoom-reset"} hitSlop={6}>
              <Icon name="fit-to-screen-outline" size={18} color={colors.goldBright} />
            </Pressable>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}
