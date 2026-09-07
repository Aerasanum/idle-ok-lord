// Public player showcase: the Lord with the equipped skin, the army banner and the castle skin, plus power/campaign/alliance.
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect } from "react";
import { Image, Pressable, ScrollView, useWindowDimensions, View } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useShowcase } from "@/src/api/hooks";
import { castleArtFor, lordArtFor, regionBackground, skinArt } from "@/src/art";
import { Ambient } from "@/src/battle/effects";
import { UnitProxy } from "@/src/battle/sprites";
import { fonts, rarityColor, useTheme } from "@/src/theme";
import { Btn, Icon, Loading, Panel, RARITY_LABEL, Row, SLOT_ICON, SLOT_LABEL, Txt, fmt } from "@/src/ui";

export default function PlayerShowcaseScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const { data: s, isLoading, error } = useShowcase(id);
  const bob = useSharedValue(0);
  const sway = useSharedValue(0);
  useEffect(() => {
    bob.value = withRepeat(withSequence(withTiming(1, { duration: 1000, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 1000, easing: Easing.inOut(Easing.sin) })), -1, false);
    sway.value = withRepeat(withSequence(withTiming(1, { duration: 1500, easing: Easing.inOut(Easing.sin) }), withTiming(0, { duration: 1500, easing: Easing.inOut(Easing.sin) })), -1, false);
  }, [bob, sway]);
  const lordStyle = useAnimatedStyle(() => ({ transform: [{ translateY: -4 * bob.value }, { scale: 1 + 0.02 * bob.value }] }));
  const bannerStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${-3 + 6 * sway.value}deg` }] }));
  if (isLoading) return <Loading />;
  if (!s || error) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center", gap: 12, padding: 24 }} testID="showcase-missing">
        <Icon name="account-question" size={48} color={colors.muted} />
        <Txt v="h3">Giocatore non trovato</Txt>
        <Btn title="Indietro" variant="ghost" onPress={() => router.back()} testID="showcase-back-missing" />
      </View>
    );
  }
  const stageH = 340;
  const heraldic = s.cosmetics?.army?.color ?? s.heraldic_color ?? colors.brandPrimary;
  const glow = s.cosmetics?.army?.glow ?? colors.goldBright;
  const lord = lordArtFor(s.cosmetics?.lord_skin, s.has_chest, s.army_visual_tier?.tier ?? 0);
  const banner = s.cosmetics?.army ? skinArt(s.cosmetics.army.key) : undefined;
  const castle = castleArtFor(s.cosmetics?.castle_skin, s.castle_level);
  const bg = regionBackground(Math.max(1, Math.ceil(Math.max(1, s.campaign.highest_cleared) / 20)));
  const lordH = 250, lordW = lordH * 0.9;
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }} testID="showcase-screen">
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + 24 }} showsVerticalScrollIndicator={false}>
        <View style={{ height: stageH, overflow: "hidden", backgroundColor: colors.surfaceTertiary }} testID="showcase-stage">
          {bg ? <Image source={bg} style={{ position: "absolute", left: 0, top: 0, width, height: stageH }} resizeMode="cover" /> : null}
          <LinearGradient colors={["rgba(0,0,0,0.55)", "rgba(0,0,0,0)", "rgba(0,0,0,0.2)", "rgba(9,11,16,1)"]} locations={[0, 0.3, 0.8, 1]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
          <Ambient width={width} height={stageH} color={glow} rise />
          {/* castle skin in the background */}
          {castle ? <Image source={castle} style={{ position: "absolute", right: 6, top: 54, width: 140, height: 120, opacity: 0.95 }} resizeMode="contain" testID="showcase-castle" /> : null}
          {/* heraldic glow pool */}
          <View style={{ position: "absolute", left: width * 0.08, top: stageH * 0.84, width: width * 0.84, height: 26, borderRadius: 999, backgroundColor: glow, opacity: 0.3 }} />
          {/* banner */}
          {banner ? (
            <Animated.View style={[{ position: "absolute", left: 10, top: stageH * 0.9 - 230, width: 96, height: 230, transformOrigin: "bottom" }, bannerStyle]} testID="showcase-banner">
              <Image source={banner} style={{ width: "100%", height: "100%" }} resizeMode="contain" />
            </Animated.View>
          ) : null}
          {/* honour guard */}
          <View style={{ position: "absolute", right: 8, bottom: 30, flexDirection: "row", alignItems: "flex-end", gap: 2 }}>
            {(s.army_visual_tier?.tier ?? 0) >= 1 ? ["infantry", "archer", "cavalry"].map((u, i) => <UnitProxy key={u} unit={u} scale={1.4} banner={i === 0 ? heraldic : undefined} />) : null}
          </View>
          {/* Lord */}
          <Animated.View style={[{ position: "absolute", left: width * 0.5 - lordW * 0.5, top: stageH * 0.9 - lordH, width: lordW, height: lordH }, lordStyle]} testID="showcase-lord">
            <View style={{ position: "absolute", bottom: -2, left: lordW * 0.15, width: lordW * 0.7, height: 14, borderRadius: 999, backgroundColor: "#000", opacity: 0.35 }} />
            {lord ? <Image source={lord} style={{ width: lordW, height: lordH }} resizeMode="contain" /> : null}
          </Animated.View>
          <Pressable onPress={() => router.back()} style={{ position: "absolute", top: insets.top + 8, left: 10, width: 40, height: 40, borderRadius: 20, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold, alignItems: "center", justifyContent: "center" }} testID="showcase-back" hitSlop={8}>
            <Icon name="arrow-left" size={20} color={colors.goldBright} />
          </Pressable>
          {s.alliance ? (
            <View style={{ position: "absolute", top: insets.top + 12, right: 10, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold }} testID="showcase-alliance">
              <Txt v="caption" color={colors.goldBright}>[{s.alliance.tag}] {s.alliance.name}</Txt>
            </View>
          ) : null}
          <View style={{ position: "absolute", left: 12, right: 12, bottom: 8 }}>
            <Txt v="h1" color={colors.goldBright} style={{ textShadowColor: "#000", textShadowRadius: 6 }} testID="showcase-lord-name">{s.hero.name}</Txt>
            <Txt v="caption" color={colors.onSurface} testID="showcase-player-name">Lv {s.hero.level} · Giocatore {s.display_name}{s.is_me ? " (tu)" : ""}</Txt>
          </View>
        </View>

        <View style={{ padding: 12, gap: 10 }}>
          <Panel variant="parchment" testID="showcase-power">
            <Row style={{ justifyContent: "space-between" }}>
              <View><Txt v="caption" color={colors.onSurfaceInverse}>Potenza</Txt><Txt v="h2" color={colors.onSurfaceInverse}>{fmt(s.power.total)}</Txt></View>
              <View style={{ alignItems: "flex-end" }}>
                <Txt v="small" color={colors.onSurfaceInverse}>Lord {fmt(s.power.hero)} · Esercito {fmt(s.power.army)}</Txt>
                <Txt v="small" color={colors.onSurfaceInverse}>Stage {s.campaign.highest_cleared} · {s.campaign.region}</Txt>
                <Txt v="small" color={colors.onSurfaceInverse}>Castello {s.castle_level} · Dominio {s.domain_tiles ?? 0}/100</Txt>
              </View>
            </Row>
          </Panel>
          <Txt v="h2">Vetrina</Txt>
          <Row style={{ gap: 8 }}>
            <SkinCard label="Lord" name={s.cosmetics?.lord_skin ? skinName(s.cosmetics.lord_skin) : "Aspetto base"} img={lord} testID="showcase-skin-lord" />
            <SkinCard label="Castello" name={s.cosmetics?.castle_skin ? skinName(s.cosmetics.castle_skin) : "Castello del regno"} img={castle} testID="showcase-skin-castle" />
            <SkinCard label="Stendardo" name={s.cosmetics?.army?.name ?? "Vessillo araldico"} img={banner} color={heraldic} testID="showcase-skin-army" />
          </Row>
          <Txt v="h2">Equipaggiamento</Txt>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }} testID="showcase-gear">
            {s.gear.length === 0 ? <Txt v="small" color={colors.muted}>Nessun pezzo indossato.</Txt> : null}
            {s.gear.map((g: any) => {
              const col = rarityColor(colors, g.rarity);
              return (
                <View key={g.slot} style={{ width: "31%", flexGrow: 1, borderWidth: 1.5, borderColor: col, borderRadius: 6, padding: 6, backgroundColor: colors.surfaceSecondary, gap: 2 }}>
                  <Row style={{ gap: 4 }}><Icon name={SLOT_ICON[g.slot] ?? "sword"} size={14} color={col} /><Txt v="small" numberOfLines={1}>{SLOT_LABEL[g.slot] ?? g.slot}</Txt></Row>
                  <Txt v="caption" color={col}>{RARITY_LABEL[g.rarity] ?? g.rarity} · lv {g.item_level}</Txt>
                </View>
              );
            })}
          </View>
          {s.is_me ? <Btn title="Cambia skin nel Negozio" variant="gold" icon="storefront" onPress={() => router.push("/shop")} testID="showcase-shop" /> : null}
        </View>
      </ScrollView>
    </View>
  );
}

const SKIN_NAMES: Record<string, string> = {
  lord_forest_ranger: "Ranger della Foresta", lord_crimson_paladin: "Paladino Cremisi", lord_frost_warden: "Guardiano del Gelo", lord_shadow_reaper: "Mietitore d'Ombra",
  lord_dragon_knight: "Cavaliere del Drago", lord_golden_emperor: "Imperatore Dorato", castle_winter_citadel: "Cittadella d'Inverno", castle_elven_palace: "Palazzo Elfico",
  castle_obsidian_fortress: "Fortezza d'Ossidiana", castle_dragon_keep: "Fortezza del Drago",
};
const skinName = (k: string) => SKIN_NAMES[k] ?? k;

function SkinCard({ label, name, img, color, testID }: { label: string; name: string; img?: number; color?: string; testID: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ flex: 1, borderRadius: 8, borderWidth: 1.5, borderColor: colors.gold, backgroundColor: colors.surfaceSecondary, overflow: "hidden" }} testID={testID}>
      <View style={{ height: 84, alignItems: "center", justifyContent: "center", backgroundColor: colors.surfaceTertiary }}>
        {color ? <View style={{ position: "absolute", bottom: 4, width: 60, height: 10, borderRadius: 999, backgroundColor: color, opacity: 0.5 }} /> : null}
        {img ? <Image source={img} style={{ width: 76, height: 76 }} resizeMode="contain" /> : <Icon name="flag-variant" size={36} color={color ?? colors.muted} />}
      </View>
      <View style={{ padding: 6 }}>
        <Txt v="caption" color={colors.goldBright}>{label}</Txt>
        <Txt v="small" numberOfLines={2} style={{ fontFamily: fonts.bodyBold }}>{name}</Txt>
      </View>
    </View>
  );
}
