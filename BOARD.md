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
| ROTA-T056 | Architect | Codex | `main` (brief only; implementation branch not created) | `e4260555645c5c00a3829bacf28bcc1233422f47` | READY_FOR_CODEX | **PREIMPLEMENTATION AUDIT.** Brief: `tasks/ROTA-T056/brief.md`. Cel: dodatkowe miesięczne kody realnej pracy D6+/N6+ do domknięcia bilansu przez istniejącą ręczną korektę; D1–D5/N1–N5 zamrożone, U/C bez zmian. Architektura minimalna: mały current-state record `(site_id,month)->extra_work_code_intervals` w istniejącym `site_repository.py`; nie zmieniać całego `SitePrintSettings` na per-month. Kod nie staje się nowym `Assignment.operational_code`: wybór D6/N6 w `MonthlyPlanning` ustawia realny interval Assignmentu i idzie przez istniejące `apply_manual_correction`; export odtwarza kod z rodziny demandu + realnego intervalu + miesięcznej konfiguracji, tak jak dziś D1–D5/N1–N5. Solver, shift catalog, WorkBalance i analytics są jawnie poza diffem. Export musi uwzględnić extra code w `_map_work_code`, `_hours_of`, legendzie i `document_revision`. Ważny invariant: interval w tej samej rodzinie musi być jednoznaczny względem standardowych i dodatkowych kodów, inaczej round-trip kodu bez nowego ID na Assignment jest niemożliwy. Acceptance zawiera realny PDF gate z D6/N6 i kodem >6: PLAN/WYK, sumy, legenda, brak ucięcia/kolizji, skala szarości. Codex ma sprawdzić przede wszystkim minimalność nowego miesięcznego persistence seam, brak potrzeby backendowego `apply code` endpointu/`operational_code`, kompletność literalnego TASK_SCOPE i czy obecny layout eksportu da się rozszerzyć lokalnie bez subsystemu. Test nie tworzy kontraktu. |
