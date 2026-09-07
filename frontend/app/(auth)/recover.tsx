import { useRouter } from "expo-router";
import React, { useState } from "react";
import { View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api/client";
import { Btn, Input, Panel, Txt } from "@/src/ui";
import { HeroBackdrop } from "@/src/ui/HeroBackdrop";
import { useToast } from "@/src/ui/Toast";

export default function Recover() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<1 | 2>(1);
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim() });
      toast.show("Se l'indirizzo è registrato riceverai un codice", "info");
      setStep(2);
    } catch (e: any) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  const reset = async () => {
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { email: email.trim(), code: code.trim(), new_password: password });
      toast.show("Password aggiornata. Accedi di nuovo.", "success");
      router.replace("/(auth)/login");
    } catch (e: any) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <HeroBackdrop>
      <KeyboardAwareScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 32, gap: 16 }} bottomOffset={24} testID="recover-screen">
        <Txt v="title">Recupero password</Txt>
        <Panel variant="wood">
          <View style={{ gap: 12 }}>
            <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" testID="recover-email-input" />
            {step === 1 ? <Btn title="Invia codice" onPress={send} loading={busy} disabled={!email} testID="recover-send-button" /> : (
              <>
                <Input label="Codice a 6 cifre" value={code} onChangeText={setCode} keyboardType="number-pad" maxLength={6} testID="recover-code-input" />
                <Input label="Nuova password" value={password} onChangeText={setPassword} secureTextEntry testID="recover-password-input" />
                <Btn title="Imposta nuova password" onPress={reset} loading={busy} disabled={code.length !== 6 || password.length < 10} testID="recover-submit-button" />
              </>
            )}
          </View>
        </Panel>
        <Btn title="Torna al login" variant="ghost" onPress={() => router.replace("/(auth)/login")} testID="recover-back-button" />
      </KeyboardAwareScrollView>
    </HeroBackdrop>
  );
}
