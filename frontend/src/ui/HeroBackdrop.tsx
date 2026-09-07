// Full-bleed key-art backdrop for auth/splash screens (falls back to the navy gradient when the asset is missing).
import { LinearGradient } from "expo-linear-gradient";
import React from "react";
import { Image, StyleSheet, View } from "react-native";

import { ART } from "@/src/art/manifest";
import { useTheme } from "@/src/theme";

export function HeroBackdrop({ children, testID }: { children: React.ReactNode; testID?: string }) {
  const { colors } = useTheme();
  const art = ART["splash/key_art"];
  return (
    <View style={{ flex: 1, backgroundColor: colors.navy }} testID={testID}>
      {art ? <Image source={art} style={StyleSheet.absoluteFill} resizeMode="cover" /> : null}
      <LinearGradient colors={["rgba(11,15,23,0.15)", "rgba(11,15,23,0.55)", colors.surface]} locations={[0, 0.45, 1]} style={StyleSheet.absoluteFill} />
      {children}
    </View>
  );
}
