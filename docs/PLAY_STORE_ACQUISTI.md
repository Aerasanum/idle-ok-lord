# Acquisti in-app su Google Play: catalogo e collegamento a RevenueCat

App: **Empire Lords Dragon: Idle** · package `com.idlempirelordsdragon.game`

Il gioco usa **RevenueCat** (`react-native-purchases`) sopra Google Play Billing. Il catalogo canonico è in
`backend/canon/IDLE_1_v1.1_CANONICAL_SPEC.json` (`monetization.ruby_packs`, `monetization.starter_bundle`,
`monetization.season_pass`, `events.event_pass`): gli **ID prodotto devono essere identici** a quelli sotto, altrimenti
il backend risponde `unknown_product` e non accredita nulla.

## 1. Catalogo da creare in Play Console

Play Console → **Monetizza con Play → Prodotti → Prodotti in-app** (o "Prodotti una tantum") → **Crea prodotto**.
Tutti e 8 sono prodotti **una tantum** (nessun abbonamento): i pass hanno durata gestita dal server.

| # | ID prodotto | Nome (max 55 car.) | Descrizione | Prezzo base | Tipo in RevenueCat |
|---|---|---|---|---|---|
| 1 | `idle1.rubies.120` | 120 Rubini | Una manciata di Rubini per accelerare la crescita del tuo regno. | 1,99 € | Consumabile |
| 2 | `idle1.rubies.700` | 700 Rubini | Un sacchetto di Rubini per costruzioni, ricerche e dungeon extra. | 9,99 € | Consumabile |
| 3 | `idle1.rubies.1500` | 1500 Rubini | Uno scrigno di Rubini per i signori più ambiziosi. | 19,99 € | Consumabile |
| 4 | `idle1.rubies.4000` | 4000 Rubini | Un forziere di Rubini degno di un impero. | 49,99 € | Consumabile |
| 5 | `idle1.rubies.8500` | 8500 Rubini | Il tesoro del drago: la scorta di Rubini più grande. | 99,99 € | Consumabile |
| 6 | `idle1.starter.bundle` | Starter Bundle | 500 Rubini, 250 Polvere di Forgia, 6 ore di risorse e il Mantello del Fondatore. Acquistabile una sola volta. | 4,99 € | **Non consumabile** |
| 7 | `idle1.event_pass.weekly` | Event Pass (7 giorni) | Sblocca il percorso premium dell'evento della settimana. | 3,99 € | Consumabile |
| 8 | `idle1.season_pass.28d` | Season Pass (28 giorni) | Sblocca il percorso premium della stagione: Rubini, materiali e cosmetici esclusivi. | 9,99 € | Consumabile |

Per ogni prodotto: inserisci ID, nome e descrizione → aggiungi l'**opzione di acquisto** (tipo "Acquista") → imposta
il prezzo in EUR (Google converte automaticamente le altre valute) → **Salva** → **Attiva**.

> L'ID prodotto non si può cambiare né riutilizzare dopo la creazione: copialo esattamente.

I Pass sono "consumabili" lato Google per poterli ricomprare alla scadenza; il server registra la durata e il negozio
disabilita il pulsante finché il pass è attivo.

## 2. RevenueCat

1. **Crea progetto** su app.revenuecat.com → *Apps* → **+ New** → **Google Play Store**, package
   `com.idlempirelordsdragon.game`.
2. **Credenziali Google (service account)**, seguendo la guida RevenueCat "Google Play service credentials":
   - Google Cloud Console: abilita *Google Play Android Developer API* e *Google Play Developer Reporting API*,
     crea un service account e scarica la chiave JSON.
   - Play Console → **Utenti e autorizzazioni** → invita l'email del service account con i permessi
     *Visualizza dati finanziari* e *Gestisci ordini e abbonamenti*.
   - Carica il JSON in RevenueCat. La validazione può richiedere fino a 36 ore.
3. **Prodotti**: *Product catalog → Products → Import* (o aggiungili a mano con gli stessi 8 ID).
   Apri `idle1.starter.bundle` e imposta il tipo **Non-consumable**; gli altri restano *Consumable*.
   Non servono Entitlements né Offerings: il gioco legge i prodotti per ID e le autorizzazioni le gestisce il backend.
4. **Chiavi API** (*Project settings → API keys*):
   - chiave pubblica Android (`goog_…`) → variabile di build **`EXPO_PUBLIC_RC_ANDROID_KEY`** (frontend);
   - **Secret API key versione V1** (`sk_…`) → variabile del backend **`REVENUECAT_SECRET_KEY`**
     (il backend chiama `GET /v1/subscribers/{id}`).
5. **Webhook** (*Integrations → Webhooks → + New*):
   - URL: `https://<dominio-backend>/api/purchases/revenuecat/webhook`
   - Authorization header value: `Bearer <token-a-tua-scelta>` (scrivi anche la parola `Bearer`)
   - backend: **`REVENUECAT_WEBHOOK_TOKEN=<token-a-tua-scelta>`** (solo il token, senza `Bearer`)
   - facoltativo: signing secret → **`REVENUECAT_WEBHOOK_SIGNING_SECRET`**

Dopo aver impostato `EXPO_PUBLIC_RC_ANDROID_KEY` serve una **nuova build** (le variabili `EXPO_PUBLIC_*` vengono
incluse al momento della build), caricata in un canale di test.

## 3. Test senza addebiti

1. Play Console (livello account) → **Impostazioni → Test della licenza** → aggiungi i Gmail dei tester.
2. Gli stessi account devono essere tester del canale (test interno o chiuso) e installare il gioco **dal Play Store**.
3. Nel negozio del gioco i prezzi devono comparire in euro (non "Prezzo dallo store"); l'acquisto usa
   la carta di prova "Test card, always approves".
4. Verifica: il saldo Rubini sale **una sola volta**, la cronologia in Profilo mostra lo stato `credited`
   e su RevenueCat → *Customers* compare l'acquisto (sandbox).

Se i prezzi non compaiono: prodotto non *Attivo* in Play Console, ID diverso, credenziali RevenueCat non ancora
validate, oppure app installata non dal Play Store.
