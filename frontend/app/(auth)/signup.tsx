import { Link, useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, View } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Input, Panel, Txt } from "@/src/ui";
import { HeroBackdrop } from "@/src/ui/HeroBackdrop";
import { useToast } from "@/src/ui/Toast";

function Check({ value, onChange, label, testID }: { value: boolean; onChange: (v: boolean) => void; label: string; testID: string }) {
  const { colors } = useTheme();
  return (
    <Pressable onPress={() => onChange(!value)} style={{ flexDirection: "row", gap: 10, alignItems: "center", minHeight: 44 }} testID={testID}>
      <Icon name={value ? "checkbox-marked" : "checkbox-blank-outline"} size={22} color={colors.goldBright} />
      <Txt v="small" style={{ flex: 1 }}>{label}</Txt>
    </Pressable>
  );
}

export default function Signup() {
  const { register } = useAuth();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [age, setAge] = useState(false);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await register({ email: email.trim(), password, display_name: name.trim(), age_confirmed: age, consent });
      toast.show("Account creato. Controlla l'email per il codice di verifica.", "success");
      router.replace("/verify");
    } catch (e: any) {
      toast.show(e.message ?? "Registrazione non riuscita", "error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <HeroBackdrop>
      <KeyboardAwareScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 32, paddingBottom: insets.bottom + 24, gap: 16 }} bottomOffset={24} testID="signup-screen">
        <Txt v="title">Nuovo Lord</Txt>
        <Panel variant="wood">
          <View style={{ gap: 12 }}>
            <Input label="Nome del Lord" value={name} onChangeText={setName} testID="signup-name-input" placeholder="3-16 caratteri" maxLength={16} />
            <Input label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" testID="signup-email-input" placeholder="lord@regno.it" />
            <Input label="Password (min 10 caratteri)" value={password} onChangeText={setPassword} secureTextEntry testID="signup-password-input" placeholder="••••••••••" />
            <Check value={age} onChange={setAge} label="Confermo di avere almeno 13 anni" testID="signup-age-checkbox" />
            <Check value={consent} onChange={setConsent} label="Accetto Privacy Policy e Termini di servizio" testID="signup-consent-checkbox" />
            <Btn title="Fonda il tuo Regno" onPress={submit} loading={busy} disabled={!email || !password || !name || !age || !consent} testID="signup-submit-button" />
          </View>
        </Panel>
        <Link href="/(auth)/login" asChild>
          <Btn title="Ho già un account" variant="ghost" testID="signup-login-link" />
        </Link>
      </KeyboardAwareScrollView>
    </HeroBackdrop>
  );
}
