// "Guerra dichiarata: prenotati!" banner for the Battle tab — visible while any war of my alliance is open for booking.
import { useRouter } from "expo-router";
import React from "react";
import { Pressable, View } from "react-native";

import { useWars } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { fonts, useTheme } from "@/src/theme";
import { Icon, Txt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

export function WarCallBanner() {
  const { colors } = useTheme();
  const router = useRouter();
  const { user } = useAuth();
  const { data } = useWars();
  const me = user?.player_id;
  const mine = data?.alliance_id;
  const open = (data?.wars ?? []).filter((w: any) => w.status === "prep" && new Date(w.lock_at) > new Date());
  const w = open[0];
  const left = useCountdown(w?.lock_at);
  if (!w || !mine) return null;
  const attacking = w.attacker_id === mine;
  const roster: string[] = attacking ? w.attack_roster : w.defense_roster;
  const reserve: string[] = (attacking ? w.attack_reserve : w.defense_reserve) ?? [];
  const free = Math.max(0, 10 - roster.length);
  const enlisted = !!me && roster.includes(me);
  const inReserve = !!me && reserve.includes(me);
  const status = enlisted ? "Sei schierato ✓" : inReserve ? `In riserva n.${reserve.indexOf(me!) + 1}` : free > 0 ? `${free} posti liberi su 10` : `Roster completo · riserve ${reserve.length}`;
  return (
    <Pressable onPress={() => router.push("/alliance/war")} style={{ marginHorizontal: 12, marginTop: 8, borderRadius: 8, borderWidth: 1.5, borderColor: colors.goldBright, backgroundColor: enlisted ? colors.brandTertiary : colors.error, padding: 10, flexDirection: "row", alignItems: "center", gap: 10 }} testID="war-call-banner">
      <Icon name={attacking ? "sword-cross" : "shield-alert"} size={26} color={colors.goldBright} />
      <View style={{ flex: 1 }}>
        <Txt v="bodyBold" color={colors.onSurface} style={{ fontFamily: fonts.bodyBold }} testID="war-call-title">{attacking ? "Guerra dichiarata: prenotati!" : "Siamo sotto attacco: difendi!"}</Txt>
        <Txt v="small" color={colors.onSurface} testID="war-call-status">Nodo {w.node_id} · {status} · blocco tra {fmtDuration(left)}</Txt>
      </View>
      <Icon name="chevron-right" size={22} color={colors.goldBright} />
    </Pressable>
  );
}
