import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Panel, Txt } from "@/src/ui";
import { useToast } from "@/src/ui/Toast";

const STEPS = [
  { icon: "sword", title: "Un solo guerriero", text: "Inizi da solo. Ogni stage vinto ti rende più forte: XP, oro, equipaggiamento." },
  { icon: "castle", title: "Un Regno che cresce", text: "Costruisci, ricerca, recluta. Il Castello sblocca edifici, formazioni ed alleanze." },
  { icon: "account-group", title: "Un esercito enorme", text: "Dispiega infanteria, cavalleria, bestie e creature mitiche. L'esercito domina la campagna." },
  { icon: "flag", title: "Alleanze e guerre", text: "Guerre asincrone 10v10, territorio 19x19, Titan Hunt. Tutto calcolato dal server." },
];

export default function Onboarding() {
  const { user, refreshMe } = useAuth();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const [age, setAge] = useState(false);
  const [busy, setBusy] = useState(false);
  const needsConsent = !!user?.needs_consent;
  const finish = async () => {
    if (needsConsent) {
      setBusy(true);
      try {
        await api.post("/account/consent", { age_confirmed: age });
        await refreshMe();
      } catch (e: any) {
        toast.show(e.message, "error");
        setBusy(false);
        return;
      }
    }
    router.replace("/(tabs)/battle");
  };
  return (
    <LinearGradient colors={[colors.navy, colors.surface]} style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 32, paddingBottom: insets.bottom + 24, gap: 14 }} testID="onboarding-screen">
        <Txt v="title">Benvenuto, Lord</Txt>
        {STEPS.map((s) => (
          <Panel key={s.title} variant="wood">
            <View style={{ flexDirection: "row", gap: 12, alignItems: "center" }}>
              <Icon name={s.icon as any} size={30} color={colors.goldBright} />
              <View style={{ flex: 1 }}>
                <Txt v="h3">{s.title}</Txt>
                <Txt v="small" color={colors.muted}>{s.text}</Txt>
              </View>
            </View>
          </Panel>
        ))}
        {needsConsent ? (
          <Pressable onPress={() => setAge(!age)} style={{ flexDirection: "row", gap: 10, alignItems: "center", minHeight: 44 }} testID="onboarding-consent-checkbox">
            <Icon name={age ? "checkbox-marked" : "checkbox-blank-outline"} size={22} color={colors.goldBright} />
            <Txt v="small" style={{ flex: 1 }}>Confermo di avere almeno 13 anni e accetto Privacy Policy e Termini</Txt>
          </Pressable>
        ) : null}
        <Btn title="Inizia la campagna" onPress={finish} loading={busy} disabled={needsConsent && !age} testID="onboarding-start-button" />
      </ScrollView>
    </LinearGradient>
  );
}
