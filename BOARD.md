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
| ROTA-T056 | Architect | Codex | `main` (brief only; implementation HOLD) | corrected brief `9d8305dd10202d5e2a4052361523f1bb1344eaef` | READY_FOR_CODEX | **PREIMPLEMENTATION RE-AUDIT po R2.** Przeniesiono OWNER ruling PDF: legenda pokazuje tylko kody faktycznie użyte; jeśli nie mieszczą się czytelnie na stronie grafiku, druga strona legendy ze wszystkimi użytymi oznaczeniami. Poprawiono F1/F3/F5/F6: prawidłowy `frontend/src/screens/Room.tsx`, dodany `ControlPanel.tsx`, literalne testy/REAL-PDF artifacts w TASK_SCOPE, unified action history przez istniejący `CONTEXT_CONFIGURATION_SAVED`, WHERE_MAP REQUIRED. T56-03 ma jeden owning boundary dla kolizji D6+/N6+; wycofany false-positive z drugim standard-code write path i duplicate exporter validation. **F2 — świadoma korekta architekta:** zastane czerwone SIZE_FILE/SIZE_FUNC w `db.py`/`schedule_export.py` istniały przed T056 i nie tworzą obowiązku refaktoryzacji tego tasku. T056 nie osłabia backend.py, nie zwiększa liczby naruszeń i raportuje baseline-vs-HEAD; nie tworzyć nowych modułów wyłącznie po to, by wyzerować metrykę (`test nie tworzy architektury`). Stale schema-version tests są jawnie sklasyfikowane i dozwolona jest tylko literalna aktualizacja wersji przy nowej migracji. Prośba: wąski re-audyt exact SHA kontraktu; bez kodu produktu do PASS. |
