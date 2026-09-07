import { Tabs } from "expo-router";
import React from "react";
import { Platform } from "react-native";

import { useProfile } from "@/src/api/hooks";
import { setActiveSkins } from "@/src/art";
import { fonts, useTheme } from "@/src/theme";
import { Icon, IconName } from "@/src/ui";

const TABS: { name: string; title: string; icon: IconName; sf: string }[] = [
  { name: "battle", title: "Battaglia", icon: "sword-cross", sf: "shield.lefthalf.filled" },
  { name: "kingdom", title: "Regno", icon: "castle", sf: "building.columns" },
  { name: "domain", title: "Dominio", icon: "map", sf: "map" },
  { name: "army", title: "Esercito", icon: "account-group", sf: "person.3" },
  { name: "events", title: "Eventi", icon: "calendar-star", sf: "calendar" },
  { name: "social", title: "Social", icon: "flag", sf: "flag" },
];

export default function TabsLayout() {
  const { colors } = useTheme();
  const { data: profile } = useProfile();
  setActiveSkins(profile?.cosmetics); // keep Lord/Castle skin lookups in sync with the server profile
  const iosVersion = Platform.OS === "ios" ? parseInt(String(Platform.Version), 10) : 0;
  if (Platform.OS === "ios" && iosVersion >= 26) {
    // Liquid-glass native tabs on iOS 26+
    const { NativeTabs, Icon: NIcon, Label } = require("expo-router/unstable-native-tabs");
    return (
      <NativeTabs>
        {TABS.map((t) => (
          <NativeTabs.Trigger key={t.name} name={t.name}>
            <Label>{t.title}</Label>
            <NIcon sf={t.sf} />
          </NativeTabs.Trigger>
        ))}
      </NativeTabs>
    );
  }
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.goldBright,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { backgroundColor: colors.surfaceSecondary, borderTopColor: colors.gold, borderTopWidth: 2, ...(Platform.OS === "web" ? { height: 64 } : {}) },
        tabBarItemStyle: { alignSelf: "center" },
        tabBarLabelStyle: { fontFamily: fonts.bodyBold, fontSize: 11 },
        sceneStyle: { backgroundColor: colors.surface },
      }}
    >
      {TABS.map((t) => (
        <Tabs.Screen key={t.name} name={t.name} options={{ title: t.title, tabBarIcon: ({ color, size }) => <Icon name={t.icon} size={size} color={String(color)} />, tabBarButtonTestID: `tab-${t.name}` }} />
      ))}
    </Tabs>
  );
}
