"""Art pipeline: generate stylized-3D game assets with Gemini (Nano Banana) via the Emergent key, chroma-key them and emit WebP files
plus a TypeScript require-manifest for the Expo app.

Usage: python scripts/gen_art.py [--only monsters|backgrounds|lord|buildings|ground] [--limit N] [--force]
Resumable: existing outputs are skipped unless --force. Never prints base64.
"""
import argparse
import asyncio
import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageFilter

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env")
sys.path.insert(0, str(BACKEND))
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

MODEL = "gemini-3.1-flash-image-preview"
CANON = json.load(open(BACKEND / "canon" / "IDLE_1_v1.1_CANONICAL_SPEC.json"))
OUT = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "art"
RAW = BACKEND / "art_raw"
GREEN = "pure flat chroma green background (#00FF00), no shadow on the background, no ground plane"
STYLE = ("stylized 3D mobile game render, Clash-of-Clans / AFK-Arena look, soft volumetric lighting, vivid saturated colors, "
         "clean silhouettes, subtle rim light, high quality, no text, no watermark")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def monster_prompts():
    items = []
    for r in CANON["battle"]["regions"]:
        biome = r["visual"]
        for fam in r["enemy_families"]:
            items.append((f"monsters/{slug(fam)}", f"Exactly ONE creature (single figure, no multiple views): full body {fam}, fantasy enemy from the '{r['name']}' region ({biome}), menacing but readable, "
                          f"3/4 view facing LEFT, standing pose, complete body visible with feet, centered, {STYLE}, {GREEN}"))
        boss = r["region_boss"]
        items.append((f"monsters/{slug(boss)}", f"Exactly ONE creature (single figure, no multiple views): full body {boss}, colossal boss enemy of the '{r['name']}' region ({biome}), imposing, gold ornaments, glowing eyes, "
                      f"3/4 view facing LEFT, standing pose, complete body visible with feet, centered, {STYLE}, {GREEN}"))
    return items


def background_prompts():
    return [(f"bg/region_{r['region']}", f"Wide battle background for a fantasy idle game: {r['name']} — {r['visual']}. Layered depth (far mountains/sky, mid props, empty flat ground in the "
             f"lower third for characters to stand on), horizon at 60% height, no characters, no creatures, no text, cinematic soft light, 16:9, {STYLE}") for r in CANON["battle"]["regions"]]


def lord_prompts():
    base = "Exactly ONE character (single figure, no turnaround, no multiple views): The Lord, heroic human knight commander, mid-30s, determined face, short dark hair and beard, full body 3/4 view facing RIGHT, holding a longsword in the right hand"
    return [
        ("lord/base", f"{base}, wearing a simple burgundy tunic with leather straps and a small heraldic emblem, no armor, no helmet, standing battle stance, complete body with feet, centered, {STYLE}, {GREEN}"),
        ("lord/armored", f"{base}, wearing polished steel plate armor with gold trim, helmet with a burgundy plume, round heraldic shield in the left hand, standing battle stance, complete body with feet, centered, {STYLE}, {GREEN}"),
        ("lord/royal", f"{base}, wearing ornate gold-and-steel royal armor, a golden crown, long crimson cape, glowing legendary sword, kite shield with a dragon crest, standing battle stance, complete body with feet, centered, {STYLE}, {GREEN}"),
    ]


BUILDING_DESC = {
    "castle": "small wooden keep with a palisade and one burgundy banner",
    "farm": "farmhouse with wheat fields, windmill and hay bales",
    "lumberyard": "lumber mill with log piles, saw bench and a woodcutter's hut",
    "clay_pit": "open clay quarry with wooden scaffolds, clay bricks and a kiln",
    "warehouse": "large stone warehouse with barrels, crates and sacks",
    "barracks": "military barracks with training dummies, weapon racks and a flag",
    "iron_mine": "mountain mine entrance with rails, ore carts and iron ingots",
    "university": "tall stone university tower with an observatory dome, books and glowing arcane windows",
    "gold_mine": "gold mine with a wooden shaft tower, glowing gold nuggets and carts",
    "walls": "stone defensive wall segment with a gate and two towers",
    "stable": "horse stable with paddock, hay and a mounted-cavalry banner",
    "workshop": "siege workshop with a half-built catapult, gears and anvils",
    "alliance_hall": "grand alliance hall with many colorful banners and a round table pavilion",
    "bestiary": "beast pen with iron cages, a chained griffin and monster skulls",
    "temple": "white marble temple with golden dome and glowing shrine",
    "mythic_sanctuary": "mythic sanctuary with floating runes, dragon statue and magical fire",
}


def building_prompts():
    items = [(f"buildings/{k}", f"Isometric 3/4 top-down view of a fantasy medieval {v}, single building on its own small patch of grass and dirt, complete building, centered, "
              f"{STYLE}, {GREEN}") for k, v in BUILDING_DESC.items()]
    items.append(("buildings/castle_fortress", f"Isometric 3/4 top-down view of a fantasy medieval stone fortress castle with a tall keep, low stone walls, corner towers, burgundy banners, single building on a small patch of grass, centered, {STYLE}, {GREEN}"))
    items.append(("buildings/castle_royal", f"Isometric 3/4 top-down view of a monumental fantasy royal citadel with high towers, golden domes, double walls, bridge, crimson and gold banners, single building on a small patch of grass, centered, {STYLE}, {GREEN}"))
    return items


UNIT_DESC = {
    "infantry": "human footman soldier with sword, round shield and steel helmet, burgundy tabard",
    "archer": "human archer with longbow drawn, leather armor, green hood, quiver",
    "cavalry": "armored knight riding a warhorse with lance and burgundy banner",
    "catapult": "wooden siege catapult with iron fittings, loaded with a boulder",
    "conquest_wagon": "armored siege wagon with iron plating, banner and battering ram",
    "bear": "huge war bear with leather harness and spiked collar",
    "wolf": "battle wolf with light armor plates",
    "lion": "war lion with golden mane and ornate harness",
    "falcon": "war falcon with spread wings and small steel talon guards",
    "war_elephant": "war elephant with howdah tower, banners and armored tusks",
    "dragon": "red battle dragon, wings spread, smoke from nostrils",
    "angel": "armored angel warrior with white wings and glowing spear",
    "demon": "horned demon warrior with fiery greatsword",
}


def unit_prompts():
    return [(f"units/{k}", f"Exactly ONE (single figure, no multiple views): {v}, army unit for a fantasy idle game, full body 3/4 view facing RIGHT, complete body visible, centered, {STYLE}, {GREEN}") for k, v in UNIT_DESC.items()]


def splash_prompts():
    return [("splash/key_art", "Vertical 9:16 key art for a fantasy idle game: the Lord, a heroic human knight commander in burgundy-and-gold armor with a plumed helmet, seen from behind at 3/4, "
             "raising a longsword toward a distant medieval kingdom with a castle on a hill at golden hour, dramatic sky, epic mood, lots of empty dark space in the lower half for UI, "
             "no text, no watermark, " + STYLE)]


def ground_prompts():
    return [("kingdom/ground", "Top-down isometric fantasy game terrain plane for a kingdom builder: lush green meadow with two crossing dirt roads (one horizontal across the lower middle, one vertical in the center), "
             "small flowers, subtle grass texture, soft shadows, no buildings, no characters, no text, 16:9, " + STYLE)]


GROUPS = {"monsters": monster_prompts, "backgrounds": background_prompts, "lord": lord_prompts, "buildings": building_prompts, "ground": ground_prompts, "units": unit_prompts, "splash": splash_prompts}
TRANSPARENT = {"monsters", "lord", "buildings", "units"}
MAX_SIDE = {"monsters": 512, "lord": 640, "buildings": 640, "backgrounds": 1280, "ground": 1280, "units": 384, "splash": 1280}


def chroma_key(img: Image.Image) -> Image.Image:
    """Remove a flat green background (with soft edges) -> RGBA."""
    img = img.convert("RGB")
    px = img.load()
    w, h = img.size
    mask = Image.new("L", (w, h), 255)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            # greenness: how much green dominates red/blue
            dom = g - max(r, b)
            if dom > 60 and g > 120:
                mp[x, y] = 0
            elif dom > 25 and g > 100:
                mp[x, y] = int(255 * (1 - (dom - 25) / 35))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    # despill: pull green tint out of semi-transparent edge pixels
    out = img.convert("RGBA")
    op = out.load()
    for y in range(h):
        for x in range(w):
            a = mp[x, y]
            if a == 0:
                op[x, y] = (0, 0, 0, 0)
            else:
                r, g, b, _ = op[x, y]
                if g > max(r, b):
                    g = max(r, b)
                op[x, y] = (r, g, b, a)
    return out


def trim(img: Image.Image, pad: int = 6) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    return img.crop((max(0, l - pad), max(0, t - pad), min(img.width, r + pad), min(img.height, b + pad)))


def postprocess(group: str, raw_path: Path, out_path: Path):
    img = Image.open(raw_path)
    if group in TRANSPARENT:
        img = trim(chroma_key(img))
    else:
        img = img.convert("RGB")
    m = MAX_SIDE[group]
    if max(img.size) > m:
        s = m / max(img.size)
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=82, method=6)
    return img.size


async def generate(prompt: str, raw_path: Path, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"art-{raw_path.stem}-{attempt}", system_message="You are a senior game concept artist producing production-ready 3D-styled game assets.")
            chat.with_model("gemini", MODEL).with_params(modalities=["image", "text"])
            _text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
            if images:
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(base64.b64decode(images[0]["data"]))
                return True
            print(f"  no image returned (attempt {attempt + 1})")
        except Exception as e:  # noqa: BLE001
            print(f"  error (attempt {attempt + 1}): {str(e)[:160]}")
            await asyncio.sleep(3 * (attempt + 1))
    return False


def write_manifest():
    """Emit frontend/src/art/manifest.ts with static require() calls (Metro needs literal paths)."""
    files = sorted(p for p in OUT.rglob("*.webp"))
    lines = ["// AUTO-GENERATED by backend/scripts/gen_art.py — do not edit by hand.", "/* eslint-disable @typescript-eslint/no-require-imports */", "export const ART: Record<string, number> = {"]
    for p in files:
        key = str(p.relative_to(OUT).with_suffix("")).replace(os.sep, "/")
        lines.append(f'  "{key}": require("../../assets/art/{key}.webp"),')
    lines.append("};")
    lines.append("")
    lines.append("export function art(key: string): number | undefined {")
    lines.append("  return ART[key];")
    lines.append("}")
    manifest = OUT.parents[1] / "src" / "art" / "manifest.ts"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines) + "\n")
    print(f"manifest: {manifest} ({len(files)} assets)")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(GROUPS), nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--manifest-only", action="store_true")
    ap.add_argument("--keys", nargs="*", help="only these asset keys (e.g. monsters/harpy)")
    args = ap.parse_args()
    if args.manifest_only:
        write_manifest()
        return
    groups = args.only or list(GROUPS)
    todo = [(g, key, prompt) for g in groups for key, prompt in GROUPS[g]()]
    if args.keys:
        todo = [t for t in todo if t[1] in set(args.keys)]
    if args.limit:
        todo = todo[: args.limit]
    ok = fail = skipped = 0
    t0 = time.time()
    for i, (g, key, prompt) in enumerate(todo, 1):
        out_path = OUT / f"{key}.webp"
        raw_path = RAW / f"{key}.png"
        if out_path.exists() and not args.force:
            skipped += 1
            continue
        print(f"[{i}/{len(todo)}] {key}")
        if not raw_path.exists() or args.force:
            if not await generate(prompt, raw_path):
                fail += 1
                continue
        size = postprocess(g, raw_path, out_path)
        ok += 1
        print(f"  saved {out_path.relative_to(OUT.parents[2])} {size} · {time.time() - t0:.0f}s")
    write_manifest()
    print(f"done: ok={ok} skipped={skipped} failed={fail} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
