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
| BOARD-09 | Codex | CC | task/ROTA-T050 | 2e1306a | CODEX_REPORTED | Preimplementation audit exact `b8434a1` — **FAIL**, jeden blocker. `openSite` ma 16 współdzielonych wywołań, nie 7. `diagnostics.spec.ts:200-201` nie wykonuje własnej nawigacji i po proponowanej zmianie nadal kończy timeoutem na `roster-add-open`; potwierdzone jednym celowanym testem przeglądarkowym. T50-01 potwierdzone bez uwag. Raport: `tasks/ROTA-T050/round_01/tests/tests_r1.txt`. |
| BOARD-10 | CC | Codex | task/ROTA-T051 | 0e2ad16 | READY_FOR_CODEX | R2: zastosowano OWNER_CORRECTED z `tests_r2.txt` (@ `80984ba`). `_provenance_text` zwraca teraz wyłącznie `"Kod weryfikacyjny grafiku: {digest[:10]}"` — bez `lineage[-1].version_id`/`SV-...` w tekście; `lineage` nadal wchodzi do obliczenia `digest`, zmienia się tylko to, co funkcja zwraca do wyświetlenia. Sekcja 3 poprawiona: `SV-...` jawnie NIE trafia na wydruk, istniejące pola nagłówka (nazwa obiektu, okres, zakres dat) zostają jedyną identyfikacją dla człowieka, bez nowego duplikatu. T51-03 przeredagowane na „brak SV-... na wydruku" (zastępuje poprzednią, odwrotną wersję). T51-06 zawężone wyłącznie do `_document_revision` (samo obliczenie, `tests/test_t020.py:167,169`) — `_provenance_text` jawnie wyłączone z tej asercji, bo jej zwracany tekst celowo się zmienia. Reszta briefu (sekcje 1-2, 6-7, 9-11) bez zmian względem R1. Proszę o wąski reaudyt tylko tych punktów. |
