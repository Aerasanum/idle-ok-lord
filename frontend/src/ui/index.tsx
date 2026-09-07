import { MaterialDesignIcons } from "@react-native-vector-icons/material-design-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Text, TextInput, TextProps, View, ViewProps } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import { runOnJS, useSharedValue } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { resourceArt } from "@/src/art";
import { fonts, makeStyles, radius, rarityColor, resourceColor, spacing, useTheme } from "@/src/theme";
import { UI_SCALE_MAX, UI_SCALE_MIN, getUiScale, setUiScale, stepUiScale, useUiScale } from "./uiScale";

export type IconName = React.ComponentProps<typeof MaterialDesignIcons>["name"];

export function Icon({ name, size = 18, color }: { name: IconName; size?: number; color?: string }) {
  const { colors } = useTheme();
  return <MaterialDesignIcons name={name} size={size} color={color ?? colors.onSurface} />;
}

// ---- typography ------------------------------------------------------------------------
type TxtVariant = "title" | "h1" | "h2" | "h3" | "body" | "bodyBold" | "small" | "caption" | "num";
export function Txt({ v = "body", style, color, children, ...rest }: TextProps & { v?: TxtVariant; color?: string }) {
  const s = useTxt();
  const k = useUiScale();
  const base = s[v] as { fontSize: number; lineHeight?: number };
  const scaled = k !== 1 ? { fontSize: base.fontSize * k, lineHeight: base.lineHeight ? base.lineHeight * k : undefined } : null;
  return (
    <Text {...rest} style={[s[v], scaled, color ? { color } : null, style]}>
      {children}
    </Text>
  );
}

/** Compact UI zoom control (−/+): scales every Txt on text pages. */
export function ZoomPill({ testID = "ui-zoom" }: { testID?: string }) {
  const { colors } = useTheme();
  const k = useUiScale();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: colors.wood, borderRadius: 6, backgroundColor: colors.overlay }} testID={testID}>
      <Pressable onPress={() => stepUiScale(-1)} disabled={k <= UI_SCALE_MIN + 0.001} style={{ width: 30, height: 30, alignItems: "center", justifyContent: "center", opacity: k <= UI_SCALE_MIN + 0.001 ? 0.4 : 1 }} testID={`${testID}-out`} hitSlop={4}>
        <Icon name="magnify-minus-outline" size={16} color={colors.goldBright} />
      </Pressable>
      <Text style={{ fontFamily: fonts.bodyMedium, fontSize: 10, color: colors.onSurface, minWidth: 30, textAlign: "center" }} testID={`${testID}-value`}>{Math.round(k * 100)}%</Text>
      <Pressable onPress={() => stepUiScale(1)} disabled={k >= UI_SCALE_MAX - 0.001} style={{ width: 30, height: 30, alignItems: "center", justifyContent: "center", opacity: k >= UI_SCALE_MAX - 0.001 ? 0.4 : 1 }} testID={`${testID}-in`} hitSlop={4}>
        <Icon name="magnify-plus-outline" size={16} color={colors.goldBright} />
      </Pressable>
    </View>
  );
}

/** Pinch anywhere on a text page to change the UI zoom (mobile); the ZoomPill covers web/mouse. */
export function UiPinch({ children }: { children: React.ReactNode }) {
  const start = useSharedValue(1);
  const apply = (v: number) => setUiScale(v);
  const pinch = Gesture.Pinch()
    .onStart(() => {
      start.value = getUiScale();
    })
    .onUpdate((e) => {
      runOnJS(apply)(start.value * e.scale);
    });
  return (
    <GestureDetector gesture={pinch}>
      <View style={{ flex: 1 }} collapsable={false}>{children}</View>
    </GestureDetector>
  );
}
const useTxt = makeStyles((c) => ({
  title: { fontFamily: fonts.display, fontSize: 32, color: c.goldBright, letterSpacing: 0.5 },
  h1: { fontFamily: fonts.display, fontSize: 26, color: c.onSurface },
  h2: { fontFamily: fonts.displaySemi, fontSize: 21, color: c.onSurface },
  h3: { fontFamily: fonts.displaySemi, fontSize: 17, color: c.onSurface },
  body: { fontFamily: fonts.body, fontSize: 14, color: c.onSurface, lineHeight: 20 },
  bodyBold: { fontFamily: fonts.bodyBold, fontSize: 14, color: c.onSurface, lineHeight: 20 },
  small: { fontFamily: fonts.body, fontSize: 12, color: c.onSurface, lineHeight: 16 },
  caption: { fontFamily: fonts.bodyMedium, fontSize: 11, color: c.muted, letterSpacing: 0.6, textTransform: "uppercase" },
  num: { fontFamily: fonts.displaySemi, fontSize: 18, color: c.goldBright },
}));

// ---- panels ---------------------------------------------------------------------------------
export function Panel({ children, style, variant = "iron", ...rest }: ViewProps & { variant?: "iron" | "parchment" | "wood" }) {
  const s = usePanel();
  return (
    <View {...rest} style={[s.base, s[variant], style]}>
      <View style={s.inner}>{children}</View>
    </View>
  );
}
const usePanel = makeStyles((c) => ({
  base: { borderWidth: 2, borderRadius: radius.md, padding: 3 },
  iron: { backgroundColor: c.ironDark, borderColor: c.iron },
  parchment: { backgroundColor: c.parchmentDark, borderColor: c.gold },
  wood: { backgroundColor: c.woodDark, borderColor: c.wood },
  inner: { borderWidth: 1, borderColor: "rgba(184,153,71,0.35)", borderRadius: radius.sm, padding: spacing.md, backgroundColor: "rgba(17,21,28,0.55)" },
}));

export function Divider() {
  const { colors } = useTheme();
  return <View style={{ height: 1, backgroundColor: colors.divider, marginVertical: spacing.sm }} />;
}

// ---- buttons ---------------------------------------------------------------------------------
type BtnVariant = "primary" | "gold" | "secondary" | "ghost" | "danger";
export function Btn({ title, onPress, variant = "primary", icon, disabled, loading, small, testID, style }: { title: string; onPress?: () => void; variant?: BtnVariant; icon?: IconName; disabled?: boolean; loading?: boolean; small?: boolean; testID?: string; style?: any }) {
  const s = useBtn();
  const { colors } = useTheme();
  const textColor = variant === "gold" ? colors.onBrandSecondary : variant === "ghost" ? colors.goldBright : colors.onBrandPrimary;
  return (
    <Pressable testID={testID} onPress={onPress} disabled={disabled || loading} style={({ pressed }) => [s.base, s[variant], small && s.small, (disabled || loading) && s.disabled, pressed && s.pressed, style]}>
      {loading ? <ActivityIndicator color={textColor} /> : (
        <>
          {icon ? <Icon name={icon} size={small ? 14 : 18} color={textColor} /> : null}
          <Text style={[s.text, small && s.textSmall, { color: textColor }]}>{title}</Text>
        </>
      )}
    </Pressable>
  );
}
const useBtn = makeStyles((c) => ({
  base: { minHeight: 48, paddingHorizontal: 18, borderRadius: radius.md, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: 8, borderWidth: 2 },
  small: { minHeight: 36, paddingHorizontal: 12 },
  primary: { backgroundColor: c.brandPrimary, borderColor: c.gold },
  gold: { backgroundColor: c.brandSecondary, borderColor: c.goldBright },
  secondary: { backgroundColor: c.surfaceTertiary, borderColor: c.iron },
  ghost: { backgroundColor: "transparent", borderColor: c.gold },
  danger: { backgroundColor: c.error, borderColor: c.burgundy },
  disabled: { opacity: 0.45 },
  pressed: { transform: [{ scale: 0.97 }], opacity: 0.9 },
  text: { fontFamily: fonts.displaySemi, fontSize: 17, letterSpacing: 0.4 },
  textSmall: { fontSize: 14 },
}));

// ---- inputs ----------------------------------------------------------------------------------
export function Input(props: React.ComponentProps<typeof TextInput> & { label?: string }) {
  const s = useInput();
  const { colors } = useTheme();
  return (
    <View style={{ gap: 6 }}>
      {props.label ? <Txt v="caption">{props.label}</Txt> : null}
      <TextInput placeholderTextColor={colors.muted} {...props} style={[s.input, props.style]} />
    </View>
  );
}
const useInput = makeStyles((c) => ({
  input: { backgroundColor: c.surfaceTertiary, borderColor: c.wood, borderWidth: 2, borderRadius: radius.md, color: c.onSurfaceTertiary, paddingHorizontal: 14, minHeight: 48, fontFamily: fonts.body, fontSize: 15 },
}));

// ---- chips / stats / progress ----------------------------------------------------------------------
export function Chip({ label, selected, onPress, testID }: { label: string; selected?: boolean; onPress?: () => void; testID?: string }) {
  const s = useChip();
  return (
    <Pressable testID={testID} onPress={onPress} style={[s.chip, selected && s.selected]}>
      <Text style={[s.text, selected && s.textSel]}>{label}</Text>
    </Pressable>
  );
}
const useChip = makeStyles((c) => ({
  chip: { height: 36, paddingHorizontal: 14, borderRadius: radius.pill, borderWidth: 1.5, borderColor: c.iron, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  selected: { borderColor: c.goldBright, backgroundColor: c.brandPrimary },
  text: { fontFamily: fonts.bodyMedium, fontSize: 13, color: c.muted },
  textSel: { color: c.onBrandPrimary },
}));

export function ChipRow({ children }: { children: React.ReactNode }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ height: 56, flexGrow: 0 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16, alignItems: "center" }}>
      {children}
    </ScrollView>
  );
}

export function Progress({ value, max, color, height = 10, label, testID }: { value: number; max: number; color?: string; height?: number; label?: string; testID?: string }) {
  const { colors } = useTheme();
  const pct = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0;
  return (
    <View testID={testID} style={{ gap: 3 }}>
      <View style={{ height, backgroundColor: colors.surfaceTertiary, borderRadius: radius.sm, borderWidth: 1, borderColor: colors.wood, overflow: "hidden" }}>
        <LinearGradient colors={[color ?? colors.gold, color ?? colors.goldBright]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={{ width: `${pct * 100}%`, height: "100%" }} />
      </View>
      {label ? <Txt v="small" color={colors.muted}>{label}</Txt> : null}
    </View>
  );
}

export function Stat({ label, value, color, testID }: { label: string; value: string | number; color?: string; testID?: string }) {
  return (
    <View style={{ alignItems: "center", minWidth: 64 }} testID={testID}>
      <Txt v="num" color={color}>{typeof value === "number" ? fmt(value) : value}</Txt>
      <Txt v="caption">{label}</Txt>
    </View>
  );
}

export const RES_ICON: Record<string, IconName> = { grain: "barley", wood: "pine-tree", clay: "cube", iron: "anvil", gold: "gold", rubies: "diamond-stone", forge_dust: "creation", reforge_stone: "hexagon-slice-6", mythic_essence: "star-four-points", war_coins: "shield-sword", event_tokens: "ticket" };
export const RES_LABEL: Record<string, string> = { grain: "Grano", wood: "Legno", clay: "Argilla", iron: "Ferro", gold: "Oro", rubies: "Rubini", forge_dust: "Polvere", reforge_stone: "Pietre", mythic_essence: "Essenza", war_coins: "Monete", event_tokens: "Gettoni" };

export function Res({ kind, value, size = 14, testID, art: withArt }: { kind: string; value: number | string; size?: number; testID?: string; art?: boolean }) {
  const { colors } = useTheme();
  const img = withArt ? resourceArt(kind) : undefined;
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }} testID={testID}>
      {img ? <Image source={img} style={{ width: size * 1.6, height: size * 1.6 }} resizeMode="contain" testID={testID ? `${testID}-art` : undefined} /> : <Icon name={RES_ICON[kind] ?? "circle"} size={size} color={resourceColor(colors, kind)} />}
      <Text style={{ fontFamily: fonts.displaySemi, fontSize: size + 1, color: colors.onSurface }}>{typeof value === "number" ? fmt(value) : value}</Text>
    </View>
  );
}

export function ResourceBar({ resources, compact }: { resources: Record<string, number>; compact?: boolean }) {
  const s = useBar();
  const keys = compact ? ["gold", "rubies"] : ["grain", "wood", "clay", "iron", "gold", "rubies"];
  return (
    <View style={s.bar} testID="resource-bar">
      {keys.map((k) => (
        <Res key={k} kind={k} value={resources?.[k] ?? 0} size={13} testID={`res-${k}`} />
      ))}
      <View style={{ marginLeft: "auto" }}><ZoomPill testID="ui-zoom-bar" /></View>
    </View>
  );
}
const useBar = makeStyles((c) => ({ bar: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 10, paddingHorizontal: 12, paddingVertical: 4, backgroundColor: c.overlay, borderBottomWidth: 2, borderColor: c.gold } }));

export function fmt(n: number): string {
  if (n === undefined || n === null || isNaN(n)) return "0";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (a >= 10000) return (n / 1e3).toFixed(1) + "K";
  return Math.round(n).toLocaleString("it-IT");
}

export function fmtDuration(sec: number): string {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  if (h >= 24) return `${Math.floor(h / 24)}g ${h % 24}h`;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s}s`;
  return `${s}s`;
}

export function RarityFrame({ rarity, size = 56, children, testID }: { rarity: string; size?: number; children: React.ReactNode; testID?: string }) {
  const { colors } = useTheme();
  const col = rarityColor(colors, rarity);
  return (
    <View testID={testID} style={{ width: size, height: size, borderWidth: 3, borderColor: col, borderRadius: radius.md, backgroundColor: colors.surfaceTertiary, alignItems: "center", justifyContent: "center", shadowColor: col, shadowOpacity: 0.6, shadowRadius: 6 }}>
      {children}
    </View>
  );
}

export const SLOT_ICON: Record<string, IconName> = { weapon: "sword", offhand: "shield", helmet: "hard-hat", chest: "tshirt-crew", gloves: "hand-back-right", boots: "shoe-formal", cloak: "wizard-hat", ring: "ring", amulet: "necklace" };
export const SLOT_LABEL: Record<string, string> = { weapon: "Arma", offhand: "Secondaria", helmet: "Elmo", chest: "Corazza", gloves: "Guanti", boots: "Stivali", cloak: "Mantello", ring: "Anello", amulet: "Amuleto" };
export const RARITY_LABEL: Record<string, string> = { common: "Comune", uncommon: "Non comune", rare: "Raro", epic: "Epico", legendary: "Leggendario", mythic: "Mitico", ancient: "Antico" };

// ---- screen scaffolding -----------------------------------------------------------------------
export function Screen({ title, subtitle, children, right, scroll = true, back = true, testID }: { title: string; subtitle?: string; children: React.ReactNode; right?: React.ReactNode; scroll?: boolean; back?: boolean; testID?: string }) {
  const s = useScreen();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  return (
    <View style={s.root} testID={testID}>
      <View style={[s.header, { paddingTop: insets.top + 6 }]}>
        {back ? (
          <Pressable onPress={() => (router.canGoBack() ? router.back() : router.replace("/(tabs)/battle"))} style={s.back} testID="header-back-button">
            <Icon name="chevron-left" size={26} color={colors.goldBright} />
          </Pressable>
        ) : <View style={{ width: 8 }} />}
        <View style={{ flex: 1 }}>
          <Txt v="h1" numberOfLines={1}>{title}</Txt>
          {subtitle ? <Txt v="caption">{subtitle}</Txt> : null}
        </View>
        {right}
        <ZoomPill />
      </View>
      <UiPinch>
        {scroll ? (
          <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 24, gap: spacing.md }} showsVerticalScrollIndicator={false}>
            {children}
          </ScrollView>
        ) : (
          <View style={{ flex: 1 }}>{children}</View>
        )}
      </UiPinch>
    </View>
  );
}
const useScreen = makeStyles((c) => ({
  root: { flex: 1, backgroundColor: c.surface },
  header: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 12, paddingBottom: 10, backgroundColor: c.surfaceSecondary, borderBottomWidth: 2, borderColor: c.gold },
  back: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
}));

export function Loading({ label }: { label?: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 10, padding: 32 }} testID="loading-indicator">
      <ActivityIndicator color={colors.goldBright} size="large" />
      {label ? <Txt v="small" color={colors.muted}>{label}</Txt> : null}
    </View>
  );
}

export function Empty({ icon = "shield-off", title, text }: { icon?: IconName; title: string; text?: string }) {
  const { colors } = useTheme();
  return (
    <Panel variant="wood" style={{ marginTop: 8 }}>
      <View style={{ alignItems: "center", gap: 8, paddingVertical: 12 }}>
        <Icon name={icon} size={36} color={colors.gold} />
        <Txt v="h3">{title}</Txt>
        {text ? <Txt v="small" color={colors.muted} style={{ textAlign: "center" }}>{text}</Txt> : null}
      </View>
    </Panel>
  );
}

export function Row({ children, style, gap = 8, testID }: { children: React.ReactNode; style?: any; gap?: number; testID?: string }) {
  return <View testID={testID} style={[{ flexDirection: "row", alignItems: "center", gap }, style]}>{children}</View>;
}
