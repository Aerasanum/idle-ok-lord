// Ten campaign regions: distinct sky/ground/fog/prop language (Art Direction v1.1). Colors are region identity (fixed art), not theme tokens.
export type RegionPalette = { sky: [string, string]; ground: string; groundAlt: string; fog: string; accent: string; props: "trees" | "swamp" | "ruins" | "dunes" | "peaks" | "ice" | "graves" | "obsidian" | "shards" | "void"; monster: string[] };

export const REGIONS: Record<number, RegionPalette> = {
  1: { sky: ["#3E5B3A", "#9AB27A"], ground: "#4F6B3A", groundAlt: "#3C5230", fog: "rgba(200,220,170,0.25)", accent: "#B89947", props: "trees", monster: ["#6B8E23", "#8B6B3E", "#5C7A3A"] },
  2: { sky: ["#1E2B2A", "#4C6A5A"], ground: "#2F3F32", groundAlt: "#24302A", fog: "rgba(120,160,130,0.35)", accent: "#7FB08A", props: "swamp", monster: ["#4E6E52", "#6E5A3A", "#3E5B49"] },
  3: { sky: ["#3A3F4B", "#8A8D88"], ground: "#5A5A55", groundAlt: "#46463F", fog: "rgba(180,180,170,0.3)", accent: "#C0B8A0", props: "ruins", monster: ["#8A8A7A", "#5B6068", "#7A6A5A"] },
  4: { sky: ["#8A5A2B", "#E7B872"], ground: "#C99A5B", groundAlt: "#A97E47", fog: "rgba(240,200,140,0.35)", accent: "#E3C16F", props: "dunes", monster: ["#B5813E", "#8C5A2E", "#D0A15A"] },
  5: { sky: ["#2E3A55", "#7C8DA8"], ground: "#5B6478", groundAlt: "#464E60", fog: "rgba(200,210,230,0.3)", accent: "#B8C4D8", props: "peaks", monster: ["#7A8398", "#4A5063", "#9AA3B5"] },
  6: { sky: ["#23385A", "#9CC5E6"], ground: "#B9D4E6", groundAlt: "#93B2C9", fog: "rgba(220,240,255,0.45)", accent: "#E6F4FF", props: "ice", monster: ["#7FB3D5", "#4B6F8E", "#D6EBF7"] },
  7: { sky: ["#171522", "#3B3350"], ground: "#2E2A3A", groundAlt: "#23202C", fog: "rgba(110,90,140,0.4)", accent: "#8E7BB5", props: "graves", monster: ["#6E6A8A", "#3F3A55", "#A29BC0"] },
  8: { sky: ["#3B0F0C", "#B0361D"], ground: "#3A1F1A", groundAlt: "#2A1512", fog: "rgba(255,110,40,0.3)", accent: "#FF7A2F", props: "obsidian", monster: ["#B0361D", "#5A1B12", "#FF9A3F"] },
  9: { sky: ["#0F2140", "#4F7FC9"], ground: "#233A66", groundAlt: "#1A2C4E", fog: "rgba(120,180,255,0.35)", accent: "#8FD3FF", props: "shards", monster: ["#4F7FC9", "#2C4A80", "#9FE0FF"] },
  10: { sky: ["#05060C", "#2B1A4A"], ground: "#1A1230", groundAlt: "#120C22", fog: "rgba(180,120,255,0.3)", accent: "#E5E4E2", props: "void", monster: ["#7E4FC9", "#3B2466", "#E5E4E2"] },
};

export function paletteFor(region: number): RegionPalette {
  return REGIONS[Math.max(1, Math.min(10, region))];
}

export function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return Math.abs(h >>> 0);
}
