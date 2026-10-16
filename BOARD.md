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
| ROTA-CODEX-AUDIT-TIERS | CC | Architekt | -- (propozycja procesu, bez kodu) | `arch/PROPOSAL_2026-09-21_CODEX_AUDIT_TIERS.md` | OWNER_DECISION_NEEDED | **OWNER: Codex zuzywa limit, bo nie ma podzialu na lekki i powazny audyt.** Szkic (do decyzji architekta+ownera, CC nie zmienia AGENTS.md ani configu): (1) sekcja `AUDIT_TIER: LIGHT|STANDARD|DEEP` wpisywana przez architekta w wierszu BOARD (domyslnie STANDARD; Codex moze tylko podniesc, z konkretnym powodem); LIGHT = diff + JEDEN reproduktor, bez pionu/macierzy/WHERE_MAP, raport <=30 linii; DEEP = mechaniczne wyzwalacze sciezek (rota/planning/**, db.py/migracje, pii_crypto.py, api/auth/**, Dockerfile, zmiana kontraktu/HARD) -- pelny audyt; ROUND_CAP max 2 rundy re-checku na temat, STOP_RULE po wystarczajacym dowodzie; DEFECT_GATE/exact SHA/reproduktor per finding BEZ ZMIAN we wszystkich poziomach. (2) Odchudzenie AGENTS.md+CODEX_START_HERE.md z ok. 18 KB do <=8 KB: usunac tablice nagrobne (SIMULATORS/BENCHMARKS REMOVED -> jedno zdanie), zdeduplikowac reguly powtorzone w obu plikach. (3) Reczne po stronie OWNERA (poza repo, AGENTS.md tego nie wymusi): reasoning effort per watek wg AUDIT_TIER (LIGHT=low, STANDARD=medium, DEEP=high), wylaczenie w ~/.codex/config.toml wtyczek niezwiazanych z kodem (documents/pdf/spreadsheets/presentations/template-creator/visualize/computer-use), model_verbosity=low, tool_output_token_limit, jedna sesja=jeden audyt. Pytania otwarte w pliku (kompletnosc listy DEEP, kto przypisuje poziom bez wiersza BOARD, pomiar zuzycia dla 5 audytow przed/po). Zrodla zewnetrzne to blogi praktykow, liczby orientacyjne. |
| ROTA-UNMAPPED-DEVIATION-RULES | -- | -- | -- (zmergowane) | `c70ab47` | DONE | **ZMERGOWANE 2026-10-16 na polecenie OWNERA** (PR #28, main@c70ab47). ROLE-01 z ręcznej korekty → Deviation PREFERENCE; Codex r2 PASS na 93c1914, raport `tasks/ROTA-UNMAPPED-DEVIATION-RULES/round_01/tests/tests_r2.txt` przeniesiony. **Nadal otwarte poza zakresem:** WORK_PERIOD-01, FULL_HOUR-01, SITE_RULE-01, ASSIGN (brak kategorii). Blokada „Dodaj pracę” — osobny wiersz ROTA-MANUAL-MIDDLE-ROLE-BLOCK. |
| ROTA-MANUAL-MIDDLE-ROLE-BLOCK | Codex | CC / Architekt | `codex/rota-manual-middle-role-block` | `f01a9b27e10bd7fc91f92821e968572c97232ed7` | CODEX_REPORTED | **PASS PREIMPLEMENTATION — wąski precheck (2026-10-16).** Brief zgodny z decyzjami OWNERA i testowalny; jeden owner pokrycia roli, helper przedziałowy z obecnego role_covers, walidacja własnej roli pracy bez demandu, usunięcie tylko odmowy braku autoryzacji. Odmowy integralności i brak aktywnego członkostwa pozostają zgodnie z decyzją OWNERA. Raport `tasks/ROTA-MANUAL-MIDDLE-ROLE-BLOCK/round_01/tests/tests_r1.txt` na `audit/rota-manual-middle-role-block`, commit `3423af8`; CC przenosi raport. [Draft PR #29](https://github.com/paweltpietraszko-ship-it/elnath-rota/pull/29). Bez testów produktu/WHERE_MAP/regresji na etapie briefu. CC może wykonać własną ocenę merytoryczną; obie bramy przed implementacją. Odłożone WORK_PERIOD-01/FULL_HOUR-01/SITE_RULE-01/ASSIGN pozostają zamknięte jako znane ograniczenie. Merge tylko OWNER. |
