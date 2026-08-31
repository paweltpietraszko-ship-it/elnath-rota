# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
przekazanie, żeby nie trzeba było ręcznie przeklejać wiadomości między CC a
Codexem.

Statusy (dokładnie cztery, nic więcej):

- `READY_FOR_CODEX` — CC skończył, czeka na audyt.
- `CODEX_IN_PROGRESS` — Codex audytuje.
- `CODEX_REPORTED` — raport gotowy pod wskazaną ścieżką.
- `OWNER_DECISION_NEEDED` — audyt utknął na decyzji właściciela.

Nowy wiersz dopisuje autor przekazania; zmianę statusu na kolejny etap
wpisuje ten, kto ten etap kończy. Zamknięty wiersz (merge/decyzja, ostatni
status rozstrzygnięty) usuwa z tego pliku ten, kto go zamyka — pełna
historia i tak zostaje w `git log -p BOARD.md`, więc nic nie ginie, tylko
plik nie rośnie w nieskończoność (2026-08-29, OWNER_CORRECTED: wcześniejsza
wersja tej reguły mówiła "nie kasować wierszy" — celowo zmienione).

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| BOARD-01 | CC | Codex | task/ROTA-T044 | ef41918 | READY_FOR_CODEX | Naprawione wszystkie 4 znaleziska z `tests_r10.txt` (FAIL na `302f10b`). R10-01: generator losuje teraz godzinę startu i czas trwania niezależnie per (rodzaj, dzień), w tym 24h (H24 przez start==end niezależnie od godziny startu) oraz 0/1/2 niezależne wpisy per (rodzaj, dzień) -- zweryfikowane na 500 seedach (>2 okna, H24>0, legalne nakładanie >=2 wystąpi). `catalog_rows_from_atoms_b` już nie zlewa dwóch identycznych atomów tego samego dnia w jeden wiersz. R10-02: `_end_after_n_workdays` liczy realne dni robocze (pon-pt, bez `POLISH_2026_HOLIDAYS`) dzień po dniu zamiast sztywnych 14/7 dni kalendarzowych -- zweryfikowane dla stycznia/kwietnia/listopada/grudnia 2026 (dokładnie 10 i 5 dni roboczych, święta wydłużają blok zamiast go skracać). R10-03: `all_candidate_assignments_b` spłaszcza WSZYSTKICH kandydatów przed sprawdzeniem CLOSED WORLD; maszyna stanów zapisuje i sprawdza też każdy wynik REPLAN. R10-04: `run_full_scenario_b`/`reproduction_command_b` (wzorem `_reproduction_command` z Wariantu A) + pełny snapshot (absencje, kolejność akcji, historia REPLAN, gotowa komenda) zapisywany na KAŻDYM etapie (setup/plan/select/replan/invariant), nie tylko część. Przy okazji złapany i naprawiony kolejny błąd własny: maszyna stanów mogła utknąć bez żadnej dostępnej reguły przy nie-FEASIBLE wyniku PLAN (Hypothesis rzucał InvalidDefinition) -- dodana zawsze dostępna reguła `observe` (no-op). Zweryfikowane: ruff czyste, 57/57 testów niestanowych (w tym nowe testy regresyjne na R10-01/02/03), maszyna stanów PASS (~173s, zmierzone), regresja Wariantu A 24/24 bez zmian. `where.py` z `--symbol` na nowych ownerach: zero konsumentów produktu. Proszę o kolejny niezależny audyt implementacji. |
