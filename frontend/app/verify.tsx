import { useRouter } from "expo-router";
import React, { useState } from "react";
import { View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";

import { api } from "@/src/api/client";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Input, Panel, Screen, Txt } from "@/src/ui";
import { useToast } from "@/src/ui/Toast";

export default function Verify() {
  const { user, refreshMe } = useAuth();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const verify = async () => {
    setBusy(true);
    try {
      await api.post("/auth/verify-email", { code: code.trim() });
      await refreshMe();
      toast.show("Email verificata!", "success");
      router.replace("/(tabs)/battle");
    } catch (e: any) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Screen title="Verifica email" subtitle={user?.account.email} scroll={false} testID="verify-screen">
      <KeyboardAwareScrollView contentContainerStyle={{ padding: 16, gap: 12 }} bottomOffset={24}>
        <Panel variant="parchment">
          <View style={{ gap: 12 }}>
            <Txt v="body" color={colors.onSurfaceInverse}>Inserisci il codice a 6 cifre inviato alla tua email. Chat e alleanze richiedono un account verificato; puoi già combattere e costruire.</Txt>
            <Input value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} placeholder="000000" testID="verify-code-input" />
            <Btn title="Verifica" onPress={verify} loading={busy} disabled={code.length !== 6} testID="verify-submit-button" />
            <Btn title="Invia di nuovo il codice" variant="ghost" small onPress={() => api.post("/auth/resend-verification").then(() => toast.show("Codice inviato", "success")).catch((e) => toast.show(e.message, "error"))} testID="verify-resend-button" />
          </View>
        </Panel>
        <Btn title="Più tardi, vai al campo di battaglia" variant="secondary" onPress={() => router.replace("/(tabs)/battle")} testID="verify-skip-button" />
      </KeyboardAwareScrollView>
    </Screen>
  );
}
