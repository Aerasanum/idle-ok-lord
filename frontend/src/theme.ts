// Design tokens for IDLE 1 v1.1 — premium medieval-fantasy, dark only (Art Direction v1.1).
// Keys match the "color" block of /app/design_guidelines.json plus game palettes (rarities, resources).
// Components build sheets with makeStyles() and read useTheme().colors for color props.

import { useMemo } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";

const dark = {
  surface: "#11151C", // midnight canvas
  onSurface: "#E6D8B8", // parchment text
  surfaceSecondary: "#1B2029", // panels (iron/stone)
  onSurfaceSecondary: "#E6D8B8",
  surfaceTertiary: "#2A2A35", // inputs, chips
  onSurfaceTertiary: "#F4EBD8",
  surfaceInverse: "#F4EBD8", // parchment sheets
  onSurfaceInverse: "#11151C",
  muted: "#8C929C",

  brand: "#800020", // burgundy
  onBrand: "#F4EBD8",
  brandPrimary: "#800020",
  onBrandPrimary: "#F4EBD8",
  brandSecondary: "#B89947", // antique gold
  onBrandSecondary: "#11151C",
  brandTertiary: "#2E472D", // forest green
  onBrandTertiary: "#F4EBD8",

  success: "#436F4D",
  onSuccess: "#FFFFFF",
  warning: "#C79338",
  onWarning: "#11151C",
  error: "#8B2635",
  onError: "#FFFFFF",
  info: "#4A6B8C",
  onInfo: "#FFFFFF",

  border: "#4A3B2C", // dark wood
  borderStrong: "#B89947", // gold frame
  divider: "#3D3A30",

  // game palettes
  wood: "#4A3B2C",
  woodDark: "#2E241B",
  iron: "#5C6470",
  ironDark: "#3A3F47",
  parchment: "#F4EBD8",
  parchmentDark: "#D9C9A3",
  gold: "#B89947",
  goldBright: "#E3C16F",
  navy: "#1B2A44",
  burgundy: "#800020",
  forest: "#2E472D",
  overlay: "rgba(17,21,28,0.86)",
  scrim: "rgba(0,0,0,0.55)",

  rarity_common: "#8C929C",
  rarity_uncommon: "#548259",
  rarity_rare: "#4169E1",
  rarity_epic: "#7851A9",
  rarity_legendary: "#DAA520",
  rarity_mythic: "#DC143C",
  rarity_ancient: "#E5E4E2",

  res_grain: "#E3C16F",
  res_wood: "#8B5A2B",
  res_clay: "#A36A4F",
  res_iron: "#9AA1A9",
  res_gold: "#FFD700",
  res_rubies: "#E0115F",
  res_forge_dust: "#B0C4DE",
  res_reforge_stone: "#708090",
  res_mythic_essence: "#9370DB",
  res_war_coins: "#B87333",
  res_event_tokens: "#3CB371",
};

export type ThemeColors = typeof dark;

export const defaultScheme = "dark" satisfies ColorScheme;
export const themes: { light: ThemeColors; dark?: ThemeColors } = { light: dark, dark };

export const fonts = {
  display: "CormorantGaramond-Bold",
  displaySemi: "CormorantGaramond-SemiBold",
  displayMedium: "CormorantGaramond-Medium",
  body: "Satoshi-Regular",
  bodyMedium: "Satoshi-Medium",
  bodyBold: "Satoshi-Bold",
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, xxxl: 48 };
export const radius = { sm: 2, md: 6, lg: 12, pill: 999 };

export function setColorScheme(scheme: ColorScheme) {
  Appearance.setColorScheme?.(scheme);
}

setColorScheme("dark");

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors } {
  const system = useColorScheme();
  const scheme: ColorScheme = system === "dark" || system === "light" ? system : defaultScheme;
  return { scheme, colors: themes[scheme] ?? themes.light };
}

export function makeStyles<T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>>(
  factory: (colors: ThemeColors) => T & StyleSheet.NamedStyles<any>,
): () => T {
  return function useStyles(): T {
    const { colors } = useTheme();
    return useMemo(() => StyleSheet.create(factory(colors)), [colors]);
  };
}

export function rarityColor(colors: ThemeColors, rarity: string): string {
  return (colors as any)[`rarity_${rarity}`] ?? colors.rarity_common;
}

export function resourceColor(colors: ThemeColors, res: string): string {
  return (colors as any)[`res_${res}`] ?? colors.gold;
}
