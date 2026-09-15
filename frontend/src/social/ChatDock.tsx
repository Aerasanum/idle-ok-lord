// Always-on chat dock for the main (Battle) screen: Globale / Alleanza tabs, latest messages, inline composer.
// Collapsed = 2 latest lines + input; tap the header to expand into a taller live feed. Never leaves the screen.
import { useRouter } from "expo-router";
import React, { useEffect, useRef, useState } from "react";
import { Keyboard, Platform, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAction, useChat, useMyAlliance } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { fonts, useTheme } from "@/src/theme";
import { Icon, Input, Txt } from "@/src/ui";

export function ChatDock() {
  const { colors } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { user } = useAuth();
  const { data: mine } = useMyAlliance();
  const a = mine?.alliance;
  const channels = [{ key: "global:it", label: "Globale", icon: "earth" as const }, ...(a ? [{ key: `alliance:${a.id}`, label: "Alleanza", icon: "flag" as const }] : [])];
  const [channel, setChannel] = useState("global:it");
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const { data } = useChat(channel);
  const send = useAction("post", "/chat/messages", [["chat", channel]]);
  const listRef = useRef<ScrollView>(null);
  const msgs: any[] = data?.messages ?? [];
  const shown = open ? msgs.slice(-40) : msgs.slice(-2);
  const verified = !!user?.account.email_verified;
  useEffect(() => { if (open) setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 50); }, [open, msgs.length]);
  const submit = () => {
    const t = text.trim();
    if (!t || !verified) return;
    send.mutate({ channel, text: t }, { onSuccess: () => setText("") });
  };
  return (
    <View style={{ borderTopWidth: 2, borderColor: colors.gold, backgroundColor: colors.surfaceSecondary, paddingBottom: Platform.OS === "web" ? 0 : Math.max(0, insets.bottom - 8) }} testID="chat-dock">
      {/* header: channels + expand */}
      <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 8, paddingTop: 6, gap: 6 }}>
        {channels.map((c) => (
          <Pressable key={c.key} onPress={() => setChannel(c.key)} style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 9, height: 28, borderRadius: 14, backgroundColor: channel === c.key ? colors.brandPrimary : colors.surfaceTertiary, borderWidth: 1, borderColor: channel === c.key ? colors.goldBright : colors.iron }} testID={`dock-channel-${c.label}`} hitSlop={4}>
            <Icon name={c.icon} size={13} color={channel === c.key ? colors.goldBright : colors.muted} />
            <Txt v="caption" color={channel === c.key ? colors.goldBright : colors.muted}>{c.label}</Txt>
          </Pressable>
        ))}
        {!a ? <Txt v="caption" color={colors.muted} numberOfLines={1} style={{ flex: 1 }}>Entra in un&apos;alleanza per la chat di gruppo</Txt> : <View style={{ flex: 1 }} />}
        <Pressable onPress={() => router.push("/alliance/chat")} style={{ width: 28, height: 28, alignItems: "center", justifyContent: "center" }} testID="dock-open-full" hitSlop={6}>
          <Icon name="open-in-new" size={16} color={colors.muted} />
        </Pressable>
        <Pressable onPress={() => { setOpen(!open); if (open) Keyboard.dismiss(); }} style={{ width: 28, height: 28, alignItems: "center", justifyContent: "center" }} testID="dock-toggle" hitSlop={6}>
          <Icon name={open ? "chevron-down" : "chevron-up"} size={22} color={colors.goldBright} />
        </Pressable>
      </View>
      {/* messages */}
      <ScrollView ref={listRef} style={{ maxHeight: open ? 260 : 44, marginTop: 4 }} contentContainerStyle={{ paddingHorizontal: 10, gap: 3 }} showsVerticalScrollIndicator={open} scrollEnabled={open} testID="dock-messages">
        {shown.length === 0 ? <Txt v="caption" color={colors.muted}>Nessun messaggio ancora: saluta tutti!</Txt> : null}
        {shown.map((m) => (
          <View key={m.id} style={{ flexDirection: "row", gap: 6, alignItems: "flex-start" }} testID={`dock-message-${m.id}`}>
            <Txt v="caption" color={m.player_id === user?.player_id ? colors.goldBright : colors.onSurface} style={{ fontFamily: fonts.bodyBold, maxWidth: 96 }} numberOfLines={1}>{m.display_name}</Txt>
            <Txt v="caption" color={colors.onSurface} style={{ flex: 1 }} numberOfLines={open ? 6 : 1}>{m.text}</Txt>
          </View>
        ))}
      </ScrollView>
      {/* composer */}
      <View style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 8, paddingVertical: 6 }}>
        <Input value={text} onChangeText={setText} placeholder={verified ? (channel === "global:it" ? "Scrivi a tutti…" : "Scrivi alla tua alleanza…") : "Verifica l'email per scrivere"} editable={verified} maxLength={300} style={{ flex: 1, height: 38 }} onSubmitEditing={submit} returnKeyType="send" blurOnSubmit={false} testID="dock-input" onFocus={() => setOpen(true)} />
        <Pressable onPress={submit} disabled={!verified || !text.trim() || send.isPending} style={{ width: 40, height: 38, borderRadius: 6, alignItems: "center", justifyContent: "center", backgroundColor: colors.brandPrimary, borderWidth: 1.5, borderColor: colors.gold, opacity: verified && text.trim() ? 1 : 0.5 }} testID="dock-send" hitSlop={4}>
          <Icon name="send" size={18} color={colors.goldBright} />
        </Pressable>
      </View>
    </View>
  );
}
