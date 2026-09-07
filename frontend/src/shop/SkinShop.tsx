// Cosmetic skins (Lord, Castle, Army banner) — 3D art previews, daily deal with countdown, buy with Rubies, equip/unequip, full-screen preview.
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React from "react";
import { Image, Pressable, ScrollView, View } from "react-native";

import { QK, useAction, useCosmetics } from "@/src/api/hooks";
import { hubArt, skinArt } from "@/src/art";
import { fonts, rarityColor, useTheme } from "@/src/theme";
import { Btn, Icon, RARITY_LABEL, Res, Row, Txt, fmtDuration } from "@/src/ui";
import { useCountdown } from "@/src/ui/useCountdown";

export const SKIN_KEYS = [QK.cosmetics, QK.profile, QK.store];
export const SKIN_SECTIONS: { kind: "lord" | "castle" | "army"; title: string; hint: string; icon: "account" | "castle" | "flag" }[] = [
  { kind: "lord", title: "Skin del Lord", hint: "Cambia l'aspetto del tuo eroe in battaglia, nella Formazione e nel Titan Hunt. Solo estetica: nessun bonus.", icon: "account" },
  { kind: "castle", title: "Skin del Castello", hint: "Cambia l'aspetto del Castello nel tuo Regno. Solo estetica: nessun bonus.", icon: "castle" },
  { kind: "army", title: "Stendardi dell'esercito", hint: "Stendardo di guerra piantato in battaglia e colore araldico di bandierine, vessilli e aura delle truppe. Solo estetica.", icon: "flag" },
];

export function SkinShop() {
  const { colors } = useTheme();
  const router = useRouter();
  const { data: c } = useCosmetics();
  const buy = useAction("post", "/store/cosmetics/buy", SKIN_KEYS, { success: (d) => (d.deal ? "Offerta presa! Skin acquistata e indossata" : "Skin acquistata e indossata!") });
  const equip = useAction("post", "/store/cosmetics/equip", SKIN_KEYS, { success: (d) => (d.equipped ? "Skin indossata" : "Aspetto predefinito ripristinato") });
  const dealLeft = useCountdown(c?.deal?.ends_at);
  if (!c) return null;
  const deal = c.catalog.find((x: any) => x.key === c.deal.key);
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

      {/* daily deal */}
      {deal ? (
        <Pressable onPress={() => router.push({ pathname: "/skin-preview", params: { key: deal.key } })} testID="daily-deal" style={{ borderRadius: 10, borderWidth: 2, borderColor: colors.goldBright, backgroundColor: colors.surfaceSecondary, overflow: "hidden" }}>
          <LinearGradient colors={[colors.brandPrimary, colors.surfaceSecondary]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
          <Row style={{ padding: 10, gap: 10 }}>
            <View style={{ width: 96, height: 96, alignItems: "center", justifyContent: "center" }}>
              {skinArt(deal.key) ? <Image source={skinArt(deal.key)!} style={{ width: 96, height: 96 }} resizeMode="contain" /> : null}
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Row style={{ gap: 6 }}>
                <View style={{ paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.error }}><Txt v="caption" color={colors.onSurface} style={{ fontFamily: fonts.bodyBold }}>-{c.deal.discount_pct}%</Txt></View>
                <Txt v="caption" color={colors.goldBright}>Offerta del giorno</Txt>
              </Row>
              <Txt v="h3" numberOfLines={1}>{deal.name}</Txt>
              <Row style={{ gap: 8 }}>
                <Res kind="rubies" value={c.deal.rubies} size={15} />
                <Txt v="small" color={colors.muted} style={{ textDecorationLine: "line-through" }}>{c.deal.original_rubies}</Txt>
              </Row>
              <Txt v="caption" color={colors.onSurface} testID="daily-deal-countdown">Scade tra {fmtDuration(dealLeft)}</Txt>
            </View>
            <View style={{ gap: 6 }}>
              {deal.owned ? <Btn title={deal.equipped ? "Indossata" : "Indossa"} small variant="secondary" disabled={deal.equipped} onPress={() => equip.mutate({ kind: deal.kind, key: deal.key })} testID="daily-deal-equip" />
                : <Btn title={`${c.deal.rubies}`} icon="diamond-stone" small variant="gold" disabled={c.rubies < c.deal.rubies} loading={buy.isPending} onPress={() => buy.mutate({ key: deal.key })} testID="daily-deal-buy" />}
              <Btn title="Anteprima" small variant="ghost" icon="play" onPress={() => router.push({ pathname: "/skin-preview", params: { key: deal.key } })} testID="daily-deal-preview" />
            </View>
          </Row>
        </Pressable>
      ) : null}

      {SKIN_SECTIONS.map((s) => {
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
                const price = x.rubies_now ?? x.rubies;
                const onDeal = price !== x.rubies;
                const canBuy = c.rubies >= price;
                return (
                  <View key={x.key} style={{ width: 168, borderRadius: 10, borderWidth: 2, borderColor: x.equipped ? colors.goldBright : col, backgroundColor: colors.surfaceSecondary, overflow: "hidden" }} testID={`skin-${x.key}`}>
                    <Pressable onPress={() => router.push({ pathname: "/skin-preview", params: { key: x.key } })} testID={`preview-${x.key}`} style={{ height: 150, alignItems: "center", justifyContent: "flex-end", backgroundColor: colors.surfaceTertiary }}>
                      <LinearGradient colors={[col + "55", "rgba(0,0,0,0)"]} style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }} />
                      {s.kind === "army" ? <View style={{ position: "absolute", bottom: 6, width: 120, height: 16, borderRadius: 999, backgroundColor: x.glow, opacity: 0.35 }} /> : null}
                      {skinArt(x.key) ? <Image source={skinArt(x.key)!} style={{ width: 150, height: 140 }} resizeMode="contain" /> : <Icon name={s.icon} size={64} color={col} />}
                      {x.equipped ? (
                        <View style={{ position: "absolute", top: 6, left: 6, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.goldBright }}>
                          <Txt v="caption" color={colors.onBrandPrimary} style={{ fontFamily: fonts.bodyBold }}>Indossata</Txt>
                        </View>
                      ) : onDeal ? (
                        <View style={{ position: "absolute", top: 6, left: 6, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: colors.error }}>
                          <Txt v="caption" color={colors.onSurface} style={{ fontFamily: fonts.bodyBold }}>-{c.deal.discount_pct}%</Txt>
                        </View>
                      ) : null}
                      <View style={{ position: "absolute", top: 6, right: 6, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, backgroundColor: col }}>
                        <Txt v="caption" color={colors.onBrandPrimary}>{RARITY_LABEL[x.rarity] ?? x.rarity}</Txt>
                      </View>
                      <View style={{ position: "absolute", bottom: 6, right: 6, width: 26, height: 26, borderRadius: 13, backgroundColor: colors.overlay, borderWidth: 1, borderColor: colors.gold, alignItems: "center", justifyContent: "center" }}>
                        <Icon name="play" size={14} color={colors.goldBright} />
                      </View>
                    </Pressable>
                    <View style={{ padding: 8, gap: 4 }}>
                      <Txt v="h3" numberOfLines={1}>{x.name}</Txt>
                      <Txt v="small" color={colors.muted} numberOfLines={3} style={{ minHeight: 44 }}>{x.desc}</Txt>
                      {x.owned ? (
                        <Btn title={x.equipped ? "Indossata" : "Indossa"} small variant={x.equipped ? "secondary" : "gold"} disabled={x.equipped} loading={equip.isPending} onPress={() => equip.mutate({ kind: s.kind, key: x.key })} testID={`equip-${x.key}`} />
                      ) : (
                        <Pressable onPress={() => canBuy && buy.mutate({ key: x.key })} disabled={!canBuy || buy.isPending} style={{ height: 36, borderRadius: 6, backgroundColor: canBuy ? colors.brandPrimary : colors.surfaceTertiary, borderWidth: 1, borderColor: canBuy ? colors.goldBright : colors.iron, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, opacity: buy.isPending ? 0.6 : 1 }} testID={`buy-${x.key}`}>
                          <Res kind="rubies" value={price} size={14} />
                          {onDeal ? <Txt v="caption" color={colors.muted} style={{ textDecorationLine: "line-through" }}>{x.rubies}</Txt> : null}
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
