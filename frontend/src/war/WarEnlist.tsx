// War roster booking: first come, first served — the first 10 members who book a slot deploy their troops.
import React from "react";
import { View } from "react-native";

import { QK, useAction } from "@/src/api/hooks";
import { useAuth } from "@/src/auth/AuthContext";
import { fonts, useTheme } from "@/src/theme";
import { Btn, Icon, Row, Txt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

export function WarEnlist({ detail, myAllianceId }: { detail: any; myAllianceId?: string }) {
  const { colors } = useTheme();
  const { user } = useAuth();
  const w = detail.war;
  const side: "attack_roster" | "defense_roster" | null = w.attacker_id === myAllianceId ? "attack_roster" : w.defender_id === myAllianceId ? "defense_roster" : null;
  const enlist = useAction("post", `/wars/${w.id}/enlist`, [QK.wars, QK.warMap], { success: (d) => (d.reserve ? `Sei in riserva n.${d.reserve_position}: entri se qualcuno si ritira` : "Prenotato! Le tue truppe scenderanno in campo") });
  const withdraw = useAction("post", `/wars/${w.id}/withdraw`, [QK.wars, QK.warMap], { success: (d) => (d.promoted ? "Ritirato: una riserva ha preso il tuo posto" : "Ti sei ritirato") });
  const lockLeft = useCountdown(w.lock_at);
  if (!side) return null;
  const roster: string[] = w[side];
  const reserve: string[] = w[side.replace("roster", "reserve")] ?? [];
  const me = user?.player_id;
  const enlisted = !!me && roster.includes(me);
  const inReserve = !!me && reserve.includes(me);
  const full = roster.length >= 10;
  const other: string[] = side === "attack_roster" ? w.defense_roster : w.attack_roster;
  return (
    <View style={{ gap: 8, marginTop: 8 }} testID="war-enlist">
      <Row style={{ justifyContent: "space-between" }}>
        <Txt v="h3" color={colors.onSurfaceInverse}>{side === "attack_roster" ? "⚔️ Eserciti d'attacco" : "🛡️ Eserciti di difesa"} {roster.length}/10</Txt>
        <Txt v="caption" color={colors.onSurfaceInverse} testID="war-lock-countdown">Blocco tra {fmtDuration(lockLeft)}</Txt>
      </Row>
      <Txt v="small" color={colors.onSurfaceInverse}>I primi 10 che si prenotano schierano le loro truppe (formazione attuale). Si può combattere anche con meno di 10, ma ogni corsia vuota è persa.</Txt>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }} testID="war-roster-slots">
        {Array.from({ length: 10 }).map((_, i) => {
          const pid = roster[i];
          const pl = pid ? detail.roster_players?.[pid] : null;
          const isMe = pid === me;
          return (
            <View key={i} style={{ width: "48%", flexGrow: 1, height: 36, borderRadius: 6, paddingHorizontal: 8, flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1.5, borderStyle: pid ? "solid" : "dashed", borderColor: isMe ? colors.goldBright : pid ? colors.forest : colors.wood, backgroundColor: pid ? (isMe ? colors.brandPrimary : colors.forest) : "transparent" }} testID={`war-slot-${i + 1}`}>
              <Txt v="caption" color={pid ? colors.onBrandTertiary : colors.onSurfaceInverse} style={{ fontFamily: fonts.bodyBold, width: 16 }}>{i + 1}</Txt>
              {pid ? <Txt v="small" color={isMe ? colors.goldBright : colors.onBrandTertiary} numberOfLines={1} style={{ flex: 1 }}>{pl?.display_name ?? "…"}{pl ? ` L${pl.hero_level}` : ""}</Txt> : <Txt v="small" color={colors.onSurfaceInverse} style={{ flex: 1, opacity: 0.6 }}>Posto libero</Txt>}
              {pid ? <Icon name="shield-sword" size={14} color={isMe ? colors.goldBright : colors.onBrandTertiary} /> : null}
            </View>
          );
        })}
      </View>
      {reserve.length > 0 ? (
        <View style={{ gap: 3 }} testID="war-reserve-list">
          <Txt v="caption" color={colors.onSurfaceInverse} style={{ fontFamily: fonts.bodyBold }}>⏳ Riserve ({reserve.length}) — entrano in automatico se qualcuno si ritira</Txt>
          {reserve.map((pid, i) => <Txt key={pid} v="small" color={pid === me ? colors.brandPrimary : colors.onSurfaceInverse} testID={`war-reserve-${i + 1}`}>{i + 1}. {detail.roster_players?.[pid]?.display_name ?? "…"}{pid === me ? " (tu)" : ""}</Txt>)}
        </View>
      ) : null}
      {enlisted || inReserve ? (
        <Btn title={inReserve ? `Esci dalla riserva (sei n.${reserve.indexOf(me!) + 1})` : "Ritirati dal roster"} small variant="secondary" icon="undo" loading={withdraw.isPending} onPress={() => withdraw.mutate({})} testID="war-withdraw-button" />
      ) : (
        <Btn title={full ? `Roster completo: prenotati come riserva (${reserve.length + 1}ª)` : "Prenotati: schiera le tue truppe"} small variant="gold" icon={full ? "timer-sand" : "sword-cross"} loading={enlist.isPending} onPress={() => enlist.mutate({})} testID="war-enlist-button" />
      )}
      <Txt v="caption" color={colors.onSurfaceInverse}>Avversari schierati: {other.length}/10{side === "attack_roster" && w.defender_id ? "" : side === "attack_roster" ? " (guarnigione NPC)" : ""}</Txt>
    </View>
  );
}
