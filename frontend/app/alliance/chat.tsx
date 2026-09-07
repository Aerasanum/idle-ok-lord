import { useRouter } from "expo-router";
import React, { useMemo, useRef, useState } from "react";
import { FlatList, Pressable, View } from "react-native";
import { KeyboardAwareScrollView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAction, useChat, useMyAlliance, useWars } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { useTheme } from "@/src/theme";
import { Btn, Chip, ChipRow, Icon, Input, Row, Screen, Txt } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";

export default function ChatScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const { data: mine } = useMyAlliance();
  const { data: wars } = useWars();
  const a = mine?.alliance;
  const channels = useMemo(() => {
    const out = [{ key: "global:it", label: "Globale" }];
    if (a) out.push({ key: `alliance:${a.id}`, label: "Alleanza" }, { key: `system:${a.id}`, label: "Feed" });
    for (const w of wars?.wars ?? []) if (["prep", "locked", "resolved"].includes(w.status) && !(w.archived_at && new Date(w.archived_at) < new Date())) out.push({ key: `war:${w.id}`, label: `Guerra ${w.node_id}` });
    return out;
  }, [a, wars]);
  const [channel, setChannel] = useState(channels[0].key);
  const [text, setText] = useState("");
  const [sel, setSel] = useState<any>(null);
  const sheet = useRef<SheetRef>(null);
  const { data } = useChat(channel);
  const send = useAction("post", "/chat/messages", [["chat", channel]], { silent: false });
  const moderate = useAction("post", "/chat/moderate", [["chat", channel]], { success: (d) => Object.keys(d)[0] });
  const verified = user?.account.email_verified;
  const readOnly = channel.startsWith("system:");
  const officer = a?.my_role === "leader" || a?.my_role === "officer";
  return (
    <Screen title="Chat" subtitle={verified ? "Sii cortese: segnala e blocca chi non lo è" : "Verifica l'email per scrivere"} scroll={false} testID="chat-screen">
      <ChipRow>{channels.map((c) => <Chip key={c.key} label={c.label} selected={channel === c.key} onPress={() => setChannel(c.key)} testID={`channel-${c.label}`} />)}</ChipRow>
      <FlatList
        data={data?.messages ?? []}
        keyExtractor={(m: any) => m.id}
        contentContainerStyle={{ padding: 12, gap: 8, paddingBottom: 90 }}
        renderScrollComponent={(props) => <KeyboardAwareScrollView {...props} />}
        renderItem={({ item: m }: any) => m.system && m.kind ? (
          <View style={{ alignSelf: "stretch", flexDirection: "row", gap: 8, alignItems: "center", backgroundColor: colors.surfaceTertiary, borderWidth: 1.5, borderColor: m.kind === "titan" ? colors.brandPrimary : colors.gold, borderLeftWidth: 5, borderRadius: 8, padding: 8 }} testID={`message-${m.id}`}>
            <Icon name={m.kind === "titan" ? "paw" : "sword-cross"} size={20} color={colors.goldBright} />
            <View style={{ flex: 1 }}>
              <Txt v="caption" color={colors.goldBright}>{m.display_name} · {new Date(m.created_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</Txt>
              <Txt v="bodyBold">{m.text}</Txt>
            </View>
          </View>
        ) : (
          <Pressable onLongPress={() => { if (!m.system) { setSel(m); sheet.current?.present(); } }} style={{ alignSelf: m.player_id === user?.player_id ? "flex-end" : "flex-start", maxWidth: "85%", backgroundColor: m.system ? colors.surfaceTertiary : m.player_id === user?.player_id ? colors.brandPrimary : colors.surfaceSecondary, borderWidth: 1, borderColor: m.system ? colors.iron : colors.wood, borderRadius: 8, padding: 8 }} testID={`message-${m.id}`}>
            <Txt v="caption" color={m.system ? colors.goldBright : colors.muted}>{m.display_name} · {new Date(m.created_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</Txt>
            <Txt v="body">{m.text}</Txt>
          </Pressable>
        )}
        ListEmptyComponent={<Txt v="small" color={colors.muted} style={{ textAlign: "center", marginTop: 24 }}>Nessun messaggio.</Txt>}
      />
      <KeyboardStickyView offset={{ closed: 0, opened: insets.bottom }}>
        <View style={{ padding: 10, paddingBottom: insets.bottom + 10, backgroundColor: colors.surfaceSecondary, borderTopWidth: 2, borderColor: colors.gold }}>
          <Row>
            <Input value={text} onChangeText={setText} placeholder={readOnly ? "Canale di sola lettura" : "Messaggio (max 300)"} maxLength={300} editable={!!verified && !readOnly} style={{ flex: 1 }} testID="chat-input" onSubmitEditing={() => text.trim() && send.mutate({ channel, text }, { onSuccess: () => setText("") })} />
            <Pressable testID="chat-send-button" disabled={!text.trim() || !verified || readOnly || send.isPending} onPress={() => send.mutate({ channel, text }, { onSuccess: () => setText("") })} style={{ width: 48, height: 48, alignItems: "center", justifyContent: "center", backgroundColor: colors.brandPrimary, borderRadius: 6, borderWidth: 2, borderColor: colors.gold, opacity: text.trim() && verified ? 1 : 0.5 }}>
              <Icon name="send" color={colors.onBrandPrimary} />
            </Pressable>
          </Row>
        </View>
      </KeyboardStickyView>
      <Sheet ref={sheet} title={sel ? `Messaggio di ${sel.display_name}` : ""} snap={["40%"]} testID="moderation-sheet">
        {sel ? (
          <View style={{ gap: 8 }}>
            <Btn title="Vedi la vetrina del giocatore" icon="account-star" variant="gold" onPress={() => { sheet.current?.dismiss(); router.push({ pathname: "/player/[id]", params: { id: sel.player_id } }); }} testID="showcase-button" />
            <Btn title="Segnala messaggio" icon="flag" variant="secondary" onPress={() => moderate.mutate({ action: "report", message_id: sel.id, reason: "inappropriate" }, { onSuccess: () => sheet.current?.dismiss() })} testID="report-button" />
            {sel.player_id !== user?.player_id ? <Btn title="Blocca utente" icon="account-cancel" variant="danger" onPress={() => moderate.mutate({ action: "block", target_id: sel.player_id }, { onSuccess: () => sheet.current?.dismiss() })} testID="block-button" /> : null}
            {officer && !channel.startsWith("global") ? <Btn title="Elimina (moderatore)" icon="delete" variant="ghost" onPress={() => moderate.mutate({ action: "delete", message_id: sel.id }, { onSuccess: () => sheet.current?.dismiss() })} testID="delete-button" /> : null}
            {officer && channel.startsWith("alliance") && sel.player_id !== user?.player_id ? <Btn title="Silenzia 60 min" icon="volume-off" variant="ghost" onPress={() => moderate.mutate({ action: "mute", target_id: sel.player_id, channel, minutes: 60 }, { onSuccess: () => sheet.current?.dismiss() })} testID="mute-button" /> : null}
          </View>
        ) : null}
      </Sheet>
    </Screen>
  );
}
