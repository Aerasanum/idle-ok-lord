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
