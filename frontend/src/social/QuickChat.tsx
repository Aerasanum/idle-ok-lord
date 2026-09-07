// Quick global chat: last messages + inline composer, without leaving the Social tab.
import { useRouter } from "expo-router";
import React, { useState } from "react";
import { Pressable, View } from "react-native";

import { useAction, useChat } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Input, Panel, Row, Txt } from "@/src/ui";

const CHANNEL = "global:it";

export function QuickChat() {
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const { data } = useChat(CHANNEL);
  const send = useAction("post", "/chat/messages", [["chat", CHANNEL]]);
  const [text, setText] = useState("");
  const verified = user?.account.email_verified;
  const msgs: any[] = (data?.messages ?? []).slice(-4);
  const submit = () => {
    const t = text.trim();
    if (!t) return;
    send.mutate({ channel: CHANNEL, text: t }, { onSuccess: () => setText("") });
  };
  return (
    <Panel testID="quick-chat">
      <Row style={{ justifyContent: "space-between" }}>
        <Row style={{ gap: 6 }}>
          <Icon name="earth" size={18} color={colors.goldBright} />
          <Txt v="h3">Chat globale</Txt>
        </Row>
        <Btn title="Apri chat" small variant="ghost" icon="chat" onPress={() => router.push("/alliance/chat")} testID="quick-chat-open" />
      </Row>
      <View style={{ gap: 6, marginTop: 6 }} testID="quick-chat-messages">
        {msgs.length === 0 ? <Txt v="small" color={colors.muted}>Nessun messaggio: scrivi tu il primo.</Txt> : null}
        {msgs.map((m) => (
          <Pressable key={m.id} onPress={() => router.push("/alliance/chat")} style={{ flexDirection: "row", gap: 6, alignItems: "flex-start" }} testID={`quick-message-${m.id}`}>
            <Txt v="small" color={m.player_id === user?.player_id ? colors.goldBright : colors.muted} style={{ maxWidth: 110 }} numberOfLines={1}>{m.display_name}</Txt>
            <Txt v="small" style={{ flex: 1 }} numberOfLines={2}>{m.text}</Txt>
            <Txt v="caption" color={colors.muted}>{new Date(m.created_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</Txt>
          </Pressable>
        ))}
      </View>
      <Row style={{ marginTop: 8, gap: 6 }}>
        <Input value={text} onChangeText={setText} placeholder={verified ? "Scrivi a tutti…" : "Verifica l'email per scrivere"} editable={!!verified} maxLength={300} style={{ flex: 1 }} onSubmitEditing={submit} returnKeyType="send" testID="quick-chat-input" />
        <Btn title="" icon="send" small disabled={!verified || !text.trim()} loading={send.isPending} onPress={submit} testID="quick-chat-send" />
      </Row>
    </Panel>
  );
}
