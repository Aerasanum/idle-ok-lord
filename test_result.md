#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
user_problem_statement: "IDLE 1 v1.1 — idle/auto-battler mobile (Expo RN + FastAPI + MongoDB), server-authoritative, following the canonical JSON spec. Auth email+password (Argon2id, Resend codes), Emergent Google Auth, RevenueCat IAP webhook, Emergent push. Italian UI."

backend:
  - task: "Auth lifecycle (register/verify/login/refresh rotation/reset/logout-all/export/delete)"
    implemented: true
    working: true
    file: "backend/app/domain/account.py, backend/app/core/security.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "pytest test_auth_lifecycle green; email sender mocked in tests (Resend blocks synthetic recipients)."
  - task: "Campaign battle attempt/claim idempotent + rewards + drops"
    implemented: true
    working: true
    file: "backend/app/domain/campaign.py, backend/app/domain/gear.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "pytest green (concurrency 8x claim credits once, 425 too_early, stage lock 400)."
  - task: "Kingdom upgrade/queues/timers/offline chest"
    implemented: true
    working: true
    file: "backend/app/domain/kingdom.py, backend/app/domain/player.py, backend/app/domain/offline.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Fixed research completion (node keys contain dots -> whole-object $set). pytest green."
  - task: "Research/army/formation/hero talents/skills/forge"
    implemented: true
    working: true
    file: "backend/app/domain/kingdom.py, hero.py, gear.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "pytest green after aligning tests to canon (skills power_strike/war_cry, nodes economy.crop_yield...)."
  - task: "LiveOps events/dungeons/quests/achievements/codex/season"
    implemented: true
    working: true
    file: "backend/app/domain/liveops.py, backend/app/routers/liveops.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "pytest green."
  - task: "Alliances/chat moderation/wars 10v10/Titan Hunt"
    implemented: true
    working: true
    file: "backend/app/domain/social.py, backend/app/domain/wars.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Fixed wars.map_view rules key + boss attack counters. pytest green."
  - task: "Store catalog / RevenueCat webhook idempotent + refund / crates"
    implemented: true
    working: true
    file: "backend/app/domain/store.py, backend/app/routers/store.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Added optional HMAC signature check (REVENUECAT_WEBHOOK_SIGNING_SECRET). pytest green."

frontend:
  - task: "Auth screens (login/signup/recover/verify/onboarding) + session persistence"
    implemented: true
    working: "NA"
    file: "frontend/app/(auth)/*, frontend/app/verify.tsx, frontend/src/auth/AuthContext.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Needs E2E test."
  - task: "Battle tab (auto battle, stage nav, result card, hero card, quick links)"
    implemented: true
    working: "NA"
    file: "frontend/app/(tabs)/battle.tsx, frontend/src/battle/BattleScene.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Needs E2E test."
  - task: "Kingdom tab (scene, building sheet, upgrade, queues, speedup) + Research screen"
    implemented: true
    working: "NA"
    file: "frontend/app/(tabs)/kingdom.tsx, frontend/app/kingdom/research.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Needs E2E test."
  - task: "Army tab (recruit sheet, formation), Domain tab, Social tab + Alliance hub/chat/war/boss"
    implemented: true
    working: "NA"
    file: "frontend/app/(tabs)/army.tsx, domain.tsx, social.tsx, frontend/app/alliance/*"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Needs E2E test."
  - task: "Hero gear/talents, Events/Dungeons/Quests/Achievements/Codex, Shop, Profile, Offline, Inbox"
    implemented: true
    working: "NA"
    file: "frontend/app/hero/*, frontend/app/events/*, frontend/app/shop.tsx, profile.tsx, offline.tsx, inbox.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Needs E2E test."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: true

test_plan:
  current_focus:
    - "Auth screens (login/signup/recover/verify/onboarding) + session persistence"
    - "Battle tab (auto battle, stage nav, result card, hero card, quick links)"
    - "Kingdom tab (scene, building sheet, upgrade, queues, speedup) + Research screen"
    - "Army tab (recruit sheet, formation), Domain tab, Social tab + Alliance hub/chat/war/boss"
    - "Hero gear/talents, Events/Dungeons/Quests/Achievements/Codex, Shop, Profile, Offline, Inbox"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Backend: 25/25 pytest green (python -m pytest /app/backend/tests -q). Please run API contract checks against the live preview URL and a full frontend E2E on web preview (390x844). QA account in /app/memory/test_credentials.md. Test hooks available under /api/_test/* (grant, time-shift, tick). Google login / push / native IAP cannot be exercised on web preview (expected)."
  - agent: "testing"
    message: "Iteration 1: backend 31/31 live E2E pass (tests/test_live_e2e.py); frontend E2E all flows pass. One MEDIUM bug: /hero/talents 'totale attuale NaN%'."
  - agent: "main"
    message: "Fixed talents NaN (parse numeric suffix of effect_per_rank string). Verified via screenshot: shows 0.0%."
  - agent: "main"
    message: "NEW (iteration 2 scope): Battle VFX (screen shake, flashes, floating damage numbers, slash arcs, spark bursts, coin shower + VITTORIA/SCONFITTA banner held 1.5s before claim, boss HP bar, region ambience) in src/battle/BattleScene.tsx + effects.tsx; SVG enemy sprites per archetype (src/battle/monsters.tsx) and SVG Lord (src/battle/lord.tsx, gear-aware, swinging sword); guided tutorial (src/tutorial/Tutorial.tsx, 9 steps, spotlight overlay, auto-starts when profile.settings.tutorial_done !== true, 'Rivedi il tutorial' in Profile, completion stored via PATCH /account/settings {tutorial_done}). Alliance boss screen now uses MonsterSprite."
  - agent: "main"
    message: "ITERATION 3: (1) Expo Go boot crash fix — expo-notifications now loaded lazily via src/push/adapter.ts (guarded by ExecutionEnvironment.StoreClient); src/push.tsx moved to src/push/index.tsx. Acceptance script: `node /app/frontend/scripts/expo-go-acceptance.mjs` (must PASS). (2) Skill VFX: each equipped auto-skill fires a distinct effect + flashing name banner (testID skill-banner) every cooldown cycle. (3) Kingdom life: peasants, smoke, construction sites (testID construction-site) with progress bar, castle flag. QA account now has skill slot power_strike (cooldown 9s)."
  - agent: "main"
    message: "ITERATION 4: AI-generated stylized-3D art (frontend/assets/art, 96 webp) wired into battle scene (region backgrounds, Lord/monster/unit images, testIDs lord-art, monster-art), kingdom scene (ground + building renders), army tab, hero portrait (testID hero-portrait), auth/splash key art (HeroBackdrop). Research UX fix: open-research-button moved under the kingdom scene; university building-sheet has sheet-open-research-button; research screen shows research-reason-<node> text when Avvia is disabled. New fresh account lord.tester@idle1.app / Idle1Lord!2026."
  - agent: "main"
    message: "ITERATION 5: enemy combat animation loop (MonsterSprite attack shared value), Lord heavy strikes every 4th swing (big golden slash, burst, shake), enemy counter-attack numbers (red) + Lord recoil; Domain map now uses illustrated tiles (frontend/assets/art/tiles) with perspective tilt and conquest reveal; procedural audio (frontend/assets/audio: 9 sfx + 10 region loops) via expo-audio — music starts on battle scene mount, volumes in Profile (testIDs audio-settings, music-volume-minus/plus/value, sfx-volume-*), persisted to settings.music_volume/sfx_volume."
  - agent: "main"
    message: "ITERATION 6: (1) Item icons — 45 generated item illustrations (frontend/assets/art/items/<slot>_<tier>.webp, tier by rarity: common=basic_a, uncommon=basic_b, rare=fine_a, epic=fine_b, legendary+/mythic/ancient=ornate) + 11 resource icons (assets/art/resources). Component src/ui/ItemIcon.tsx (testID <id>-art on the Image) used in /hero/gear (equipped grid, inventory grid, item detail sheet testID item-detail-icon, forge cost row shows gold+forge_dust art), battle ResultCard (testID result-loot, loot-<id>), offline chest (testID offline-loot). Res component got an `art` prop (image instead of vector icon). (2) Alliance war verification: seed script backend/scripts/seed_war_demo.py — QA Lord leads [QAT] with 10 members (can declare war), rival [ORS] Orsi Neri has 10 members and already captured node 3 (leaderboard 100 pts). WarMap now has a legend (testID war-map-legend), stronger ownership colors; war rows/detail show Italian status labels; roster picker pre-fills the saved roster."
  - agent: "main"
    message: "ITERATION 7 (owner batch): (a) CANON v1.2 live update (scripts/canon_v12.py; hash 481dd024…; unit stats unchanged): unit counters (units.counters: strong_vs +30% / weak_vs -20% vs 7 enemy classes; battle.enemy_classes), late-game ramp enemy_power = 75*1.047^(s-1)*(1+0.004*max(0,s-50)), conquest_wagon renamed 'Ariete d'Assedio'. Backend: F.stage_enemy_mix/unit_counter_pct/army_class_mix, combat_profile(enemy_mix), campaign attempt uses stage mix, GET /battle/stage/{n} returns army_counter_net_pct + enemy_mix, GET /army returns counters + region_counter, war lanes re-evaluate army vs opponent class mix (lane_power) and expose attacker/defender_counter_pct/_npc/_level. (b) War chat live alerts: alliance_alert() posts system messages (kind 'war'/'titan', display_name 'Araldo di guerra') in alliance:{id} channel on declare (both sides), roster save, lock, cancel, result; Titan start/kill. (c) Titan Hunt: boss_view returns titan_family (region boss of tier), tier_families, leaderboard [{rank, display_name, damage, attacks, share_pct}], my_player_id. Test hook war-shift accepts include_resolved to clear the 24h cooldown. Frontend: BattleScene rewritten (Lord moves slash/heavy/spin/dash/leap, SUPER power-up at 6s then every 20s with aura testID super-aura, banner 'POTENZA MASSIMA', ultimate-wave, combo-counter, super-gauge; enemy moves lunge/leap/spin/roar/dodge/spit/swoop with projectiles/dust/shockwaves; death dissolve). SFX removed entirely (music only; Profile shows only 'Musica' slider testID music-volume). Kingdom walls = perimeter ring (testID kingdom-walls / kingdom-walls-unbuilt) with towers + gatehouse tap target building-walls. Army tab shows Forte/Debole contro (testID counters-<unit>, region-pct-<unit>, enemy-mix). Battle tab shows 'Contro-unità ±x%' (army-counter-net). War detail: animated WarReplay (testIDs war-replay, war-replay-score, war-replay-lanes, war-replay-lane-label, war-replay-lane-result, war-replay-toggle, war-replay-skip, war-replay-summary, war-replay-restart). Chat renders war/titan alerts as highlighted cards. Titan Hunt screen: TitanStage (titan-stage, titan-art, titan-name), leaderboard (titan-leaderboard, hunter-<pid>), tier preview (titan-preview)."
  - agent: "main"
    message: "ITERATION 8 (owner batch 2): (1) 18 realistic VFX sprites generated (assets/art/vfx/*.webp, luma→alpha) and wired: Slash/Burst/Shockwave/Lightning/DustPuff/Projectile(energy_orb|arrow_volley)/SuperAura(energy_aura)/UltimateWave(holy_beam)/DeathDissolve(soul_wisp) + SpriteFx primitive. (2) Removed the upside-down moves: Lord spin → rising slash (kind 3), enemy spin charge → straight charge (kind 2); new Lord kind 8 = dodge back-dash. (3) Army proxies now fight (FightingProxy: step/strike/pounce/recoil per category) and shoot volleys every 2.4s (archers/falcon arrows, siege orbs, dragon fire_breath) with small damage numbers. (4) Lord and enemies scale down with bigger armies (k = max(0.82, 1 − proxies·0.016)). (5) Boss special moves: BOSS_MOVES per regional boss (Ogre Warlord Schianto della Mazza/slam, Ancient Treant roots, Mountain Tyrant Frana/quake, Bone Colossus quake, Ice Giant King shards, Sand Wyrm vortex, Leviathan wave, Elder Dragon breath, Fallen Seraph beam, World Devourer void): testID boss-warning strip '⚠ MOSSA SPECIALE <name>' for 1.25s with the boss glowing red (MonsterSprite charging), then BossMoveFx; the Lord dodges (attempt.win: back-dash + ghosts + float-text 'SCHIVATA!') or takes a big hit (loss). Backend build_timeline gives the boss wave 35% of the duration (first move at +1.5s then every 7s). (6) Zoom: src/ui/ZoomPan.tsx (pinch/pan/double-tap + buttons testIDs <id>-zoom-in/-zoom-out/-zoom-reset) on battle (battle-zoom), kingdom (kingdom-zoom), domain map (domain-zoom), war map (war-zoom), titan (titan-zoom), formation preview (formation-preview); global UI text zoom src/ui/uiScale.ts (0.85–1.4) applied by Txt, controls ZoomPill (testIDs ui-zoom / ui-zoom-bar in ResourceBar / ui-zoom-profile in Profile with -out/-in/-value) + pinch on Screen pages (UiPinch). (7) Formation area /army/formation (testIDs formation-screen, formation-preview, formation-power, formation-types, formation-command, suggest-formation-button → suggestion-panel with apply-suggestion-button / edit-suggestion-button, per-unit formation-plus/minus/plus10/max/zero-<unit>, apply-formation-button) reachable from Army tab (open-formation-button) and Battle hero card (open-formation-button). Backend GET /army/suggest?stage= (K.suggest_formation: top units by power-per-command with counters, fill command capacity) returns formation/picks/army_power/current_army_power/required_power. (8) Lord rename shortcut: pencil on the Battle hero card (rename-lord-button → rename-sheet, rename-input, rename-save-button → PATCH /account/settings display_name). Test bot orsi.bot1@idle1.app / QaBot!2026 was granted highest_cleared 49 (stage 50 = boss Mountain Tyrant) with auto-battle OFF for boss-move checks."
  - agent: "main"
    message: "ITERATION 9 (owner batch 3): (A) Duel HUD in battle: src/battle/effects.tsx HpBar (testIDs lord-hp-bar, lord-hp-bar-name/-sub/-pct; boss-bar, boss-bar-name/-sub/-pct during the boss wave) — Lord bar shows name · 'Lv N · Potenza X' · %, boss bar shows 'Stage N · Potenza richiesta' · %. (B) Lord name separate from player name: profile.hero.name (default 'Lord'); PATCH /account/settings {lord_name}; Battle hero card (lord-name, lord-level-power, player-name, rename-lord-button → rename-sheet/rename-input/rename-save-button now sends lord_name); Profile 'Identità' panel has display-name-input/rename-button AND lord-name-input/rename-lord-profile-button. Battle tab badge running-stage-badge ('In corso: Stage X') when attempt.stage != selected. (C) Rulebook PDF: GET /api/docs/regolamento.pdf (public, read-only AES-256 with empty user password, 41 pages, generated by backend/scripts/gen_rules_pdf.py); Profile button rules-pdf-button. (D) NEW TAB 'Eventi' (tab-events → events-hub-screen) = hub of 3D-art tiles (src/ui/HubTile.tsx): hub-daily, hub-weekly, hub-login (→ /events/quests), hub-event (→ /events/weekly, the old /events index was renamed), hub-dungeons, hub-titan (→ /alliance/boss or /social), hub-achievements, hub-codex, hub-shop (→ /shop); badges <id>-badge with claimable counts. Social tab now has art tiles hub-chat (→ /alliance/chat, channels channel-Globale / channel-Alleanza / channel-Feed / channel-Guerra N), hub-war, hub-boss (locked without alliance) + hub-events / hub-shop-social. ResourceBar rubies chip res-rubies-shop opens /shop. (E) Cosmetic skins: backend app/domain/cosmetics.py (6 Lord skins, 4 Castle skins, Rubies), GET /store/cosmetics, POST /store/cosmetics/buy {key} (atomic rubies check, auto-equip), POST /store/cosmetics/equip {kind: lord|castle, key|null}; profile.cosmetics {lord_skin, castle_skin, owned}. Frontend src/shop/SkinShop.tsx in /shop (testIDs skin-shop, skins-lord, skins-castle, skin-<key>, buy-<key>, equip-<key>, unequip-<kind>); skins override lordArt()/buildingArt('castle') everywhere via setActiveSkins (tabs layout). Art generated: assets/art/skins/*.webp (10) and assets/art/hub/*.webp (11). QA account owns lord_frost_warden + castle_dragon_keep (both equipped) and has ~3.9K rubies."
  - agent: "main"
    message: "ITERATION 10 (owner batch 4): (1) Skin preview: /skin-preview?key=<skin> full-screen (testIDs skin-preview-screen, skin-preview-stage, skin-preview-name, skin-preview-lord | skin-preview-castle | skin-preview-banner, skin-preview-buy | skin-preview-equip, skin-preview-close, skin-preview-back); Lord skins loop a special move (SUPER aura → dash → slash/burst/shockwave → ultimate wave, banner 'MOSSA SPECIALE'); castles get fireworks; army banners show a marching row. Opened from shop cards (preview-<key>) and the daily deal. (2) Army skins: cosmetics kind 'army' (4 banners: army_crimson_legion 400, army_azure_order 400, army_emerald_wardens 550, army_obsidian_pact 750; fields color/glow); profile.cosmetics.army_skin + resolved profile.cosmetics.army {key,name,color,glow}; equip kind 'army'; battle scene plants the banner (testID army-banner, WarBanner in effects.tsx) and uses the skin colour as heraldicColor for troop flags. Shop section skins-army. (3) Quick chat on Social tab: testIDs quick-chat, quick-chat-messages, quick-message-<id>, quick-chat-input, quick-chat-send, quick-chat-open (last 4 global:it messages, inline send). (4) Daily deal: GET /store/cosmetics returns deal {key, kind, name, rubies, original_rubies, discount_pct 30, ends_at next UTC midnight} + catalog[].rubies_now; buy charges the discounted price for the deal key (response deal:true). Shop card daily-deal (daily-deal-countdown, daily-deal-buy | daily-deal-equip, daily-deal-preview). QA now also owns army_crimson_legion (equipped) — leave it equipped."
  - agent: "main"
    message: "ITERATION 11: Public player showcase. Backend GET /api/players/{player_id}/showcase (auth) → {player_id, is_me, display_name, heraldic_color, hero{name,level}, power{total,hero,army}, campaign{highest_cleared,region}, castle_level, army_visual_tier, alliance{tag,name}|null, cosmetics (resolved incl. army {key,name,color,glow}), has_chest, gear[{slot,rarity,item_level}], domain_tiles}; 404 player_not_found. Frontend route /player/[id] (testIDs showcase-screen, showcase-stage, showcase-lord, showcase-banner (only if army skin), showcase-castle, showcase-alliance, showcase-lord-name, showcase-player-name, showcase-power, showcase-skin-lord/-castle/-army, showcase-gear, showcase-back, showcase-shop (only is_me), showcase-missing for 404). Entry points: alliance member rows (showcase-<player_id> in /alliance), Titan leaderboard rows (hunter-<player_id> now pressable), chat long-press sheet button showcase-button, Profile button my-showcase-button."
  - agent: "main"
    message: "ITERATION 12: War map redesign. src/war/WarMap.tsx: illustrated tiles (assets/art/tiles) with bevel, calm palette (gold = own with dot markers war-own-<id>, crimson = rivals, unowned base sites = ruins), banners on owned home castles, pulsing war-ring on contested nodes, legend war-map-legend, 'Il mio territorio' button war-goto-mine (auto-focus on mount), map inside ZoomPan (testID war-zoom) with controls war-zoom-zoom-in/-zoom-out/-zoom-reset and a D-pad war-zoom-dpad with war-zoom-pan-up/-down/-left/-right; content 760x760 inside a ~366x337 viewport (min scale fits, max 3.2). src/ui/ZoomPan.tsx now supports contentWidth/Height, minScale/maxScale, dpad, ref.focus/reset/panBy (used by battle, kingdom, domain, titan — regressions to check). War simulation hooks: POST /api/_test/war-shift {seconds, include_resolved} moves lock/resolve times; POST /api/_test/tick runs the scheduler; declare = POST /api/wars/declare {node_id}, roster = POST /api/wars/roster {war_id, attackers|defenders...}, GET /api/wars/map, GET /api/wars/{id}. tests/test_alliance_wars.py has an E2E flow (QA alliance QAT vs bots ORS; node 21 is already owned by QAT → pick another adjacent enemy/neutral node)."
  - agent: "main"
    message: "ITERATION 13: Always-visible chat dock on the Battle tab (src/social/ChatDock.tsx, mounted at the bottom of app/(tabs)/battle.tsx above the tab bar). testIDs: chat-dock, dock-channel-Globale, dock-channel-Alleanza (only if in an alliance), dock-toggle (expand/collapse: collapsed shows last 2 messages, expanded up to 40 in a 260px list), dock-open-full (→ /alliance/chat), dock-messages, dock-message-<id>, dock-input (focusing expands the dock), dock-send. Sends POST /chat/messages {channel, text}; polls every 4s."
  - agent: "main"
    message: "ITERATION 14: War roster booking (prenotazioni). Backend: POST /api/wars/{war_id}/enlist (any member of attacker/defender alliance; first-come first-served, atomic, max 10 per side, 409 already_enlisted / roster_full / war_not_open / roster_locked, 403 not_in_war), POST /api/wars/{war_id}/withdraw (409 not_enlisted). Declaring (leader or officer) auto-books the declarer as attacker #1. lock_war: under-filled ATTACK is now allowed — missing attackers become 'Corsia vuota' entries (war_power 0, npc+empty) that lose their lane; only an EMPTY attack roster cancels the war (reason empty_attack_roster). Officers keep POST /wars/roster override. Frontend app/alliance/war.tsx → src/war/WarEnlist.tsx inside war-detail for prep wars: testIDs war-enlist, war-lock-countdown, war-roster-slots, war-slot-1..10, war-enlist-button, war-withdraw-button. Current open war: war_59a1d8ecf93240558b32bb02ab2a1190 (QAT attacking ORS node 22, prep, QA Lord enlisted)."
  - agent: "main"
    message: "ITERATION 15: (1) Reserves: when a side's roster is full, POST /wars/{id}/enlist adds the player to attack_reserve/defense_reserve (response reserve:true, reserve_position; 409 already_reserve if repeated); POST /wars/{id}/withdraw from the roster promotes the first reserve automatically (response promoted:<player_id>); withdraw while in reserve just leaves the queue. Detail roster_players includes reserves. UI (WarEnlist): war-reserve-list, war-reserve-<n>; button text changes to 'Roster completo: prenotati come riserva' / 'Esci dalla riserva (sei n.X)'. (2) Battle tab banner src/war/WarCallBanner.tsx: testIDs war-call-banner, war-call-title ('Guerra dichiarata: prenotati!' for attackers / 'Siamo sotto attacco: difendi!' for defenders), war-call-status ('N posti liberi su 10' | 'Sei schierato ✓' | 'In riserva n.X' | 'Roster completo · riserve N' + lock countdown); tap → /alliance/war; hidden when no prep war. Current state: war war_0b2db37c91bb4cd8b4ca6e933ca8509d (QAT → ORS node 22, prep): attack roster 10 (qa.lord, qa.bot1..8, lord.tester who joined QAT with castle 8), reserve: qa.bot9."
  - agent: "main"
    message: "ITERATION 16: (A) Canon v1.3 (scripts/canon_v13.py; spec_hash + REQUIRED_VERSION updated): Warehouse capacity_each_resource raised for levels 11-20 so capacity(L) >= 1.1 x the largest single upgrade cost (castle L->L+1, buildings and research unlocked at castle <= L). New capacities L11..L20: 80000,123000,191000,297000,459000,711000,1102000,1706000,2641000,2641000 (was 68929..730960). Castle 20 (2.4M wood) now fits in warehouse 19/20. Capacities are read live from the canon → existing players keep progress and immediately get the higher caps. GET /api/canon/static VERSION == '1.3'. Kingdom building sheet shows capacity-hint when a cost exceeds the current warehouse capacity. (B) Roster power: GET /api/wars/{id} now returns my_side, team_power and roster_players[pid].war_power ONLY for the requester's own alliance (enemy players have no war_power key). UI WarEnlist: war-team-power, war-slot-power-<n>; enemy side shows only the count ('la loro potenza resta segreta'). (C) Rulebook regenerated as static/IDLE1_Regolamento.pdf (same route /api/docs/regolamento.pdf), header says spec v1.3 and the warehouse rule is documented in chapter 2."
  - agent: "main"
    message: "ITERATION 17: Canon v1.4 (scripts/canon_v14.py; REQUIRED_VERSION 1.4, new spec_hash). (A) Units rebalanced: base_power = command × (36 + 1.4×unlock_castle + 14 mythic/6 siege/3 beast); stats scaled by the same factor, recruit costs by 85% of the factor. New base_power/command: infantry 37/1, archer 40/1, cavalry 129/3, catapult 414/8, conquest_wagon 655/12, wolf 106/2, falcon 109/2, bear 212/4, lion 218/4, war_elephant 558/10, dragon 1740/25, angel 1810/25, demon 1880/25 → a Dragon (1740) now beats 25 infantry (925) for the same command. (B) Enemy curve now canon-driven: battle.enemy_power_base 75, battle.enemy_power_growth 1.043 (was hardcoded 1.047 in formulas.py), difficulty_ramp per_stage 0.0015 from stage 50. Required power bosses: 50→1,092 · 100→9,633 · 150→84,586 · 180→310,807 · 200→739,513; conservative attainable model (scripts/canon_v14.py attainable()) gives 45.5K / 185K / 428K / 722K / 879K → all beatable. (C) /army/suggest (kingdom.suggest_formation) fixed: greedy by power-per-command over ALL candidates, a type only takes a slot if ≥1 unit fits, leftover command is filled by next-best types. (D) Rulebook regenerated with v1.4 texts (chapter 4.1 curve, 5.2 unit rule, formulas page). Tests updated (test_formulas, test_canon_v13_warehouse)."
  - agent: "main"
    message: "ITERATION 18: Canon v1.5 (scripts/canon_v15.py, idempotent; REQUIRED_VERSION 1.5, hash b5ab4a57…; docs/CANONICAL_SPEC.json mirrored). (1) Unlocks: each unit has effective_unlock_castle_level = max(castle gate, castle level of the required research) (archer 3→4, cavalry 5→7, conquest_wagon 9→10, war_elephant 12→13); all gates unchanged. GET /api/army units[] now includes effective_unlock_castle_level, required_research_name, required_research_castle_level; Army tab locked text (testID unit-gates-<key>) shows 'Ricerca <name> (Castello N)' and '· disponibile dal Castello N'. (2) Rarity: gear.stage_drop_weights split into 7 bands (1-9 common 100; 10-24 common 77/uncommon 23; 25-49 56/35/9; 50-89, 90-139, 140-179, 180-200 unchanged) so no band lists a locked rarity; gear.drop_filter_rule documents the filter + exceptions. (3) Domain: F.domain_tiles_for_stage = min(100, 1 + max(0, floor((stage-4)/2)+1)) → 1 tile until stage 3, 2 at stage 4, 99 at 199, 100 at 200 (personal_domain.first_extra_tile_stage=4). Stored domain.owned is only rewritten on the next stage clear. (4) document.rounding lists every rounding; PDF now prints floor()/ceil() instead of ⌊⌋⌈⌉ (font had no glyphs). (5) gear.reforge.effect documents actual behaviour (retired affix NOT protected). (6) Quests: canon templates have Italian text (+ alternatives); GET /api/quests daily/weekly.templates[] now {key, points, target, text, alt_active} and tasks[key] has text/alt_active/alt_when. Alternatives: forge maxed on all 9 slots → reforge/salvage credit forge_upgrade/forge_upgrades (1 per item); research all max → building upgrade credits start_or_finish_research; research+buildings max → recruit order credits it. progress.py: quest_alternatives(), alt_quest_progress(), forge_all_max/research_all_max/buildings_all_max. (7) WAR CASUALTIES: wars.lane_casualties() + resolve_lanes() attach attacker_casualties/defender_casualties per lane; apply_casualties() deducts once per war+player via ledger key war_losses:<war_id>:<pid>, never above deployed/owned, clamps formation, snapshot untouched; result.casualties[pid] = {side, lane, won, ratio, rate_pct, units{k:{deployed,lost,survived,rate_pct}}, deployed_total, lost_total}. Formula: r=min/max lane powers; winner 0.05+0.20r, loser 0.30+0.30(1-r); defender x0.85; category regular 1/beast 0.9/siege 0.8/mythic 0.6; lost=floor(deployed*rate) → ≥1 survivor per type; empty lanes → no fight, NPC → nothing to lose. GET /api/wars/{id} adds my_casualties and team_casualties {deployed, lost, players[]} (own side only). Alliance chat result alert appends '⚰ Perdite: X unità cadute su Y schierate (Z superstiti)'. UI war detail: testIDs war-casualties, war-casualty-<pid>, war-my-casualties. Live check script scripts/check_war_casualties.py passed (QAT vs ORS node 2: 76 lost / 1642 deployed, idempotent on re-tick, snapshot identical). Rulebook regenerated: 43 pages, chapters 5.3 (Disponibile dal), 8.2 (rarity filter), 8.5 (reforge), 9.1 (domain table), 10.4 (quest texts + alternatives), 11.3 (casualties formulas + table + 6 worked examples), 13 (formulas + rounding). Unit tests: tests/test_canon_v15.py (8) + test_formulas/test_canon_v13 all green."
  - agent: "main"
    message: "ITERATION 18b: Achievements now have texts. GET /api/achievements items include title ('Conquistatore I..V', 'Veterano', 'Cercatore di reliquie', 'Signore del Castello', 'Reclutatore', 'Signore del Dominio', 'Esploratore', 'Fratello d'armi' + tier numeral), description ('Supera lo stage 50 della Campagna'), unit_label, status ('Riscattata: +N Rubini' | 'Completata! Ritira N Rubini' | 'Supera ancora X stage per ottenere N Rubini'), category_label; response has category_labels. UI /events/achievements: testIDs ach-title-<key>, ach-desc-<key>, ach-status-<key>; claim button reads 'Ritira N' when unlocked; category chips in Italian. Verified by screenshot."
  - agent: "main"
    message: "ITERATION 18c: Achievement alerts. src/achievements/useAchievementAlerts.ts (mounted in app/(tabs)/_layout.tsx): polls /achievements every 30s (also invalidated by every useAction success and by battle claim); the first run on a device stores the current claimable set (storage key idle1.ach.notified.<player_id>) so only NEW unlocks toast: 'toast-success' text '🏆 Impresa completata: <title> — ritira N Rubini in Eventi › Traguardi' (or 'N imprese completate…'). Eventi tab icon shows a red counter dot testID tab-events-dot (count of claimable, '9+' cap; rendered twice by the web tab bar → use .first). Verified via screenshot: dot '9+' and toast 'Veterano III' after granting hero level 50 (restored to 47)."
  - agent: "main"
    message: "ITERATION 19/20: (a) Max account max.lord@idle1.app / MaxLord!2026 (castle 20, all buildings 20, hero 100, research max, forge 20, stage 200 cleared, domain 100) — testing agent iteration_19 verified end-game playable via UI + API (10/10 backend, all frontend). (b) World simulation scripts/sim_world.py: 250 players / 30 alliances / 20 days via API (prefix w21, report /app/test_reports/sim_world.json + sim_world_report.md): 218,809 requests, 0 5xx, 0 invariant violations, all players grew (stage 38.8→162.5 avg, hero →100, domain →80.8, units 50K→306K), 364 wars resolved with casualties (21% of deployed lost). Balance finding: 40/200 daily-warring players ended <100 units (attrition) vs 0/50 non-warring — presented to owner as an option (loss cap / infirmary / lower loser rate), no rule change made. Backend: RATE_LIMIT_DISABLED env flag (preview only, refused in production) added in app/core/config.py + ratelimit.py to allow load simulations."
  - agent: "main"
    message: "ITERATION 20b (nav): new 'Guerra' tab (app/(tabs)/war.tsx → WarScreen inTab: territory map + bonus + wars list, testID war-screen, no back button, tab-war). 'Social' tab renamed 'Alleanza' (tab-social kept; title 'Alleanza'; tiles hub-chat 'Chat alleanza', hub-boss 'Titano', hub-war 'Guerra 10v10' → /alliance/war?section=roster which hides the map and shows only wars + enlistment/formation, title 'Guerra 10v10'). Tab bar now 7 tabs (label font 9.5). Logout already exists in Profilo (logout-button 'Esci', logout-all-button)."
