import { useRouter } from "expo-router";
import React from "react";
import { Pressable, View } from "react-native";

import { QK, useAction, useNotifications } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Empty, Icon, IconName, Loading, Panel, Row, Screen, Txt } from "@/src/ui";

const ICON: Record<string, IconName> = { construction_complete: "hammer", research_complete: "flask", recruitment_complete: "account-plus", offline_chest_full: "treasure-chest", event_ending: "calendar-clock", purchase_credited: "diamond-stone", war: "sword-cross" };

export default function InboxScreen() {
  const { colors } = useTheme();
  const router = useRouter();
  const { data, isLoading } = useNotifications();
  const read = useAction("post", "/notifications/read", [QK.notifications]);
  if (isLoading || !data) return <Loading />;
  return (
    <Screen title="Cronaca" subtitle={`${data.unread} non lette`} testID="inbox-screen" right={<Btn title="Segna lette" small variant="ghost" onPress={() => read.mutate({})} disabled={!data.unread} testID="mark-all-read" />}>
      {!data.notifications.length ? <Empty icon="bell-outline" title="Nessuna notizia" text="Completamenti di timer, eventi in scadenza, guerre e acquisti compariranno qui." /> : null}
      {data.notifications.map((n: any) => (
        <Pressable key={n.id} testID={`notification-${n.id}`} onPress={() => { if (!n.read) read.mutate({ ids: [n.id] }); if (n.action_url) router.push(n.action_url); }}>
          <Panel variant={n.read ? "wood" : "iron"}>
            <Row>
              <Icon name={ICON[n.kind] ?? "bell"} size={20} color={n.read ? colors.muted : colors.goldBright} />
              <View style={{ flex: 1 }}>
                <Txt v="bodyBold">{n.title}</Txt>
                <Txt v="small" color={colors.muted}>{n.message}</Txt>
                <Txt v="caption">{new Date(n.created_at).toLocaleString("it-IT")}</Txt>
              </View>
            </Row>
          </Panel>
        </Pressable>
      ))}
    </Screen>
  );
}
