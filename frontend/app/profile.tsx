import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Linking, Pressable, View } from "react-native";

import { api } from "@/src/api/client";
import { QK, useAction, useProfile, usePurchases } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Divider, Input, Loading, Panel, Row, Screen, Stat, Txt, ZoomPill, fmt } from "@/src/ui";
import { useToast } from "@/src/ui/Toast";
import { useTutorial } from "@/src/tutorial/Tutorial";
import { AudioSettings } from "@/src/audio/AudioSettings";

const COLORS = ["#800020", "#1B2A44", "#2E472D", "#B89947", "#5C6470", "#4A6B8C", "#7851A9", "#B0361D"];

export default function ProfileScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const tut = useTutorial();
  const { user, logout, logoutAll, refreshMe } = useAuth();
  const { data: p, isLoading } = useProfile();
  const { data: purchases } = usePurchases();
  const [name, setName] = useState("");
  const [lordName, setLordName] = useState("");
  const [pw, setPw] = useState({ current: "", next: "" });
  const [delPw, setDelPw] = useState("");
  const [confirmDel, setConfirmDel] = useState(false);
  const settings = useAction("patch", "/account/settings", [QK.profile], { success: () => "Salvato" });
  const changePw = useAction("post", "/account/change-password", [], { success: () => "Password cambiata: accedi di nuovo" });
  if (isLoading || !p || !user) return <Loading />;
  const exportData = async () => {
    try {
      const d = await api.get("/account/export");
      toast.show(`Esportazione pronta (${Object.keys(d).length} sezioni, ${d.gear_items.length} oggetti)`, "success");
      console.log("IDLE1 export", JSON.stringify(d).slice(0, 2000));
    } catch (e: any) {
      toast.show(e.message, "error");
    }
  };
  const del = async () => {
    try {
      await api.post("/account/delete", { password: delPw, confirm: "DELETE" });
      toast.show("Account eliminato", "success");
      await logout();
    } catch (e: any) {
      toast.show(e.message, "error");
    }
  };
  const legal = user.legal ?? {};
  return (
    <Screen title="Profilo" subtitle={user.account.email} testID="profile-screen">
      <Panel variant="parchment" testID="profile-summary">
        <Row style={{ justifyContent: "space-around" }}>
          <Stat label="Livello" value={p.hero.level} color={colors.onSurfaceInverse} />
          <Stat label="Stage" value={p.campaign.highest_cleared} color={colors.onSurfaceInverse} />
          <Stat label="Castello" value={p.kingdom.castle_level} color={colors.onSurfaceInverse} />
          <Stat label="Potenza" value={p.combat.total_power} color={colors.onSurfaceInverse} />
        </Row>
        <Txt v="small" color={colors.onSurfaceInverse} style={{ textAlign: "center" }}>Uccisioni {fmt(p.stats.kills)} · Oggetti trovati {p.stats.items_found} · Leggendari+ {p.stats.legendary_or_higher_items_found} · Truppe reclutate {fmt(p.stats.units_recruited_total)}</Txt>
      </Panel>
      <Panel testID="identity-panel">
        <Txt v="h3">Identità</Txt>
        <Txt v="caption" style={{ marginTop: 4 }}>Nome giocatore · visibile in alleanze, chat e guerre</Txt>
        <Row>
          <Input placeholder={p.display_name} value={name} onChangeText={setName} maxLength={16} style={{ flex: 1 }} testID="display-name-input" />
          <Btn title="Rinomina" small disabled={name.trim().length < 3} onPress={() => settings.mutate({ display_name: name.trim() }, { onSuccess: () => { setName(""); refreshMe(); } })} testID="rename-button" />
        </Row>
        <Txt v="caption" style={{ marginTop: 8 }}>Nome del Lord · il tuo eroe in battaglia</Txt>
        <Row>
          <Input placeholder={p.hero.name ?? "Lord"} value={lordName} onChangeText={setLordName} maxLength={16} style={{ flex: 1 }} testID="lord-name-input" />
          <Btn title="Rinomina" small disabled={lordName.trim().length < 3} onPress={() => settings.mutate({ lord_name: lordName.trim() }, { onSuccess: () => setLordName("") })} testID="rename-lord-profile-button" />
        </Row>
        <Txt v="caption" style={{ marginTop: 8 }}>Colore araldico</Txt>
        <Row style={{ flexWrap: "wrap" }}>{COLORS.map((c) => <Pressable key={c} onPress={() => settings.mutate({ heraldic_color: c })} style={{ width: 36, height: 36, backgroundColor: c, borderWidth: p.heraldic_color === c ? 3 : 1, borderColor: p.heraldic_color === c ? colors.goldBright : colors.iron, borderRadius: 4 }} testID={`color-${c.slice(1)}`} />)}</Row>
        {p.cosmetics?.owned?.length ? <Txt v="small" color={colors.muted}>Cosmetici: {p.cosmetics.owned.join(", ")}</Txt> : null}
      </Panel>
      <Panel testID="settings-panel">
        <Txt v="h3">Impostazioni</Txt>
        <AudioSettings />
        <View style={{ height: 1, backgroundColor: colors.wood, marginVertical: 8, opacity: 0.6 }} />
        <Row style={{ justifyContent: "space-between" }} testID="ui-zoom-setting">
          <View style={{ flex: 1 }}><Txt v="body">Zoom interfaccia</Txt><Txt v="small" color={colors.muted}>Ingrandisce testi e pannelli in tutte le pagine (anche con due dita). Le scene si zoomano con pinch o i pulsanti +/−.</Txt></View>
          <ZoomPill testID="ui-zoom-profile" />
        </Row>
        <View style={{ height: 1, backgroundColor: colors.wood, marginVertical: 8, opacity: 0.6 }} />
        <Row style={{ justifyContent: "space-between" }}>
          <Txt v="body">Notifiche non essenziali (eventi, forziere pieno)</Txt>
          <Btn title={p.settings.push_nonessential ? "ON" : "OFF"} small variant={p.settings.push_nonessential ? "gold" : "secondary"} onPress={() => settings.mutate({ push_nonessential: !p.settings.push_nonessential })} testID="push-toggle" />
        </Row>
        <Row style={{ justifyContent: "space-between", marginTop: 6 }}>
          <Txt v="body">Analisi anonime (opt-in)</Txt>
          <Btn title={p.settings.analytics ? "ON" : "OFF"} small variant={p.settings.analytics ? "gold" : "secondary"} onPress={() => settings.mutate({ analytics: !p.settings.analytics })} testID="analytics-toggle" />
        </Row>
        <Divider />
        {user.account.providers.includes("email_password") ? (
          <View style={{ gap: 6 }}>
            <Txt v="caption">Cambia password</Txt>
            <Input placeholder="Password attuale" secureTextEntry value={pw.current} onChangeText={(v) => setPw({ ...pw, current: v })} testID="current-password-input" />
            <Input placeholder="Nuova password (min 10)" secureTextEntry value={pw.next} onChangeText={(v) => setPw({ ...pw, next: v })} testID="new-password-input" />
            <Btn title="Aggiorna password" small variant="secondary" disabled={pw.next.length < 10 || !pw.current} onPress={() => changePw.mutate({ current_password: pw.current, new_password: pw.next }, { onSuccess: () => logout() })} testID="change-password-button" />
          </View>
        ) : null}
        {!user.account.email_verified ? <Btn title="Verifica email" small variant="ghost" onPress={() => router.push("/verify")} testID="profile-verify-button" /> : null}
        <Btn title="Rivedi il tutorial" small variant="ghost" icon="school" onPress={() => tut.start()} testID="replay-tutorial-button" />
        <Btn title="La tua vetrina pubblica" small variant="gold" icon="account-star" onPress={() => router.push({ pathname: "/player/[id]", params: { id: user?.player_id ?? "" } })} testID="my-showcase-button" />
        <Btn title="Regolamento completo (PDF)" small variant="secondary" icon="book-open-page-variant" onPress={() => Linking.openURL(`${process.env.EXPO_PUBLIC_BACKEND_URL}/api/docs/regolamento.pdf`)} testID="rules-pdf-button" />
        <Txt v="small" color={colors.muted}>Regole, unità e contro-unità, costi e tempi di edifici, ricerche, XP eroe, equipaggiamento e guerre: tutto ciò che il server applica.</Txt>
      </Panel>
      <Panel variant="wood" testID="privacy-panel">
        <Txt v="h3">Privacy & Account</Txt>
        <Txt v="small" color={colors.muted}>Età minima {legal.min_age} anni · consenso registrato · nessuna vendita di dati · analisi solo opt-in.</Txt>
        <Row style={{ marginTop: 6, flexWrap: "wrap" }}>
          <Btn title="Privacy Policy" small variant="ghost" onPress={() => (legal.privacy_policy_url ? Linking.openURL(legal.privacy_policy_url) : toast.show("URL Privacy Policy: input del proprietario ancora mancante", "info"))} testID="privacy-link" />
          <Btn title="Termini" small variant="ghost" onPress={() => (legal.terms_url ? Linking.openURL(legal.terms_url) : toast.show("URL Termini: input del proprietario ancora mancante", "info"))} testID="terms-link" />
          <Btn title="Esporta i miei dati" small variant="secondary" icon="download" onPress={exportData} testID="export-button" />
        </Row>
        <Txt v="caption" style={{ marginTop: 8 }}>Acquisti</Txt>
        {(purchases?.purchases ?? []).slice(0, 5).map((x: any) => <Txt key={x.id} v="small" color={colors.muted}>{x.sku ?? x.item} · {x.status ?? x.kind} · {new Date(x.created_at).toLocaleDateString("it-IT")}</Txt>)}
        {!purchases?.purchases?.length ? <Txt v="small" color={colors.muted}>Nessun acquisto registrato.</Txt> : null}
        <Divider />
        <Row>
          <Btn title="Esci" small variant="secondary" icon="logout" onPress={logout} testID="logout-button" />
          <Btn title="Esci da tutti i dispositivi" small variant="secondary" onPress={logoutAll} testID="logout-all-button" />
        </Row>
        <Divider />
        {!confirmDel ? <Btn title="Elimina account" small variant="danger" icon="delete-forever" onPress={() => setConfirmDel(true)} testID="delete-account-button" /> : (
          <View style={{ gap: 6 }}>
            <Txt v="small" color={colors.error}>Irreversibile: profilo, inventario e chat vengono rimossi; i record di acquisto restano solo per la riconciliazione con gli store.</Txt>
            {user.account.providers.includes("email_password") ? <Input placeholder="Conferma password" secureTextEntry value={delPw} onChangeText={setDelPw} testID="delete-password-input" /> : null}
            <Row><Btn title="Conferma eliminazione" small variant="danger" onPress={del} testID="confirm-delete-button" /><Btn title="Annulla" small variant="ghost" onPress={() => setConfirmDel(false)} testID="cancel-delete-button" /></Row>
          </View>
        )}
      </Panel>
    </Screen>
  );
}
