# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T056 | Architect | Codex | `main` (brief only; implementation HOLD) | corrected brief `e5dc5e1b5be7e90e75acd97448eba57b08313089` | READY_FOR_CODEX | **FINAL PREIMPLEMENTATION RE-AUDIT.** Zastosowane oba OWNER rulings z `tasks/ROTA-T056/round_01/tests/tests_r4.txt`, bez nowego designu. (1) Długości D1–D5/N1–N5 pozostają zamrożone, ale ich istniejące per-site start/end/end_next_day pozostają edytowalne. Jeden invariant signature jest egzekwowany na obu legalnych write boundaries: monthly-extra save odrzuca kolizję ze standardem/extra; istniejący standard print-settings save odrzuca kolizję z dowolnym zapisanym miesiącem extra codes tego Site. Bez duplicate exporter validation. Acceptance T56-03 obejmuje obie kolejności. (2) Brief zapisuje dokładnie sześć OWNER-accepted baseline size violations z wartościami: `db.py` 635, `schedule_export.py` 684, `_apply_24h_periods` 53, `test_t012.py` 1735, `test_t019b.py` 907, `test_t020.py` 773; wymagany baseline-vs-HEAD, brak zmiany backend.py i brak siódmego naruszenia. Pozostałe kontrakty bez rozszerzeń: monthly current-state seam, istniejący manual-correction, brak operational_code, unified action history, workingMonth flow, used-only legenda + druga strona, real PDF gates. Prośba: ostatni wąski re-audyt exact SHA; implementacja nadal HOLD do PASS. |