import { LinearGradient } from "expo-linear-gradient";
import { Redirect } from "expo-router";
import React from "react";
import { ActivityIndicator } from "react-native";

import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Txt } from "@/src/ui";

export default function Index() {
  const { loading, user } = useAuth();
  const { colors } = useTheme();
  if (loading) {
    return (
      <LinearGradient colors={[colors.navy, colors.surface]} style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 16 }} testID="splash-screen">
        <Txt v="title">IDLE 1</Txt>
        <Txt v="caption">Da guerriero solitario a Lord di un impero</Txt>
        <ActivityIndicator color={colors.goldBright} />
      </LinearGradient>
    );
  }
  if (!user) return <Redirect href="/(auth)/login" />;
  if (user.needs_consent) return <Redirect href="/onboarding" />;
  return <Redirect href="/(tabs)/battle" />;
}
