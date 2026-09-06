# IDLE 1 v1.1 — Traceability Matrix (requisiti → codice → test)

Autorità: Master Bible v1.1 FROZEN → CANONICAL_SPEC v1.1 (`backend/canon/IDLE_1_v1.1_CANONICAL_SPEC.json`, hash `a5ba20db…5995`) → Guardrails v1.1 → Art Direction v1.1.
Stato: **DONE** = implementato e coperto da test automatici; **DONE (manual)** = implementato, verifica manuale/testing agent; **BLOCKED** = dipende da input del proprietario; **DERIVED** = distribuzione derivata da totali canonici (documentata nel codice).

## 1. Blocchi di implementazione I01–I16

| ID | Blocco | Gate canonico | Backend | Frontend | Test | Stato |
|---|---|---|---|---|---|---|
| I01 | Account, privacy, secure auth | create/login/recover/delete/export; secure storage; policy screens | `app/domain/account.py`, `app/core/security.py` (Argon2id, JWT 15m, refresh rotante + reuse detection, token_version), `app/core/email.py` (Resend, guard G2/G3), `app/routers/auth.py` | `app/(auth)/login.tsx`, `signup.tsx`, `recover.tsx`, `app/verify.tsx`, `app/onboarding.tsx` (consenso/età), `app/profile.tsx` (privacy, export, delete, logout-all), `src/auth/AuthContext.tsx`, `src/api/client.ts` (SecureStore + refresh single-flight) | `test_core_loop.py::test_auth_lifecycle`, `test_register_validation`, `test_account_export_and_delete` | DONE |
| I01b | Google login (Emergent) | metodo `google` | `account.google_session` (`/auth/session`) | `AuthContext.googleLogin` (WebBrowser/deep link `session_id`) | manual (richiede browser Google) | DONE (manual) |
| I01c | Sign in with Apple | metodo `sign_in_with_apple` | — | pulsante disabilitato in `login.tsx` | — | BLOCKED (account Apple Developer) |
| I02 | Canonical loader + fondamenta Mongo | numeri runtime dal JSON v1.1; idempotenza | `app/core/canon.py` (hash/version/check), `app/core/db.py` (indici), `app/core/ledger.py` (chiave idempotente + guard `recent_ledger_keys`) | `GET /canon/static` → `useCanon` | `test_formulas.py::test_canon_validation`, ledger in `test_battle_attempt_claim_idempotent_and_concurrent` | DONE |
| I03 | Campagna auto-combat | 200 stage, 10 regioni, ondate/elite/boss, esiti deterministici | `app/domain/campaign.py` (attempt escrow → claim idempotente), `app/domain/formulas.py` (`enemy_power`, `enemy_required_power`, `first_clear_rewards`, `repeat_rewards`, `victory_duration`, `monsters_per_wave`) | `app/(tabs)/battle.tsx`, `src/battle/BattleScene.tsx` (anima la timeline server), `src/battle/regions.ts`, `src/battle/sprites.tsx` | `test_enemy_power_table`, `test_first_clear_rewards_table`, `test_battle_attempt_claim_idempotent_and_concurrent`, `test_failure_gives_partial_rewards_and_repeat_farm` | DONE |
| I04 | Eroe XP/skill/talenti | curva 1-100, 3 slot skill, talenti/respec | `app/domain/hero.py`, `formulas.xp_to_next`, `hero_base_stats`, `talent_points_for_level`, `player.hero_stats` | `app/hero/talents.tsx`, hero card in `battle.tsx` | `test_hero_xp_table`, `test_talents_and_skills` | DONE |
| I05 | Gear/inventario/forge/reforge | 9 slot, rarità, drop, auto-salvage/equip, forge +0..20 | `app/domain/gear.py`, `formulas.item_level_for_stage`, `item_base_stats`, `affix_value`, `forge_next_cost`, `forge_multiplier`, `salvage_yield`, `reforge_cost`, `unlocked_drop_weights` | `app/hero/gear.tsx` | `test_item_level_and_stats_samples`, `test_forge_costs_cumulative_samples`, `test_drop_weights_respect_rarity_unlock`, `test_concurrent_forge_never_overspends`, `test_speedup_and_boss_formulas` (salvage) | DONE |
| I06 | Regno, edifici, produzione, timer | 20 livelli Castello, 7 tier visivi, code, timer offline | `app/domain/kingdom.py` (upgrade/speedup), `app/domain/player.py` (`production_per_hour`, `warehouse_capacity`, `settle`, `_apply_completed_queues`), `app/domain/scheduler.py` | `app/(tabs)/kingdom.tsx`, `src/kingdom/KingdomScene.tsx`, sheet "Building Detail" | `test_kingdom_queue_costs_and_timers` | DONE |
| I07 | Ricerca ed esercito | 48×5 ricerche, 13 unità, gate, comando, formazione | `kingdom.start_research`, `research_view`, `recruit`, `set_formation`, `formulas.command_capacity`, `unit_power_multiplier` | `app/kingdom/research.tsx`, `app/(tabs)/army.tsx` | `test_command_capacity_samples`, `test_research_army_formation_rules` | DONE |
| I08 | Renderer spettacolo esercito | tier 0-8, budget proxy 60/120 | `app/core/canon.army_visual_tier` (server decide il tier) | `src/battle/BattleScene.tsx`, `src/battle/sprites.tsx` (coorti proxy, cap low/high-end) | visual/manual | DONE (manual) |
| I09 | Dominio personale | 10×10, 1 tessera ogni 2 stage, bonus produzione | `app/domain/domain_map.py` (ordine di conquista adiacente deterministico), `formulas.domain_tiles_for_stage`, `domain_bonus_pct` | `app/(tabs)/domain.tsx`, `src/domain/DomainMap.tsx` | `test_domain_order_is_adjacent_and_complete` | DONE |
| I10 | Progressione offline | 12h server-timestamp, claim singolo, no device clock | `app/domain/offline.py`, `player.settle` (accrual su `last_seen_at`/`last_production_at` server) | `app/offline.tsx` (modal) | `test_offline_hourly_equivalence_stage_200`, doppio claim in `test_kingdom_queue_costs_and_timers` | DONE |
| I11 | Eventi, dungeon, quest, imprese, codex | evento sempre attivo, energia, track, 4 dungeon, retention | `app/domain/liveops.py`, `app/domain/progress.py`, `app/routers/liveops.py` | `app/events/index.tsx`, `dungeons.tsx`, `quests.tsx`, `achievements.tsx`, `codex.tsx` | `test_events_dungeons_quests` | DONE |
| I12 | Alleanze, chat, moderazione | 30 membri, ruoli, canali, report/block/mute/delete | `app/domain/social.py`, `app/routers/social.py` | `app/(tabs)/social.tsx`, `app/alliance/index.tsx`, `app/alliance/chat.tsx` | `test_alliance_chat_moderation` | DONE |
| I13 | Guerra 10v10 asincrona + Titan Hunt | mappa 19×19, snapshot al lock, 10 lane, cattura, boss | `app/domain/wars.py` (`generate_map`, `declare`, `set_roster`, `lock_war`, `resolve_lanes`, `resolve_war`, `tick_wars`, `attack_boss`) | `app/alliance/war.tsx`, `src/war/WarMap.tsx`, `app/alliance/boss.tsx` | `test_war_full_cycle_deterministic_and_idempotent` (replay deterministico, snapshot unico), `test_titan_hunt` | DONE |
| I14 | Store, pagamenti, restore/refund | prezzi localizzati, verifica server, credito idempotente, refund | `app/domain/store.py` (catalogo canonico, webhook Bearer + HMAC opzionale, dedup event id + transaction key, refund `CANCELLATION/CUSTOMER_SUPPORT`, `EXPIRATION`, restore via REST) | `app/shop.tsx`, `src/billing.ts` (react-native-purchases; nessuna simulazione) | `test_store_webhook_idempotent_and_refund` | DONE (sandbox store: BLOCKED su chiavi RevenueCat) |
| I15 | Shell mobile, push, performance | stesso account iOS/Android, push/deep-link | `app/core/push.py` (relay Emergent), `scheduler.notify` (inbox + push per i 7 tipi canonici), `POST /register-push` | `src/push.tsx` (permessi, token, deep-link `action_url`), `app/inbox.tsx`, `app.json` (bundle `com.idlempirelordsdragon.game`, permessi) | manual (solo build nativa) | DONE (manual) |
| I16 | Audit sicurezza/economia | zero P0/P1, invarianti, concorrenza | rate limit (`slowapi`), CORS, `TEST_HOOKS` vietati in production (`config.py`), ledger, guard versioni | — | suite completa (25 test) + testing agent | IN PROGRESS |

## 2. Formule canoniche → implementazione → test

| Campo canonico | Formula | Codice | Test |
|---|---|---|---|
| `battle.enemy_power_formula` | `round(75·1.047^(stage−1))` | `formulas.enemy_power` | `test_enemy_power_table` (75 / 698 958) |
| `battle.elite/boss_power_multiplier` | ×1.35 / ×1.85 | `enemy_required_power` | idem |
| `battle.first_clear_*_formula` | `25·s^1.35`, `18·s^1.22`, `12·s^1.18` | `first_clear_rewards` | `test_first_clear_rewards_table` |
| `battle.soft_resource_split` | 30/28/24/18 % | `split_soft` | idem |
| `battle.repeat_*_fraction` | 5 % / 12 % / 8 % | `repeat_rewards` | `test_offline_hourly_equivalence_stage_200` |
| `campaign_power_resolution.victory_duration_seconds_formula` | clamp(18+55·req/pow, 18, 90) | `victory_duration` | `test_battle_attempt_*` (425 prima della fine) |
| `campaign_power_resolution.hero_power_formula` | `atk·2 + def·1.5 + hp·0.15` | `player.hero_stats` | `test_battle_attempt_*` (100 potenza iniziale) |
| `hero.xp_to_next_formula` | `round(80·L^1.55 + 40·L)` | `xp_to_next` | `test_hero_xp_table` |
| `hero.talents` | 1 punto / 5 livelli, max 20; warrior +2 % atk | `talent_points_for_level`, `talents_pct` | `test_talents_and_skills` |
| `units.command_capacity_formula` | `50 + L·10 + C²·20` | `command_capacity` | `test_command_capacity_samples` |
| `gear.item_level_formula` | `min(100, max(1, ceil(stage/2)))` | `item_level_for_stage` | `test_item_level_and_stats_samples` |
| `gear.base_stat_formula` | `round(coef·(1+il·0.12)·rarity)` | `item_base_stats` | idem (weapon L50 rare = 99; chest L100 legendary = 2288) |
| `gear.forge.*_cost_formula` | `round((25+il·8)·1.35^f)`, `ceil((2+il·0.08)·1.22^f)` | `forge_next_cost` | `test_forge_costs_cumulative_samples` (tabella `samples`) |
| `gear.forge.stat_multiplier_formula` | `1+0.04f+0.002f²` | `forge_multiplier` | idem (+20 → 2.6) |
| `gear.affix_values.formula` | base·(0.35+0.65·il/100)·rarity·roll, cap | `affix_value` | copertura indiretta (drop) |
| `gear.salvage.forge_dust_formula` | base + floor(il/10)·factor | `salvage_yield` | `test_speedup_and_boss_formulas` |
| `gear.reforge.gold_cost_formula` | `round(50·il·rarity)` | `reforge_cost` | — (API) |
| `gear.stage_drop_weights` + `rarity_unlock_stage` | bande rinormalizzate sulle rarità sbloccate | `unlocked_drop_weights` | `test_drop_weights_respect_rarity_unlock` |
| `battle.gear_drop.*` | 12/30 %, boss 1 garantito +25 %, repeat ×0.5, milestone min rarity | `gear.stage_drop_plan` | `test_concurrent_forge_never_overspends` (boss 10 garantito) |
| `monetization.speedup_formula_rubies` | `max(5, ceil(min/3))` | `speedup_rubies` | `test_speedup_and_boss_formulas` |
| `personal_domain.*` | 1 tessera/2 stage, +5 %/10 tessere, cap 50 % | `domain_tiles_for_stage`, `domain_bonus_pct` | `test_domain_order_is_adjacent_and_complete` |
| `offline.*` | 12h, 0.7 loot, 0.85 risorse, 0.7 gear roll | `offline.preview/claim`, `player.settle` | `test_offline_hourly_equivalence_stage_200` |
| `events.base_deployment_reward.*` | token `(20+s·0.35)·m`, oro `(150+s·8)·m` | `event_deploy_rewards` | `test_events_dungeons_quests` |
| `dungeons.catalog[*].formula` | 4 formule | `dungeon_rewards` | idem (forge_depths T2 = 130) |
| `events.alliance_boss.*` | HP `500000·t^1.8`, danno `pow·4`, 3 free + 3 paid | `boss_hp`, `boss_attack_damage`, `wars.attack_boss` | `test_titan_hunt`, `test_speedup_and_boss_formulas` |
| `alliance_war.*` | prep 8h, lock 30', 10 lane, varianza 0.98–1.02, NPC 70 % mediana, punti 100/25, monete 100+150 | `wars.*` | `test_war_full_cycle_deterministic_and_idempotent` |
| `buildings[*].levels` | costi/tempi/produzione per livello | `kingdom.building_view/upgrade_building` | `test_kingdom_queue_costs_and_timers` |
| `research.nodes[*].levels` | costi/tempi | `kingdom.start_research` | `test_research_army_formation_rules` |
| `units.catalog[*]` | costi, gate, potenza | `kingdom.recruit`, `player.army_power` | idem (30 infantry = 1143 con +3 %) |
| `quests.login_calendar` | 35 Rubini / 7 gg | `liveops.LOGIN_RUBIES` **DERIVED** (3,3,4,4,5,6,10) | `test_events_dungeons_quests` |
| `events.event_track` | 40 free / +80 premium | `liveops._track_rewards` **DERIVED** | copertura API |
| `monetization.season_pass` | 150 / 500 Rubini, materiali | `liveops.season_level_rewards` **DERIVED** | copertura API |

## 3. Guardrail / sicurezza

| Requisito | Implementazione | Verifica |
|---|---|---|
| `security.server_authoritative`, `device_clock_trusted=false` | tutti i timer/claim usano `now()` server; `time-shift` test-hook sposta i timestamp server | tutti i test usano `/_test/time-shift` |
| `security.idempotency_required` (iap, reward, event, war, offline) | `ledger.apply_to_player` con chiave unica + `recent_ledger_keys` | test idempotenza battle/offline/event/war/store |
| `security.password_hashing` Argon2id | `pwdlib.PasswordHash.recommended()` | `test_auth_lifecycle` |
| `security.jwt` short-lived + rotating refresh | `security.issue_tokens`, `rotate_refresh` (famiglia revocata al riuso) | `test_auth_lifecycle` |
| `security.rate_limits` | `slowapi` su auth/chat/export; chat 5 msg/10 s | `test_alliance_chat_moderation` (429) |
| `security.production_memory_store_forbidden` | stato solo in MongoDB | — |
| `payments.client_trusted_for_entitlement=false` | `/purchases/verify` → 503 senza segreto RC; credito solo da webhook/REST | `test_store_webhook_idempotent_and_refund` |
| `monetization.paid_random_gear_or_gacha=false` | catalogo senza casse gear; flag esposto | idem (`paid_random_gear_or_gacha is False`) |
| `monetization.display_price_rule` | prezzi da `Purchases.getProducts`; `reference_eur` mostrato solo in anteprima web | `shop.tsx` |
| `alliance_war.snapshot_lock_rule` | snapshot unico immutabile (`war_snapshots`, 1 per guerra) | `test_war_full_cycle_*` (`snaps == 1`, replay deterministico) |
| Email G2/G3 (no form, https, nessuna richiesta credenziali) | `email._assert_safe_email` | eseguito anche nei test (mock invia) |
| `accounts.in_app_account_deletion`, `account_export` | `account.delete_account` (anonimizzazione, retention acquisti), `export_data` | `test_account_export_and_delete` |
| `privacy_account.legal_copy` (non inventare) | URL da env `PRIVACY_POLICY_URL`/`TERMS_URL`; UI mostra "input del proprietario mancante" | BLOCKED (deployment input) |
| `TEST_HOOKS_ENABLED` mai in produzione | `config.py` solleva errore se `IDLE1_ENV=production` | avvio |

## 4. Schermate canoniche (`ux.screens`) → route Expo

Splash `app/index.tsx` · Login `(auth)/login` · Sign Up `(auth)/signup` · Password Recovery `(auth)/recover` · Onboarding `onboarding` · Battle `(tabs)/battle` · Kingdom `(tabs)/kingdom` · Building Detail (sheet in kingdom) · Research `kingdom/research` · Army `(tabs)/army` · Personal Domain Map `(tabs)/domain` · Events `events/index` · Alliance `alliance/index` · Alliance War Map `alliance/war` · Chat `alliance/chat` · Chronicle/Inbox `inbox` · Shop `shop` · Profile/Settings/Privacy & Account `profile` · Gear/Inventory/Forge `hero/gear` · Talents `hero/talents` · Dungeons `events/dungeons` · Daily/Weekly Quests `events/quests` · Achievements `events/achievements` · Codex `events/codex` · Alliance Boss `alliance/boss` · Offline chest `offline` · Verify email `verify`.

## 5. Notifiche push canoniche (`notifications.push`)

| Tipo | Origine |
|---|---|
| construction_complete / research_complete / recruitment_complete | `scheduler.tick_timers` |
| offline_chest_full | `scheduler.tick_offline_full` |
| event_ending | `scheduler.tick_event_ending` |
| alliance_war_roster_needed | `wars.declare` |
| alliance_war_result | `wars.resolve_war` |
Opt-out non essenziali: `settings.push_nonessential` (`PATCH /account/settings`). Registrazione device: `POST /register-push` (solo build nativa).

## 6. Input di deployment (non canon, non inventati)

Account Apple/Google Play, chiavi RevenueCat (`EXPO_PUBLIC_RC_IOS_KEY`, `EXPO_PUBLIC_RC_ANDROID_KEY`, `REVENUECAT_SECRET_KEY`, `REVENUECAT_WEBHOOK_SIGNING_SECRET`), `google-services.json`, `EMERGENT_PUSH_KEY` (impostato al Publish), URL Privacy/Termini, titolo marketing.
