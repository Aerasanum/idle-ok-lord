// Enemy sprites: vector silhouettes per archetype (Art Direction v1.1 monster regions). Colors are fixed art identity, not theme tokens.
import React, { memo, useEffect } from "react";
import { Image, View } from "react-native";
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import Svg, { Circle, Ellipse, G, Path, Rect } from "react-native-svg";

import { monsterArt } from "@/src/art";
import { hashStr } from "./regions";

export type MonsterType = "normal" | "elite" | "boss";
type Arch = "goblin" | "humanoid" | "knight" | "robed" | "canine" | "boar" | "arthropod" | "brute" | "golem" | "treant" | "flyer" | "spirit" | "dragon";

export function archetypeFor(family: string): Arch {
  const f = family.toLowerCase();
  if (/goblin|imp/.test(f)) return "goblin";
  if (/cultist|acolyte|herald/.test(f)) return "robed";
  if (/knight|legionary|soldier/.test(f)) return "knight";
  if (/bandit|raider|marauder/.test(f)) return "humanoid";
  if (/wolf|warg/.test(f)) return "canine";
  if (/boar|beast/.test(f)) return "boar";
  if (/scorpion|spider/.test(f)) return "arthropod";
  if (/golem|colossus|construct/.test(f)) return "golem";
  if (/treant/.test(f)) return "treant";
  if (/troll|ogre|giant|titan|tyrant/.test(f)) return "brute";
  if (/harpy|wyvern|drake|siren|horror|seraph/.test(f)) return "flyer";
  if (/wraith|djinn|spawn|drowned/.test(f)) return "spirit";
  if (/dragon|wyrm|leviathan|devourer/.test(f)) return "dragon";
  return "humanoid";
}

export function shade(hex: string, amt: number): string {
  const n = parseInt(hex.replace("#", ""), 16);
  const ch = (v: number) => Math.max(0, Math.min(255, Math.round(amt < 0 ? v * (1 + amt) : v + (255 - v) * amt)));
  const r = ch((n >> 16) & 255), g = ch((n >> 8) & 255), b = ch(n & 255);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}

const WHITE = "#F4EBD8", INK = "#111111", STEEL = "#8C929C", STEEL_D = "#5C6470", BLADE = "#DDE3EA", GOLD = "#E3C16F", WOOD = "#4A3B2C", BONE = "#D9D0B8";

type P = { body: string; dark: string; light: string; eye: string; undead: boolean; f: string; type: MonsterType };

function Goblin({ body, dark, eye, f }: P) {
  const imp = /imp/.test(f);
  return (
    <G>
      <Path d="M40 72 L36 92 L46 92 L48 74Z" fill={dark} />
      <Path d="M54 74 L58 92 L68 92 L62 72Z" fill={dark} />
      <Path d="M34 48 Q52 40 68 50 L66 76 L36 76Z" fill={body} />
      <Path d="M38 66 L64 66 L62 78 L40 78Z" fill="#5A4632" />
      <Path d="M66 52 L80 70 L74 74 L62 60Z" fill={body} />
      <Path d="M76 72 L88 44" stroke={WOOD} strokeWidth={5} strokeLinecap="round" />
      <Circle cx={88} cy={42} r={6} fill="#6E5A44" />
      <Path d="M36 52 L22 66 L28 70 L40 60Z" fill={body} />
      <Path d="M22 66 L10 56" stroke={BLADE} strokeWidth={3} strokeLinecap="round" />
      <Circle cx={46} cy={34} r={13} fill={body} />
      <Path d="M34 30 L16 22 L34 38Z" fill={body} />
      <Path d="M58 30 L74 20 L58 38Z" fill={body} />
      <Path d="M36 31 L24 26 L36 35Z" fill={dark} />
      {imp ? <Path d="M40 24 L36 8 L46 22Z" fill={dark} /> : null}
      {imp ? <Path d="M52 24 L58 8 L48 22Z" fill={dark} /> : null}
      {imp ? <Path d="M66 74 Q84 80 82 92" stroke={body} strokeWidth={4} fill="none" strokeLinecap="round" /> : null}
      <Circle cx={41} cy={32} r={3} fill={eye} />
      <Circle cx={50} cy={31} r={3} fill={eye} />
      <Path d="M38 42 L52 42 L50 46 L40 46Z" fill="#2A0F0F" />
      <Path d="M40 42 L42 45 L44 42Z" fill={WHITE} />
      <Path d="M46 42 L48 45 L50 42Z" fill={WHITE} />
    </G>
  );
}

function Humanoid({ body, dark, eye }: P) {
  return (
    <G>
      <Path d="M30 44 L72 44 L78 82 L24 82Z" fill={dark} />
      <Path d="M40 70 L36 92 L46 92 L48 72Z" fill="#3A2F26" />
      <Path d="M54 72 L58 92 L68 92 L62 70Z" fill="#3A2F26" />
      <Path d="M34 42 Q52 36 68 44 L66 72 L36 72Z" fill={body} />
      <Rect x={36} y={62} width={30} height={4} fill="#8A6A3A" />
      <Path d="M66 46 L78 64 L72 68 L62 54Z" fill={body} />
      <Path d="M76 66 L70 20" stroke="#6E5A44" strokeWidth={3} />
      <Path d="M70 20 L84 26 L70 34Z" fill={BLADE} />
      <Path d="M36 48 L20 60 L24 66 L40 58Z" fill={body} />
      <Path d="M20 62 L4 46" stroke={BLADE} strokeWidth={3.5} strokeLinecap="round" />
      <Path d="M16 56 L24 64" stroke={GOLD} strokeWidth={3} />
      <Circle cx={48} cy={32} r={12} fill="#C89B77" />
      <Path d="M34 36 Q36 12 52 14 Q66 16 64 36 L60 30 Q52 26 40 30Z" fill={dark} />
      <Path d="M38 30 Q48 26 58 30 L56 40 Q48 44 40 40Z" fill={INK} />
      <Circle cx={44} cy={34} r={2.5} fill={eye} />
      <Circle cx={53} cy={33} r={2.5} fill={eye} />
    </G>
  );
}

function Knight({ body, dark, eye, undead }: P) {
  const plate = undead ? BONE : STEEL, plateD = undead ? shade(BONE, -0.3) : STEEL_D;
  return (
    <G>
      <Path d="M40 70 L36 92 L46 92 L48 72Z" fill={plateD} />
      <Path d="M54 72 L58 92 L68 92 L62 70Z" fill={plateD} />
      <Path d="M32 42 Q50 34 68 42 L66 72 L34 72Z" fill={plate} />
      <Path d="M42 48 L58 48 L56 70 L44 70Z" fill={body} />
      <Path d="M50 42 L50 48" stroke={plateD} strokeWidth={2} />
      <Circle cx={34} cy={46} r={8} fill={plateD} />
      <Circle cx={66} cy={46} r={8} fill={plateD} />
      <Path d="M66 46 L78 62 L72 66 L62 52Z" fill={plateD} />
      <Path d="M76 62 L84 16" stroke={BLADE} strokeWidth={4} strokeLinecap="round" />
      <Path d="M70 58 L82 66" stroke={GOLD} strokeWidth={3} />
      <Path d="M14 46 L34 46 L34 66 Q24 78 14 66Z" fill={body} stroke={GOLD} strokeWidth={2} />
      <Path d="M20 50 L28 50 L28 64 L20 64Z" fill={dark} />
      {undead ? (
        <G>
          <Circle cx={50} cy={30} r={13} fill={BONE} />
          <Circle cx={45} cy={29} r={3.5} fill={INK} />
          <Circle cx={55} cy={29} r={3.5} fill={INK} />
          <Circle cx={45} cy={29} r={1.5} fill={eye} />
          <Circle cx={55} cy={29} r={1.5} fill={eye} />
          <Path d="M42 38 L58 38 L56 44 L44 44Z" fill={BONE} />
          <Path d="M46 38 L46 44 M50 38 L50 44 M54 38 L54 44" stroke={INK} strokeWidth={1} />
        </G>
      ) : (
        <G>
          <Path d="M36 34 Q36 14 50 14 Q64 14 64 34 L64 42 L36 42Z" fill={plate} />
          <Rect x={38} y={30} width={26} height={5} fill={INK} />
          <Circle cx={44} cy={32.5} r={2} fill={eye} />
          <Circle cx={54} cy={32.5} r={2} fill={eye} />
          <Path d="M50 14 Q60 4 72 12 Q60 10 52 18Z" fill={body} />
        </G>
      )}
    </G>
  );
}

function Robed({ body, dark, eye, f }: P) {
  const horns = /herald|infernal|demon/.test(f);
  return (
    <G>
      <Path d="M36 40 Q50 32 64 40 L74 92 L26 92Z" fill={body} />
      <Path d="M50 44 L46 92" stroke={dark} strokeWidth={2} />
      <Path d="M50 44 L58 92" stroke={dark} strokeWidth={2} />
      <Path d="M40 60 L62 58 L62 64 L40 66Z" fill={GOLD} />
      <Path d="M64 46 L78 62 L72 66 L60 54Z" fill={dark} />
      <Path d="M36 46 L18 62 L24 68 L40 56Z" fill={dark} />
      <Path d="M20 66 L14 20" stroke={WOOD} strokeWidth={3.5} />
      <Circle cx={13} cy={16} r={10} fill={eye} opacity={0.25} />
      <Circle cx={13} cy={16} r={6} fill={eye} opacity={0.9} />
      <Path d="M34 40 Q34 10 50 10 Q66 10 66 40 Q58 34 50 34 Q42 34 34 40Z" fill={dark} />
      {horns ? <Path d="M40 16 Q34 6 38 -2 Q40 8 46 14Z" fill="#B0361D" /> : null}
      {horns ? <Path d="M60 16 Q66 6 62 -2 Q60 8 54 14Z" fill="#B0361D" /> : null}
      <Path d="M40 30 Q50 26 60 30 L58 40 Q50 44 42 40Z" fill={INK} />
      <Circle cx={45} cy={34} r={2.5} fill={eye} />
      <Circle cx={55} cy={34} r={2.5} fill={eye} />
    </G>
  );
}

function Canine({ body, dark, eye }: P) {
  return (
    <G>
      <Path d="M84 58 Q98 44 90 34" stroke={body} strokeWidth={7} strokeLinecap="round" fill="none" />
      <Path d="M70 72 L78 92 L86 92 L80 70Z" fill={dark} />
      <Path d="M62 74 L64 92 L72 92 L70 72Z" fill={dark} />
      <Path d="M26 54 Q36 44 62 46 Q84 48 86 62 Q84 76 62 76 L30 74 Q22 66 26 54Z" fill={body} />
      <Path d="M34 50 L40 42 L46 50 L52 42 L58 50 L64 44 L70 52" stroke={dark} strokeWidth={3} fill="none" strokeLinejoin="round" />
      <Path d="M30 72 L24 92 L32 92 L38 74Z" fill={dark} />
      <Path d="M40 74 L38 92 L46 92 L48 74Z" fill={body} />
      <Path d="M28 50 L8 56 L4 64 L14 68 L30 70Z" fill={body} />
      <Path d="M26 50 L24 34 L36 50Z" fill={body} />
      <Path d="M27 48 L26 40 L32 48Z" fill={dark} />
      <Path d="M6 64 L14 70 L26 70 L22 64Z" fill={dark} />
      <Path d="M10 64 L12 69 L14 64Z" fill={WHITE} />
      <Path d="M18 64 L20 69 L22 64Z" fill={WHITE} />
      <Circle cx={18} cy={56} r={3} fill={eye} />
      <Circle cx={6} cy={60} r={2} fill={INK} />
    </G>
  );
}

function Boar({ body, dark, light, eye }: P) {
  return (
    <G>
      <Path d="M86 60 Q96 54 92 46" stroke={dark} strokeWidth={4} strokeLinecap="round" fill="none" />
      <Path d="M68 74 L72 92 L82 92 L80 72Z" fill={dark} />
      <Path d="M30 74 L26 92 L36 92 L40 74Z" fill={dark} />
      <Path d="M22 56 Q30 40 60 42 Q88 44 88 64 Q86 78 60 78 L30 76 Q18 70 22 56Z" fill={body} />
      <Path d="M30 46 L34 34 L40 44 L46 32 L52 42 L58 32 L64 42 L70 36 L74 46" stroke={dark} strokeWidth={4} fill="none" strokeLinejoin="round" />
      <Path d="M56 76 L58 92 L68 92 L66 76Z" fill={body} />
      <Path d="M42 76 L40 92 L50 92 L52 76Z" fill={body} />
      <Path d="M26 50 L6 58 L8 70 L30 74Z" fill={dark} />
      <Circle cx={8} cy={66} r={5} fill={light} />
      <Circle cx={6} cy={65} r={1.2} fill={INK} />
      <Circle cx={10} cy={66} r={1.2} fill={INK} />
      <Path d="M12 72 Q2 66 6 58" stroke={WHITE} strokeWidth={3} fill="none" strokeLinecap="round" />
      <Path d="M18 72 Q10 68 12 60" stroke={WHITE} strokeWidth={3} fill="none" strokeLinecap="round" />
      <Circle cx={16} cy={58} r={2.6} fill={eye} />
    </G>
  );
}

function Arthropod({ body, dark, eye, f }: P) {
  const spider = /spider/.test(f);
  return (
    <G>
      {spider ? <Ellipse cx={64} cy={60} rx={26} ry={20} fill={body} /> : <Path d="M80 62 Q100 50 92 30 Q88 22 82 26" stroke={body} strokeWidth={8} strokeLinecap="round" fill="none" />}
      {spider ? <Path d="M56 48 Q64 44 72 48 M52 60 Q64 52 76 60" stroke={dark} strokeWidth={2} fill="none" /> : <Path d="M82 26 L74 18 L80 32Z" fill={dark} />}
      {!spider ? <Ellipse cx={64} cy={66} rx={20} ry={12} fill={body} /> : null}
      <Ellipse cx={spider ? 34 : 44} cy={66} rx={16} ry={11} fill={body} />
      <Ellipse cx={spider ? 20 : 28} cy={66} rx={12} ry={9} fill={dark} />
      <Path d="M36 70 L26 92 M44 72 L40 92 M56 72 L60 92 M66 70 L78 92" stroke={dark} strokeWidth={3} strokeLinecap="round" />
      <Path d="M38 66 L22 84 M60 66 L74 86" stroke={dark} strokeWidth={3} strokeLinecap="round" />
      {spider ? <Path d="M30 60 L10 44 M40 58 L26 40 M68 60 L86 40 M76 62 L94 50" stroke={dark} strokeWidth={3} strokeLinecap="round" /> : null}
      {!spider ? <Path d="M18 62 Q6 56 8 66 Q12 72 20 68Z" fill={dark} /> : null}
      {!spider ? <Path d="M22 70 Q8 74 10 82 Q14 86 24 76Z" fill={dark} /> : null}
      {spider ? <Path d="M12 70 L8 80 M18 72 L16 82" stroke={WHITE} strokeWidth={2.5} strokeLinecap="round" /> : null}
      <Circle cx={spider ? 14 : 20} cy={62} r={2.2} fill={eye} />
      <Circle cx={spider ? 20 : 25} cy={60} r={2.2} fill={eye} />
      {spider ? <Circle cx={16} cy={57} r={1.4} fill={eye} /> : null}
      {spider ? <Circle cx={23} cy={56} r={1.4} fill={eye} /> : null}
    </G>
  );
}

function Brute({ body, dark, eye, type }: P) {
  return (
    <G>
      <Path d="M74 46 L90 78 L82 84 L66 56Z" fill={body} />
      <Circle cx={86} cy={82} r={7} fill={body} />
      <Path d="M86 80 L78 30" stroke={WOOD} strokeWidth={7} strokeLinecap="round" />
      <Path d="M78 30 L70 22 L80 34Z" fill={BLADE} />
      <Path d="M76 36 L84 28 L82 40Z" fill={BLADE} />
      <Path d="M30 72 L24 92 L42 92 L46 74Z" fill={dark} />
      <Path d="M56 74 L60 92 L78 92 L74 72Z" fill={dark} />
      <Path d="M22 42 Q50 22 82 44 Q86 62 78 74 L26 74 Q16 60 22 42Z" fill={body} />
      <Path d="M30 66 L74 66 L70 82 L34 82Z" fill="#5A4632" />
      <Path d="M50 50 Q54 60 48 68" stroke={dark} strokeWidth={2} fill="none" />
      {type !== "normal" ? <Path d="M64 38 L80 34 L82 46 L68 48Z" fill={STEEL_D} /> : null}
      <Path d="M26 48 L10 78 L20 84 L38 56Z" fill={body} />
      <Circle cx={14} cy={82} r={8} fill={body} />
      <Circle cx={34} cy={36} r={11} fill={body} />
      <Path d="M24 32 L44 30 L44 34 L24 36Z" fill={dark} />
      <Circle cx={28} cy={36} r={2.5} fill={eye} />
      <Circle cx={36} cy={35} r={2.5} fill={eye} />
      <Path d="M26 44 L24 50 L30 44Z" fill={WHITE} />
      <Path d="M36 44 L38 50 L40 44Z" fill={WHITE} />
    </G>
  );
}

function Golem({ body, dark, eye, undead }: P) {
  const rock = undead ? BONE : body, rockD = undead ? shade(BONE, -0.3) : dark;
  return (
    <G>
      <Rect x={28} y={68} width={18} height={24} rx={3} fill={rockD} />
      <Rect x={56} y={68} width={18} height={24} rx={3} fill={rockD} />
      <Path d="M14 40 L4 76 L18 80 L26 44Z" fill={rock} />
      <Path d="M86 40 L96 76 L82 80 L74 44Z" fill={rock} />
      <Rect x={2} y={74} width={18} height={14} rx={3} fill={rockD} />
      <Rect x={80} y={74} width={18} height={14} rx={3} fill={rockD} />
      <Path d="M22 36 L80 36 L84 70 L18 70Z" fill={rock} />
      <Path d="M22 36 L40 52 L18 70 M80 36 L62 54 L84 70" stroke={rockD} strokeWidth={2} fill="none" />
      {undead ? <Path d="M34 46 L68 46 M36 54 L66 54 M38 62 L64 62" stroke={rockD} strokeWidth={2.5} /> : null}
      <Path d="M44 44 L50 56 L46 66 M58 42 L56 52 L62 60" stroke={eye} strokeWidth={2.5} fill="none" />
      <Rect x={36} y={18} width={28} height={20} rx={4} fill={rock} />
      <Rect x={40} y={26} width={7} height={4} fill={eye} />
      <Rect x={53} y={26} width={7} height={4} fill={eye} />
    </G>
  );
}

function Treant({ body, eye }: P) {
  return (
    <G>
      <Path d="M30 72 L20 92 L34 92 L40 74Z" fill="#2E241B" />
      <Path d="M58 74 L66 92 L80 92 L70 72Z" fill="#2E241B" />
      <Path d="M22 90 L10 96 M78 90 L92 96" stroke="#2E241B" strokeWidth={4} strokeLinecap="round" />
      <Path d="M32 40 L10 24 M10 24 L4 14 M10 24 L2 32" stroke={WOOD} strokeWidth={6} strokeLinecap="round" />
      <Path d="M68 40 L90 24 L96 14 M90 24 L98 32" stroke={WOOD} strokeWidth={6} strokeLinecap="round" />
      <Path d="M32 30 L68 30 L74 76 L26 76Z" fill={WOOD} />
      <Path d="M40 32 L38 76 M56 32 L60 76" stroke="#2E241B" strokeWidth={2} />
      <Circle cx={50} cy={20} r={16} fill={body} />
      <Circle cx={32} cy={26} r={10} fill={body} />
      <Circle cx={68} cy={26} r={10} fill={body} />
      <Circle cx={8} cy={14} r={6} fill={body} />
      <Circle cx={94} cy={14} r={6} fill={body} />
      <Path d="M40 46 L48 44 L48 50 L40 52Z" fill={eye} />
      <Path d="M60 44 L52 46 L52 50 L60 52Z" fill={eye} />
      <Path d="M42 60 Q50 68 58 60" stroke={INK} strokeWidth={3} fill="none" />
    </G>
  );
}

function Flyer({ body, dark, light, eye, f }: P) {
  const holy = /seraph|angel/.test(f), reptile = /wyvern|drake/.test(f);
  const wing = holy ? "#E6F4FF" : dark, bone = holy ? GOLD : shade(dark, -0.3);
  return (
    <G>
      <Path d="M50 48 Q30 16 4 30 Q22 34 30 56Z" fill={wing} />
      <Path d="M50 48 Q70 16 96 30 Q78 34 70 56Z" fill={wing} />
      <Path d="M50 48 L14 30 M50 48 L26 42 M50 48 L86 30 M50 48 L74 42" stroke={bone} strokeWidth={2} />
      {holy ? <Ellipse cx={40} cy={26} rx={12} ry={3.5} stroke={GOLD} strokeWidth={2.5} fill="none" /> : null}
      <Ellipse cx={50} cy={60} rx={13} ry={18} fill={body} />
      <Path d="M44 76 L40 88 M48 76 L48 88 M56 76 L58 88" stroke={dark} strokeWidth={3} strokeLinecap="round" />
      {reptile ? <Path d="M60 72 Q80 84 92 76" stroke={body} strokeWidth={5} fill="none" strokeLinecap="round" /> : null}
      {reptile ? <Path d="M92 76 L98 70 L96 82Z" fill={dark} /> : null}
      <Circle cx={40} cy={42} r={9} fill={body} />
      {reptile ? <Path d="M32 42 L18 46 L32 50Z" fill={light} /> : <Path d="M32 42 L22 46 L32 48Z" fill={dark} />}
      {reptile ? <Path d="M42 34 L46 20 L48 34Z" fill={dark} /> : null}
      {reptile ? <Path d="M36 34 L38 22 L42 34Z" fill={dark} /> : null}
      <Circle cx={37} cy={41} r={2.5} fill={eye} />
    </G>
  );
}

function Spirit({ body, dark, light, eye, f }: P) {
  const tentacles = /spawn|drowned|leviathan/.test(f);
  return (
    <G>
      <Ellipse cx={50} cy={56} rx={30} ry={36} fill={body} opacity={0.18} />
      <Path d="M30 34 Q50 8 70 34 L72 62 Q66 70 62 62 Q58 82 50 70 Q42 82 38 62 Q34 70 28 62Z" fill={body} opacity={0.9} />
      <Path d="M38 36 Q50 20 62 36 L62 56 Q50 66 38 56Z" fill={light} opacity={0.45} />
      <Path d="M32 44 Q14 50 10 66" stroke={body} strokeWidth={6} strokeLinecap="round" fill="none" opacity={0.85} />
      <Path d="M68 44 Q84 52 88 66" stroke={body} strokeWidth={6} strokeLinecap="round" fill="none" opacity={0.85} />
      <Path d="M10 66 L4 72 M10 66 L8 74 M88 66 L94 72 M88 66 L90 74" stroke={dark} strokeWidth={2.5} strokeLinecap="round" />
      {tentacles ? <Path d="M40 70 Q34 84 40 94 M50 72 Q52 86 46 96 M60 70 Q66 84 58 94" stroke={body} strokeWidth={4} strokeLinecap="round" fill="none" opacity={0.8} /> : null}
      <Path d="M36 34 Q50 14 64 34 Q50 40 36 34Z" fill={dark} />
      <Circle cx={44} cy={32} r={6} fill={eye} opacity={0.3} />
      <Circle cx={56} cy={32} r={6} fill={eye} opacity={0.3} />
      <Circle cx={44} cy={32} r={3.5} fill={eye} />
      <Circle cx={56} cy={32} r={3.5} fill={eye} />
    </G>
  );
}

function Dragon({ body, dark, light, eye, f }: P) {
  const winged = /dragon|drake|wyvern|devourer/.test(f);
  return (
    <G>
      {winged ? <Path d="M56 50 Q60 10 96 8 Q84 26 78 46Z" fill={dark} /> : null}
      {winged ? <Path d="M52 50 Q40 14 8 10 Q22 26 30 48Z" fill={dark} /> : null}
      {winged ? <Path d="M56 50 L96 8 M56 50 L84 26 M52 50 L8 10 M52 50 L22 26" stroke={shade(dark, -0.3)} strokeWidth={1.5} /> : null}
      <Path d="M76 66 Q96 60 94 44" stroke={body} strokeWidth={9} strokeLinecap="round" fill="none" />
      <Path d="M94 44 L100 36 L98 50Z" fill={dark} />
      <Path d="M36 78 L30 92 L44 92 L46 80Z" fill={dark} />
      <Path d="M60 80 L62 92 L76 92 L72 80Z" fill={dark} />
      <Path d="M22 62 Q40 44 62 50 Q84 56 84 70 Q80 82 60 82 L30 80 Q16 74 22 62Z" fill={body} />
      <Path d="M28 74 L76 78" stroke={light} strokeWidth={5} strokeLinecap="round" />
      <Path d="M36 50 L38 40 L44 48 L48 38 L54 48 L60 40 L64 50Z" fill={dark} />
      <Path d="M24 60 Q10 52 12 40 L28 44 Q30 54 26 62Z" fill={body} />
      <Path d="M4 36 L2 46 L20 50 L30 40 L22 30Z" fill={body} />
      <Path d="M2 46 L8 54 L20 52 L20 50Z" fill={dark} />
      <Path d="M6 47 L8 51 L10 47Z M12 48 L14 52 L16 48Z" fill={WHITE} />
      <Path d="M24 32 L30 16 L28 34Z" fill={dark} />
      <Path d="M18 30 L18 16 L24 32Z" fill={dark} />
      <Circle cx={14} cy={40} r={3} fill={eye} />
      {/dragon|wyrm|devourer/.test(f) ? <Ellipse cx={1} cy={51} rx={6} ry={3} fill="#FF7A2F" opacity={0.85} /> : null}
    </G>
  );
}

const RENDER: Record<Arch, (p: P) => React.ReactElement> = { goblin: Goblin, humanoid: Humanoid, knight: Knight, robed: Robed, canine: Canine, boar: Boar, arthropod: Arthropod, brute: Brute, golem: Golem, treant: Treant, flyer: Flyer, spirit: Spirit, dragon: Dragon };
const FLOATERS: Arch[] = ["flyer", "spirit"];

export const MonsterSprite = memo(function MonsterSprite({ family, type, palette, size, hurtTick = 0 }: { family: string; type: MonsterType; palette: string[]; size: number; hurtTick?: number }) {
  const h = hashStr(family);
  const arch = archetypeFor(family);
  const f = family.toLowerCase();
  const body = palette[h % palette.length];
  const p: P = { body, dark: shade(body, -0.38), light: shade(body, 0.3), eye: type === "boss" ? "#FFD700" : type === "elite" ? "#7FE3FF" : "#FF3B3B", undead: /undead|bone|skeleton|drowned|fallen/.test(f), f, type };
  const floater = FLOATERS.includes(arch);

  const breath = useSharedValue(0);
  const hurt = useSharedValue(0);
  useEffect(() => {
    const d = 700 + (h % 5) * 90;
    breath.value = withRepeat(withSequence(withTiming(1, { duration: d, easing: Easing.inOut(Easing.quad) }), withTiming(0, { duration: d, easing: Easing.inOut(Easing.quad) })), -1, false);
  }, [breath, h]);
  useEffect(() => {
    if (!hurtTick) return;
    hurt.value = 1;
    hurt.value = withTiming(0, { duration: 280, easing: Easing.out(Easing.quad) });
  }, [hurtTick, hurt]);
  const bodyStyle = useAnimatedStyle(() => ({
    transform: floater
      ? [{ translateY: -6 * breath.value }, { translateX: 6 * hurt.value }]
      : [{ scaleY: 1 + 0.035 * breath.value }, { translateX: 6 * hurt.value }, { rotate: `${-4 * hurt.value}deg` }],
  }));
  const flashStyle = useAnimatedStyle(() => ({ opacity: 0.7 * hurt.value }));
  const img = monsterArt(family);

  if (img) {
    return (
      <Animated.View style={[{ width: size, height: size, justifyContent: "flex-end", alignItems: "center" }, bodyStyle]} testID="monster-art">
        <View style={{ position: "absolute", bottom: size * 0.02, width: size * 0.7, height: size * 0.14, borderRadius: size, backgroundColor: "#000", opacity: floater ? 0.18 : 0.35 }} />
        {type === "boss" ? <View style={{ position: "absolute", bottom: -size * 0.02, width: size * 0.9, height: size * 0.22, borderRadius: size, borderWidth: 3, borderColor: GOLD, opacity: 0.6 }} /> : null}
        <Image source={img} style={{ width: size, height: size }} resizeMode="contain" />
        <Animated.View pointerEvents="none" style={[{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, alignItems: "center", justifyContent: "flex-end" }, flashStyle]}>
          <Image source={img} style={{ width: size, height: size, tintColor: "#FFFFFF" }} resizeMode="contain" />
        </Animated.View>
        {type !== "normal" ? (
          <View style={{ position: "absolute", top: 0, right: size * 0.04, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 3, backgroundColor: "rgba(17,21,28,0.8)", borderWidth: 1, borderColor: type === "boss" ? GOLD : "#C9CED6" }}>
            <Svg width={12} height={12} viewBox="0 0 100 100">{type === "boss" ? <Path d="M14 80 L22 22 L44 52 L50 10 L56 52 L78 22 L86 80Z" fill={GOLD} /> : <Path d="M50 6 L30 60 L70 60Z M22 70 L78 70 L78 90 L22 90Z" fill="#C9CED6" />}</Svg>
          </View>
        ) : null}
      </Animated.View>
    );
  }

  return (
    <Animated.View style={[{ width: size, height: size, justifyContent: "flex-end" }, bodyStyle]}>
      <Svg viewBox="0 0 100 100" width={size} height={size}>
        <Ellipse cx={50} cy={95} rx={floater ? 18 : 26} ry={4.5} fill="#000" opacity={floater ? 0.2 : 0.35} />
        {type === "boss" ? <Ellipse cx={50} cy={92} rx={44} ry={8} stroke={GOLD} strokeWidth={2} fill={GOLD} opacity={0.35} /> : null}
        {type === "boss" ? <Ellipse cx={50} cy={50} rx={46} ry={46} fill={p.eye} opacity={0.10} /> : null}
        {RENDER[arch](p)}
        {type === "elite" ? <Path d="M28 46 L44 40 L42 52Z M72 46 L56 40 L58 52Z" fill="#C9CED6" /> : null}
        {type === "elite" ? <Path d="M50 2 L45 14 L55 14Z" fill="#C9CED6" /> : null}
        {type === "boss" ? <Path d="M34 12 L38 0 L44 10 L50 -2 L56 10 L62 0 L66 12Z" fill={GOLD} /> : null}
        {type === "boss" ? <Rect x={34} y={11} width={32} height={4} fill={GOLD} /> : null}
      </Svg>
      <Animated.View pointerEvents="none" style={[{ position: "absolute", left: size * 0.1, right: size * 0.1, top: size * 0.05, bottom: size * 0.05, borderRadius: size / 2, backgroundColor: "#FFFFFF" }, flashStyle]} />
    </Animated.View>
  );
});
