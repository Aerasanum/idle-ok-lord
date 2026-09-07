# IDLE 1 v1.1 — Product Requirements & Status

## Original problem statement
Realizzare e completare **IDLE 1 v1.1** come gioco mobile iOS/Android *production-candidate*, seguendo integralmente i cinque allegati (Master Bible v1.1 FROZEN, CANONICAL_SPEC v1.1, Regole & Handoff, Gameplay/Economia/LiveOps, Tecnica & QA).
Lingua utente: **italiano**.

## Stack (deviazione autorizzata: Capacitor → Expo/React Native)
- Frontend: Expo SDK 57 / React Native, expo-router (file-based), React Query, SecureStore (Keychain/Keystore), react-native-purchases, expo-notifications.
- Backend: FastAPI + Pydantic, MongoDB (Motor), Argon2id (pwdlib), JWT access (15 min) + refresh rotante (30 gg) con rilevamento riuso.
- Canon: `backend/canon/IDLE_1_v1.1_CANONICAL_SPEC.json` (hash verificato all'avvio). Ogni numero di gioco è letto dal JSON; nessuna costante inventata.

## Requisiti chiave (dal problem statement)
- Auth: email+password (Argon2id, verifica email via Emergent Resend, recupero password, logout-all, export, cancellazione), Emergent Google Auth, Sign in with Apple **preparato ma bloccato** (manca account developer).
- Gameplay server-authoritative: campagna 200 stage (normal/elite/boss), ricompense escrow + claim idempotente, gear (drop, forge, reforge, salvage, auto-equip/auto-salvage), eroe (XP/talenti/skill), regno (edifici, code, ricerca 48 nodi, reclutamento 13 unità, formazione/comando), dominio 10x10, progressione offline (12h, timestamp server), LiveOps (evento settimanale + energia + track, 4 dungeon, quest daily/weekly, login calendar, imprese, codex, season pass), alleanze (chat moderata, ruoli, donazioni), guerre asincrone 10v10 su mappa 19x19 con snapshot immutabile, Titan Hunt.
- Monetizzazione: RevenueCat (webhook idempotente, refund, restore), nessun gacha, prezzi dallo store.
- Push: Emergent-managed push (funziona solo in build nativa dopo Publish; serve `google-services.json`).
- QA: matrice di tracciabilità (`/app/docs/TRACEABILITY_MATRIX.md`), test unit/contract/integration/idempotency/concurrency.

## Stato attuale (giugno 2026)
### Completato
- Backend completo (`app/core`, `app/domain`, `app/routers`) con 25 test pytest **tutti verdi** (`python -m pytest /app/backend/tests -q`).
- Fix sessione corrente: mock email nei test; ricerca salvata come oggetto intero (le chiavi nodo contengono `.`); regole guerra (`minimum_members_to_attack` da `alliances`); contatori attacchi Titan Hunt; verifica firma HMAC opzionale webhook RevenueCat (`REVENUECAT_WEBHOOK_SIGNING_SECRET`).
- Test allineati allo spec canonico (costi edifici, item stats, SKU `idle1.event_pass.weekly`, casse `small/medium/…`, 100 Rubini iniziali).
- Frontend: auth (login/signup/recover/verify/onboarding), 5 tab (Battaglia con scena animata da timeline server, Regno con scena 2.5D + sheet edificio, Dominio, Esercito, Social), Hero gear/talenti, Ricerca, Alleanza (hub/chat/guerra/Titan), Eventi/Dungeon/Quest/Imprese/Codex, Negozio, Profilo (privacy/export/delete), Forziere offline, Inbox.
- Integrazioni: Google Auth (session exchange), Resend (codici), RevenueCat (bridge nativo + webhook/restore server), Push (registrazione device + relay server, no-op in Expo Go/web).

### Iterazione 2 (giugno 2026) — Effetti battaglia, sprite, tutorial
- VFX scena battaglia (`src/battle/BattleScene.tsx`, `effects.tsx`): scosse camera, lampi, numeri di danno fluttuanti (critici dorati), archi di spada, scintille, pioggia di monete, banner VITTORIA/STAGE CONQUISTATO/SCONFITTA (1,5 s prima del claim), barra HP boss, ambiente regionale (astro, nuvole, particelle), haptics su nativo.
- Sprite vettoriali SVG: nemici per archetipo (`src/battle/monsters.tsx`: goblin, umanoidi, cavalieri/non-morti, incappucciati, canidi, cinghiali, artropodi, bruti, golem, treant, volatili, spiriti, draghi; elite con creste, boss con corona/aura) e Lord equipaggiabile (`src/battle/lord.tsx`: elmo/pennacchio, corazza, scudo araldico, mantello, spada oscillante con bagliore per rarità).
- Tutorial guidato (`src/tutorial/Tutorial.tsx`): 9 passi con spotlight, navigazione automatica Battaglia→Regno→Battaglia, salta/avanti, completamento salvato server-side (`settings.tutorial_done`, `PATCH /account/settings`), "Rivedi il tutorial" nel Profilo.
- Testing agent iteration_2: tutto verde, zero errori console.

### Iterazione 3 (giugno 2026) — Fix avvio Expo Go + Abilità visive + Regno animato
- **Root cause crash Expo Go Android**: `src/push.tsx` importava `expo-notifications` staticamente; da SDK 53 il modulo lancia un errore all'import in Expo Go Android → il modulo `_layout.tsx` falliva la valutazione (da cui "missing default export" e "ErrorBoundary of undefined" a cascata). Fix: adapter `src/push/adapter.ts` con `import()` dinamico guardato da `ExecutionEnvironment.StoreClient`, no-op in Expo Go/web; `src/push/index.tsx` usa solo l'adapter. Inbox in-app invariata. Acceptance test `frontend/scripts/expo-go-acceptance.mjs` (AC-EXPO-GO) aggiunto alla matrice.
- Abilità visive: effetto distinto per ogni auto-skill (Colpo Potente, Grido di Guerra, Muro di Scudi, Pioggia d'Acciaio, Colpo Reale, Vessillo del Drago) + nome lampeggiante (`effects.tsx`, `BattleScene.tsx`).
- Regno animato (`src/kingdom/life.tsx`): contadini che camminano sulle strade, fumo dai camini degli edifici attivi, cantieri con impalcature/martello/polvere e barra di avanzamento su tempo server, bandiera araldica che ondeggia sul Castello.

### Iterazione 4 (giugno 2026) — Grafica "render 3D stilizzato" generata con IA
- Pipeline `backend/scripts/gen_art.py` (Gemini `gemini-3.1-flash-image-preview` via Emergent key): 96 asset WebP in `frontend/assets/art/` (10 sfondi regione, 50 nemici/boss, Lord ×3, 18 edifici incl. castello ×3 tier, 13 unità, terreno regno, key art splash), chroma-key automatico su verde, manifest `frontend/src/art/manifest.ts` generato. Resumable (`--only`, `--keys`, `--force`).
- Integrazione: `src/art/index.ts` (lookup con fallback vettoriale), BattleScene (sfondo regione, Lord/nemici/unità renderizzati, max 4 nemici visibili + contatore), KingdomScene (terreno + edifici renderizzati, ombre, badge costruisci/lock), Army tab (unità), Hero card (ritratto Lord), Login/Signup/Recover/Splash (key art `HeroBackdrop`).
- Fix UX ricerca: pulsanti Ricerca/Esercito subito sotto la scena del Regno; scheda Università con "Apri Ricerca"; schermata Ricerca mostra il motivo se "Avvia" è disabilitato (coda occupata / risorse mancanti con quantità).
- Costo: ~100 generazioni immagine sulla Universal Key.

### Iterazione 5 (giugno 2026) — Combattimento vivo, Dominio 3D, audio
- Nemici in combattimento: ogni creatura ha un ciclo caricamento → affondo verso il Lord → rinculo (desincronizzato), flash quando colpita; il Lord subisce contrattacchi (rinculo + numeri rossi, più frequenti se la battaglia è persa).
- Colpi spettacolari del Lord: cadenza 1,2 s; ogni 4° colpo è un **colpo pesante** (affondo lungo, doppio arco dorato, esplosione di scintille, scossa, flash, suono).
- Mappa Dominio 3D: 10 tessere terreno illustrate (`tiles/*`) + varianti "nebbia" derivate; mappa inclinata in prospettiva; animazione di rivelazione per le tessere conquistate dall'ultima visita (AsyncStorage `idle1.domain.seenOwned`).
- Audio (`backend/scripts/gen_audio.py`, sintesi procedurale numpy→MP3, licenza libera): 9 SFX + 10 loop musicali per regione (32 s, ~200 KB ciascuno). Modulo `src/audio` (expo-audio): musica per regione in battaglia, SFX su colpi/uccisioni/skill/vittoria/sconfitta/costruzione; volumi Musica/Effetti nel Profilo (cache locale + `settings.music_volume/sfx_volume` server).

### Iterazione 6 (giugno 2026) — Icone oggetti + verifica Alleanze/Guerre 10v10
- Icone oggetti: 45 illustrazioni (`assets/art/items/<slot>_<tier>.webp`, 9 slot × 5 tier visivi; tier per rarità: comune=basic_a, non comune=basic_b, raro=fine_a, epico=fine_b, leggendario/mitico/antico=ornate) + 11 icone risorse (`assets/art/resources`). Componente `src/ui/ItemIcon.tsx` (cornice rarità, bagliore per leggendario+, badge forgia +N) in Equipaggiamento (griglia equipaggiati, inventario, scheda dettaglio, costo forgia con icone Oro/Polvere), loot della scheda risultato battaglia (tile oggetto + rarità + slot), Forziere offline. `Res` accetta `art` (immagine al posto del glifo) — usato **solo** in inventario/forgia/loot per scelta utente; barra risorse e costi edifici restano vettoriali.
- Verifica Alleanze & Guerre: scenario demo `backend/scripts/seed_war_demo.py` (idempotente): QA Lord leader di [QAT] con 10 membri (bot `qa.bot1..9@idle1.app`), rivale [ORS] Orsi Neri con 10 membri e una guerra già vinta. Testing agent iterazione 6: dichiarazione dal UI → roster 10 → lock/risoluzione via `_test/war-shift` + `_test/tick` → 10 corsie, nodo conquistato, +100 punti, monete non duplicate al secondo tick; Titan Hunt start/attacco OK. Nuovo test live `backend/tests/test_alliance_wars.py`.
- UX guerra: legenda mappa (tuo territorio / altre alleanze / guerra in corso / castello), colori proprietà più leggibili, stati guerra in italiano, roster pre-compilato con quello salvato.

### Iterazione 7 (giugno 2026) — Batch proprietario: VFX "wow", solo musica, mura, canon v1.2, replay guerra, avvisi chat, vetrina Titano
- **Canon v1.2 (live update approvato dal proprietario)** — `backend/scripts/canon_v12.py` (idempotente, hash `481dd024…` calcolato da `compute_spec_hash`; `docs/CANONICAL_SPEC.json` speculare). Statistiche unità INVARIATE. Novità: `units.counters` (bonus +30% / malus −20% per unità contro 7 classi nemiche: Umanoidi, Bestie, Giganti, Corazzati, Volanti, Spiriti, Draghi — tabella approvata in chat), `battle.enemy_classes` (classe di ogni famiglia/boss), rampa difficoltà `enemy_power = round(75·1.047^(s−1)·(1+0.004·max(0,s−50)))` (+20% a 100, +40% a 150, +60% a 200), `conquest_wagon` rinominato **"Ariete d'Assedio"** (key invariata, unità mantenuta).
  - Applicazione: campagna → mix nemico dello stage (famiglie regione 25% ciascuna; boss 50% classe boss + 50% famiglie) moltiplica la potenza di ogni unità (`combat_profile(enemy_mix)`); `/battle/stage/{n}` espone `army_counter_net_pct` ed `enemy_mix`; `/army` espone `counters` + `region_counter`. Guerra 10v10: `lane_power()` rivaluta l'esercito di ogni corsia contro il mix di classi dell'avversario (NPC neutri; snapshot legacy → war_power congelato); le corsie espongono `attacker/defender_counter_pct`, `_npc`, `_level`.
- **Battaglia VFX**: `BattleScene.tsx` riscritto. Lord: 5 mosse (affondo, colpo pesante, rotazione, scatto con afterimage, balzo con onda d'urto) + **SUPER** (aura dorata stile Super Saiyan a 6s e poi ogni 20s: vignetta, zoom, banner "POTENZA MASSIMA", poi onda finale, flash, numeri enormi su tutti i nemici, indicatore SUPER nella HUD). Nemici: 7 mosse (affondo, balzo, carica rotante, ruggito con onda d'urto, schivata, sputo con proiettile ad arco, picchiata per i volanti) scelte per archetipo; reazioni al colpo, dissolvenza alla morte, linee di velocità, bagliori, polvere, combo counter.
- **Audio**: rimossi tutti gli SFX (asset, manifest, chiamate); resta la musica per regione. Profilo: solo cursore "Musica". `gen_audio.py` genera SFX solo con `--with-sfx`.
- **Mura del Regno**: anello perimetrale reale (`WallRing`): spessore, torri angolari con tetto e pennoni araldici e casa-porta (arte `walls.webp`) crescono col livello mura; stato non costruito tratteggiato; tap sulla porta apre l'edificio.
- **Replay guerra animato** (`src/war/WarReplay.tsx`): 10 corsie come duelli tra Lord (attaccante sx / difensore dx, guarnigione NPC in grigio), scontro con flash/linee/numeri, perdente atterrato, punteggio live, puntini corsie, Pausa / Vai al risultato / Rivedi.
- **Avvisi chat guerra**: `alliance_alert()` pubblica messaggi di sistema ("Araldo di guerra", kind `war`/`titan`) nel canale Alleanza per dichiarazione (attaccante e difensore), roster salvato, roster bloccato, annullamento, risultato, avvio/uccisione Titano; la chat li mostra come card evidenziate.
- **Vetrina Titan Hunt**: `TitanStage` (illustrazione 3D del boss regionale del tier su sfondo regione, respiro, flash e ruggito al colpo, Lord che entra e colpisce), classifica danni live (`leaderboard` dal backend, refetch 8s) con quota % e colpi, anteprima Titano per tier nel pannello di avvio.
- Test: backend 27/27 (+ `test_canon_v12_and_alerts.py` live del testing agent, 8/8); testing agent iterazione 7 tutto verde (frontend e backend). Hook `_test/war-shift` accetta `include_resolved` per azzerare il cooldown 24h in QA.

### Da fare / backlog
- Sign in with Apple: solo UI disabilitata (deployment input).
- Input del proprietario al deploy: chiavi RevenueCat (`EXPO_PUBLIC_RC_IOS_KEY`, `EXPO_PUBLIC_RC_ANDROID_KEY`, `REVENUECAT_SECRET_KEY`, signing secret), `google-services.json`, URL Privacy/Termini, `EMERGENT_PUSH_KEY` (impostato al Publish).
- v1.2+: tuning bilanciamento da telemetria (fuori canon v1.1).

## File di riferimento
- `/app/docs/TRACEABILITY_MATRIX.md` — requisiti → codice → test.
- `/app/design_guidelines.json`, `/app/frontend/src/theme.ts` — design tokens.
- `/app/memory/test_credentials.md` — account QA.
- `/app/backend/tests/*` — suite pytest (25 test).
