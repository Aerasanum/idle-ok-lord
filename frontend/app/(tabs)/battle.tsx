import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api } from "@/src/api/client";
import { QK, useAction, useCanon, useProfile } from "@/src/api/hooks";
import { Attempt, BattleScene } from "@/src/battle/BattleScene";
import { ChatDock } from "@/src/social/ChatDock";
import { WarCallBanner } from "@/src/war/WarCallBanner";
import { paletteFor } from "@/src/battle/regions";
import { LinearGradient } from "expo-linear-gradient";
import { rarityColor, useTheme } from "@/src/theme";
import { Btn, Icon, IconName, Input, Loading, Panel, RARITY_LABEL, Res, ResourceBar, Row, SLOT_LABEL, Txt, fmt } from "@/src/ui";
import { Sheet, SheetRef } from "@/src/ui/Sheet";
import { useToast } from "@/src/ui/Toast";
import { ItemIcon } from "@/src/ui/ItemIcon";
import { lordArt } from "@/src/art";
import { TutorialTarget, useTutorial } from "@/src/tutorial/Tutorial";

type Result = any;

const CLASS_LABEL: Record<string, string> = { umanoidi: "Umanoidi", bestie: "Bestie", giganti: "Giganti", corazzati: "Corazzati", volanti: "Volanti", spiriti: "Spiriti", draghi: "Draghi" };

export default function BattleTab() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const toast = useToast();
  const qc = useQueryClient();
  const { data: profile, isLoading } = useProfile();
  const { data: canon } = useCanon();
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [serverTime, setServerTime] = useState<string>(new Date().toISOString());
  const [auto, setAuto] = useState(true);
  const [stage, setStage] = useState<number | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [nameDraft, setNameDraft] = useState("");
  const renameSheet = useRef<SheetRef>(null);
  const rename = useAction("patch", "/account/settings", [QK.profile], { success: () => "Nome del Lord aggiornato" });
  const [busy, setBusy] = useState(false);
  const starting = useRef(false);
  const tut = useTutorial();
  const scrollRef = useRef<ScrollView>(null);
  const targetY = useRef<Record<string, number>>({});

  const highest = profile?.campaign?.highest_cleared ?? 0;
  const curStage = stage ?? Math.max(1, Math.min(highest + 1, profile?.campaign?.current_stage ?? 1));

  useEffect(() => {
    if (!profile) return;
    api.get(`/battle/stage/${curStage}`).then(setPreview).catch(() => {});
  }, [curStage, profile?.combat?.total_power, profile]);

  const start = useCallback(
    async (s: number) => {
      if (starting.current) return;
      starting.current = true;
      setBusy(true);
      try {
        const d = await api.post("/battle/attempt", { stage: s });
        setAttempt(d.attempt);
        setServerTime(new Date().toISOString());
        setResult(null);
      } catch (e: any) {
        toast.show(e.message, "error");
        setAuto(false);
      } finally {
        setBusy(false);
        starting.current = false;
      }
    },
    [toast],
  );

  const onFinished = useCallback(
    async (id: string) => {
      try {
        const r = await api.post("/battle/claim", { attempt_id: id });
        setResult(r);
        setAttempt(null);
        qc.invalidateQueries({ queryKey: QK.profile });
        qc.invalidateQueries({ queryKey: QK.inventory });
        if (r.gear?.found?.length) toast.show(`Trovato: ${r.gear.found.map((g: any) => RARITY_LABEL[g.rarity]).join(", ")}`, "success");
        if (r.levels_gained) toast.show(`Il Lord sale al livello ${r.hero_level}!`, "success");
        if (auto) {
          const next = r.win ? Math.min((r.highest_cleared ?? 0) + 1, (attempt?.stage ? Number(attempt.stage) : 0) + 1) : Math.max(1, r.highest_cleared || 1);
          setStage(next);
          setTimeout(() => start(next), 1200);
        }
      } catch (e: any) {
        if (e.status === 425) setTimeout(() => onFinished(id), 1000);
        else toast.show(e.message, "error");
      }
    },
    [auto, attempt, qc, start, toast],
  );

  useEffect(() => {
    if (profile && !attempt && auto && !result && !busy) start(curStage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.id]);

  // first-play tutorial: once per account (settings.tutorial_done), once per app session
  useEffect(() => {
    if (!profile || tut.active || tut.autoStarted || profile.settings?.tutorial_done === true) return;
    tut.markAutoStarted();
    const t = setTimeout(() => tut.start(), 900);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.id, profile?.settings?.tutorial_done]);
  useEffect(() => {
    const id = tut.step?.target;
    if (!tut.active || !id) return;
    const y = targetY.current[id];
    if (y !== undefined) scrollRef.current?.scrollTo({ y: Math.max(0, y - 96), animated: true });
  }, [tut.active, tut.step?.target]);

  if (isLoading || !profile) return <Loading label="Il Lord si prepara..." />;
  const equipped: Record<string, any> = {};
  for (const it of profile.equipped_items ?? []) equipped[it.slot] = it;
  const skills = (canon?.skills ?? []).filter((s: any) => (profile.hero.skill_slots ?? []).includes(s.key));
  const pal = paletteFor(preview?.region?.region ?? 1);
  const offlineReady = profile.offline_preview?.claimable;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="battle-screen">
      <View style={{ paddingTop: insets.top, backgroundColor: colors.surfaceSecondary }}>
        <ResourceBar resources={profile.resources} />
      </View>
      <ScrollView ref={scrollRef} contentContainerStyle={{ paddingBottom: 24 }} showsVerticalScrollIndicator={false}>
        <WarCallBanner />
        {attempt ? (
          <BattleScene attempt={attempt} serverTime={serverTime} formation={profile.army.formation} equipped={equipped} armyTier={profile.army_visual_tier} heraldicColor={profile.cosmetics?.army?.color ?? profile.heraldic_color} armyBanner={profile.cosmetics?.army ?? null} onFinished={onFinished} skills={skills} firstClear={Number(attempt.stage) > highest} lordName={profile.hero.name} lordLevel={profile.hero.level} />
        ) : (
          <LinearGradient colors={pal.sky} style={{ height: 220, alignItems: "center", justifyContent: "center", borderBottomWidth: 3, borderColor: colors.gold }} testID="battle-idle-scene">
            <Txt v="h1">{preview?.region?.name ?? "Campagna"}</Txt>
            <Txt v="small">Stage {curStage} · {preview?.kind === "boss" ? `Boss: ${preview?.region?.boss}` : preview?.kind === "elite" ? "Elite" : "Ondate normali"}</Txt>
            <Btn title={busy ? "..." : "Inizia la battaglia"} icon="sword" onPress={() => start(curStage)} loading={busy} style={{ marginTop: 16 }} testID="battle-start-button" />
          </LinearGradient>
        )}

        {/* stage bar */}
        <TutorialTarget id="stage-panel" onLayout={(y) => (targetY.current["stage-panel"] = y)}>
        <Panel style={{ margin: 12 }} testID="stage-panel">
          <Row style={{ justifyContent: "space-between" }}>
            <Pressable testID="stage-prev-button" onPress={() => setStage(Math.max(1, curStage - 1))} style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }} disabled={!!attempt}>
              <Icon name="chevron-left" size={28} color={colors.goldBright} />
            </Pressable>
            <View style={{ alignItems: "center" }}>
              <Txt v="h2" testID="stage-number">Stage {curStage}</Txt>
              <Txt v="caption">Record: {highest} · {preview?.region?.name}</Txt>
              {attempt && Number(attempt.stage) !== curStage ? <Txt v="caption" color={colors.goldBright} testID="running-stage-badge">In corso: Stage {attempt.stage}</Txt> : null}
            </View>
            <Pressable testID="stage-next-button" onPress={() => setStage(Math.min(highest + 1, curStage + 1))} style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }} disabled={!!attempt || curStage >= highest + 1}>
              <Icon name="chevron-right" size={28} color={curStage >= highest + 1 ? colors.muted : colors.goldBright} />
            </Pressable>
          </Row>
          <Row style={{ justifyContent: "space-between", marginTop: 6 }}>
            <View style={{ flex: 1, paddingRight: 8 }}>
              <Txt v="caption">La tua potenza</Txt>
              <Txt v="num" testID="player-power">{fmt(preview?.player_power ?? profile.combat.total_power)}</Txt>
              <Txt v="small" color={colors.muted}>Lord {fmt(profile.combat.hero.power)} · Esercito {fmt(preview?.army_power ?? profile.combat.army_power)}</Txt>
              {preview?.army_counter_net_pct ? (
                <Txt v="small" color={preview.army_counter_net_pct > 0 ? colors.success : colors.error} testID="army-counter-net">
                  Contro-unità: {preview.army_counter_net_pct > 0 ? "+" : ""}{preview.army_counter_net_pct}% · nemici {Object.entries(preview.enemy_mix ?? {}).map(([c, s]) => `${CLASS_LABEL[c] ?? c} ${Math.round((s as number) * 100)}%`).join(", ")}
                </Txt>
              ) : null}
            </View>
            <View style={{ alignItems: "flex-end" }}>
              <Txt v="caption">Richiesta</Txt>
              <Txt v="num" color={preview?.can_win ? colors.success : colors.error} testID="required-power">{fmt(preview?.required_power ?? 0)}</Txt>
              <Txt v="small" color={colors.muted}>{preview?.first_clear ? `1ª vittoria: ${fmt(preview.first_clear.xp)} XP · ${fmt(preview.first_clear.gold)} oro` : ""}</Txt>
            </View>
          </Row>
          <Row style={{ marginTop: 10 }}>
            <TutorialTarget id="auto-battle-toggle" onLayout={() => (targetY.current["auto-battle-toggle"] = targetY.current["stage-panel"] ?? 0)}>
              <Btn title={auto ? "Auto: ON" : "Auto: OFF"} variant={auto ? "gold" : "secondary"} small icon={auto ? "play-circle" : "pause-circle"} onPress={() => setAuto(!auto)} testID="auto-battle-toggle" />
            </TutorialTarget>
            {!attempt ? <Btn title="Combatti" small icon="sword" onPress={() => start(curStage)} loading={busy} testID="battle-fight-button" /> : <Txt v="small" color={colors.muted}>Battaglia in corso (server)</Txt>}
          </Row>
        </Panel>
        </TutorialTarget>

        {result ? <ResultCard result={result} onClose={() => setResult(null)} /> : null}

        {/* hero card */}
        <TutorialTarget id="hero-card" onLayout={(y) => (targetY.current["hero-card"] = y)}>
        <Panel variant="wood" style={{ marginHorizontal: 12, marginBottom: 12 }} testID="hero-card">
          <Row style={{ justifyContent: "space-between" }}>
            <Row style={{ flex: 1 }}>
              {lordArt(equipped, profile.army_visual_tier?.tier ?? 0) ? (
                <View style={{ width: 52, height: 60, borderRadius: 6, overflow: "hidden", backgroundColor: colors.surfaceTertiary, borderWidth: 1.5, borderColor: colors.gold, alignItems: "center", justifyContent: "flex-end" }} testID="hero-portrait">
                  <Image source={lordArt(equipped, profile.army_visual_tier?.tier ?? 0)!} style={{ width: 80, height: 96, marginBottom: -30 }} resizeMode="contain" />
                </View>
              ) : null}
              <View style={{ flex: 1 }}>
                <Pressable onPress={() => { setNameDraft(profile.hero.name ?? ""); renameSheet.current?.present(); }} style={{ flexDirection: "row", alignItems: "center", gap: 6 }} testID="rename-lord-button" hitSlop={6}>
                  <Txt v="h3" testID="lord-name">{profile.hero.name ?? "Lord"}</Txt>
                  <Icon name="pencil" size={14} color={colors.goldBright} />
                </Pressable>
                <Txt v="small" color={colors.goldBright} testID="lord-level-power">Lv {profile.hero.level} · Potenza {fmt(profile.combat.total_power)}</Txt>
                <Txt v="small" color={colors.muted}>XP {fmt(profile.hero.xp)} / {fmt(profile.xp_to_next)} · Talenti {profile.talent_points_total - profile.talent_points_spent} liberi</Txt>
                <Txt v="small" color={colors.muted} testID="player-name">Giocatore: {profile.display_name}</Txt>
              </View>
            </Row>
            <Row>
              <Btn title="Equip" small variant="ghost" icon="sword" onPress={() => router.push("/hero/gear")} testID="open-gear-button" />
              <Btn title="Talenti" small variant="ghost" icon="star" onPress={() => router.push("/hero/talents")} testID="open-talents-button" />
            </Row>
          </Row>
          <Row style={{ flexWrap: "wrap", marginTop: 8, gap: 6 }}>
            {Object.entries(profile.equipped).map(([slot, id]) => {
              const it = equipped[slot];
              return (
                <View key={slot} style={{ width: 34, height: 34, borderWidth: 2, borderColor: it ? rarityColor(colors, it.rarity) : colors.iron, borderRadius: 4, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceTertiary }} testID={`hero-slot-${slot}`}>
                  <Txt v="small" color={it ? colors.onSurface : colors.muted}>{SLOT_LABEL[slot].slice(0, 2)}</Txt>
                  {profile.forge[slot] ? <Txt v="small" color={colors.goldBright} style={{ position: "absolute", bottom: -2, right: 1, fontSize: 8 }}>+{profile.forge[slot]}</Txt> : null}
                </View>
              );
            })}
            <Btn title="Formazione" small variant="ghost" icon="chess-rook" onPress={() => router.push("/army/formation")} testID="open-formation-button" />
          </Row>
        </Panel>
        <Sheet ref={renameSheet} title="Nome del Lord" testID="rename-sheet">
          <Txt v="small" color={colors.muted}>È il nome del tuo eroe in battaglia. Il nome giocatore (alleanze, chat, guerre) si cambia nel Profilo.</Txt>
          <Input value={nameDraft} onChangeText={setNameDraft} placeholder="Nuovo nome (3-16 caratteri)" maxLength={16} testID="rename-input" />
          <Btn title="Salva nome" icon="content-save" loading={rename.isPending} disabled={nameDraft.trim().length < 3} onPress={() => rename.mutate({ lord_name: nameDraft.trim() }, { onSuccess: () => renameSheet.current?.dismiss() })} testID="rename-save-button" style={{ marginTop: 8 }} />
        </Sheet>
        </TutorialTarget>

        {/* quick links */}
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, paddingHorizontal: 12 }} onLayout={(e) => (targetY.current["quick-offline"] = e.nativeEvent.layout.y)}>
          <Quick icon="treasure-chest" label="Forziere" badge={offlineReady ? "!" : undefined} onPress={() => router.push("/offline")} testID="quick-offline" tutorialId="quick-offline" />
          <Quick icon="calendar-star" label="Eventi" onPress={() => router.push("/events/weekly")} testID="quick-events" />
          <Quick icon="door-closed" label="Dungeon" onPress={() => router.push("/events/dungeons")} testID="quick-dungeons" />
          <Quick icon="clipboard-check" label="Missioni" onPress={() => router.push("/events/quests")} testID="quick-quests" />
          <Quick icon="trophy" label="Imprese" onPress={() => router.push("/events/achievements")} testID="quick-achievements" />
          <Quick icon="book-open-variant" label="Codex" onPress={() => router.push("/events/codex")} testID="quick-codex" />
          <Quick icon="storefront" label="Negozio" onPress={() => router.push("/shop")} testID="quick-shop" />
          <Quick icon="bell" label="Cronaca" badge={profile.unread_notifications ? String(profile.unread_notifications) : undefined} onPress={() => router.push("/inbox")} testID="quick-inbox" />
          <Quick icon="account" label="Profilo" onPress={() => router.push("/profile")} testID="quick-profile" />
        </View>
        {!profile.account?.email_verified ? (
          <Pressable onPress={() => router.push("/verify")} style={{ margin: 12, padding: 10, borderWidth: 1, borderColor: colors.warning, borderRadius: 6, backgroundColor: colors.surfaceSecondary }} testID="verify-banner">
            <Txt v="small" color={colors.warning}>Email non verificata: tocca per inserire il codice (necessario per chat e alleanze).</Txt>
          </Pressable>
        ) : null}
      </ScrollView>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={insets.bottom + 56}>
        <ChatDock />
      </KeyboardAvoidingView>
    </View>
  );
}

function Quick({ icon, label, onPress, badge, testID, tutorialId }: { icon: IconName; label: string; onPress: () => void; badge?: string; testID: string; tutorialId?: string }) {
  const { colors } = useTheme();
  const btn = (
    <Pressable onPress={onPress} testID={testID} style={({ pressed }) => ({ flex: 1, minHeight: 64, backgroundColor: colors.surfaceSecondary, borderWidth: 1.5, borderColor: colors.wood, borderRadius: 6, alignItems: "center", justifyContent: "center", gap: 4, opacity: pressed ? 0.8 : 1 })}>
      <Icon name={icon} size={22} color={colors.goldBright} />
      <Txt v="small">{label}</Txt>
      {badge ? <View style={{ position: "absolute", top: 4, right: 6, backgroundColor: colors.brandPrimary, borderRadius: 8, paddingHorizontal: 5, borderWidth: 1, borderColor: colors.gold }}><Txt v="small" color={colors.onBrandPrimary}>{badge}</Txt></View> : null}
    </Pressable>
  );
  const box = { width: "31%" as const, flexGrow: 1, minHeight: 64 };
  return tutorialId ? <TutorialTarget id={tutorialId} style={box}>{btn}</TutorialTarget> : <View style={box}>{btn}</View>;
}

function ResultCard({ result, onClose }: { result: any; onClose: () => void }) {
  const { colors } = useTheme();
  const r = result.rewards ?? {};
  return (
    <Panel variant="parchment" style={{ marginHorizontal: 12, marginBottom: 12 }} testID="battle-result-card">
      <Row style={{ justifyContent: "space-between" }}>
        <Txt v="h2" color={result.win ? colors.forest : colors.burgundy}>{result.win ? (result.first_clear ? "Stage conquistato!" : "Vittoria") : "Sconfitta"}</Txt>
        <Pressable onPress={onClose} testID="result-close-button" style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}><Icon name="close" color={colors.onSurfaceInverse} /></Pressable>
      </Row>
      <Row style={{ flexWrap: "wrap", gap: 12 }}>
        <Res kind="gold" value={r.gold ?? 0} testID="result-gold" art />
        <Row gap={4}><Icon name="star-four-points" size={14} color={colors.res_event_tokens} /><Txt v="bodyBold" color={colors.onSurfaceInverse}>{fmt(r.xp ?? 0)} XP</Txt></Row>
        {Object.entries(r.soft_split ?? {}).map(([k, v]) => <Res key={k} kind={k} value={v as number} art />)}
      </Row>
      {result.first_clear ? <Txt v="small" color={colors.onSurfaceInverse}>Dominio: {result.domain_tiles} tessere · Record stage {result.highest_cleared}</Txt> : null}
      {result.gear?.found?.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 8 }} testID="result-loot">
          {result.gear.found.map((g: any) => {
            const state = result.gear.equipped.includes(g.id) ? "equipaggiato" : result.gear.salvaged.some((s: any) => s.id === g.id) ? "smantellato" : null;
            return (
              <View key={g.id} style={{ alignItems: "center", width: 76, gap: 2 }} testID={`loot-${g.id}`}>
                <ItemIcon slot={g.slot} rarity={g.rarity} size={56}>
                  {state ? <View style={{ position: "absolute", top: -6, right: -6, backgroundColor: state === "equipaggiato" ? colors.success : colors.iron, borderRadius: 8, padding: 2 }}><Icon name={state === "equipaggiato" ? "check" : "hammer"} size={10} color={colors.onSuccess} /></View> : null}
                </ItemIcon>
                <Txt v="small" color={rarityColor(colors, g.rarity)} style={{ fontSize: 10, textAlign: "center" }} numberOfLines={1}>{RARITY_LABEL[g.rarity]}</Txt>
                <Txt v="small" color={colors.onSurfaceInverse} style={{ fontSize: 10, textAlign: "center" }} numberOfLines={1}>{SLOT_LABEL[g.slot]} Lv {g.item_level}</Txt>
              </View>
            );
          })}
        </View>
      ) : null}
    </Panel>
  );
}
