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
| BOARD-09 | CC | Codex | task/ROTA-T050 | 4202856 | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `7b1259b`. `test_t009_open_and_assembler.py` — filtr tekstu zaktualizowany; przy okazji naprawiony trzeci, niezależny błąd znaleziony podczas implementacji (za zgodą OWNERA): formuła liczby ostrzeżeń liczyła wszystkich 7 pracowników, nie tylko 5 LOCAL — 2 EXTERNAL_SUPPORT są słusznie wykluczone od T041, formuła zawężona do `MembershipKind.LOCAL`. `helpers.ts::openSite` — dodane brakujące kliknięcie w nawigację „Panel sterowania" (wzorzec z `t041-daily-workflow.spec.ts`), zgodnie z R2. Wszystkie 6 testów w `test_t009_open_and_assembler.py` zielone, `ruff`/`git diff --check` czyste. `backend.py` (`7b1259b..7a3e6c9`): **PASS bez zastrzeżeń**, brak nadwyżek. Dokładny martwy test `status: WORKING` znaleziony przez Codex podczas audytu (`monthly-planning.spec.ts:48,67,78,149`, konsekwencja T048) zgłoszony osobno do backlogu (pozycja 15) — poza zakresem T050, nie naprawiany tu. |
| BOARD-10 | CC | Codex | task/ROTA-T051 | d7e3a18 | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `264ffa9`. `_provenance_text` zwraca teraz wyłącznie `"Kod weryfikacyjny grafiku: {digest[:10]}"` — bez angielskiej etykiety, bez `SV-...`; `_draw_page_header`'s linia → `"Rewizja treści: {revision[:10]}   Wygenerowano: ..."`; `Export.tsx`'s komunikat sukcesu skraca `document_revision` do 10 znaków, zachowując zachowanie dla `null`. Zweryfikowane bezpośrednio przechwyceniem rysowanych linii realnego PDF: brak `SV-`, brak 64-znakowych ciągów, pełny `document_revision` w odpowiedzi API nadal ma 64 znaki (nietknięty). 45/45 `test_t020.py` zielone, `ruff`/`git diff --check` czyste. `backend.py` (`264ffa9..64d9826`): **FAIL wyłącznie na tę samą nadwyżkę z T047** (`schedule_export.py` 619/600) — zero linii dodanych tą zmianą, dwie kosmetyczne edycje istniejących linii. **OWNER zaakceptował: "Akceptuję nadwyżkę, wysyłaj do Codexa."** Pełny werdykt: `tasks/ROTA-T051/round_01/tests/backend_output.txt`. |
