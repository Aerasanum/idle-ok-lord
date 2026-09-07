import { Redirect } from "expo-router";
import React from "react";
import { ActivityIndicator, View } from "react-native";

import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Txt } from "@/src/ui";
import { HeroBackdrop } from "@/src/ui/HeroBackdrop";

export default function Index() {
  const { loading, user } = useAuth();
  const { colors } = useTheme();
  if (loading) {
    return (
      <HeroBackdrop testID="splash-screen">
        <View style={{ flex: 1, alignItems: "center", justifyContent: "flex-end", gap: 12, paddingBottom: 96 }}>
          <Txt v="title">IDLE 1</Txt>
          <Txt v="caption">Da guerriero solitario a Lord di un impero</Txt>
          <ActivityIndicator color={colors.goldBright} />
        </View>
      </HeroBackdrop>
    );
  }
  if (!user) return <Redirect href="/(auth)/login" />;
  if (user.needs_consent) return <Redirect href="/onboarding" />;
  return <Redirect href="/(tabs)/battle" />;
}
