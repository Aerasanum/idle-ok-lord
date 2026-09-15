import { Tabs } from "expo-router";
import React from "react";
import { Platform, Text, View } from "react-native";

import { useAchievementAlerts } from "@/src/achievements/useAchievementAlerts";
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
  { name: "war", title: "Guerra", icon: "map-marker-radius", sf: "map.fill" },
  { name: "social", title: "Alleanza", icon: "shield-account", sf: "person.2.badge.shield" },
];

export default function TabsLayout() {
  const { colors } = useTheme();
  const { data: profile } = useProfile();
  setActiveSkins(profile?.cosmetics); // keep Lord/Castle skin lookups in sync with the server profile
  const claimable = useAchievementAlerts(profile?.id); // toast on new claimable achievements + dot on the Eventi tab
  const iosVersion = Platform.OS === "ios" ? parseInt(String(Platform.Version), 10) : 0;
  if (Platform.OS === "ios" && iosVersion >= 26) {
    // Liquid-glass native tabs on iOS 26+. Loaded lazily because the module is
    // unavailable on the other platforms, so a static import would break them.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
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
        tabBarItemStyle: { alignSelf: "center", paddingHorizontal: 0 },
        tabBarAllowFontScaling: false,
        tabBarLabelStyle: { fontFamily: fonts.bodyBold, fontSize: 9.5, letterSpacing: -0.2 },
        sceneStyle: { backgroundColor: colors.surface },
      }}
    >
      {TABS.map((t) => (
        <Tabs.Screen
          key={t.name}
          name={t.name}
          options={{
            title: t.title,
            tabBarIcon: ({ color, size }) => (
              <View>
                <Icon name={t.icon} size={size} color={String(color)} />
                {t.name === "events" && claimable > 0 ? (
                  <View style={{ position: "absolute", top: -3, right: -6, minWidth: 14, height: 14, paddingHorizontal: 3, borderRadius: 7, backgroundColor: colors.error, borderWidth: 1, borderColor: colors.goldBright, alignItems: "center", justifyContent: "center" }} testID="tab-events-dot">
                    <Text style={{ color: colors.onBrandPrimary, fontSize: 9, fontFamily: fonts.bodyBold, lineHeight: 11 }}>{claimable > 9 ? "9+" : claimable}</Text>
                  </View>
                ) : null}
              </View>
            ),
            tabBarButtonTestID: `tab-${t.name}`,
          }}
        />
      ))}
    </Tabs>
  );
}
