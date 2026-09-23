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
    # v1.10: heroic combat stance instead of the old idle pose, plus rim light, so the Lord reads against the battle backdrop.
    base = ("Exactly ONE character (single figure, no turnaround, no multiple views): The Lord, heroic human knight commander, mid-30s, determined face, short dark hair and beard, "
            "full body 3/4 view FACING RIGHT, heroic dynamic combat stance with the weight forward on the front leg, powerful heroic proportions, crisp readable silhouette")
    light = ("strong warm key light from the upper right, cool rim light along the right edge outlining the body and the blade, soft ambient occlusion, high detail, "
             "complete body from head to feet with the feet fully visible, centered")
    return [
        ("lord/base", f"{base}, wearing a burgundy tunic with leather straps and a small golden lion emblem, no armor, no helmet, longsword held low and forward in the right hand ready to strike, left hand clenched, {light}, {STYLE}, {GREEN}"),
        ("lord/armored", f"{base}, wearing polished steel plate armor with gold trim, helmet with a burgundy plume, burgundy cape billowing behind, heraldic lion shield braced forward on the left arm, longsword raised diagonally mid-swing, {light}, {STYLE}, {GREEN}"),
        ("lord/royal", f"{base}, wearing ornate gold-and-steel royal armor with lion pauldrons, a golden crown, long crimson cape sweeping behind, kite shield with a dragon crest, glowing runed longsword extended forward spilling pale blue light on the armor, {light}, {STYLE}, {GREEN}"),
    ]


# Parallax silhouettes (v1.10): flat black shapes, chroma-keyed to alpha and tinted per region in the app, so three
# reusable mid-distance skylines and three foreground strips cover all ten regions.
PARALLAX_MID = {
    "peaks": "a range of jagged rocky mountain peaks and sharp crags of varying heights",
    "ruins": "the ruins of an ancient fortress city: broken towers, crumbling walls, collapsed arches and a leaning obelisk of varying heights",
    "forest": "a dense forest treeline of pines, oaks and a few bare twisted trees of varying heights",
}
PARALLAX_FG = {
    "rocks": "a rugged rocky ridge with scattered boulders, jagged stones and cracked rock slabs, with a few taller rock spires",
    "flora": "overgrown vegetation: tall grass tufts, ferns, reeds, a few broken branches and leafy bushes, with a few taller stalks",
    "bones": "grim battlefield debris: scattered bones, a few skulls, broken spears and tattered banner poles leaning at angles, cracked stone shards",
}
SILHOUETTE = ("Pure solid BLACK silhouette shapes only (no interior detail, no shading, no gradient). No characters, no text, no watermark, no border, "
              "flat 2D vector shapes, clean crisp edges. Everything else in the frame is pure flat chroma green (#00FF00)")


def parallax_prompts():
    out = [(f"parallax/mid_{k}", f"Game art asset: a wide horizontal mid-distance silhouette skyline for a 2D side-scrolling fantasy game parallax background, showing {v}, "
            f"the tallest shapes reaching about 70% of the frame height, continuous across the full width and touching the bottom edge. {SILHOUETTE}.") for k, v in PARALLAX_MID.items()]
    out += [(f"parallax/fg_{k}", f"Game art asset: a wide horizontal foreground silhouette strip for a 2D side-scrolling fantasy game, used as the closest parallax layer, showing {v}, "
             f"occupying only the BOTTOM 45% of the frame with an irregular top edge and touching the bottom edge continuously across the full width. {SILHOUETTE}.") for k, v in PARALLAX_FG.items()]
    return out


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


TILE_DESC = {
    "plains": "lush green meadow with wildflowers and a winding footpath",
    "forest": "dense pine and oak forest canopy seen from above with a small clearing",
    "hills": "rolling golden-green hills with rocky outcrops and sheep",
    "river": "a blue river crossing the tile diagonally with grassy banks and a small wooden bridge",
    "mountains": "snow-capped rocky mountain peaks with pine trees at the base",
    "village": "small medieval village with thatched cottages, a well and vegetable gardens",
    "mine": "hillside mine with a wooden shaft entrance, ore carts and rails",
    "ruins": "ancient stone ruins with broken pillars overgrown by moss",
    "fort": "square stone fort with corner towers, a gate and a burgundy banner",
    "city": "walled medieval city with dense rooftops, a cathedral spire and golden domes",
}


def tile_prompts():
    return [(f"tiles/{k}", f"Top-down (bird's eye, orthographic) square game map tile for a fantasy kingdom map: {v}. Fills the whole square edge to edge, "
             f"consistent overhead lighting from top-left, edges that blend into generic grass so tiles can sit side by side, no border, no text, {STYLE}") for k, v in TILE_DESC.items()]


def fog_variant(img: Image.Image) -> Image.Image:
    from PIL import ImageEnhance
    g = ImageEnhance.Color(img.convert("RGB")).enhance(0.2)
    g = ImageEnhance.Brightness(g).enhance(0.5)
    tint = Image.new("RGB", g.size, (38, 46, 66))
    return Image.blend(g, tint, 0.35)


ITEM_SLOT_DESC = {
    "weapon": "longsword", "offhand": "round shield", "helmet": "knight helmet", "chest": "chest armor breastplate", "gloves": "pair of gauntlets",
    "boots": "pair of armored boots", "cloak": "ONE single hooded cloak draped on a wooden hanger (only one cloak, never several)", "ring": "ring", "amulet": "amulet pendant on a chain",
}
ITEM_TIERS = {
    "basic_a": "worn iron and brown leather, simple and battered",
    "basic_b": "dull steel with dark leather straps and bronze rivets",
    "fine_a": "polished blue steel with silver trim and a sapphire gem",
    "fine_b": "dark violet enamel with silver filigree and an amethyst gem",
    "ornate": "gleaming gold and crimson with glowing runes, dragon motifs and a radiant ruby, legendary aura",
}
RESOURCE_DESC = {
    "grain": "a bundle of golden wheat sheaves tied with twine",
    "wood": "a stack of three cut oak logs",
    "clay": "a stack of terracotta clay bricks",
    "iron": "three stacked dark iron ingots",
    "gold": "a pile of shiny gold coins",
    "rubies": "a large faceted glowing red ruby gem",
    "forge_dust": "a small leather pouch spilling glowing orange ember dust",
    "reforge_stone": "a hexagonal rune-carved violet stone glowing softly",
    "mythic_essence": "a swirling cyan-white magical essence orb with sparkles",
    "war_coins": "a heavy bronze war medal coin with crossed swords",
    "event_tokens": "a golden festival token with a star emblem",
}


def item_prompts():
    items = []
    for slot, desc in ITEM_SLOT_DESC.items():
        for tier, look in ITEM_TIERS.items():
            items.append((f"items/{slot}_{tier}", f"Single fantasy game inventory icon: a {desc}, {look}, exactly one object, slight 3/4 view, centered, filling the frame, {STYLE}, {GREEN}"))
    return items


def resource_prompts():
    return [(f"resources/{k}", f"Single fantasy game resource icon: {v}, exactly one object group, centered, filling the frame, {STYLE}, {GREEN}") for k, v in RESOURCE_DESC.items()]


def ground_prompts():
    return [("kingdom/ground", "Top-down isometric fantasy game terrain plane for a kingdom builder: lush green meadow with two crossing dirt roads (one horizontal across the lower middle, one vertical in the center), "
             "small flowers, subtle grass texture, soft shadows, no buildings, no characters, no text, 16:9, " + STYLE)]


BLACK = "on a pure solid black background (#000000), nothing else in frame, no ground, no characters, no text"
VFX_STYLE = "realistic cinematic 3D VFX render, volumetric glow, high dynamic range light, particles and sparks, sharp detail, game-ready effect sprite, centered"


LORD_SKIN_DESC = {
    "crimson_paladin": "crimson-and-silver paladin plate armor with a white cross tabard, winged helmet, glowing holy longsword",
    "frost_warden": "ice-blue enchanted armor with frost crystals on the shoulders, fur-lined cape, frozen glowing greatsword",
    "dragon_knight": "black-and-red dragon-scale armor with a dragon-skull helmet, small wing ornaments, flaming sword",
    "shadow_reaper": "dark hooded assassin-knight armor with purple void energy, tattered cloak, twin curved blades",
    "golden_emperor": "radiant gold imperial armor with a tall crown, white-and-gold cape, jeweled scepter-sword",
    "forest_ranger": "green-and-brown elven ranger leather armor with leaf motifs, hooded cloak, ornate longbow on the back and a sword in hand",
}
CASTLE_SKIN_DESC = {
    "winter_citadel": "snow-covered white stone citadel with ice-blue rooftops, frozen banners, icicles and glowing lanterns",
    "dragon_keep": "black volcanic fortress with red-hot lava cracks, dragon statues, spiked towers and a dragon perched on the main tower",
    "elven_palace": "elegant elven palace of white marble and living trees, golden leaf domes, hanging gardens and glowing runes",
    "obsidian_fortress": "dark obsidian fortress with purple arcane crystals, floating stones and violet flames on the towers",
}


ARMY_SKIN_DESC = {
    "crimson_legion": "crimson war banner with a golden roaring lion emblem, gold fringe, on a dark wooden pole with a golden spearhead finial",
    "azure_order": "royal blue war banner with a silver griffin emblem, silver fringe, on a steel pole with a winged finial",
    "emerald_wardens": "deep green war banner with a golden stag antler emblem and leaf border, on an ancient oak pole",
    "obsidian_pact": "black war banner with a glowing violet skull emblem and purple runes, tattered edges, on a black iron pole",
}


def skin_prompts():
    base = "Exactly ONE character (single figure, no turnaround, no multiple views): The Lord, heroic human knight commander, mid-30s, determined face, short dark hair and beard, full body 3/4 view facing RIGHT, holding a sword in the right hand"
    out = [(f"skins/lord_{k}", f"{base}, wearing {v}, standing battle stance, complete body with feet, centered, {STYLE}, {GREEN}") for k, v in LORD_SKIN_DESC.items()]
    out += [(f"skins/castle_{k}", f"Isometric 3/4 view of a fantasy castle for a mobile strategy game: {v}. Single building, complete, centered, {STYLE}, {GREEN}") for k, v in CASTLE_SKIN_DESC.items()]
    out += [(f"skins/army_{k}", f"Exactly ONE object: a tall standing medieval war banner, {v}, fabric gently waving, vertical composition, complete pole visible top to bottom, centered, {STYLE}, {GREEN}") for k, v in ARMY_SKIN_DESC.items()]
    return out


HUB_DESC = {
    "daily_quests": "a parchment scroll with a golden wax seal and a quill, checkmarks glowing, on a wooden war table with candles",
    "weekly_quests": "a large ornate war-room map with seven golden pins and a heraldic banner, morning light",
    "login_calendar": "a medieval stone calendar wheel with 28 glowing rune slots, a gift chest and coins in front",
    "weekly_event": "a festive medieval tournament ground with colorful tents, fireworks and a golden trophy at golden hour",
    "dungeons": "a dark dungeon entrance carved with skulls, torches, glowing treasure inside and a chained gate",
    "titan_hunt": "a colossal stone titan boss rising from the mountains, tiny knights charging, dramatic storm sky",
    "achievements": "a wall of golden trophies, medals and laurel wreaths in a royal hall with spotlights",
    "codex": "a huge ancient open tome with glowing illustrations of monsters and maps, floating magical pages",
    "shop": "a lavish medieval merchant stall with mannequins wearing ornate knight armors, castle miniature, gems and gold",
    "chat": "two heraldic banners crossed over a round table with speech-scroll parchments and a messenger falcon",
    "alliance_war": "two armies with different heraldic colors facing each other over a hex war map on a table, war horns",
}


def hub_prompts():
    return [(f"hub/{k}", f"Landscape 16:9 illustration for a fantasy mobile game menu tile: {v}. Rich detail, cinematic lighting, no characters' faces close-up, no text, no UI, no watermark, {STYLE}") for k, v in HUB_DESC.items()]


def vfx_prompts():
    return [
        ("vfx/slash_gold", f"Single curved crescent blade-of-light slash trail, golden white-hot core with orange glowing edges and trailing sparks, sweeping from upper-left to lower-right, {VFX_STYLE}, {BLACK}"),
        ("vfx/slash_white", f"Single thin curved sword slash arc of pure white-blue light with motion blur and tiny sparks, sweeping diagonally, {VFX_STYLE}, {BLACK}"),
        ("vfx/impact_burst", f"Radial impact explosion of golden white light: hot bright core, star-shaped rays, flying embers and sparks, {VFX_STYLE}, {BLACK}"),
        ("vfx/fire_burst", f"Fireball explosion: bright yellow-white core, orange and red flames, black smoke wisps at the edges, embers flying, {VFX_STYLE}, {BLACK}"),
        ("vfx/shockwave_ring", f"Glowing energy shockwave ring seen at a slight top-down angle (wide flattened ellipse), golden-white bright ring with dust and sparks along the edge, hollow center, {VFX_STYLE}, {BLACK}"),
        ("vfx/energy_aura", f"Tall vertical rising energy aura of golden flames and lightning-like sparks, like a fighter's power-up aura, symmetric, widest at the bottom, transparent hollow center where a character would stand, {VFX_STYLE}, {BLACK}"),
        ("vfx/lightning", f"Vertical bolt of blue-white lightning striking downward with branching forks and a bright flash at the impact point at the bottom, {VFX_STYLE}, {BLACK}"),
        ("vfx/dust_cloud", f"Puff of ground dust and small rock debris kicked up by a heavy landing, warm beige-brown dust lit from the left, spreading sideways, {VFX_STYLE}, {BLACK}"),
        ("vfx/energy_orb", f"Glowing magic energy orb projectile flying to the left with a long comet-like tail of fire and violet sparks, {VFX_STYLE}, {BLACK}"),
        ("vfx/soul_wisp", f"Ghostly soul wisps rising upward, pale cyan-white translucent spirit flames with sparkles, several small tongues, {VFX_STYLE}, {BLACK}"),
        ("vfx/fire_breath", f"Horizontal cone of dragon fire breath blasting from right to left, white-yellow core, orange flames, smoke and embers, {VFX_STYLE}, {BLACK}"),
        ("vfx/ice_shards", f"Cluster of sharp glowing ice crystal shards and frost mist bursting outward, icy blue-white, {VFX_STYLE}, {BLACK}"),
        ("vfx/sand_vortex", f"Swirling sand tornado vortex with glowing golden dust and small stones, tall spiral, {VFX_STYLE}, {BLACK}"),
        ("vfx/rock_slam", f"Ground slam cracks: glowing molten orange fissures radiating from a center point on the ground with flying rock chunks and dust, seen at a slight top-down angle, {VFX_STYLE}, {BLACK}"),
        ("vfx/holy_beam", f"Vertical pillar of holy golden-white light descending from above with floating light particles and lens flare at the base, {VFX_STYLE}, {BLACK}"),
        ("vfx/water_wave", f"Large crashing sea wave with glowing cyan foam and spray moving to the left, {VFX_STYLE}, {BLACK}"),
        ("vfx/void_burst", f"Dark violet-black void explosion with purple lightning cracks and a bright magenta core, {VFX_STYLE}, {BLACK}"),
        ("vfx/arrow_volley", f"A volley of five flying arrows with faint motion trails, medieval wooden arrows with steel tips flying to the right, slightly fanned out, {VFX_STYLE}, {BLACK}"),
    ]


GROUPS = {"monsters": monster_prompts, "backgrounds": background_prompts, "lord": lord_prompts, "buildings": building_prompts, "ground": ground_prompts, "units": unit_prompts, "splash": splash_prompts, "tiles": tile_prompts, "items": item_prompts, "resources": resource_prompts, "vfx": vfx_prompts, "skins": skin_prompts, "hub": hub_prompts, "parallax": parallax_prompts}
TRANSPARENT = {"monsters", "lord", "buildings", "units", "items", "resources", "skins", "parallax"}
LUMA_ALPHA = {"vfx"}
MAX_SIDE = {"monsters": 512, "lord": 640, "buildings": 640, "backgrounds": 1280, "ground": 1280, "units": 384, "splash": 1280, "tiles": 256, "items": 256, "resources": 192, "vfx": 512, "skins": 640, "hub": 768, "parallax": 1024}


def luma_to_alpha(img: Image.Image) -> Image.Image:
    """Light-on-black VFX -> RGBA: alpha = max channel (additive look), colour un-premultiplied so glows stay saturated."""
    img = img.convert("RGB")
    px = img.load()
    w, h = img.size
    out = Image.new("RGBA", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            a = max(r, g, b)
            if a < 14:
                op[x, y] = (0, 0, 0, 0)
            else:
                k = 255 / a
                op[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), a)
    return out


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
    elif group in LUMA_ALPHA:
        img = trim(luma_to_alpha(img))
    else:
        img = img.convert("RGB")
    m = MAX_SIDE[group]
    if max(img.size) > m:
        s = m / max(img.size)
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if group == "tiles":
        side = min(img.size)
        img = img.crop(((img.width - side) // 2, (img.height - side) // 2, (img.width + side) // 2, (img.height + side) // 2))
        fog_variant(img).save(out_path.with_name(out_path.stem + "_fog.webp"), "WEBP", quality=80, method=6)
    img.save(out_path, "WEBP", quality=82, method=6)
    return img.size


async def generate(prompt: str, raw_path: Path, retries: int = 3) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # imported here so postprocessing works without the LLM SDK

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
