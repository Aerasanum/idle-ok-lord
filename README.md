# IDLE 1

Idle game con campagna PvE, regno, esercito e guerre di alleanza 10v10.
Backend FastAPI + MongoDB, app React Native (Expo, SDK 57), tutti i numeri di bilanciamento
vengono dal canone in `backend/canon/IDLE_1_v1.1_CANONICAL_SPEC.json`.

```
backend/    API FastAPI, dominio di gioco, canone, script di QA e suite di test
frontend/   app Expo (expo-router, React Query)
docs/       documenti di prodotto: canone, regole, economia, matrice di tracciabilita
```

## Requisiti

- Python 3.12
- Node 20 + Yarn 1
- MongoDB 8 in ascolto su `mongodb://127.0.0.1:27017`

## Avvio del backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Nel `.env` locale servono almeno questi valori:

```ini
MONGO_URL="mongodb://127.0.0.1:27017"
DB_NAME="idle1_v11"
IDLE1_ENV="preview"          # in produzione i test hook vengono rifiutati
JWT_SECRET="<openssl rand -hex 32>"
CORS_ORIGINS="http://localhost:8081"
TEST_HOOKS_ENABLED="true"    # abilita /api/_test/*, usato da seed e test
RATE_LIMIT_DISABLED="true"   # solo QA: vedi "Test" qui sotto
```

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8001
curl http://127.0.0.1:8001/api/health
```

## Avvio dell'app

```bash
cd frontend
yarn install
echo 'EXPO_PUBLIC_BACKEND_URL=http://127.0.0.1:8001' > .env
yarn web --port 8081       # oppure: yarn start, yarn ios, yarn android
```

Apri l'app su `http://localhost:8081`: l'origine deve comparire in `CORS_ORIGINS`,
altrimenti il browser blocca le chiamate (`http://127.0.0.1:8081` e un'origine diversa
da `http://localhost:8081`).

Gli acquisti reali girano su RevenueCat e richiedono una build nativa: in Expo Go e sul
web il modulo non c'e e lo store dichiara `unavailable` invece di finire in errore.

## Mondo di QA

Le suite live parlano con un backend in esecuzione e si aspettano gli account definiti in
`backend/qa_fixtures.py`. Lo script di seed li crea, mette due alleanze confinanti sulla
mappa, decora l'account vetrina e porta un secondo account a fine gioco:

```bash
cd backend
python scripts/seed_qa.py --base http://127.0.0.1:8001/api
```

Lo script e idempotente e ripara un mondo lasciato a meta (alleanza spostata dalla mappa,
confine perso, cooldown di attacco attivo), quindi puoi rilanciarlo quando vuoi.

## Test

```bash
cd backend && python -m pytest tests -q      # 185 test: contratto in-process + suite live
cd frontend && yarn test                     # typecheck + lint
cd frontend && yarn doctor                   # coerenza delle dipendenze Expo
```

Le suite live fanno login con circa venticinque account di fixture e superano il limite di
20 login al minuto per IP: servono `TEST_HOOKS_ENABLED="true"` e `RATE_LIMIT_DISABLED="true"`
sul backend sotto test. Entrambe le variabili sono rifiutate in produzione.

Il backend sotto test si sceglie con `EXPO_PUBLIC_BACKEND_URL` (o `EXPO_BACKEND_URL`); in
mancanza di variabili viene letto `frontend/.env` e infine si usa `http://127.0.0.1:8001`.
Se gli account di fixture non esistono, le suite live si fermano con un messaggio che
rimanda al seed invece di fallire una per una.
