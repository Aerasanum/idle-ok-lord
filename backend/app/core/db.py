from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from .config import settings

client = AsyncIOMotorClient(settings.MONGO_URL, uuidRepresentation="standard")
db = client[settings.DB_NAME]

COLLECTIONS = [
    "accounts", "refresh_sessions", "one_time_codes", "players", "gear_items", "ledgers", "battle_attempts", "offline_claims", "dungeon_runs",
    "event_deployments", "alliances", "alliance_members", "alliance_applications", "chat_messages", "reports_blocks", "war_shards", "alliance_map_nodes",
    "alliance_wars", "war_snapshots", "alliance_boss_runs", "purchases", "entitlements", "rc_events", "notifications", "audit_events", "export_requests",
]


def rebind(new_client: AsyncIOMotorClient) -> None:
    """Rebind all collection handles (used by the test suite to attach Motor to the test event loop)."""
    global client, db
    client = new_client
    db = new_client[settings.DB_NAME]
    g = globals()
    for name in COLLECTIONS:
        g[name] = db[name]

accounts = db.accounts
refresh_sessions = db.refresh_sessions
one_time_codes = db.one_time_codes
players = db.players  # aggregated player state (profile+hero+kingdom+army+domain+campaign+quests)
gear_items = db.gear_items
ledgers = db.ledgers  # idempotency ledger for every reward/claim/purchase/war side effect
battle_attempts = db.battle_attempts
offline_claims = db.offline_claims
dungeon_runs = db.dungeon_runs
event_deployments = db.event_deployments
alliances = db.alliances
alliance_members = db.alliance_members
alliance_applications = db.alliance_applications
chat_messages = db.chat_messages
reports_blocks = db.reports_blocks
war_shards = db.war_shards
alliance_map_nodes = db.alliance_map_nodes
alliance_wars = db.alliance_wars
war_snapshots = db.war_snapshots
alliance_boss_runs = db.alliance_boss_runs
purchases = db.purchases
entitlements = db.entitlements
rc_events = db.rc_events
notifications = db.notifications
audit_events = db.audit_events
export_requests = db.export_requests


async def ensure_indexes() -> None:
    await accounts.create_index("email", unique=True)
    await refresh_sessions.create_index("token_hash", unique=True)
    await refresh_sessions.create_index("account_id")
    await refresh_sessions.create_index("expires_at", expireAfterSeconds=0)
    await one_time_codes.create_index([("account_id", ASCENDING), ("kind", ASCENDING)])
    await one_time_codes.create_index("expires_at", expireAfterSeconds=0)
    await players.create_index("account_id", unique=True)
    await players.create_index("alliance_id")
    await players.create_index("kingdom.queue_next_end")
    await gear_items.create_index([("owner_id", ASCENDING), ("equipped_slot", ASCENDING)])
    await gear_items.create_index(
        [("owner_id", ASCENDING), ("equipped_slot", ASCENDING)],
        unique=True,
        partialFilterExpression={"equipped_slot": {"$type": "string"}},
        name="one_item_per_equipped_slot",
    )
    await ledgers.create_index("key", unique=True)
    await ledgers.create_index("player_id")
    await battle_attempts.create_index([("player_id", ASCENDING), ("created_at", DESCENDING)])
    await offline_claims.create_index([("player_id", ASCENDING), ("interval_end", DESCENDING)])
    await dungeon_runs.create_index([("player_id", ASCENDING), ("status", ASCENDING)])
    await event_deployments.create_index([("player_id", ASCENDING), ("status", ASCENDING)])
    await alliances.create_index("name_lower", unique=True)
    await alliances.create_index("shard_id")
    await alliance_members.create_index([("alliance_id", ASCENDING), ("player_id", ASCENDING)], unique=True)
    await alliance_members.create_index("player_id", unique=True)
    await alliance_applications.create_index([("alliance_id", ASCENDING), ("player_id", ASCENDING)], unique=True)
    await chat_messages.create_index([("channel", ASCENDING), ("created_at", DESCENDING)])
    await reports_blocks.create_index([("player_id", ASCENDING), ("kind", ASCENDING), ("target_id", ASCENDING)])
    await alliance_map_nodes.create_index([("shard_id", ASCENDING), ("node_id", ASCENDING)], unique=True)
    await alliance_map_nodes.create_index([("shard_id", ASCENDING), ("owner_alliance_id", ASCENDING)])
    await alliance_wars.create_index([("shard_id", ASCENDING), ("status", ASCENDING)])
    await alliance_wars.create_index("resolves_at")
    await war_snapshots.create_index("war_id", unique=True)
    await alliance_boss_runs.create_index([("alliance_id", ASCENDING), ("status", ASCENDING)])
    await purchases.create_index("transaction_key", unique=True)
    await purchases.create_index("player_id")
    await entitlements.create_index([("player_id", ASCENDING), ("entitlement", ASCENDING)], unique=True)
    await rc_events.create_index("event_id", unique=True)
    await notifications.create_index([("player_id", ASCENDING), ("created_at", DESCENDING)])
    await notifications.create_index("created_at", expireAfterSeconds=30 * 24 * 3600)
    await audit_events.create_index([("player_id", ASCENDING), ("created_at", DESCENDING)])
