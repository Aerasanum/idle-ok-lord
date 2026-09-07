// Item icon: generated illustration per slot × rarity tier inside a rarity frame (vector glyph fallback).
import React from "react";
import { Image, View } from "react-native";

import { itemArt } from "@/src/art";
import { rarityColor, useTheme } from "@/src/theme";
import { Icon, RarityFrame, SLOT_ICON, Txt } from "@/src/ui";

const GLOW = ["legendary", "mythic", "ancient"];

export function ItemIcon({ slot, rarity, size = 56, forge, testID, children }: { slot: string; rarity: string; size?: number; forge?: number; testID?: string; children?: React.ReactNode }) {
  const { colors } = useTheme();
  const img = itemArt(slot, rarity);
  const col = rarityColor(colors, rarity);
  return (
    <RarityFrame rarity={rarity} size={size} testID={testID}>
      {GLOW.includes(rarity) ? <View style={{ position: "absolute", width: size * 0.7, height: size * 0.7, borderRadius: size, backgroundColor: col, opacity: 0.3 }} /> : null}
      {img ? <Image source={img} style={{ width: size * 0.8, height: size * 0.8 }} resizeMode="contain" testID={testID ? `${testID}-art` : undefined} /> : <Icon name={SLOT_ICON[slot]} size={size * 0.45} color={col} />}
      {forge ? (
        <View style={{ position: "absolute", bottom: -2, right: -2, paddingHorizontal: 3, borderRadius: 3, backgroundColor: colors.gold }}>
          <Txt v="small" color={colors.onBrandSecondary} style={{ fontSize: Math.max(9, size * 0.15), lineHeight: Math.max(12, size * 0.2) }}>+{forge}</Txt>
        </View>
      ) : null}
      {children}
    </RarityFrame>
  );
}
