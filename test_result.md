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
