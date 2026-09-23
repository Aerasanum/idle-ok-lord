import React from "react";
import { View } from "react-native";

import { QK, useAction, useQuests } from "@/src/api/hooks";
import { useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, Progress, Res, RES_LABEL, Row, Screen, Txt } from "@/src/ui";

const rewardText = (r: Record<string, number>) => Object.entries(r).map(([k, v]) => `${v} ${RES_LABEL[k] ?? k}`).join(" + ");

export default function QuestsScreen() {
  const { colors } = useTheme();
  const { data: q, isLoading } = useQuests();
  const chest = useAction("post", "/quests/claim", [QK.quests, QK.season], { success: (d) => `Forziere: ${Object.entries(d.granted).map(([k, v]) => `${v} ${k}`).join(", ")} · +${d.season_points} punti stagione` });
  const login = useAction("post", "/quests/login/claim", [QK.quests, QK.inventory], {
    success: (d) => `Giorno ${d.day}: +${d.rubies} Rubini${d.bonus_pct ? ` (+${d.bonus_pct}% serie)` : ""}${d.gear ? " + equipaggiamento" : ""}` +
      `${d.recovered ? " · serie recuperata" : ""}${d.milestone ? ` · traguardo ${d.milestone.days} giorni!` : ""}`,
  });
  const season = useAction("post", "/season/claim", [QK.quests, QK.season, QK.inventory], { success: () => "Ricompensa stagione riscattata" });
  if (isLoading || !q) return <Loading />;
  const s = q.season;
  return (
    <Screen title="Missioni" subtitle="Giornaliere · Settimanali · Calendario · Stagione" testID="quests-screen">
      <Panel variant="parchment" testID="login-calendar">
        <Row style={{ justifyContent: "space-between" }}>
          <View>
            <Txt v="h3" color={colors.onSurfaceInverse}>Calendario accessi · giorno {q.login.cycle_day}/7</Txt>
            <Txt v="small" color={colors.onSurfaceInverse}>{q.login.rubies_total} Rubini per ciclo · giorno 7: {q.login.day_7}</Txt>
          </View>
          <Btn title={q.login.claimed_today ? "Ritirato" : "Ritira"} small variant="gold" disabled={q.login.claimed_today} loading={login.isPending} onPress={() => login.mutate({})} testID="login-claim-button" />
        </Row>
        <Row style={{ marginTop: 8, justifyContent: "space-between" }}>
          {q.login.rewards.map((r: number, i: number) => <View key={i} style={{ alignItems: "center", width: 40, paddingVertical: 4, borderRadius: 4, backgroundColor: i < q.login.cycle_day ? colors.forest : colors.parchment, borderWidth: 1, borderColor: colors.gold }}><Txt v="small" color={i < q.login.cycle_day ? colors.onBrandTertiary : colors.onSurfaceInverse}>G{i + 1}</Txt><Txt v="small" color={i < q.login.cycle_day ? colors.onBrandTertiary : colors.onSurfaceInverse}>{r}</Txt></View>)}
        </Row>
        <View style={{ marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderColor: colors.parchmentDark, gap: 3 }} testID="login-streak">
          <Row style={{ justifyContent: "space-between" }}>
            <Row style={{ gap: 5 }}>
              <Icon name="fire" size={16} color={colors.burgundy} />
              <Txt v="bodyBold" color={colors.onSurfaceInverse}>Serie di {q.login.streak} {q.login.streak === 1 ? "giorno" : "giorni"}</Txt>
            </Row>
            <Txt v="small" color={colors.onSurfaceInverse}>Record {q.login.best_streak}</Txt>
          </Row>
          <Txt v="small" color={colors.onSurfaceInverse}>
            {q.login.claimed_today
              ? q.login.bonus_pct > 0 ? `Bonus serie di oggi: +${q.login.bonus_pct}% Rubini` : "Torna domani per far salire la serie"
              : `Ritirando oggi: serie a ${q.login.streak_if_claimed_today}${q.login.bonus_pct > 0 ? `, +${q.login.bonus_pct}% Rubini` : ""}`}
            {!q.login.claimed_today && q.login.recovers_streak_today ? " · recuperi la serie persa" : ""}
          </Txt>
          {q.login.milestone_today ? <Txt v="small" color={colors.burgundy}>Oggi scatta il traguardo dei {q.login.milestone_today.days} giorni: {rewardText(q.login.milestone_today.rewards)}</Txt> : null}
          {q.login.next_milestone ? <Txt v="small" color={colors.onSurfaceInverse}>Prossimo traguardo tra {q.login.next_milestone.days_left} {q.login.next_milestone.days_left === 1 ? "giorno" : "giorni"} ({q.login.next_milestone.days} totali): {rewardText(q.login.next_milestone.rewards)}</Txt> : null}
          {q.login.recovery_left > 0 ? <Txt v="small" color={colors.onSurfaceInverse}>Hai {q.login.recovery_left} recupero disponibile questo mese: se salti un solo giorno la serie non si azzera.</Txt> : null}
        </View>
      </Panel>
      {(["daily", "weekly"] as const).map((kind) => {
        const d = q[kind];
        return (
          <Panel key={kind} testID={`${kind}-quests`}>
            <Txt v="h3">{kind === "daily" ? "Giornaliere" : "Settimanali"} · {d.points}/100 punti</Txt>
            <Progress value={d.points} max={100} />
            <Row style={{ justifyContent: "space-between", marginTop: 6, flexWrap: "wrap" }}>
              {d.chests.map((c: any, i: number) => (
                <View key={i} style={{ alignItems: "center", gap: 4 }}>
                  <Row style={{ flexWrap: "wrap", justifyContent: "center", gap: 4 }}>{Object.entries(c).filter(([k]) => k !== "points").map(([k, v]) => <Res key={k} kind={k} value={v as number} size={11} />)}</Row>
                  <Btn title={d.chests_claimed.includes(i) ? "✓" : `${c.points} pt`} small variant={d.points >= c.points && !d.chests_claimed.includes(i) ? "gold" : "secondary"} disabled={d.points < c.points || d.chests_claimed.includes(i)} onPress={() => chest.mutate({ kind, index: i })} testID={`${kind}-chest-${i}`} />
                </View>
              ))}
            </Row>
            <View style={{ marginTop: 8, gap: 4 }}>
              {d.templates.map((t: any) => {
                const task = d.tasks[t.key];
                return (
                  <Row key={t.key} style={{ justifyContent: "space-between" }} testID={`${kind}-task-${t.key}`}>
                    <Icon name={task.done ? "check-circle" : "circle-outline"} size={16} color={task.done ? colors.success : colors.muted} />
                    <Txt v="small" style={{ flex: 1 }}>{t.text}{t.alt_active ? <Txt v="small" color={colors.goldBright}> · alternativa</Txt> : null}</Txt>
                    <Txt v="small" color={colors.muted}>{Math.floor(task.progress)}/{task.target} · {t.points}pt</Txt>
                  </Row>
                );
              })}
            </View>
          </Panel>
        );
      })}
      <Panel variant="wood" testID="season-pass">
        <Txt v="h3">Season Pass {s.season_key} · livello {s.level_reached}/{s.levels}</Txt>
        <Progress value={s.points % s.points_per_level} max={s.points_per_level} label={`${s.points} punti · 1 pt per punto giornaliero, 2 per settimanale`} />
        {Object.entries(s.rewards).slice(0, s.levels).map(([lvl, r]: any) => {
          const n = Number(lvl);
          const reached = n <= s.level_reached;
          return (
            <Row key={lvl} style={{ justifyContent: "space-between", paddingVertical: 4, borderBottomWidth: 1, borderColor: colors.divider, opacity: reached ? 1 : 0.6 }} testID={`season-level-${lvl}`}>
              <Txt v="bodyBold" style={{ width: 36 }}>L{lvl}</Txt>
              <View style={{ flex: 1 }}>
                <Row>{Object.entries(r.free).map(([k, v]) => <Res key={k} kind={k} value={v as number} size={11} />)}</Row>
                <Row style={{ flexWrap: "wrap" }}><Icon name="crown" size={11} color={colors.goldBright} />{Object.entries(r.premium).map(([k, v]) => k === "cosmetic" ? <Txt key={k} v="small" color={colors.goldBright}>{String(v)}</Txt> : <Res key={k} kind={k} value={v as number} size={11} />)}</Row>
              </View>
              <View style={{ gap: 3 }}>
                <Btn title={s.claimed_free.includes(n) ? "✓" : "Free"} small variant="secondary" disabled={!reached || s.claimed_free.includes(n)} onPress={() => season.mutate({ level: n, premium: false })} testID={`season-free-${lvl}`} />
                <Btn title={s.claimed_premium.includes(n) ? "✓" : "Pass"} small variant="gold" disabled={!reached || s.claimed_premium.includes(n)} onPress={() => season.mutate({ level: n, premium: true })} testID={`season-premium-${lvl}`} />
              </View>
            </Row>
          );
        })}
      </Panel>
    </Screen>
  );
}
