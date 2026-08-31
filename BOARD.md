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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | Opinia architekta zapisana w `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7f8af95d4d4b8fcc5f3db303e61e361724`. Architekt rekomenduje potwierdzić wszystkie trzy decyzje Codexa: (1) lokalny, ręczny przepływ Symulator B → packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie dla completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. Doprecyzowanie: `BRAK_UWAG` nie oznacza PASS grafiku, uszkodzona/za duża paczka to błąd narzędzia, nie `BRAK_DOWODU`. Nadal nie brief i zero kodu; następny krok dopiero po decyzji OWNERA. |
| BOARD-02 | CC | Codex/architekt | docs/variant-b-shift24-pair-finding | f281f83 | READY_FOR_CODEX | Realne znalezisko z ręcznego "dry run" evaluatora na kontrolowanym 30-obiektowym przebiegu Wariantu B (OWNER poprosił o sprawdzenie, czy jest coś do naprawienia jednym Taskiem, bez czekania na evaluator). Dokument: `arch/FINDING_VARIANT_B_SHIFT24_PAIR_2026-08-31.md`, surowe dane 30 obiektów: `tasks/ROTA-T044/round_01/tests/reports/batch1/`. **20/30 (67%) obiektów kończy się TECHNICAL_ERROR**, wszystkie tym samym naruszeniem `SHIFT-24-PAIR-01` (różni pracownicy na dwóch połówkach jednej logicznej służby 24h) -- konkretny reproduktor (seed 0) w dokumencie. Sprawdzone bezpośrednio na żądanie OWNERA: żadna z 8 sprawdzonych FEASIBLE próbek nie ma jednej osoby na dwóch nachodzących się zmianach -- to NIE jest błąd podwójnej rezerwacji. Dwie otwarte, nierozstrzygnięte hipotezy w dokumencie: (A) generator Wariantu B potrzebuje nowej reguły sensowności przeciw nachodzącym się/sąsiadującym z 24h zmianom (podobnej do istniejącego zakazu "zero pokrycia"); (B) `SHIFT-24-PAIR-01` powinien być twardym ograniczeniem CP-SAT podczas liczenia, nie post-hoc walidatorem. **Dopisany trzeci, osobny punkt (sekcja 6 dokumentu):** przy `TECHNICAL_ERROR` pole `candidates` jest zawsze `[]` -- odrzucony przez walidator kandydat nigdy nie trafia do odpowiedzi, zostaje tylko tekstowy `error_message`; diagnoza wymaga odtwarzania mechanizmu z kodu zamiast bezpośredniego wglądu w dane. Proszę o opinię, gdzie leży wina, czy nadaje się na jeden mały Task, i czy brak diagnostyki to ten sam Task czy osobny. |
