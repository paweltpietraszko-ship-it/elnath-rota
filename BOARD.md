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
| ROTA-RARE-WEEKLY-SLOT-PINNED | CC | Architekt | — (diagnostyka w toku, przerwana z braku budżetu sesji) | `arch/FINDING_2026-09-21c_CONTROLLED_EXPERIMENT_DOES_NOT_REPRODUCE_REAL_SKEW.md` | OWNER_DECISION_NEEDED | **STATUS: praca wg zlecenia architekta (pełny realny `assemble_planning_state`, nie uproszczony `base_state`) w toku, PRZERWANA świadomie z braku budżetu sesji CC -- nie porzucona, nie zakończona wnioskiem.** Podejście: jednorazowa kopia `/data/accounts/pawel.db` na serwerze Railway (za zgodą ownera, tylko dane testowe), w kopii usunięte 3 styczniowe schedule_versions (po wcześniejszym `DROP TRIGGER` na immutability-guardach FINAL, tylko w kopii), żeby `assemble_planning_state` zobaczył prawdziwy stan SPRZED pierwszego PLAN (boundary/other-site assignments, site_rules, work_balances, holiday_history -- żadne z tego nie było w moim wcześniejszym uproszczonym repro). **DOKŁADNY BLOKER, gdzie to stanęło**: `get_employee`/`pii_crypto.decrypt_name` rzuca `ValueError: employee display_name failed integrity check` nawet po skopiowaniu `pawel.db.pii_keystore` obok kopii -- `pii_crypto.resolve_key` (rota/persistence/pii_crypto.py:351) wiąże klucz z dokładną ścieżką pliku DB (`_get_or_create_dek_for_path`), więc sama kopia keystore nie wystarcza przy innej ścieżce pliku. Analiza nie potrzebuje w ogóle odszyfrowanych imion (tylko employee_id/godziny/feasibility) -- najszybsza dalsza droga: zmonkeypatchować `pii_crypto.decrypt_name`/`get_employee` żeby pomijał deszyfrowanie display_name przed wywołaniem `assemble_planning_state`, zamiast naprawiać resolve_key. Tymczasowe pliki na serwerze (kopia DB, keystore, skrypt) posprzątane -- serwer czysty, oryginał nietknięty. Wszystkie wcześniejsze ustalenia (3/2 jest jedynym dowiedzionym optimum w uproszczonym modelu; katalog zmian/role/uprawnienia wykluczone jako wyjaśnienie) pozostają aktualne i opisane w plikach findingu -- to jest kontynuacja tej samej, nierozstrzygniętej diagnostyki, nie nowy wątek. Następna sesja CC (lub Codex, jeśli dostępny) może podjąć dokładnie w tym miejscu. **NOWA DANA OD OWNERA (2026-09-21, ręczne 10 przebiegów PLAN na Bolf, styczeń): 8/10 razy solver oddał WSZYSTKIE soboty temu samemu pracownikowi (Pawłowi), 2/10 inaczej.** To już NIE wygląda na czysty, symetryczny remis 50/50 między dwoma identycznymi tie-breakami (mój wcześniejszy n=3 próbek pokazywał flip między osobami, ale n=3 to za mało, żeby to wykluczyć) -- 80/20 sugeruje realne, systematyczne odchylenie w stronę konkretnego pracownika, nie tylko "solver grupuje soboty komuś losowo". Warte zbadania w kolejnej sesji razem z pełną rekonstrukcją: czy coś w kolejności/ID/wewnętrznej reprezentacji tego konkretnego pracownika faworyzuje go w tie-breaku, czy to inny mechanizm. **NOWA DANA OD OWNERA (2026-09-21): (1) po usunięciu niestandardowej zmiany sobotniej (9h/INNY) i zastąpieniu jej zwykłą zmianą taką jak w tygodniu, solver NADAL przyznaje wszystkie soboty jednej osobie -- to POTWIERDZA (zgodnie z moim wcześniejszym testem) że katalog_kind/INNY to fałszywy trop, wykluczone ostatecznie. (2) Kluczowe zawężenie: na REALNYCH obiektach z WIELOMA pracownikami solver poprawnie rozrzuca soboty na różne osoby -- problem wygląda na specyficzny dla MAŁEJ puli (Bolf ma tylko 2 pracowników), nie na ogólny defekt produktu. To zawęża priorytet dalszej diagnostyki: sprawdzić najpierw, czy to efekt małej liczby pracowników (np. 2-osobowa pula ma dramatycznie mniej alternatywnych "prawie tak samo dobrych" rozkładów niż pula wieloosobowa, więc słabość tie-breaka `add_weekend_fairness` ujawnia się tylko tam), zanim projektuje się ogólne rozwiązanie. |
