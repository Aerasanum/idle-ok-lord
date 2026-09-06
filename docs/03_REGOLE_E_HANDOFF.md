# 03_IDLE_1_REGOLE_E_HANDOFF.md

IDLE 1 v1.1 — raggruppamento completo, con revisione operativa richiesta dal proprietario: avvio diretto dello sviluppo.
Le intestazioni BEGIN/END delimitano ciascun documento incluso. I riferimenti ai vecchi nomi indicano le sezioni qui conservate, non ulteriori allegati da caricare.
Gameplay, formule, tabelle e requisiti grafici sono conservati. Le istruzioni di avvio sono aggiornate: verifica dei file e implementazione nello stesso incarico, con QA visiva integrata nello sviluppo.

## Documenti inclusi

- IDLE_1_v1.1_README_FIRST.txt
- 00_UPLOAD_ORDER.txt
- IDLE_1_v1.1_GUARDRAILS.md
- IDLE_1_v1.1_EMERGENT_MASTER_HANDOFF_PROMPT.md

## Nota editoriale sul confezionamento (non modifica il canone)

Il pacchetto originale contiene 17 file. I cinque allegati ne conservano tutti i contenuti di prodotto; le istruzioni di avvio sono aggiornate secondo la richiesta del proprietario. I due vecchi ordini di caricamento restano integralmente riportati; per questa consegna si caricano soltanto i cinque allegati e si incolla il nuovo prompt separato. Il README cita IDLE_1_v1.1_TRACEABILITY_MAP.json e fallback CANONICAL_SPEC_READABLE.txt / CANONICAL_FLAT: questi file non sono presenti nello ZIP ricevuto e non vengono presentati come recuperati. La tracciabilità di implementazione dovrà essere prodotta da Emergent, distinguendola da un documento canonico originale. Il JSON completo è presente. I PASS negli audit originali non certificano un gioco implementato o testato.


<!-- BEGIN DOCUMENT: IDLE_1_v1.1_README_FIRST.txt -->
IDLE 1 v1.1 - EMERGENT UPLOAD ORDER

1. IDLE_1_Master_Bible_v1.1_FROZEN.pdf
2. IDLE_1_v1.1_CANONICAL_SPEC.json
3. IDLE_1_v1.1_GUARDRAILS.md
4. IDLE_1_v1.1_GEAR_LOOT_FORGE_SPEC.md
5. IDLE_1_v1.1_ECONOMY_XP_BALANCE_AUDIT.md
6. IDLE_1_v1.1_ARMY_VISUAL_PROGRESSION.md
7. IDLE_1_v1.1_CAMPAIGN_MONSTER_REGIONS.md
8. IDLE_1_v1.1_ART_DIRECTION.md
9. IDLE_1_v1.1_ACCOUNT_PRIVACY_PAYMENTS.md
10. IDLE_1_v1.1_IMPLEMENTATION_BLOCKS.md
11. IDLE_1_v1.1_DATA_MODEL_API_CONTRACT.md
12. IDLE_1_v1.1_ZERO_GAP_AUDIT.md
13. IDLE_1_v1.1_LIVEOPS_REWARDS_SPEC.md
14. IDLE_1_v1.1_TRACEABILITY_MAP.json
15. IDLE_1_v1.1_FINAL_BUILD_CHECKLIST.md
16. IDLE_1_v1.1_EMERGENT_MASTER_HANDOFF_PROMPT.md

If JSON parsing is unreliable, additionally upload CANONICAL_SPEC_READABLE.txt or all four CANONICAL_FLAT parts.

CANONICAL VERSION = 1.1
SPEC_HASH = a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995

Read the specification, validate it and start implementation in the same task. Integrate visual QA into development.

<!-- END DOCUMENT: IDLE_1_v1.1_README_FIRST.txt -->

<!-- BEGIN DOCUMENT: 00_UPLOAD_ORDER.txt -->
IDLE 1 v1.1 — EMERGENT UPLOAD ORDER

Upload these files first:
1. IDLE_1_Master_Bible_v1.1_FROZEN.pdf
2. IDLE_1_v1.1_CANONICAL_SPEC.json
3. IDLE_1_v1.1_GUARDRAILS.md
4. IDLE_1_v1.1_ART_DIRECTION.md
5. IDLE_1_v1.1_ARMY_VISUAL_PROGRESSION.md
6. IDLE_1_v1.1_GEAR_LOOT_FORGE_SPEC.md
7. IDLE_1_v1.1_CAMPAIGN_MONSTER_REGIONS.md
8. IDLE_1_v1.1_ECONOMY_XP_BALANCE_AUDIT.md
9. IDLE_1_v1.1_LIVEOPS_REWARDS_SPEC.md
10. IDLE_1_v1.1_ACCOUNT_PRIVACY_PAYMENTS.md
11. IDLE_1_v1.1_DATA_MODEL_API_CONTRACT.md
12. IDLE_1_v1.1_IMPLEMENTATION_BLOCKS.md
13. IDLE_1_v1.1_ZERO_GAP_AUDIT.md
14. IDLE_1_v1.1_FINAL_BUILD_CHECKLIST.md

Then paste the full contents of:
IDLE_1_v1.1_EMERGENT_MASTER_HANDOFF_PROMPT.md

Do not upload duplicate Bible DOCX or fallback FLAT files unless Emergent cannot read the JSON.

<!-- END DOCUMENT: 00_UPLOAD_ORDER.txt -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_GUARDRAILS.md -->
# IDLE 1 v1.1 - GUARDRAILS

VERSION: 1.1  
SPEC_HASH: `a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995`

## Authority
1. Master Bible v1.1 FROZEN defines player experience and system meaning.
2. CANONICAL_SPEC v1.1 is the only machine-readable authority for runtime numbers, formulas, costs, timers, drops, unlocks, prices and caps.
3. This file defines implementation boundaries.
4. Art Direction controls visuals only.

## Hard rules
- Build the complete defined v1.1; do not reduce it to an MVP or generic dashboard.
- Do not import runtime rules from Empire Lords Dragon unless explicitly present in IDLE 1 v1.1.
- Every monster kill contributes visible XP/Gold/resource progress; authoritative rewards are server-ledgered.
- Gear rarity/drop/forge/reforge must use the canonical tables. No random paid gear chests or gacha.
- Forge upgrades are deterministic, never fail and are tied to equipment slots so replacement gear keeps forge investment.
- The campaign battle must visually grow from one Lord to a huge army with regular units, cavalry, siege, beasts, elephants and mythic units. Do not represent the late game as six static icons.
- Real troop quantities are authoritative data. Rendered soldiers are representative LOD cohorts; never create one expensive model per owned soldier.
- Device clock is never trusted for offline rewards, events, dungeons or timers.
- Alliance War is asynchronous 10v10. A complete combat snapshot is frozen at roster lock; later purchases/upgrades cannot change that war.
- Purchase crediting, reward claims, offline claims and war resolution are idempotent and server-authoritative.
- Production prices are localized Apple/Google store prices, never hardcoded reference EUR.
- Account deletion/export, privacy, terms, moderation/report/block and restore purchases are release requirements.
- No production MemoryStore fallback, default secrets or swallowed critical exceptions.

## Forbidden scope creep
- real-time open-world multiplayer movement
- manual action combat
- player-to-player direct messages
- guild voice chat
- full 3D free-camera city builder
- paid random gear chests / loot boxes / gacha
- live 10v10 requiring simultaneous online presence
- rendering every owned soldier as a unique full-cost model
- item enhancement failure/destruction
- player trading of gear or currencies

<!-- END DOCUMENT: IDLE_1_v1.1_GUARDRAILS.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_EMERGENT_MASTER_HANDOFF_PROMPT.md -->
# IDLE 1 v1.1 - EMERGENT MASTER HANDOFF PROMPT

Build **IDLE 1 v1.1** as a production-candidate iOS + Android game. Do not create an MVP, mockup-only product or generic fantasy dashboard.

## Read in this order
1. IDLE_1_Master_Bible_v1.1_FROZEN.pdf
2. IDLE_1_v1.1_CANONICAL_SPEC.json
3. IDLE_1_v1.1_GUARDRAILS.md
4. IDLE_1_v1.1_GEAR_LOOT_FORGE_SPEC.md
5. IDLE_1_v1.1_ECONOMY_XP_BALANCE_AUDIT.md
6. IDLE_1_v1.1_ARMY_VISUAL_PROGRESSION.md
7. IDLE_1_v1.1_CAMPAIGN_MONSTER_REGIONS.md
8. IDLE_1_v1.1_ART_DIRECTION.md
9. IDLE_1_v1.1_ACCOUNT_PRIVACY_PAYMENTS.md
10. IDLE_1_v1.1_IMPLEMENTATION_BLOCKS.md
11. IDLE_1_v1.1_DATA_MODEL_API_CONTRACT.md
12. IDLE_1_v1.1_LIVEOPS_REWARDS_SPEC.md
13. IDLE_1_v1.1_ZERO_GAP_AUDIT.md
14. IDLE_1_v1.1_FINAL_BUILD_CHECKLIST.md

Required version: **1.1**  
Required spec_hash: **a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995**

## Initial validation and immediate implementation
Parse CANONICAL_SPEC and verify the following expected values. Report the result briefly and immediately proceed with implementation in the same task; do not end the first response with validation alone:
CANONICAL_SPEC_PARSED = YES
VERSION = 1.1
SPEC_HASH = a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995
GEAR_SLOTS = 9
CAMPAIGN_STAGES = 200
CAMPAIGN_REGIONS = 10
RESEARCH_NODES = 48
UNITS = 13
CASTLE_LEVELS = 20
ARMY_VISUAL_MAX_TIER = 8
ALLIANCE_WAR = ASYNC_10V10

If the spec cannot be read, stop. Do not infer values from chat.

## Core experience that must survive implementation
The game begins with one warrior automatically fighting monsters. Every kill contributes XP/Gold/resources. The player finds progressively better gear from Common through Ancient, equips visible armor/weapon/boots/cloak, permanently upgrades gear slots through Forge, grows the Kingdom, unlocks research and recruits an increasingly large army. The Battle scene must visibly escalate until the Lord commands an enormous army containing soldiers, cavalry, siege, beasts, elephants, Dragon/Angel/Demon-scale mythic units against monster hordes and giant bosses.

## Direct implementation
Start I01-I16 after canonical validation in the same task. Apply Art Direction and Army Visual Progression directly to the working game. Perform visual QA throughout implementation and fix visual defects as part of completion.

## Stack
React + TypeScript + Capacitor, Python + FastAPI + Pydantic, MongoDB production persistence. Same account/state/backend on iOS and Android. Web/PWA is development preview only.

## Build order
Use I01-I16. A feature is complete only when UI -> API -> validation -> domain logic -> persistence -> authoritative reward/event -> response -> UI update -> automated test works.

## Do not invent
No runtime number outside CANONICAL_SPEC. No paid random gear/gacha. No manual action combat. No synchronous live 10v10. No direct messages. No sci-fi/cyberpunk/SaaS visuals. No one-model-per-owned-soldier implementation.

## Release target
Production-candidate, not prototype. Finish the defined scope, run the Final Build Checklist, and produce implementation/security/economy/mobile/payment test reports with zero open P0/P1 before claiming COMPLETE.

<!-- END DOCUMENT: IDLE_1_v1.1_EMERGENT_MASTER_HANDOFF_PROMPT.md -->
