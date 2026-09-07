// Cosmetic skins (Lord & Castle) — 3D art previews, buy with Rubies, equip/unequip. Appearance only.
import { LinearGradient } from "expo-linear-gradient";
import React from "react";
import { Image, Pressable, ScrollView, View } from "react-native";

import { QK, useAction, useCosmetics } from "@/src/api/hooks";
import { hubArt, skinArt } from "@/src/art";
import { fonts, rarityColor, useTheme } from "@/src/theme";
import { Btn, Icon, RARITY_LABEL, Res, Row, Txt } from "@/src/ui";

const KEYS = [QK.cosmetics, QK.profile, QK.store];

export function SkinShop() {
  const { colors } = useTheme();
  const { data: c } = useCosmetics();
  const buy = useAction("post", "/store/cosmetics/buy", KEYS, { success: () => "Skin acquistata e indossata!" });
  const equip = useAction("post", "/store/cosmetics/equip", KEYS, { success: (d) => (d.equipped ? "Skin indossata" : "Aspetto predefinito ripristinato") });
  if (!c) return null;
  const sections: { kind: "lord" | "castle"; title: string; hint: string }[] = [
    { kind: "lord", title: "Skin del Lord", hint: "Cambia l'aspetto del tuo eroe in battaglia, nella Formazione e nel Titan Hunt. Solo estetica: nessun bonus." },
    { kind: "castle", title: "Skin del Castello", hint: "Cambia l'aspetto del Castello nel tuo Regno. Solo estetica: nessun bonus." },
  ];
  return (
    <View style={{ gap: 10 }} testID="skin-shop">
      <View style={{ height: 120, borderRadius: 10, overflow: "hidden", borderWidth: 1.5, borderColor: colors.gold }}>
        {hubArt("shop") ? <Image source={hubArt("shop")!} style={{ position: "absolute", width: "100%", height: "100%" }} resizeMode="cover" /> : null}
        <LinearGradient colors={["rgba(0,0,0,0)", "rgba(0,0,0,0.85)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
        <View style={{ position: "absolute", left: 10, right: 10, bottom: 8 }}>
          <Txt v="h2" color={colors.goldBright} style={{ textShadowColor: "#000", textShadowRadius: 4 }}>Sartoria Reale</Txt>
          <Txt v="small" color={colors.onSurface}>{c.catalog.filter((x: any) => x.owned).length}/{c.catalog.length} skin possedute</Txt>
        </View>
      </View>
      {sections.map((s) => {
        const items = c.catalog.filter((x: any) => x.kind === s.kind);
        const equipped = c[`${s.kind}_skin`];
        return (
          <View key={s.kind} style={{ gap: 6 }} testID={`skins-${s.kind}`}>
            <Row style={{ justifyContent: "space-between" }}>
              <Txt v="h2">{s.title}</Txt>
              <Btn title="Predefinito" small variant={equipped ? "ghost" : "secondary"} disabled={!equipped} loading={equip.isPending} onPress={() => equip.mutate({ kind: s.kind, key: null })} testID={`unequip-${s.kind}`} />
            </Row>
            <Txt v="small" color={colors.muted}>{s.hint}</Txt>
            <ScrollView horizontal showsVerticalScrollIndicator={false} showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 10, paddingVertical: 4 }}>
              {items.map((x: any) => {
                const col = rarityColor(colors, x.rarity);
                const canBuy = c.rubies >= x.rubies;
                return (
                  <View key={x.key} style={{ width: 168, borderRadius: 10, borderWidth: 2, borderColor: x.equipped ? colors.goldBright : col, backgroundColor: colors.surfaceSecondary, overflow: "hidden" }} testID={`skin-${x.key}`}>
                    <View style={{ height: 150, alignItems: "center", justifyContent: "flex-end", backgroundColor: colors.surfaceTertiary }}>
                      <LinearGradient colors={[col + "55", "rgba(0,0,0,0)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
                      {skinArt(x.key) ? <Image source={skinArt(x.key)!} style={{ width: 150, height: 140 }} resizeMode="contain" /> : <Icon name={s.kind === "lord" ? "account" : "castle"} size={64} color={col} />}
                      {x.equipped ? (
                        <View style={{ position: "absolute", top: 6, left: 6, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.goldBright }}>
                          <Txt v="caption" color={colors.onBrandPrimary} style={{ fontFamily: fonts.bodyBold }}>Indossata</Txt>
                        </View>
                      ) : null}
                      <View style={{ position: "absolute", top: 6, right: 6, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: col }}>
                        <Txt v="caption" color={colors.onBrandPrimary}>{RARITY_LABEL[x.rarity] ?? x.rarity}</Txt>
                      </View>
                    </View>
                    <View style={{ padding: 8, gap: 4 }}>
                      <Txt v="h3" numberOfLines={1}>{x.name}</Txt>
                      <Txt v="small" color={colors.muted} numberOfLines={3} style={{ minHeight: 44 }}>{x.desc}</Txt>
                      {x.owned ? (
                        <Btn title={x.equipped ? "Indossata" : "Indossa"} small variant={x.equipped ? "secondary" : "gold"} disabled={x.equipped} loading={equip.isPending} onPress={() => equip.mutate({ kind: s.kind, key: x.key })} testID={`equip-${x.key}`} />
                      ) : (
                        <Pressable onPress={() => canBuy && buy.mutate({ key: x.key })} disabled={!canBuy || buy.isPending} style={{ height: 36, borderRadius: 6, backgroundColor: canBuy ? colors.brandPrimary : colors.surfaceTertiary, borderWidth: 1, borderColor: canBuy ? colors.goldBright : colors.iron, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, opacity: buy.isPending ? 0.6 : 1 }} testID={`buy-${x.key}`}>
                          <Res kind="rubies" value={x.rubies} size={14} />
                          <Txt v="small" color={canBuy ? colors.onBrandPrimary : colors.muted}>{canBuy ? "Acquista" : "Rubini insufficienti"}</Txt>
                        </Pressable>
                      )}
                    </View>
                  </View>
                );
              })}
            </ScrollView>
          </View>
        );
      })}
    </View>
  );
}
