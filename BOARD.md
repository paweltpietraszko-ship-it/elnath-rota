# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalzem pracy; ten plik tylko rejestruje
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
| ROTA-RARE-WEEKLY-SLOT-PINNED | CC | Architekt | — (eksperyment, bez implementacji) | `arch/FINDING_2026-09-21c_CONTROLLED_EXPERIMENT_DOES_NOT_REPRODUCE_REAL_SKEW.md` | OWNER_DECISION_NEEDED | **Eksperyment wykonany dokładnie wg zlecenia architekta -- wynik NEGATYWNY, nie deklaruję root cause.** Odtworzenie realnych `shift_demands`/`calendar_days` stycznia Bolf (26 realnych wierszy, read-only) + OCHRONA + 2 identycznych pracowników: solver daje PROWEN OPTIMAL podział 3/2 (27h/18h), objective==best_bound==2613, ZERO gap (nie tylko poniżej 1%) -- identycznie z wymuszonym HARD capem spreadu<=9h i identycznie przy zaostrzonej kontroli (0% gap, 120s). Wszystkie 3 warianty T017 diversity też dają 3/2. To znaczy: w tym modelu 5/0 jest ŚCIŚLE gorsze niż 3/2 (nie remis), więc realny wynik 5/0 z findingu rundy 2 NIE MOŻE być tym samym modelem trafiającym w przypadkowy tie-break -- coś w prawdziwym solve różni się od tej rekonstrukcji, czego jeszcze nie zidentyfikowałem. Potwierdzone identyczne (wykluczone jako wyjaśnienie): katalog zmian, demands, kalendarz/święta, regime, memberships obu pracowników, zero absencji, zero targetów. NIEPOTWIERDZONE (brakujące dane, zgodnie z instrukcją architekta -- nie zgaduję): czy realne 3 style stycznia to zawsze `search_attempt=0`, czy któryś to "Szukaj dalej" (randomizacja); czy zaakceptowany kandydat to candidates[0] czy diversity variant. Dwie dalsze, nieotwarte jeszcze ścieżki opisane w pliku findingu (odczyt coordinator_action_records dla search_attempt; ręczne uruchomienie z search_attempt=1/2 na tej samej rekonstrukcji). CC nie projektuje poprawki i nie deklaruje przyczyny bez tego dowodu. |
