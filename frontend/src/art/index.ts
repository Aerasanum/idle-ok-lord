// Generated art lookup (stylized-3D renders produced by backend/scripts/gen_art.py). Falls back to vector sprites when an asset is missing.
import { ART } from "./manifest";

export function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

export function regionBackground(region: number): number | undefined {
  return ART[`bg/region_${Math.max(1, Math.min(10, region))}`];
}

export function monsterArt(family: string): number | undefined {
  return ART[`monsters/${slug(family)}`];
}

export function lordArt(equipped: Record<string, any>, tier: number): number | undefined {
  if (tier >= 5 && ART["lord/royal"]) return ART["lord/royal"];
  if (equipped.chest && ART["lord/armored"]) return ART["lord/armored"];
  return ART["lord/base"];
}

export function buildingArt(key: string, tier: number): number | undefined {
  if (key === "castle") {
    if (tier >= 5 && ART["buildings/castle_royal"]) return ART["buildings/castle_royal"];
    if (tier >= 3 && ART["buildings/castle_fortress"]) return ART["buildings/castle_fortress"];
  }
  return ART[`buildings/${key}`];
}

export const kingdomGround = (): number | undefined => ART["kingdom/ground"];

export function unitArt(key: string): number | undefined {
  return ART[`units/${key}`];
}

const ITEM_TIER: Record<string, string> = { common: "basic_a", uncommon: "basic_b", rare: "fine_a", epic: "fine_b", legendary: "ornate", mythic: "ornate", ancient: "ornate" };
export function itemArt(slot: string, rarity: string): number | undefined {
  return ART[`items/${slot}_${ITEM_TIER[rarity] ?? "basic_a"}`];
}

export function resourceArt(kind: string): number | undefined {
  return ART[`resources/${kind}`];
}
