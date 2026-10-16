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
| ROTA-CLOUD-REVIEW-FIXES | CC | Architekt | `review/cloud-2026-10` (tylko finding) | `14aa586` | OWNER_DECISION_NEEDED | **Prośba o brief na jeden blok poprawek (zgoda OWNERA 2026-10-16).** Źródło: niezależny przegląd kodu z sesji chmurowej, `arch/FINDING_2026-10_CLOUD_CODE_REVIEW.md` na branchu `review/cloud-2026-10` (main@4f0ed0d). CC sprawdził w kodzie twierdzenia F1-F7: wszystkie potwierdzone (F5 dodatkowo: na Railway brak zmiennej `TZ`, Dockerfile bez `TZ`/`tzdata`). Zakres bloku (propozycja CC): **F6** walidator liczony przy otwarciu miesiąca wyrzuca `violation_details` -- L4/urlop/niedostępność wpisane po akceptacji nie są sygnalizowane (najważniejsze); **F5** serwer w UTC -- ochrona rozpoczętej służby i domyślne `effective_from` przesunięte o 1-2 h (ustawić `Europe/Warsaw`); **F3** NN wpisane po fakcie ma `effective_from=dziś`, PDF/Excel czyta starszą wersję -> zawyżone WYK (jak przy korekcie historycznej: `effective_from` = dzień zmiany); **F1** `NIGHT-STREAK-01` bez mapowania w `deviation_mapping.py` -> 500 przy ręcznej korekcie; **F2** `NIGHT-STREAK-01` w walidatorze bez ograniczenia okna `boundary_assignments` (bliźniak THIRD-CONSECUTIVE ma okno R4-01) -> stara trójka N blokuje PLAN innych miesięcy; **F7** zmiana hasła bez obecnego hasła i bez minimalnej długości; **+ Railway:** `railway.json` (Config as Code) przestaje działać 2026-12-01 -- migracja na nowy format; **+ 34 stare testy** z `ODLOZONE.md` 2026-09-24 (OWNER: naprawa w jednym bloku, gdy pojawi się powód -- to jest ten powód). **DECYZJE OWNERA (2026-10-16, dosłownie):** (a) zmiana czasu / F5 skutek uboczny: "W grafiku wstawiamy normalnie 12h, do wynagrodzenia jest liczone 13 h, ale my nie mamy programu kadrowego tylko grafik, więc ustalamy 12h." -> nocka przy zmianie czasu zostaje 12 h, NIE zmieniać arytmetyki dat; (b) F4: "Jeśli ustalam grafik od 10 października to nie ustalam zmian na dni do 10 bo to bez sensu." -> pierwsza wersja z `effective_from` w środku miesiąca NIE planuje dni przed tą datą (dziś solver obsadza cały miesiąc, ekran/saldo je liczą, PDF je pomija). Poza zakresem: wszystko inne z `ODLOZONE.md`. Przed merge: ultrareview + audyt Codexa wg poziomu. |
