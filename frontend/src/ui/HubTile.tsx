// 3D-art menu tile: generated illustration + scrim + title/subtitle + optional badge. Press = scale-down feedback.
import { LinearGradient } from "expo-linear-gradient";
import React from "react";
import { Image, Pressable, View } from "react-native";
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from "react-native-reanimated";

import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName, Txt } from "@/src/ui";

export function HubTile({ art, icon, title, subtitle, badge, onPress, testID, wide, height = 118, locked }: {
  art?: number; icon: IconName; title: string; subtitle?: string; badge?: number | string | null; onPress: () => void; testID: string; wide?: boolean; height?: number; locked?: boolean;
}) {
  const { colors } = useTheme();
  const scale = useSharedValue(1);
  const anim = useAnimatedStyle(() => ({ transform: [{ scale: scale.get() }] }));
  return (
    <Animated.View style={[{ width: wide ? "100%" : "48%", flexGrow: 1 }, anim]}>
      <Pressable
        onPress={onPress}
        onPressIn={() => { scale.set(withSpring(0.97, { damping: 18, stiffness: 300 })); }}
        onPressOut={() => { scale.set(withSpring(1, { damping: 14, stiffness: 220 })); }}
        testID={testID}
        style={{ height, borderRadius: 10, overflow: "hidden", borderWidth: 1.5, borderColor: colors.gold, backgroundColor: colors.surfaceSecondary }}
      >
        {art ? <Image source={art} style={{ position: "absolute", left: 0, top: 0, right: 0, bottom: 0, width: "100%", height: "100%" }} resizeMode="cover" /> : null}
        <LinearGradient colors={["rgba(0,0,0,0)", "rgba(0,0,0,0.35)", "rgba(0,0,0,0.88)"]} locations={[0, 0.45, 1]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
        {locked ? <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: colors.scrim }} /> : null}
        <View style={{ position: "absolute", top: 6, left: 6, width: 26, height: 26, borderRadius: 13, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold, alignItems: "center", justifyContent: "center" }}>
          <Icon name={locked ? "lock" : icon} size={15} color={colors.goldBright} />
        </View>
        {badge ? (
          <View style={{ position: "absolute", top: 6, right: 6, minWidth: 22, height: 22, paddingHorizontal: 6, borderRadius: 11, backgroundColor: colors.error, borderWidth: 1.5, borderColor: colors.goldBright, alignItems: "center", justifyContent: "center" }} testID={`${testID}-badge`}>
            <Txt v="caption" color={colors.onSurface} style={{ fontFamily: fonts.bodyBold }}>{badge}</Txt>
          </View>
        ) : null}
        <View style={{ position: "absolute", left: 8, right: 8, bottom: 7 }}>
          <Txt v="h3" color={colors.goldBright} style={{ textShadowColor: "#000", textShadowRadius: 4 }} numberOfLines={1}>{title}</Txt>
          {subtitle ? <Txt v="caption" color={colors.onSurface} style={{ textShadowColor: "#000", textShadowRadius: 3 }} numberOfLines={2}>{subtitle}</Txt> : null}
        </View>
      </Pressable>
    </Animated.View>
  );
}
