"""Procedural audio for IDLE 1: battle SFX + one ambient music loop per region, rendered with numpy and encoded to MP3 (lameenc).
All material is synthesized here (no third-party samples), so it is license-free. Output: frontend/assets/audio/{sfx,music}/*.mp3

Usage: python scripts/gen_audio.py
"""
import math
import sys
from pathlib import Path

import lameenc
import numpy as np

SR = 22050
OUT = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "audio"
rng = np.random.default_rng(7)


def t(seconds: float) -> np.ndarray:
    return np.arange(int(SR * seconds)) / SR


def env(n: int, a: float, d: float, s: float = 0.0, r: float = 0.0, sustain_level: float = 0.6) -> np.ndarray:
    """ADSR envelope in seconds over n samples."""
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, n - a_n - d_n - r_n)
    parts = [np.linspace(0, 1, a_n, endpoint=False), np.linspace(1, sustain_level, d_n, endpoint=False), np.full(s_n, sustain_level), np.linspace(sustain_level, 0, r_n)]
    e = np.concatenate(parts)[:n]
    return np.pad(e, (0, max(0, n - len(e))))


def tone(freq: float, seconds: float, kind: str = "sine", harmonics: int = 4, detune: float = 0.0) -> np.ndarray:
    x = t(seconds)
    if kind == "sine":
        return np.sin(2 * math.pi * freq * x)
    if kind == "saw":
        return sum(((-1) ** (k + 1)) * np.sin(2 * math.pi * freq * k * x) / k for k in range(1, harmonics + 1)) * 0.6
    if kind == "pluck":  # bright harmonics decaying faster than the fundamental
        return sum(np.sin(2 * math.pi * freq * k * x * (1 + detune * k)) * np.exp(-x * (2 + 3 * k)) / k for k in range(1, harmonics + 1))
    if kind == "pad":
        return (np.sin(2 * math.pi * freq * x) + 0.5 * np.sin(2 * math.pi * freq * 2.003 * x) + 0.25 * np.sin(2 * math.pi * freq * 0.5 * x)) / 1.75
    raise ValueError(kind)


def noise(seconds: float) -> np.ndarray:
    return rng.uniform(-1, 1, int(SR * seconds))


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    rc = 1 / (2 * math.pi * cutoff)
    alpha = (1 / SR) / (rc + 1 / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return x - lowpass(x, cutoff)


def normalize(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def mix(*layers: np.ndarray) -> np.ndarray:
    n = max(len(l) for l in layers)
    out = np.zeros(n)
    for l in layers:
        out[: len(l)] += l
    return out


def encode_mp3(x: np.ndarray, path: Path, kbps: int = 56):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(pcm.tobytes()) + enc.flush()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"  {path.relative_to(OUT.parents[1])} {len(data) // 1024} KB · {len(x) / SR:.1f}s")


# ---------------------------------------------------------------- SFX
def sfx_hit():
    n = noise(0.22) * env(int(SR * 0.22), 0.002, 0.08, 0.2, 0.1)
    ring = tone(1800, 0.22) * env(int(SR * 0.22), 0.001, 0.15, 0.0, 0.05) * 0.5
    return normalize(highpass(n, 900) * 0.8 + ring)


def sfx_kill():
    thud = np.sin(2 * math.pi * np.cumsum(np.linspace(160, 55, int(SR * 0.35))) / SR) * env(int(SR * 0.35), 0.002, 0.25, 0.1, 0.08)
    crunch = lowpass(noise(0.3), 1400) * env(int(SR * 0.3), 0.001, 0.12, 0.1, 0.1) * 0.7
    return normalize(mix(thud, crunch))


def sfx_crit():
    n = highpass(noise(0.5), 700) * env(int(SR * 0.5), 0.002, 0.2, 0.15, 0.2)
    chord = sum(tone(f, 0.5) for f in (1320, 1980, 2640)) / 3 * env(int(SR * 0.5), 0.001, 0.35, 0.0, 0.1)
    boom = np.sin(2 * math.pi * np.cumsum(np.linspace(120, 40, int(SR * 0.5))) / SR) * env(int(SR * 0.5), 0.002, 0.3, 0.1, 0.1)
    return normalize(mix(n * 0.7, chord * 0.8, boom))


def sfx_skill():
    x = t(0.8)
    sweep = lowpass(noise(0.8), 600) * np.sin(math.pi * x / 0.8) ** 2
    shimmer = sum(tone(f, 0.8, "pluck") * env(int(SR * 0.8), 0.01 + i * 0.12, 0.3, 0.2, 0.2) for i, f in enumerate((660, 880, 1320, 1760))) / 4
    return normalize(mix(sweep * 0.8, shimmer))


def melody(notes, dur, kind="saw", gap=0.0, release=0.25):
    out = []
    for f in notes:
        n = int(SR * dur)
        seg = tone(f, dur, kind, harmonics=5) * env(n, 0.01, 0.1, dur - 0.11 - release, release, 0.7)
        out.append(np.concatenate([seg, np.zeros(int(SR * gap))]))
    return np.concatenate(out)


def sfx_victory():
    fan = melody([523.25, 659.25, 783.99, 1046.5], 0.28, "saw") * 0.6
    tail = tone(1046.5, 0.9, "pad") * env(int(SR * 0.9), 0.02, 0.4, 0.3, 0.2)
    sparkle = sum(tone(f, 1.0, "pluck") * env(int(SR * 1.0), 0.05 * i, 0.4, 0.2, 0.3) for i, f in enumerate((1568, 2093, 2637))) / 3
    return normalize(np.concatenate([fan, mix(tail, sparkle) * 0.7]))


def sfx_defeat():
    return normalize(melody([392.0, 349.23, 311.13, 261.63], 0.38, "saw", release=0.3) * 0.7)


def sfx_coin():
    a = tone(2600, 0.3) * env(int(SR * 0.3), 0.001, 0.2, 0.0, 0.1)
    b = tone(3900, 0.25) * env(int(SR * 0.25), 0.001, 0.15, 0.0, 0.1)
    return normalize(mix(a, np.concatenate([np.zeros(int(SR * 0.05)), b])))


def sfx_ui_tap():
    return normalize(lowpass(noise(0.07), 2500) * env(int(SR * 0.07), 0.001, 0.04, 0.0, 0.02))


def sfx_build():
    tap = lambda: mix(tone(420, 0.15) * env(int(SR * 0.15), 0.001, 0.1, 0, 0.04), highpass(noise(0.12), 1500) * env(int(SR * 0.12), 0.001, 0.05, 0, 0.05) * 0.5)  # noqa: E731
    return normalize(np.concatenate([tap(), np.zeros(int(SR * 0.18)), tap()]))


SFX = {"hit": sfx_hit, "kill": sfx_kill, "crit": sfx_crit, "skill": sfx_skill, "victory": sfx_victory, "defeat": sfx_defeat, "coin": sfx_coin, "ui_tap": sfx_ui_tap, "build": sfx_build}

# ---------------------------------------------------------------- MUSIC
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10], "lydian": [0, 2, 4, 6, 7, 9, 11], "pent": [0, 2, 4, 7, 9]}
# region -> (root midi, scale, bpm, arpeggio timbre, percussion, brightness)
REGIONS = {
    1: (60, "major", 76, "pluck", False, 1.0),      # Verdant Frontier
    2: (57, "dorian", 72, "pluck", False, 0.8),     # Blackwood
    3: (55, "minor", 84, "saw", True, 0.7),         # Iron Hills
    4: (62, "phrygian", 80, "pluck", True, 0.9),    # Amber Dunes
    5: (58, "minor", 66, "pad", False, 0.6),        # Frostmere
    6: (53, "phrygian", 70, "pad", True, 0.5),      # Frozen Peaks
    7: (55, "dorian", 74, "pluck", False, 0.6),     # Drowned Coast
    8: (50, "phrygian", 92, "saw", True, 0.8),      # Ashen Wastes
    9: (64, "lydian", 78, "pluck", False, 1.0),     # Celestial Reach
    10: (48, "minor", 96, "saw", True, 0.9),        # Dragonspine
}


def midi(n: float) -> float:
    return 440 * 2 ** ((n - 69) / 12)


def music_for(region: int, seconds: float = 32.0) -> np.ndarray:
    root, scale_name, bpm, timbre, perc, bright = REGIONS[region]
    scale = SCALES[scale_name]
    r = np.random.default_rng(100 + region)
    total = int(SR * seconds)
    beat = 60 / bpm
    out = np.zeros(total)
    # chord progression: 4 chords, each 1/4 of the loop, built on scale degrees
    degrees = [0, 3, 4, 5] if scale_name in ("major", "lydian") else [0, 5, 3, 4]
    chord_len = total // 4
    for ci, deg in enumerate(degrees):
        notes = [root + scale[(deg + k) % len(scale)] + 12 * ((deg + k) // len(scale)) for k in (0, 2, 4)]
        pad = sum(tone(midi(n), chord_len / SR, "pad") for n in notes) / 3
        lfo = 0.75 + 0.25 * np.sin(2 * math.pi * 0.2 * t(chord_len / SR) + ci)
        e = env(chord_len, 1.2, 0.5, chord_len / SR - 2.5, 0.8, 0.85)
        out[ci * chord_len:(ci + 1) * chord_len] += pad * lfo * e * 0.16
        # bass on beats 1 and 3
        for b in range(int(chord_len / SR / beat)):
            if b % 2 == 0:
                start = ci * chord_len + int(b * beat * SR)
                bass = tone(midi(notes[0] - 24), beat * 1.5, "saw", harmonics=3) * env(int(beat * 1.5 * SR), 0.01, 0.3, beat * 0.6, 0.3, 0.5)
                end = min(total, start + len(bass))
                out[start:end] += bass[: end - start] * 0.3
    # arpeggio: 8th notes following the chords with gentle randomness (seeded => same loop every time)
    step = beat / 2
    n_steps = int(seconds / step)
    for i in range(n_steps):
        ci = min(3, int(i * step * SR // chord_len))
        deg = degrees[ci]
        pick = r.choice([0, 2, 4, 7, 9]) if scale_name != "pent" else r.choice([0, 2, 4])
        note = root + 12 + scale[(deg + pick) % len(scale)] + 12 * ((deg + pick) // len(scale))
        if r.random() < 0.18:
            continue
        dur = step * 1.8
        n = int(dur * SR)
        arp = tone(midi(note), dur, "pluck" if timbre == "pluck" else "saw", harmonics=6, detune=0.002) * env(n, 0.004, 0.3, max(0, dur - 0.5), 0.2, 0.45) * (0.6 + 0.4 * bright)
        start = int(i * step * SR)
        end = min(total, start + n)
        out[start:end] += arp[: end - start] * 0.6
    if perc:
        for b in range(int(seconds / beat)):
            start = int(b * beat * SR)
            if b % 4 in (0, 2):
                kick = np.sin(2 * math.pi * np.cumsum(np.linspace(110, 45, int(SR * 0.25))) / SR) * env(int(SR * 0.25), 0.002, 0.2, 0.0, 0.05)
                end = min(total, start + len(kick))
                out[start:end] += kick[: end - start] * 0.5
            if b % 4 == 3 or (region >= 8 and b % 2 == 1):
                shk = highpass(noise(0.12), 3000) * env(int(SR * 0.12), 0.002, 0.08, 0.0, 0.04)
                end = min(total, start + len(shk))
                out[start:end] += shk[: end - start] * 0.18
    # loop-safe crossfade of the last 0.5s into the first 0.5s
    xf = int(SR * 0.5)
    ramp = np.linspace(0, 1, xf)
    head = out[:xf].copy()
    out[-xf:] = out[-xf:] * (1 - ramp) + head * ramp
    out[:xf] *= ramp
    return normalize(out, 0.8)


def main():
    # SFX are disabled by owner choice (v1.2: music only). Pass --with-sfx to regenerate them anyway.
    if "--with-sfx" in sys.argv:
        print("SFX")
        for name, fn in SFX.items():
            encode_mp3(fn(), OUT / "sfx" / f"{name}.mp3", kbps=64)
    print("MUSIC")
    for region in REGIONS:
        encode_mp3(music_for(region), OUT / "music" / f"region_{region}.mp3", kbps=48)
    # manifest for Metro static requires
    files = sorted(OUT.rglob("*.mp3"))
    lines = ["// AUTO-GENERATED by backend/scripts/gen_audio.py — do not edit by hand. Music only (SFX removed by owner choice).", "export const AUDIO: Record<string, number> = {"]
    for p in files:
        key = str(p.relative_to(OUT).with_suffix("")).replace("\\", "/")
        lines.append(f'  "{key}": require("../../assets/audio/{key}.mp3"),')
    lines += ["};", ""]
    manifest = OUT.parents[1] / "src" / "audio" / "manifest.ts"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines))
    print(f"manifest: {manifest} ({len(files)} files)")


if __name__ == "__main__":
    main()
