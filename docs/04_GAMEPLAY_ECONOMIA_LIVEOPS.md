# 04_IDLE_1_GAMEPLAY_ECONOMIA_LIVEOPS.md

IDLE 1 v1.1 — raggruppamento completo, con revisione operativa richiesta dal proprietario: avvio diretto dello sviluppo.
Le intestazioni BEGIN/END delimitano ciascun documento incluso. I riferimenti ai vecchi nomi indicano le sezioni qui conservate, non ulteriori allegati da caricare.
Gameplay, formule, tabelle e requisiti grafici sono conservati. Le istruzioni di avvio sono aggiornate: verifica dei file e implementazione nello stesso incarico, con QA visiva integrata nello sviluppo.

## Documenti inclusi

- IDLE_1_v1.1_GEAR_LOOT_FORGE_SPEC.md
- IDLE_1_v1.1_ECONOMY_XP_BALANCE_AUDIT.md
- IDLE_1_v1.1_CAMPAIGN_MONSTER_REGIONS.md
- IDLE_1_v1.1_LIVEOPS_REWARDS_SPEC.md


<!-- BEGIN DOCUMENT: IDLE_1_v1.1_GEAR_LOOT_FORGE_SPEC.md -->
# IDLE 1 v1.1 - GEAR / LOOT / FORGE SPEC

VERSION 1.1 - SPEC_HASH `a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995`

## Equipment slots
Weapon, Offhand, Helmet, Chest, Gloves, Boots, Cloak, Ring, Amulet.

## Rarity progression
Common unlocks immediately; Uncommon at stage 10; Rare 25; Epic 50; Legendary 90; Mythic 140; Ancient 180. Exact stage-band drop weights are in CANONICAL_SPEC.

## Item level
`item_level = min(100, max(1, ceil(source_stage / 2)))`.

## Drop cadence
Normal stage clear: 12% gear roll. Elite: 30%. Boss: 1 guaranteed item plus 25% extra roll. Repeat farming uses 50% of normal drop chance. Boss 50/100/150/200 guarantees a minimum Epic/Legendary/Mythic/Ancient item respectively.

## Forge
Forge level is permanent per slot, not per item. Replacing a sword keeps the Weapon Forge level. Levels 0-20 never fail. Exact Gold/Dust costs are canonical.

| Item level | Gold for slot +0 -> +20 | Forge Dust for +0 -> +20 |
|---:|---:|---:|
| 10 | 120,982 | 678 |
| 50 | 489,690 | 1,438 |
| 100 | 950,574 | 2,390 |

## Salvage and reforge
Unwanted equipment is converted into Forge Dust. Higher rarities can also yield Reforge Stones and Mythic Essence. Reforge rerolls one selected secondary affix; it cannot reduce rarity or primary stats.

## UX requirements
Free Auto Equip and stage-20 Auto Salvage filters are mandatory. Inventory must show before/after power clearly. No paid random gear chest, gacha or enhancement failure.

<!-- END DOCUMENT: IDLE_1_v1.1_GEAR_LOOT_FORGE_SPEC.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_ECONOMY_XP_BALANCE_AUDIT.md -->
# IDLE 1 v1.1 - ECONOMY / XP / REWARD BALANCE AUDIT

VERSION 1.1 - SPEC_HASH `a5ba20db1ccc157207f7e4e90197a5a82b1b8fda10dce01ffffb2b3ee8cf5995`

## Key result
- XP needed Hero 1 -> 100: **4,097,345**.
- XP from clearing stages 1-200 once: **2,734,254** = **66.73%** of level-100 requirement.
- Approx Hero level after all first clears with no repeat/event XP: **85**.
- First-clear Gold across stages 1-200: **1,046,199**.
- First-clear soft-resource bundle total: **574,560**.

This prevents the campaign from instantly maxing the Hero while keeping every clear meaningful. Repeat/offline farming, quests, events and dungeons remain relevant after stage 200.

## Milestone reward check
| Stage | Enemy power | First XP | First Gold | First soft bundle | Offline XP/h | Offline Gold/h | Offline soft/h |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 75 | 25 | 18 | 12 | 26 | 45 | 20 |
| 10 | 113 | 560 | 299 | 182 | 588 | 753 | 306 |
| 20 | 179 | 1,427 | 696 | 412 | 1,498 | 1,754 | 692 |
| 50 | 712 | 4,915 | 2,128 | 1,213 | 5,161 | 5,363 | 2,038 |
| 100 | 7,076 | 12,530 | 4,958 | 2,749 | 13,156 | 12,494 | 4,618 |
| 150 | 70,326 | 21,660 | 8,130 | 4,436 | 22,743 | 20,488 | 7,452 |
| 200 | 698,958 | 31,940 | 11,549 | 6,229 | 33,537 | 29,103 | 10,465 |


## Economic controls verified
1. Hero levels consume XP only. Gold remains meaningful for Kingdom, Research, Recruitment, Forge and Reforge rather than double-taxing level-ups.
2. 75% of stage XP/Gold/soft resources is attributed across kills and 25% to clearing the stage, so the player visibly earns while the army advances.
3. Gear is deliberately less frequent than currency: normal 12%, elite 30%, boss guaranteed. This avoids inventory floods.
4. Forge is a long-term Gold/Dust sink but never destroys progress because enhancement belongs to the slot.
5. Soft-resource battle income is supplemental to buildings. Kingdom progress still values offline production, Domain ownership, quests and events.
6. Free Rubies from dailies/weekly/login are meaningful but do not trivialize passes or late-game timers.
7. Event/Dungeon paid refills are capped; Alliance War freezes snapshots before resolution.
8. Any live tuning outside these values must ship as a new canonical version, not a silent server constant.

## F2P pacing target
Castle 5 first day; Castle 10 days 2-5; Castle 14 week 1-2; Castle 17 week 2-3; Castle 20 week 4-6. Campaign 200 target roughly weeks 3-6 depending on optimization. These are telemetry targets, not hidden dynamic difficulty rules.

<!-- END DOCUMENT: IDLE_1_v1.1_ECONOMY_XP_BALANCE_AUDIT.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_CAMPAIGN_MONSTER_REGIONS.md -->
# IDLE 1 v1.1 - CAMPAIGN / MONSTER REGIONS

## 1. Green Marches - stages 1-20
Enemies: Goblin Raider, Road Bandit, Wild Boar, Marsh Wolf.  
Boss: **Ogre Warlord**.  
Visual: green valleys, wooden forts, rain and mud.

## 2. Blackwood - stages 21-40
Enemies: Dark Wolf, Forest Troll, Cultist, Giant Spider.  
Boss: **Ancient Treant**.  
Visual: dense forest, ruined shrines, fog.

## 3. Iron Hills - stages 41-60
Enemies: Orc Reaver, Armored Ogre, Harpy, Stone Golem.  
Boss: **Mountain Tyrant**.  
Visual: rocky valleys, mines, cliffs.

## 4. Ashen Plains - stages 61-80
Enemies: Ash Raider, Undead Legionary, Warg, Fire Imp.  
Boss: **Bone Colossus**.  
Visual: burnt plains, siege ruins, red skies.

## 5. Frost Crown - stages 81-100
Enemies: Frost Wolf, Ice Troll, North Raider, Frost Wraith.  
Boss: **Ice Giant King**.  
Visual: snowfields, frozen keeps, blizzards.

## 6. Sunscar Desert - stages 101-120
Enemies: Giant Scorpion, Desert Marauder, Sand Golem, Djinn Acolyte.  
Boss: **Sand Wyrm**.  
Visual: dunes, buried cities, ancient obelisks.

## 7. Drowned Coast - stages 121-140
Enemies: Drowned Soldier, Sea Troll, Siren, Leviathan Spawn.  
Boss: **Leviathan**.  
Visual: storm coast, shipwrecks, flooded ruins.

## 8. Dragonspine - stages 141-160
Enemies: Drake, Wyvern, Dragon Cultist, Magma Golem.  
Boss: **Elder Dragon**.  
Visual: volcanic peaks, dragon ruins, lava.

## 9. Celestial Rift - stages 161-180
Enemies: Fallen Knight, Winged Horror, Celestial Construct, Infernal Herald.  
Boss: **Fallen Seraph**.  
Visual: shattered temples, storm clouds, celestial fire.

## 10. End of Realms - stages 181-200
Enemies: Demon Legionary, Ancient Titan, World Beast, Abyss Wyrm.  
Boss: **World Devourer**.  
Visual: apocalyptic fortress landscape, massive armies and mythic effects.

<!-- END DOCUMENT: IDLE_1_v1.1_CAMPAIGN_MONSTER_REGIONS.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_LIVEOPS_REWARDS_SPEC.md -->
# IDLE 1 v1.1 - LIVEOPS / REWARDS SPEC

Canonical runtime values remain in `IDLE_1_v1.1_CANONICAL_SPEC.json`. This file is an implementation guide, not a second source of numbers.

## Weekly idle event
One main event is always active for 7 days. Energy cap is 10 and regenerates 1 point every 30 minutes. Deployments last 5/15/30/60 minutes and cost 1/2/3/4 Energy. Paid refill: 5 Energy for 50 Rubies, maximum 6 paid refills per day.

Each deployment grants Event Tokens, Gold, soft-resource production-equivalent rewards and a gear roll chance according to the canonical formulas. The 20-tier event track requires 100 points per tier. Free and premium reward tracks are both defined in the canonical spec. No paid random gear chest is permitted.

## Dungeons
Four 10-minute idle dungeons: Royal Treasury, Forge Depths, Ancient Ruins, Monster Hunt. Two free entries per dungeon per day. Extra entries cost 25 Rubies, maximum 3 paid extra entries per dungeon per day.

Ancient Ruins uses an exact rarity boost: tiers 1-5 roll gear rarity twice and keep the higher; tiers 6-10 roll three times and keep the highest.

## Daily / weekly / login
Daily quest templates total 100 points and award 10 Rubies through point chests. Weekly templates total 100 points and award 50 Rubies plus Forge materials. The 7-day login cycle awards 35 Rubies total plus a boosted gear roll on day 7.

Expected free Rubies from daily + weekly + login over 28 days: 620, excluding event-track rewards, achievements and Codex milestones.

## Alliance Boss - Titan Hunt
48-hour asynchronous event. 3 free attacks per member per day. Up to 3 extra attacks per day cost 50 Rubies each. Damage is based on the player's canonical campaign power. Rewards include War Coins and Forge materials. Titan Hunt never changes Alliance territory and never modifies a locked Alliance War.

## Season Pass
28 days, 30 levels, 100 points per level. Free track and premium track reward totals are defined in the canonical spec. The premium track includes Rubies, Forge materials and cosmetics. It never contains random paid gear.

<!-- END DOCUMENT: IDLE_1_v1.1_LIVEOPS_REWARDS_SPEC.md -->


---

# Grafica e progressione esercito — contenuto completo accorpato

# 05_IDLE_1_GRAFICA_ESERCITO.md

IDLE 1 v1.1 — raggruppamento completo, con revisione operativa richiesta dal proprietario: avvio diretto dello sviluppo.
Le intestazioni BEGIN/END delimitano ciascun documento incluso. I riferimenti ai vecchi nomi indicano le sezioni qui conservate, non ulteriori allegati da caricare.
Gameplay, formule, tabelle e requisiti grafici sono conservati. Le istruzioni di avvio sono aggiornate: verifica dei file e implementazione nello stesso incarico, con QA visiva integrata nello sviluppo.

## Documenti inclusi

- IDLE_1_v1.1_ART_DIRECTION.md
- IDLE_1_v1.1_ARMY_VISUAL_PROGRESSION.md


<!-- BEGIN DOCUMENT: IDLE_1_v1.1_ART_DIRECTION.md -->
# IDLE 1 v1.1 - ART DIRECTION

## North star
Premium medieval-fantasy mobile game. The player must visibly evolve from a poor lone warrior with simple gear into a royal commander leading an enormous army through increasingly spectacular monster regions.

## Battle
- 2.5D side / three-quarter battlefield with strong depth.
- Stage 1 reads as one warrior against small monsters.
- By late campaign, foreground contains representative formations and the background is filled with banners, troop cohorts, siege, cavalry, beasts, elephants and mythic silhouettes.
- Tier 8 must feel like thousands of soldiers without rendering thousands of unique expensive models.
- Bosses are giant focal enemies, often supported by monster hordes.
- Weapon, helmet, chest, boots and cloak visibly change on the Lord when equipped.

## Kingdom
Seven unmistakable visual tiers from camp to Imperial Capital. Buildings, walls, roads, population, banners and landmark density increase materially at each tier.

## Domain
Painted strategic map with ownership colors, roads, forts, villages, cities and terrain. Territory expansion must be immediately visible.

## Materials and palette
Aged parchment, stone, dark wood, forged iron, bronze, antique gold, leather, velvet, heraldic cloth. Deep navy, burgundy, forest green, iron gray, parchment ivory, antique gold.

## UI
Regal but readable. Carved/forged/embossed frames, restrained filigree, heraldic iconography. No generic SaaS cards.

## Forbidden
Cyberpunk, sci-fi, neon tech, startup-dashboard aesthetics, chibi/cartoon proportions, slot-machine loot presentation, generic fantasy placeholders.

<!-- END DOCUMENT: IDLE_1_v1.1_ART_DIRECTION.md -->

<!-- BEGIN DOCUMENT: IDLE_1_v1.1_ARMY_VISUAL_PROGRESSION.md -->
# IDLE 1 v1.1 - ARMY VISUAL PROGRESSION

## Product promise
The battle screen is a visual progression system. The player starts alone and ends as the commander of a truly enormous mixed army fighting monster hordes and giant bosses.

## Canonical progression
| Tier | Trigger | Foreground cap | Visual read |
|---:|---|---:|---|
| 0 | stage < 10 | 1 | Lord fights alone |
| 1 | stage >= 10 and army deployed | 10 | small infantry escort |
| 2 | stage >= 20 | 20 | infantry and archers with banners |
| 3 | stage >= 40 | 32 | cavalry joins; visible formation depth |
| 4 | stage >= 60 | 48 | siege engines and dense troop lines |
| 5 | stage >= 90 | 68 | beasts appear among regular troops |
| 6 | stage >= 120 | 90 | war elephants, multiple banners, wide army frontage |
| 7 | stage >= 140 | 110 | mythic units join and the army fills the battlefield |
| 8 | stage >= 180 | 120 | imperial host: thousands perceived through LOD cohorts, banners, siege, beasts and multiple mythic silhouettes |


Real recruited quantities remain authoritative. The client uses cohort virtualization, pooling, LOD and background silhouettes. Late game should feel like thousands of troops while keeping a high-end cap of 120 foreground proxies and a low-end cap of 60.

Unit unlock sequence: Infantry -> Archer -> Cavalry -> Catapult -> Conquest Wagon -> Wolf/Bear/Falcon/Lion -> War Elephant -> Dragon -> Angel -> Demon. Each unit still requires its canonical Castle/Research gates as well as the Campaign stage gate.

<!-- END DOCUMENT: IDLE_1_v1.1_ARMY_VISUAL_PROGRESSION.md -->
