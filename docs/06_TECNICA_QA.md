# 06_IDLE_1_TECNICA_IMPLEMENTAZIONE_QA.md

IDLE 1 v1.1 — raggruppamento completo, con revisione operativa richiesta dal proprietario: avvio diretto dello sviluppo.
Le intestazioni BEGIN/END delimitano ciascun documento incluso. I riferimenti ai vecchi nomi indicano le sezioni qui conservate, non ulteriori allegati da caricare.
Gameplay, formule, tabelle e requisiti grafici sono conservati. Le istruzioni di avvio sono aggiornate: verifica dei file e implementazione nello stesso incarico, con QA visiva integrata nello sviluppo.

## Documenti inclusi

- IDLE_1_v1.1_ACCOUNT_PRIVACY_PAYMENTS.md
- IDLE_1_v1.1_DATA_MODEL_API_CONTRACT.md
- IDLE_1_v1.1_IMPLEMENTATION_BLOCKS.md
- IDLE_1_v1.1_ZERO_GAP_AUDIT.md
- IDLE_1_v1.1_FINAL_BUILD_CHECKLIST.md


<!-- BEGIN DOCUMENT: IDLE_1_v1.1_ACCOUNT_PRIVACY_PAYMENTS.md -->
# IDLE 1 v1.1 - ACCOUNT / PRIVACY / PAYMENTS

## Account
Email+password, Google, Sign in with Apple, email verification, password recovery, logout-all-devices, cloud sync, data export request and in-app account deletion.

## Security
Argon2id preferred (bcrypt fallback), strong environment JWT secrets, short access tokens + rotating refresh, CORS allowlist, rate limits, native Keychain/Keystore secure storage, server-authoritative rewards/timers/purchases.

## Privacy
Privacy Policy, Terms, consent/settings screen, configurable age gate, analytics configuration, chat report/block/mute/moderation, transaction records and data-retention documentation. Legal copy/URLs remain owner deployment inputs, not gameplay gaps.

## Apple / Google payments
Use Apple StoreKit and Google Play Billing for digital goods. Production UI displays localized store-returned price. Receipt/transaction verification is server-side and idempotent. Restore purchases and refund/revocation reconciliation are mandatory.

## Products
Ruby packs, Starter Bundle, weekly Event Pass and 28-day Season Pass are defined in CANONICAL_SPEC. No paid random gear chest/gacha. Cosmetics can override appearance only.

## Competitive integrity
Alliance War combat snapshot freezes at roster lock. Purchases or upgrades after lock cannot alter the active war.

<!-- END DOCUMENT: IDLE_1_v1.1_ACCOUNT_PRIVACY_PAYMENTS.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_DATA_MODEL_API_CONTRACT.md -->
# IDLE 1 v1.1 - DATA MODEL / API CONTRACT

SPEC_HASH: `a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995`

## Core collections
accounts, refresh_sessions, player_profiles, hero_state, hero_talents, gear_items, gear_inventory, forge_slots, kingdom_state, building_state, research_state, army_inventory, army_formations, personal_domain, campaign_progress, offline_claims, dungeon_runs, event_progress, quest_progress, achievements, alliances, alliance_members, chat_messages, reports_blocks, alliance_wars, war_snapshots, alliance_map_nodes, alliance_boss_runs, purchases, entitlements, notifications, audit_events.

## Required invariants
- `player_id + world_scope` unique where applicable.
- A gear item has one owner; equipped item must exist in that player's inventory.
- Forge level is stored per player+slot and is independent of the equipped item id.
- Reward claims use a unique idempotency key before side effects.
- Campaign first-clear reward can be credited only once per player+stage.
- Offline claim intervals cannot overlap.
- War snapshot is immutable after roster lock.
- A territory node has one owner at a time; capture is atomic with war resolution.
- Purchase transaction id is unique across credit attempts.

## Representative API groups
`/auth/*`, `/account/*`, `/profile`, `/battle/attempt`, `/battle/claim`, `/offline/claim`, `/gear/inventory`, `/gear/equip`, `/gear/salvage`, `/forge/upgrade`, `/gear/reforge`, `/hero/talents`, `/kingdom/*`, `/research/*`, `/army/*`, `/domain/*`, `/dungeons/*`, `/events/*`, `/quests/*`, `/alliances/*`, `/chat/*`, `/wars/*`, `/alliance-boss/*`, `/store/catalog`, `/purchases/verify`, `/notifications/*`.

Every mutating endpoint validates auth, canonical gates, resource balances, idempotency where relevant and persists before returning the authoritative new state.

<!-- END DOCUMENT: IDLE_1_v1.1_DATA_MODEL_API_CONTRACT.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_IMPLEMENTATION_BLOCKS.md -->
# IDLE 1 v1.1 - IMPLEMENTATION BLOCKS

## I01 - Account, privacy, secure auth, cloud profile
Completion gate: Create/login/recover/delete/export works; secure storage and policy screens complete

## I02 - Canonical runtime loader and Mongo domain foundation
Completion gate: All runtime numbers load from v1.1 spec/config; world/player persistence and idempotency foundation pass tests

## I03 - Campaign auto-combat and monster regions
Completion gate: 200 stages, 10 regions, waves/elites/bosses, kill rewards and deterministic server outcomes work E2E

## I04 - Hero XP, skills and talents
Completion gate: Level 1-100 curve, 3 skill slots, talent points/respec and combat stats work E2E

## I05 - Gear, inventory, drops, salvage, forge, reforge
Completion gate: 9 slots, rarity tables, drop rolls, auto-salvage/equip and slot forge +0..20 work E2E

## I06 - Kingdom, buildings, production and timers
Completion gate: 20 Castle levels, 7 visual tiers, buildings/resources/queues and offline timers work E2E

## I07 - Research and army recruitment
Completion gate: 48x5 research, 13 units, unlock gates, command capacity and formation work E2E

## I08 - Army spectacle renderer
Completion gate: Visual tiers 0-8 scale from Lord alone to huge army within mobile performance budgets

## I09 - Personal Domain
Completion gate: 10x10 domain, one tile every 2 stages, visual growth and production bonuses work E2E

## I10 - Offline progression
Completion gate: 12h server-timestamp loot/resources/gear/timers; double-claim and clock abuse tests pass

## I11 - Events, dungeons, quests, achievements and codex
Completion gate: Always-on event loop, spend hooks, four idle dungeons and retention systems work E2E

## I12 - Alliances, chat and moderation
Completion gate: 30-member alliances, roles, Global/Alliance/War/System chat, report/block/mute work E2E

## I13 - Async 10v10 territory war and Alliance Boss
Completion gate: 19x19 season map, roster snapshot, 10 lanes, territory capture, Titan Hunt and rewards work E2E

## I14 - Store, Apple/Google payments and restore/refunds
Completion gate: Localized store products, receipt verification, idempotent crediting, restore and refund reconciliation pass sandbox tests

## I15 - Mobile shells, push, performance and visual polish
Completion gate: iOS/Android same account/state; push/deep-links; target FPS and in-game visual QA pass

## I16 - Final security, economy regression and release audit
Completion gate: Zero P0/P1; economy invariants, concurrency/idempotency, E2E and release checklist pass

<!-- END DOCUMENT: IDLE_1_v1.1_IMPLEMENTATION_BLOCKS.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_ZERO_GAP_AUDIT.md -->
# IDLE 1 v1.1 - ZERO GAP AUDIT

CANONICAL VERSION: 1.1  
SPEC_HASH: `a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995`

| Check | Result | Evidence |
|---|---|---|
| Hero gear system | PASS | 9 slots, rarity, affixes, visible equipment, forge/reforge/salvage defined |
| Loot economy | PASS | normal/elite/boss/repeat/offline gear cadence defined |
| XP economy | PASS | level curve + first/repeat/offline rewards audited |
| Monster content | PASS | 10 regions, 40 enemy families, 10 named region bosses |
| Army spectacle | PASS | unit gates + command capacity + visual tiers 0-8 + LOD caps |
| Kingdom | PASS | 20 Castle levels + existing 16 buildings + 7 visible tiers |
| Research | PASS | 48 nodes x5 retained from v1.0 |
| Units | PASS | 13-unit catalog retained with new campaign/command gates |
| Domain | PASS | 100 tiles + resource bonus + visual growth |
| Retention | PASS | events, 6 dungeons, daily/weekly/login, achievements, codex |
| Social | PASS | Alliance, chat moderation, 10v10 territory war, Alliance Boss |
| Mobile/commercial | PASS | iOS+Android, account/privacy, Apple/Google payments, no gacha |
| Security | PASS | server authority, secure auth, idempotency, Mongo atomicity |


## Remaining non-canonical deployment inputs
Store accounts, signing certificates, package/bundle ids, legal company identity, Privacy/Terms URLs, production Mongo URI, production secrets, push credentials, analytics choice and final localized store metadata. These do not authorize an AI to invent gameplay.

## Conclusion
v1.1 closes the major v1.0 design gaps around gear/loot, monster progression, XP/Gold/resource flow, dungeons/retention and the visual army-growth promise. It is suitable as a build canon for Emergent, subject to the Final Build Checklist and real implementation tests.

<!-- END DOCUMENT: IDLE_1_v1.1_ZERO_GAP_AUDIT.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_FINAL_BUILD_CHECKLIST.md -->
# IDLE 1 v1.1 - FINAL BUILD CHECKLIST

## Canon
- [ ] CANONICAL_SPEC_PARSED = YES
- [ ] VERSION = 1.1
- [ ] SPEC_HASH = a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995
- [ ] No runtime constants silently invented outside canonical config

## Gameplay
- [ ] I01-I16 all COMPLETE
- [ ] 200 campaign stages / 10 regions / elites / bosses
- [ ] Hero level 1-100, skills and talents
- [ ] 9 gear slots, inventory, rarity, drop, forge, salvage, reforge
- [ ] 20 Castle levels, buildings, resources, research and 13 units
- [ ] Army visual Tier 0 through Tier 8 visibly demonstrated
- [ ] Late battle reads as enormous army vs monster horde/boss
- [ ] 100-tile Personal Domain
- [ ] Offline claim, events, six dungeons, quests, achievements, codex
- [ ] Alliance/chat/moderation, Titan Hunt and async 10v10 territory war

## Commercial / mobile
- [ ] Apple sandbox purchase verify/restore/refund
- [ ] Google Play sandbox verify/restore/refund
- [ ] No paid random gear/gacha
- [ ] Account deletion/export, Privacy/Terms, age/consent configuration
- [ ] iOS and Android same account/state/backend

## Security / QA
- [ ] Argon2id/bcrypt, strong secrets, secure token storage
- [ ] CORS/rate limiting
- [ ] Mongo uniqueness/atomicity/transactions where needed
- [ ] Idempotency and double-claim tests
- [ ] Device-clock abuse tests
- [ ] War snapshot immutability tests
- [ ] Gear drop/forge economy regression tests
- [ ] Visual regression across low/high mobile profiles
- [ ] Zero open P0/P1

<!-- END DOCUMENT: IDLE_1_v1.1_FINAL_BUILD_CHECKLIST.md -->
