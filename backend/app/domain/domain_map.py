"""Personal Domain 10x10 (I09): canonical adjacent conquest order, deterministic terrain, visual growth."""
from ..core.canon import canon
from ..core.util import seeded_rng
from . import formulas as F

SIZE = 10


def conquest_order() -> list[int]:
    """Deterministic ring spiral from the center tile; each new tile is adjacent to owned territory."""
    cx, cy = 4, 4
    order = [cy * SIZE + cx]
    seen = {(cx, cy)}
    frontier = [(cx, cy)]
    # BFS by Manhattan rings, stable ordering (clockwise from north)
    dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    while len(order) < SIZE * SIZE:
        nxt = []
        for (x, y) in frontier:
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    order.append(ny * SIZE + nx)
                    nxt.append((nx, ny))
        frontier = nxt
    return order


_ORDER = None


def order() -> list[int]:
    global _ORDER
    if _ORDER is None:
        _ORDER = conquest_order()
    return _ORDER


def terrain(index: int) -> str:
    visuals = canon()["personal_domain"]["tile_visuals"]
    rng = seeded_rng("idle1-domain", index)
    x, y = index % SIZE, index // SIZE
    if index == 44:
        return "city"
    # rivers run as a band, mountains toward the edges, otherwise seeded mix
    if (x + y) in (7, 8) and rng.random() < 0.8:
        return "river"
    if (x in (0, 9) or y in (0, 9)) and rng.random() < 0.5:
        return "mountains"
    pool = ["plains", "plains", "forest", "forest", "hills", "village", "mine", "ruins", "fort", "plains"]
    return pool[rng.randrange(len(pool))] if pool[rng.randrange(len(pool))] in visuals else "plains"


def domain_view(p: dict) -> dict:
    owned_n = p["domain"]["owned"]
    ord_ = order()
    owned = set(ord_[:owned_n])
    next_tile = ord_[owned_n] if owned_n < len(ord_) else None
    tiles = []
    for i in range(SIZE * SIZE):
        rank = ord_.index(i)
        tiles.append({"index": i, "x": i % SIZE, "y": i // SIZE, "terrain": terrain(i), "owned": i in owned, "order": rank,
                      "unlock_stage": 0 if rank == 0 else rank * canon()["battle"]["domain_tile_every_stages"]})
    pd = canon()["personal_domain"]
    growth = "camp" if owned_n < 10 else "hamlets" if owned_n < 25 else "roads_and_farms" if owned_n < 50 else "towers_and_forts" if owned_n < 75 else "cities" if owned_n < 100 else "imperial"
    return {"size": SIZE, "owned": owned_n, "total": pd["tiles_total"], "tiles": tiles, "next_tile": next_tile, "heraldic_color": p.get("heraldic_color"),
            "production_bonus_pct": F.domain_bonus_pct(owned_n), "bonus_cap_pct": pd["production_bonus_cap_pct"], "growth_stage": growth,
            "next_tile_at_stage": (owned_n) * canon()["battle"]["domain_tile_every_stages"] if owned_n < pd["tiles_total"] else None,
            "highest_cleared": p["campaign"]["highest_cleared"]}
