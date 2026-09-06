import { LinearGradient } from "expo-linear-gradient";
import { Link, useRouter } from "expo-router";
import React, { useState } from "react";
import { Platform, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Input, Panel, Txt } from "@/src/ui";
import { useToast } from "@/src/ui/Toast";

export default function Login() {
  const { login, googleLogin } = useAuth();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await login(email.trim(), password);
      router.replace("/");
    } catch (e: any) {
      toast.show(e.message ?? "Accesso non riuscito", "error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <LinearGradient colors={[colors.navy, colors.surface]} style={{ flex: 1 }}>
      <KeyboardAwareScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 48, paddingBottom: insets.bottom + 24, gap: 16 }} bottomOffset={24} testID="login-screen">
        <View style={{ alignItems: "center", gap: 6, marginBottom: 12 }}>
          <Txt v="title">IDLE 1</Txt>
          <Txt v="caption">Un guerriero. Un impero.</Txt>
        </View>
        <Panel variant="wood">
          <View style={{ gap: 12 }}>
            <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" testID="login-email-input" placeholder="lord@regno.it" />
            <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="password" testID="login-password-input" placeholder="••••••••••" onSubmitEditing={submit} />
            <Btn title="Entra nel Regno" onPress={submit} loading={busy} disabled={!email || !password} testID="login-submit-button" />
            <Link href="/(auth)/recover" asChild>
              <Btn title="Password dimenticata" variant="ghost" small testID="login-forgot-button" />
            </Link>
          </View>
        </Panel>
        <Btn title="Continua con Google" variant="secondary" icon="google" onPress={() => googleLogin().catch((e) => toast.show(e.message, "error"))} testID="login-google-button" />
        <Btn title={Platform.OS === "ios" ? "Sign in with Apple (richiede account Apple Developer)" : "Sign in with Apple (solo iOS)"} variant="secondary" icon="apple" disabled testID="login-apple-button" />
        <Link href="/(auth)/signup" asChild>
          <Btn title="Crea un nuovo account" variant="gold" testID="login-signup-link" />
        </Link>
      </KeyboardAwareScrollView>
    </LinearGradient>
  );
}
