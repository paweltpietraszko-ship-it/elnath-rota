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
| ROTA-CLOUD-REVIEW-FIXES | Codex | Claude Code / Architekt | `codex/rota-cloud-review-fixes` | `ba6287192e18ed445b390ca87fcba48e2bdf4f4c` | CODEX_REPORTED | **PASS PREIMPLEMENTATION (2026-10-16).** Niezależny precheck briefu: źródła i O1–O5, jednoznaczność, testowalność, nazwani ownerzy i redukcja zakresu F1–F7/R/T; bez audytu produktu, testów i regresji. Raport: `tasks/ROTA-CLOUD-REVIEW-FIXES/round_01/tests/tests_r1.txt` na branchu Tasku, commit `a75da01`. Brief: `tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md`, draft PR #21. CC może wykonać własną ocenę merytoryczną; dopiero obie bramy zwalniają IMPLEMENTATION HOLD (§7). Przed merge nadal ultrareview i niezależny audyt implementacji exact SHA. Zastosowanie Railway wymaga osobnej decyzji OWNERA na konkretny plan. |
| ROTA-CLOUD-REVIEW-FIXES-MERIT | CC | Architekt | `codex/rota-cloud-review-fixes` | `ba6287192e18ed445b390ca87fcba48e2bdf4f4c` | OWNER_DECISION_NEEDED | **Ocena merytoryczna CC briefu: AKCEPTUJĘ z dwiema drobnymi poprawkami; IMPLEMENTATION HOLD trwa do ich naniesienia.** Brief jest trafny, minimalny i zgodny z findingiem (F1-F7 sprawdzone przez CC w kodzie). **P1 (zakres, blokuje bramkę):** `tests/test_audit_r15_findings.py` (`test_r15_2_uncapped_load_fallback_does_not_mask_day_only`, `'DECISION_REQUIRED' == 'TECHNICAL_ERROR'`) jest na liście 34 porażek (`ODLOZONE.md` 2026-09-24, klasa DAY_ONLY/fixture ORDINARY), ale brak go w `TASK_SCOPE` -- dopisać, inaczej zostaje czerwony albo jego zmiana = DIFF_SCOPE FAIL. Pozostałe 21 plików z tej listy są w zakresie. **P2 (reuse, nie blokuje):** F6 -- `api/routers/schedule.py:53` ma już `_DEVIATION_LABELS` (polskie etykiety reguł). Nowy `api/schedule_validation_messages.py` ma używać tej jednej mapy (F1 dopisuje tam NIGHT-STREAK-01), nie drugiej listy etykiet; walidator ma ok. 20 kodów reguł, więc formatter jest mały. Doprecyzować w §3 F6 jednym zdaniem. **Uwagi bez zmiany briefu:** (a) R zachowuje region `us-east4` (USA) -- poprawnie dla tego bloku; ewentualne przeniesienie do UE to osobna decyzja z `ODLOZONE.md` 2026-10-16 (RODO), nie łączyć z migracją IaC. (b) Implementacja na branchu `task/ROTA-CLOUD-REVIEW-FIXES` od SHA zamrożonego briefu (CLAUDE.md: jeden branch `task/<id>`); brief musi być na `main` przed startem (BRIEF_FROZEN) -- PR #21 do zmergowania po poprawkach. (c) Decyzje O3-O5 CC zna tylko z briefu -- CC prosi OWNERA o potwierdzenie w rozmowie. |
