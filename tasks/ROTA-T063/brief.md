# ROTA-T063 — Referencyjne testy biznesowego grafiku

STATUS: FINAL PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD UNTIL CODEX PASS

BASELINE: `main@af7d5c6f15dbc424a24b9647e725085afa662284`

SOURCE:
- `arch/PREBRIEF_AUDIT_2026-09-10_T063_ACTIVE_E2E_MATRIX.md`
- Codex R3: `tasks/ROTA-T063/round_01/tests/tests_r3.txt`
- OWNER rulings 2026-09-10
- normatywny `tasks/ROTA-T063/scenario_pack.md` v0.2, content SHA `675e4b5de1ab684bf93bf61854b6617c9f126a27`

## 1. Cel

T063 buduje małą warstwę wiarygodnych testów acceptance kończących się rzeczywistym wynikiem biznesowym programu.

Zielony test nie wystarcza dlatego, że UI kliknęło PLAN, API odpowiedziało albo solver zwrócił jakiś status. Test ma dowodzić z góry zamrożonego zachowania na z góry zamrożonych danych.

T063 jest wyłącznie zadaniem testowym. Nie zmienia solvera, produkcyjnej logiki planowania, reguł biznesowych ani UI.

## 2. Zasada nadrzędna

Test nie tworzy rzeczywistości, której nie zna.

Dane kadrowe scenariusza są częścią kontraktu. Fixture, helper, test ani implementer nie mogą samodzielnie zwiększać LOCAL, dodawać external, poluzowywać urlopów/chorobowego/DAY_ONLY/dostępności, zmieniać zapotrzebowania ani dobierać wygodniejszej obsady pod PASS.

T063 NIE buduje Symulatora C. Automat nie ocenia ogólnej „rozsądności” decyzji koordynatora. Może wyłącznie odtworzyć literalną decyzję wpisaną w `SCENARIO_PACK` i sprawdzić obserwowalny rezultat.

## 3. Chorobowe — zamrożony lifecycle OWNERA

Chorobowego nie planuje się z góry.

Jeżeli scenariusz T063 używa `SICK_LEAVE`, musi:
1. najpierw utworzyć rzeczywisty zapisany grafik przez PLAN,
2. dopiero potem wprowadzić chorobowe,
3. następnie użyć `Przelicz Plan` zgodnie z istniejącym lifecycle.

T063 nie może zastępować tej ścieżki przyszłą „niedostępnością” ani wpisywać choroby przed pierwszym PLANEM.

## 4. target_hours — dwa osobne tryby testowe

T063 ma pokryć oba istniejące tryby, ale nie mieszać ich w jednym scenariuszu:

- S01: A–E mają jawnie ustawione `target_hours = 168` jako syntetyczne dane testowe;
- S02 i S03: A–E mają jawnie `target_hours = NULL`;
- external w S02 pozostaje bez targetu zgodnie z istniejącym produktem.

Wartość `168` jest wyłącznie wejściem testowym i nie ustanawia ogólnej reguły biznesowej.

## 5. Normatywny SCENARIO_PACK

OWNER zatwierdził `SCENARIO_PACK v0.2` o content SHA `675e4b5de1ab684bf93bf61854b6617c9f126a27`.

Implementer odwzorowuje go 1:1. Jeśli produkt nie daje zamrożonego wyniku, test ma FAIL i powstaje finding. CC nie zmienia scenariusza pod wynik.

Minimalna macierz:

### S01 — dodatni D/N z target_hours

- dokładnie 5 LOCAL: A, B, D, E = D/N; C = DAY_ONLY;
- `target_hours = 168` dla A–E;
- bez absencji i external;
- PLAN;
- oczekiwane dokładnie `FEASIBLE`;
- pełny niepusty D/N;
- reload;
- screenshot i PDF.

### S02 — chorobowe po grafiku, kontrolowany external

Stan bazowy:
- 5 LOCAL, `target_hours = NULL`;
- C ma zatwierdzony urlop 12–18.10;
- D/E zdrowi;
- PLAN ma dać `FEASIBLE` i zapisany current.

Następnie:
- D i E otrzymują `SICK_LEAVE` 12–18.10;
- `Przelicz Plan` bez external ma dać dokładnie `DECISION_REQUIRED`;
- crash, TECHNICAL_ERROR, timeout ani pusty sukces nie spełniają expectation;
- jeśli guidance wskazuje możliwość korekty urlopu C, test odnotowuje ją przed external;
- literalna decyzja koordynatora: `NIE COFAJ URLOPU C`.

S02-V1:
- dodaj dokładnie 1 external X1 na 12–18.10;
- `Przelicz Plan`;
- oczekiwane dokładnie `FEASIBLE`.

S02-V2:
- osobny czysty start S02;
- po tej samej decyzji dodaj dokładnie X1–X3 na 12–18.10;
- `Przelicz Plan`;
- oczekiwane dokładnie `FEASIBLE`.

Brak pętli „dodawaj ludzi aż zadziała”. Solver może używać tylko osób wpisanych przed daną próbą.

### S03 — krótka choroba bez external

- bazowy PLAN na 5 LOCAL, `target_hours = NULL`, bez absencji ma dać `FEASIBLE` i zapisany current;
- dopiero potem D otrzymuje `SICK_LEAVE` 12–14.10;
- `Przelicz Plan`;
- oczekiwane dokładnie `FEASIBLE`;
- brak external;
- zachowanie fixed/odbytych służb zgodnie z istniejącym lifecycle;
- reload, screenshot i PDF.

## 6. Co test może wiarygodnie mierzyć

Automatycznie wolno sprawdzać wyłącznie rzeczy obserwowalne i zamrożone: wejściowe dane, status PLAN/Przelicz Plan, powstanie lub brak current/kandydata, komplet D/N, roster użyty w assignmentach, respektowanie zakresu external, oczekiwany krok guidance, brak przedwczesnej niedozwolonej akcji, reload i eksport PDF.

Automat nie ocenia ogólnej jakości grafiku ani czy tekst jest „dobry dla człowieka”. Te elementy pozostają do oceny przez screenshot/PDF.

## 7. Zakaz fałszywych pozytywów

PASS jest niedopuszczalny, gdy:
- PLAN ma zerowe zapotrzebowanie,
- akceptowane są przeciwne wyniki typu `FEASIBLE lub DECISION_REQUIRED`,
- utworzono pusty ScheduleVersion,
- solver nie został uruchomiony,
- staffing został rozszerzony poza `SCENARIO_PACK`,
- external dodano poza S02,
- sterownik testu improwizował decyzję koordynatora,
- crash/TECHNICAL_ERROR został potraktowany jak biznesowe zatrzymanie,
- UI tylko powtórzyło status API bez oczekiwanego biznesowego rezultatu,
- retry przykrył deterministyczny błąd produktu.

## 8. Izolacja wykonania

Każdy referencyjny przebieg ma używać świeżej dedykowanej bazy i własnego backendu.

T063 musi być uruchamiany z `CI=1`, aby `playwright.config.ts` nie używał `reuseExistingServer=true`. `global-setup.ts` ma zapewnić świeżą dedykowaną bazę przed uruchomieniem scenariuszy.

Jeżeli ten warunek okaże się niewystarczający bez zmiany `playwright.config.ts`, implementacja zatrzymuje się i wraca do architekta; CC nie rozszerza scope samodzielnie.

## 9. T043

`frontend/e2e/t043-coordinator-confidence.spec.ts` ma zostać wyłącznie uczciwie przeklasyfikowany jako test połączenia UI/API. Nie może dublować nowego acceptance D/N i nie jest dowodem biznesowego grafiku.

## 10. Zależność T064

Scenariusze używają października 2026 i wykonawczo zależą od T064. T063 nie może maskować braku T064 przez podrobienie zegara.

Finalny preimplementation PASS T063 nie znosi tej zależności wykonawczej.

## 11. Artefakty dowodowe

Każdy referencyjny przebieg zachowuje:
- nazwę scenariusza i wersję `SCENARIO_PACK`,
- wejściowy roster i target_hours,
- sekwencję operacji i statusów,
- decyzję koordynatora, jeśli występuje,
- roster faktycznie użyty w assignmentach,
- external dostępny i użyty,
- screenshot guidance, jeśli scenariusz jest decyzyjny,
- screenshot końcowego grafiku,
- PDF końcowego grafiku.

## 12. Literalny TASK_SCOPE

T063 może zmienić wyłącznie:

1. `tasks/ROTA-T063/brief.md`
2. `tasks/ROTA-T063/scenario_pack.md`
3. `frontend/e2e/t063-business-outcomes.spec.ts`
4. `frontend/e2e/t043-coordinator-confidence.spec.ts`
5. `frontend/e2e/global-setup.ts`

Poza scope pozostają bez nowej zgody architekta:
- `rota/**`
- `api/**`
- `frontend/src/**`
- `frontend/e2e/helpers.ts`
- `frontend/e2e/seed-e2e-db.py`
- `frontend/playwright.config.ts`
- `tests/property/**`
- `benchmarks/**`
- nowe ogólne runnery, generatory obsady, symulatory koordynatora i fallbacki external.

## 13. Acceptance

T63-01 — obowiązuje dokładnie OWNER-approved `SCENARIO_PACK v0.2` SHA `675e4b5de1ab684bf93bf61854b6617c9f126a27`.

T63-02 — S01 używa ustawionych target_hours; S02/S03 używają jawnie NULL. Trybów nie mieszać w jednym scenariuszu.

T63-03 — każde SICK_LEAVE pojawia się dopiero po istniejącym grafiku i dalsza operacja to `Przelicz Plan`.

T63-04 — S01 kończy się dokładnie `FEASIBLE`, pełnym D/N, reloadem, screenshotem i PDF.

T63-05 — S02 bez external po chorobowym kończy się dokładnie `DECISION_REQUIRED`, nie TECHNICAL_ERROR.

T63-06 — S02-V1 = dokładnie 1 external i `FEASIBLE`; S02-V2 = dokładnie 3 external i `FEASIBLE`.

T63-07 — S03 = trzydniowy SICK_LEAVE D po zapisanym grafiku, external NONE, `FEASIBLE` po `Przelicz Plan`.

T63-08 — żaden helper nie rozszerza staffing poza scenariusz.

T63-09 — tylko S02 może dodawać synthetic external.

T63-10 — T043 pozostaje testem mechaniki UI/API, nie drugim acceptance D/N.

T63-11 — uruchomienie T063 wymaga `CI=1` i świeżej dedykowanej bazy.

T63-12 — T063 nie zmienia produkcji ani solvera pod test.

T63-13 — odkryta niezgodność daje FAIL/finding, nie korektę danych scenariusza.

## 14. Finalny re-check Codexa

IMPLEMENTATION HOLD pozostaje do literalnego PASS Codexa na dokładnym SHA briefu i `SCENARIO_PACK v0.2`.

Codex ma sprawdzić tylko:
1. zgodność zmian z R3 i OWNER rulingami o chorobowym/target_hours;
2. jednoznaczność S02 `DECISION_REQUIRED`;
3. `CI=1` + świeżą bazę jako wystarczającą izolację bez rozszerzania scope;
4. literalny TASK_SCOPE;
5. brak nowego Symulatora C lub ukrytego fallbacku external.

Bez ponownego szerokiego audytu.