# Simulazione mondo — 250 giocatori, 30 alleanze, 20 giorni (prefisso w21)
Script: `backend/scripts/sim_world.py` (API pubblica + hook di test; 218.809 richieste, concorrenza 30).
Seed "giorno 20": Castello 8, stage 20–40, eroe 12–20, risorse iniziali; 20 alleanze da 10 (abilitate alla guerra) + 10 da 5.
Ogni giorno: offline + login, campagna fino alla prima sconfitta (max 12), 3 edifici, 1 ricerca, reclutamento, formazione suggerita, auto-equip, forgia, talenti, casse missioni, imprese; ogni alleanza da 10 dichiara una guerra (10v10 con arruolamento) che si blocca e si risolve in giornata.

## Esito
- **0 errori server (5xx), 0 violazioni di invarianti** (formazione ≤ posseduto, risorse/unità mai negative). Unici 4xx inattesi: 13 `branch_max` (bot che spende talenti su un ramo pieno) → comportamento corretto.
- **Tutti i 250 crescono**: stage 38,8 → 162,5 medio (min 129, max 179); eroe 22 → 100; dominio 19 → 80,8 caselle medio; unità totali 50K → 306K; potenza media 8K → 134K. 364 guerre risolte con perdite applicate (3.670 corsie-giocatore; 21,0% delle truppe schierate cadute).
- Muri di boss: i giocatori si fermano ai boss 130/140/…/180 quando la potenza non basta (boss 180 = 310K) — coerente con la curva v1.4: a Castello 10–11 servono più edifici/reclutamento, non è un bug.

## Osservazione di bilanciamento (perdite in guerra)
| Gruppo | Unità mediane al giorno 20 | Giocatori con < 100 unità | Stage mediano | Potenza mediana |
|---|---|---|---|---|
| Alleanze da 10 (guerra ogni giorno) | 532 | **40 / 200** | 169 | 108K |
| Alleanze da 5 (mai in guerra) | 2.330 | 0 / 50 | 179 | 218K |

Chi combatte ogni giorno e perde spesso le corsie erode l'esercito (30–60% per corsia persa) più in fretta di quanto il reclutamento a Castello 10 possa ricostruire: 40 giocatori sono rimasti con poche unità (es. w21007: 20 unità, 438K oro ma legno esaurito). Nessun bug: è l'effetto della nuova regola con guerre quotidiane.
Opzioni possibili (da decidere): tetto perdite per guerra (es. max 25% dello schierato), "infermeria" che restituisce una quota dei caduti dopo la guerra, o riduzione del tasso sconfitto.
