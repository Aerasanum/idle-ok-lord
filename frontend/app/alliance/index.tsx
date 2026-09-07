import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useMyAlliance } from "@/src/api/hooks";
import { api } from "@/src/api/client";
import { useQuery } from "@tanstack/react-query";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Input, Loading, Panel, Row, Screen, Txt, fmt } from "@/src/ui";

export default function AllianceScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { data: mine, isLoading } = useMyAlliance();
  const other = useQuery({ queryKey: ["alliance", id], queryFn: () => api.get(`/alliances/${id}`), enabled: !!id });
  const [gold, setGold] = useState("500");
  const leave = useAction("post", "/alliances/leave", [QK.alliance, QK.alliances], { success: () => "Hai lasciato l'alleanza" });
  const member = useAction("post", "/alliances/members", [QK.alliance], { success: (d) => `Azione ${d.action} eseguita` });
  const decide = useAction("post", "/alliances/applications/decide", [QK.alliance], { success: () => "Candidatura gestita" });
  const donate = useAction("post", "/alliances/donate", [QK.alliance, QK.quests], { success: (d) => `Donati ${d.donated} Oro` });
  const settings = useAction("patch", "/alliances/settings", [QK.alliance], { success: () => "Impostazioni aggiornate" });
  if (isLoading) return <Loading />;
  const a = id ? other.data?.alliance : mine?.alliance;
  if (!a) return <Screen title="Alleanza" testID="alliance-screen"><Txt v="body">Nessuna alleanza. Unisciti o fondane una dalla scheda Social.</Txt></Screen>;
  const me = a.my_role;
  const officer = me === "leader" || me === "officer";
  return (
    <Screen title={`[${a.tag}] ${a.name}`} subtitle={`${a.member_count}/${a.member_cap} membri · ${fmt(a.season_points)} punti stagione · ${a.join_mode}`} testID="alliance-screen">
      <Panel variant="parchment">
        <Txt v="body" color={colors.onSurfaceInverse}>{a.description || "Nessuna descrizione."}</Txt>
        <Txt v="small" color={colors.onSurfaceInverse}>Tesoreria {fmt(a.treasury_gold)} Oro · Guerre {a.lifetime?.wars_won}V/{a.lifetime?.wars_lost}S · Titani {a.lifetime?.bosses_killed}</Txt>
      </Panel>
      {me ? (
        <Row>
          <Btn title="Chat" small icon="chat" onPress={() => router.push("/alliance/chat")} testID="alliance-chat-button" />
          <Btn title="Guerra" small icon="map-marker-radius" variant="secondary" onPress={() => router.push("/alliance/war")} testID="alliance-war-button" />
          <Btn title="Titan Hunt" small icon="skull-crossbones" variant="secondary" onPress={() => router.push("/alliance/boss")} testID="alliance-boss-button" />
        </Row>
      ) : null}
      {me ? (
        <Panel variant="wood" testID="donate-panel">
          <Txt v="h3">Dona alla tesoreria</Txt>
          <Row>
            <Input value={gold} onChangeText={setGold} keyboardType="number-pad" style={{ flex: 1 }} testID="donate-input" />
            <Btn title="Dona" small onPress={() => donate.mutate({ gold: parseInt(gold || "0", 10) })} loading={donate.isPending} testID="donate-button" />
          </Row>
        </Panel>
      ) : null}
      {officer ? (
        <Panel testID="alliance-settings">
          <Txt v="h3">Modalità di ingresso</Txt>
          <Row>{["open", "application", "invite_only"].map((m) => <Btn key={m} title={m} small variant={a.join_mode === m ? "gold" : "secondary"} onPress={() => settings.mutate({ join_mode: m })} testID={`set-join-${m}`} />)}</Row>
          {a.applications?.length ? (
            <View style={{ marginTop: 8, gap: 6 }}>
              <Txt v="caption">Candidature</Txt>
              {a.applications.map((ap: any) => (
                <Row key={ap.id} style={{ justifyContent: "space-between" }} testID={`application-${ap.player_id}`}>
                  <Txt v="body">{ap.display_name}</Txt>
                  <Row><Btn title="Accetta" small onPress={() => decide.mutate({ player_id: ap.player_id, accept: true })} /><Btn title="Rifiuta" small variant="danger" onPress={() => decide.mutate({ player_id: ap.player_id, accept: false })} /></Row>
                </Row>
              ))}
            </View>
          ) : null}
        </Panel>
      ) : null}
      <Txt v="h2">Membri</Txt>
      {a.members.map((m: any) => (
        <Panel key={m.player_id} testID={`member-${m.player_id}`}>
          <Row style={{ justifyContent: "space-between" }}>
            <Icon name={m.role === "leader" ? "crown" : m.role === "officer" ? "shield-star" : "account"} size={20} color={m.role === "member" ? colors.muted : colors.goldBright} />
            <Pressable style={{ flex: 1 }} onPress={() => router.push({ pathname: "/player/[id]", params: { id: m.player_id } })} testID={`showcase-${m.player_id}`}>
              <Txt v="bodyBold">{m.display_name} · Lv {m.hero_level}</Txt>
              <Txt v="small" color={colors.muted}>Castello {m.castle_level} · stage {m.highest_cleared} · {m.role} · donati {fmt(m.donated_gold)} · tocca per la vetrina</Txt>
            </Pressable>
            {me === "leader" && m.role !== "leader" ? (
              <Row gap={4}>
                <Btn title={m.role === "member" ? "↑" : "↓"} small variant="ghost" onPress={() => member.mutate({ player_id: m.player_id, action: m.role === "member" ? "promote" : "demote" })} testID={`promote-${m.player_id}`} />
                <Btn title="Leader" small variant="ghost" onPress={() => member.mutate({ player_id: m.player_id, action: "transfer" })} testID={`transfer-${m.player_id}`} />
                <Btn title="✕" small variant="danger" onPress={() => member.mutate({ player_id: m.player_id, action: "kick" })} testID={`kick-${m.player_id}`} />
              </Row>
            ) : officer && m.role === "member" && me !== "leader" ? <Btn title="✕" small variant="danger" onPress={() => member.mutate({ player_id: m.player_id, action: "kick" })} testID={`kick-${m.player_id}`} /> : null}
          </Row>
        </Panel>
      ))}
      {me ? <Btn title="Lascia l'alleanza" variant="danger" onPress={() => leave.mutate({})} testID="leave-alliance-button" /> : null}
    </Screen>
  );
}
