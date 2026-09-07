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

### Da fare / backlog
- Testing agent end-to-end su frontend (in corso in questa sessione).
- Sign in with Apple: solo UI disabilitata (deployment input).
- Input del proprietario al deploy: chiavi RevenueCat (`EXPO_PUBLIC_RC_IOS_KEY`, `EXPO_PUBLIC_RC_ANDROID_KEY`, `REVENUECAT_SECRET_KEY`, signing secret), `google-services.json`, URL Privacy/Termini, `EMERGENT_PUSH_KEY` (impostato al Publish).
- v1.2+: tuning bilanciamento da telemetria (fuori canon v1.1).

## File di riferimento
- `/app/docs/TRACEABILITY_MATRIX.md` — requisiti → codice → test.
- `/app/design_guidelines.json`, `/app/frontend/src/theme.ts` — design tokens.
- `/app/memory/test_credentials.md` — account QA.
- `/app/backend/tests/*` — suite pytest (25 test).
