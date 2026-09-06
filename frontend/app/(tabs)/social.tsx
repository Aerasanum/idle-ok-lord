import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { QK, useAction, useAlliances, useMyAlliance, useProfile } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Icon, IconName, Input, Loading, Panel, ResourceBar, Row, Txt, fmt } from "@/src/ui";

export default function SocialTab() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const { data: profile } = useProfile();
  const { data: mine, isLoading } = useMyAlliance();
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [tag, setTag] = useState("");
  const [mode, setMode] = useState("open");
  const { data: list } = useAlliances(q);
  const create = useAction("post", "/alliances", [QK.alliance, QK.alliances], { success: () => "Alleanza fondata!" });
  const join = useAction("post", "/alliances/join", [QK.alliance, QK.alliances], { success: (d) => (d.applied ? "Candidatura inviata" : "Sei entrato nell'alleanza") });
  if (isLoading || !profile) return <Loading />;
  const a = mine?.alliance;
  const verified = user?.account.email_verified;
  const castleOk = profile.kingdom.castle_level >= 8;
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="social-screen">
      <View style={{ paddingTop: insets.top, backgroundColor: colors.surfaceSecondary }}>
        <ResourceBar resources={profile.resources} compact />
      </View>
      <ScrollView contentContainerStyle={{ padding: 12, paddingBottom: 24, gap: 12 }} showsVerticalScrollIndicator={false}>
        <Txt v="h1">Alleanza & Guerra</Txt>
        {a ? (
          <Panel variant="parchment" testID="my-alliance-card">
            <Row style={{ justifyContent: "space-between" }}>
              <View>
                <Txt v="h2" color={colors.onSurfaceInverse}>[{a.tag}] {a.name}</Txt>
                <Txt v="small" color={colors.onSurfaceInverse}>{a.member_count}/{a.member_cap} membri · {a.season_points} punti stagione · ruolo: {a.my_role}</Txt>
              </View>
              <Icon name="shield-crown" size={32} color={colors.burgundy} />
            </Row>
            <Btn title="Apri alleanza" small variant="gold" onPress={() => router.push("/alliance")} style={{ marginTop: 8 }} testID="open-alliance-button" />
          </Panel>
        ) : (
          <Panel variant="wood" testID="no-alliance-card">
            <Txt v="h3">Nessuna alleanza</Txt>
            <Txt v="small" color={colors.muted}>{!castleOk ? "Le alleanze si sbloccano al Castello 8." : !verified ? "Verifica l'email per entrare o fondare un'alleanza." : "Unisciti a un'alleanza o fondane una (5000 Oro)."}</Txt>
            {castleOk && verified ? <Btn title={creating ? "Chiudi" : "Fonda un'alleanza"} small variant="ghost" onPress={() => setCreating(!creating)} style={{ marginTop: 8 }} testID="toggle-create-alliance" /> : null}
            {creating ? (
              <View style={{ gap: 8, marginTop: 8 }}>
                <Input label="Nome (3-20)" value={name} onChangeText={setName} testID="alliance-name-input" />
                <Input label="Tag (2-4)" value={tag} onChangeText={setTag} maxLength={4} autoCapitalize="characters" testID="alliance-tag-input" />
                <Row>{["open", "application", "invite_only"].map((m) => <Pressable key={m} onPress={() => setMode(m)} style={{ paddingHorizontal: 10, height: 36, justifyContent: "center", borderRadius: 999, borderWidth: 1, borderColor: mode === m ? colors.goldBright : colors.iron, backgroundColor: mode === m ? colors.brandPrimary : colors.surfaceTertiary }} testID={`join-mode-${m}`}><Txt v="small">{m}</Txt></Pressable>)}</Row>
                <Btn title="Fonda (5000 Oro)" loading={create.isPending} disabled={name.length < 3 || tag.length < 2} onPress={() => create.mutate({ name, tag, join_mode: mode, description: "", language: "it" })} testID="create-alliance-button" />
              </View>
            ) : null}
          </Panel>
        )}
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          <Hub icon="chat" label="Chat" onPress={() => router.push("/alliance/chat")} testID="hub-chat" />
          <Hub icon="map-marker-radius" label="Mappa guerra" onPress={() => router.push("/alliance/war")} testID="hub-war" />
          <Hub icon="skull-crossbones" label="Titan Hunt" onPress={() => router.push("/alliance/boss")} testID="hub-boss" />
          <Hub icon="calendar-star" label="Eventi" onPress={() => router.push("/events")} testID="hub-events" />
        </View>
        <Txt v="h2">Alleanze</Txt>
        <Input placeholder="Cerca per nome" value={q} onChangeText={setQ} testID="alliance-search-input" />
        {(list?.alliances ?? []).map((al: any) => (
          <Panel key={al.id} testID={`alliance-row-${al.id}`}>
            <Row style={{ justifyContent: "space-between" }}>
              <View style={{ flex: 1 }}>
                <Txt v="h3">[{al.tag}] {al.name}</Txt>
                <Txt v="small" color={colors.muted}>{al.member_count}/30 · {fmt(al.season_points)} pt · {al.join_mode} · {al.language}</Txt>
              </View>
              {!a && al.join_mode !== "invite_only" ? <Btn title={al.join_mode === "open" ? "Entra" : "Candidati"} small disabled={!castleOk || !verified} loading={join.isPending} onPress={() => join.mutate({ id: al.id })} testID={`join-${al.id}`} /> : null}
              {a ? <Btn title="Vedi" small variant="ghost" onPress={() => router.push({ pathname: "/alliance", params: { id: al.id } })} testID={`view-${al.id}`} /> : null}
            </Row>
          </Panel>
        ))}
        {!list?.alliances?.length ? <Txt v="small" color={colors.muted}>Nessuna alleanza trovata.</Txt> : null}
      </ScrollView>
    </View>
  );
}

function Hub({ icon, label, onPress, testID }: { icon: IconName; label: string; onPress: () => void; testID: string }) {
  const { colors } = useTheme();
  return (
    <Pressable onPress={onPress} testID={testID} style={({ pressed }) => ({ width: "47%", flexGrow: 1, minHeight: 64, backgroundColor: colors.surfaceSecondary, borderWidth: 1.5, borderColor: colors.wood, borderRadius: 6, alignItems: "center", justifyContent: "center", gap: 4, opacity: pressed ? 0.8 : 1 })}>
      <Icon name={icon} size={22} color={colors.goldBright} />
      <Txt v="small">{label}</Txt>
    </Pressable>
  );
}
