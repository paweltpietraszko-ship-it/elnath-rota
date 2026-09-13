# ROTA-T065-PRINT-GAP — PDF dla ORDINARY bez drugiego eksportu

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD

BASELINE: `main@3085f6f`

SOURCE:
- `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r1.txt`
- `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r2.txt`
- T065 implementation PASS `42740118e838d704cb9679716efb7cdfb51b6083`
- istniejący eksport T020/T056/T052 oraz późniejsze zabezpieczenie LAW acknowledgement
- OWNER rulings: ORDINARY pokazuje rzeczywiste godziny, nie rodzinę D/N; role zawodowe są per demand/membership; PDF sklepu jest osobnym Taskiem prezentacyjnym

## 1. Cel

T065-PRINT-GAP domyka wydruk dla `SitePlanningRegime.ORDINARY` po T065.

Nie powstaje drugi system eksportu. Istniejący `generate_schedule_pdf()` pozostaje jedynym entry pointem PDF i zachowuje wspólny lifecycle:

- wybór CURRENT `ScheduleVersion`;
- lineage/provenance;
- świeża walidacja LAW;
- acknowledgement fingerprint;
- race check CURRENT przed i po renderze;
- document revision;
- istniejący endpoint, zapis/pobranie i obsługa błędów.

Rozgałęzienie `OCHRONA` / `ORDINARY` jest wyłącznie prezentacyjne i następuje dopiero przy budowie/renderowaniu modelu wydruku.

## 2. Nienaruszalna granica

T065-PRINT-GAP NIE zmienia:

- solvera;
- PLAN/REPLAN;
- validatora prawa pracy;
- `ScheduleVersion` lifecycle;
- naliczania WorkBalance;
- kanonicznej logiki absencji;
- manual correction/deviations;
- LAW acknowledgement;
- logiki historycznej T065;
- istniejącej semantyki i zaakceptowanego wydruku `OCHRONA`.

Eksporter jest konsumentem już zapisanej prawdy. Nie wolno mu wyliczać legalności, rekonstruować ról z bieżącej obsady ani tworzyć własnego bilansu czasu.

## 3. Jedno źródło danych historycznych

Dla `ORDINARY` wydruk bierze pracę z tej samej efektywnej historycznej wersji grafiku, z której dziś korzysta T020.

Dla każdego PRIMARY Assignment:

- konkretne godziny pochodzą z `Assignment.start_datetime/end_datetime` przy zachowaniu istniejącej kontroli spójności z `covers_demand_id`;
- rola zawodowa pochodzi z wersjonowanego `ShiftDemand.required_role` powiązanego przez `Assignment.covers_demand_id`;
- brak `required_role` jest legalnym historycznym faktem i nie może być uzupełniany z dzisiejszego `SiteMembership.allowed_roles`.

Zmiana dzisiejszej obsady, ról albo katalogu zmian nie może zmienić ponownie wygenerowanego starego PDF.

Nie tworzyć nowego snapshotu membershipu, tabeli historii wydruku ani tabeli store schedule.

## 4. Reżim OCHRONA — regresja zero

Dla `OCHRONA` pozostają dotychczasowe:

- D1..D5/N1..N5 i miesięczne D6+/N6+;
- 12h/24h `base_regime`;
- U*/C*/S1;
- 24h collapse/linkage;
- PLAN/WYK;
- legenda;
- zaakceptowany A3 landscape layout;
- T020/T056/T052 behavior i istniejące błędy fail-closed.

T065-PRINT-GAP nie jest zgodą na estetyczny refactor Ochrony.

## 5. ORDINARY — prezentacja pracy

`ORDINARY` nie mapuje Assignment do D/N ani do kodu pracy.

Komórka pracy jest budowana z rzeczywistych przedziałów czasu tego pracownika w danym dniu.

Przykładowe fakty wejściowe:

- 05:00–12:00, rola `KIEROWNIK`;
- 10:00–18:00, rola `SPRZEDAWCA_ZALOGA`;
- 22:00–06:00 następnego dnia;
- dwa niezależne, niepokrywające się Assignments tego samego dnia;
- Assignment bez roli zawodowej.

Eksporter ORDINARY musi obsłużyć wszystkie te przypadki bez `WORK_CODE_MAPPING_REQUIRED` i bez sztucznego tworzenia D/N.

Dokładny tekst komórki, skrót roli, separator wielu przedziałów oraz sposób pokazania zmiany przez północ są decyzją wizualną CHECKPOINT A i nie są jeszcze zamrożone w tym briefie.

## 6. Wiele zmian jednego dnia

Obecny błąd `MULTIPLE_WORK_ITEMS_PER_CELL` jest ochroniarskim założeniem prezentacyjnym i nie może automatycznie blokować legalnego `ORDINARY`, jeżeli historia zawiera kilka niezależnych, niepokrywających się prac tego samego pracownika tego samego dnia.

Dla `ORDINARY` wszystkie takie realne przedziały mają trafić do jednej komórki dnia w deterministycznej kolejności chronologicznej.

T065-PRINT-GAP nie zmienia walidacji overlap. Jeżeli zapisany stan jest prawnie/strukturalnie wadliwy, obowiązują istniejące LAW/provenance gates. Eksporter nie staje się drugim validator-em.

## 7. Zmiana przez północ

Dla `ORDINARY` zmiana przechodząca przez północ pozostaje jednym faktem pracy zakotwiczonym w dacie rozpoczęcia, zgodnie z istniejącym Assignment/ScheduleVersion.

Renderer ma pokazać rzeczywisty przedział bez zamiany na `N` i bez ochroniarskiego 24h collapse.

Dokładny zapis wizualny (`22–6`, `22–06 (+1)` itp.) zostaje zamrożony przez OWNERA w CHECKPOINT A.

## 8. Role zawodowe na wydruku

Role są opcjonalne historycznie.

Dla Assignment z demandem posiadającym `required_role` renderer MUSI pokazać tę rolę przy godzinach. Dokładna forma wizualna pozostaje decyzją CHECKPOINT A.

Dla demandu bez roli:

- nie wolno zgadywać roli z pracownika;
- nie wolno dopisywać `SPRZEDAWCA_ZALOGA` jako default;
- komórka nadal ma być drukowalna.

Dokładny zapis `KIEROWNIK` / `SPRZEDAWCA_ZALOGA` (pełna nazwa, skrót, osobna linia, nawias itp.) jest decyzją CHECKPOINT A.

## 9. PLAN / WYK

Nie zmieniamy semantyki istniejących danych PLAN/WYK.

To, czy `ORDINARY` zachowuje dwa osobne wiersze PLAN/WYK, czy przy akceptowanym stanie pokazuje je inaczej, jest user-visible decyzją OWNERA i pozostaje otwarte do próbki CHECKPOINT A.

Implementer nie wybiera tego samodzielnie.

## 10. Absencje i podsumowania

`ORDINARY` nie tworzy własnego mechanizmu absencji ani godzin.

Źródłem pozostają istniejące kanoniczne fakty T020 / `canonical_site_absence_days` / `absence_reference_snapshot` i obecne pola sumaryczne.

Renderer ORDINARY może mieć inną etykietę tekstową niż ochroniarskie U*/C*, ale nie może:

- inaczej liczyć godzin urlopu/L4;
- tworzyć Assignment dla nieobecności;
- rozkładać absencji na fikcyjne sklepowe zmiany;
- rekonstruować nieobecności z samego layoutu.

Dokładne etykiety (`Urlop`, `L4`, skróty) i wygląd podsumowań zamraża CHECKPOINT A.

## 11. SitePrintSettings — jeden owner, regime-aware

`SitePrintSettings` pozostaje jedynym właścicielem ustawień wydruku per Site. Nie powstaje `OrdinaryPrintSettings`, drugi repository ani drugi endpoint ustawień.

Wspólne dla obu reżimów pozostają co najmniej:

- `company_print_name`;
- `site_print_name`.

Pola ochroniarskie:

- `base_regime`;
- `work_code_intervals`;
- `reserve_hours`;
- miesięczne D6+/N6+;
- ustawienia S1 zależne od obecnego kontraktu

nie mogą być wymagane ani prezentowane jako konfiguracja ORDINARY tylko po to, żeby istniejący model przeszedł walidację.

Implementacja ma minimalnie uczynić istniejący owner regime-aware. Preferowane jest zachowanie jednej struktury/API z polami ochroniarskimi opcjonalnymi/ignorowanymi zgodnie z `planning_regime`, zamiast tworzenia równoległego modelu.

Walidacja odczytu i zapisu ma znać reżim Site i failować jawnie na sprzecznej konfiguracji; nie może zgadywać reżimu z obecności kodów.

## 12. PrintSettings UI

`Panel sterowania -> Obiekt -> Ustawienia wydruku` pozostaje jednym ekranem/komponentem.

Dla ORDINARY użytkownik ma widzieć wyłącznie ustawienia mające sens dla tego reżimu. Nie pokazujemy:

- `Reżim bazowy 12h/24h`;
- tabeli D1..D5/N1..N5;
- miesięcznych D6+/N6+;
- ochroniarskich rezerw U/C jako wymaganej konfiguracji sklepowej.

Nagłówek/nazwa firmy/nazwa obiektu pozostają dostępne.

Nie tworzyć osobnego ekranu `Store Print Settings`.

## 13. Jeden entry point eksportu

`generate_schedule_pdf()` pozostaje jedynym publicznym application entry pointem.

Dozwolony kształt wewnętrzny:

1. wspólne pre-gates i LAW acknowledgement;
2. wspólne przypięcie CURRENT/lineage;
3. odczyt `Site.planning_regime`;
4. assembly prezentacyjne odpowiednie dla OCHRONA lub ORDINARY;
5. wspólny render entry / wspólne revision/provenance/race checks.

Można wydzielić małe prywatne helpery/typy rendererów w istniejącym module, jeśli jest to konieczne do utrzymania czytelności i limitów backendu.

Nie wolno tworzyć:

- `generate_ordinary_pdf()` jako drugiego publicznego pipeline;
- drugiego API endpointu;
- osobnej tabeli/export lifecycle;
- alternatywnej walidacji LAW;
- alternatywnej provenance/revision.

## 14. CHECKPOINT A — obowiązkowy optyczny gate OWNERA

Przed implementacją produkcyjnego ORDINARY renderer CC przygotowuje prawdziwy PDF demonstracyjny na danych syntetycznych. To jest artefakt projektowy, nie produkcyjny export path.

Próbka musi zawierać co najmniej:

1. pracownika wykonującego różne role w różnych dniach;
2. Assignment z rolą oraz Assignment bez `required_role`;
3. dwie legalne, niepokrywające się zmiany jednego pracownika tego samego dnia;
4. zmianę przechodzącą przez północ;
5. urlop;
6. L4;
7. zwykły dzień bez pracy;
8. wystarczającą liczbę pracowników/dni, aby wymusić więcej niż jedną stronę.

Próbka ma korzystać z danych wizualnie realistycznych, ale syntetycznych. Nie używać realnych nazwisk.

Przed CHECKPOINT A wolno stworzyć wyłącznie izolowany prototype/mock w `tasks/ROTA-T065-PRINT-GAP/prototype/**`; nie wolno modyfikować produkcyjnego `rota/application/schedule_export.py` w celu uzyskania próbki.

OWNER po obejrzeniu próbki zamraża dokładnie:

- sposób zapisu godzin;
- sposób zapisu roli i brak roli;
- separator/kolejność wielu przedziałów;
- zapis zmiany przez północ;
- PLAN/WYK dla ORDINARY;
- słowa/skróty absencji;
- podsumowania;
- które elementy nagłówka/stopki/legendy pozostają wspólne.

Bez jawnego OWNER ACCEPTED CHECKPOINT A implementacja produkcyjna pozostaje HOLD.

## 15. CHECKPOINT B — implementacja produkcyjna

Dopiero po OWNER ACCEPTED CHECKPOINT A oraz PASS audytu briefu można zmieniać produkcyjny eksport.

Implementacja B ma odtworzyć zaakceptowany layout na kanonicznych danych historycznych i zachować wszystkie wspólne gates T020.

Nie wolno implementerowi poprawiać zaakceptowanej próbki `dla wygody` bez powrotu do OWNERA.

## 16. Acceptance funkcjonalne

T65P-01 — ten sam publiczny endpoint/generate path drukuje OCHRONA i ORDINARY zależnie od `Site.planning_regime`.

T65P-02 — reprezentatywny OCHRONA PDF zachowuje istniejące kody/layout/legendę i wszystkie gates.

T65P-03 — ORDINARY 05:00–12:00 drukuje realne godziny bez D/N i bez `WORK_CODE_MAPPING_REQUIRED`.

T65P-04 — ORDINARY demand z `required_role` pokazuje rolę zgodnie z zaakceptowanym CHECKPOINT A; brak roli nie jest zgadywany.

T65P-05 — dwie niepokrywające się prace jednego dnia drukują się deterministycznie w jednej komórce zamiast `MULTIPLE_WORK_ITEMS_PER_CELL`.

T65P-06 — zmiana przez północ jest jednym faktem zakotwiczonym w dacie startu i prezentuje się zgodnie z CHECKPOINT A.

T65P-07 — historyczny reprint po zmianie membership roles nadal pokazuje rolę z historycznego `ShiftDemand.required_role`.

T65P-08 — urlop/L4 używają kanonicznych danych i nie tworzą nowego bilansu.

T65P-09 — ORDINARY PrintSettings zapisują/odczytują wspólne pola bez wymuszania ochroniarskiego base_regime/kodów/rezerw.

T65P-10 — UI ORDINARY nie pokazuje ochroniarskich ustawień D/N/D1..N5/D6+/N6+.

T65P-11 — świeża LAW validation, acknowledgement fingerprint, CURRENT race checks, provenance i document revision działają identycznym wspólnym mechanizmem dla obu reżimów.

T65P-12 — multipage ORDINARY zachowuje czytelność i nagłówki zgodnie z zaakceptowaną próbką.

## 17. Guardrails przeciw duplikacji

Zakazane:

- drugi solver;
- drugi export endpoint;
- drugi export lifecycle;
- drugi LAW validator;
- drugi system revision/provenance;
- drugi owner PrintSettings;
- odczyt bieżącego `allowed_roles` do historycznego PDF;
- przeliczanie absencji od zera;
- sklepowe D/N albo D1/N1 tylko dla kompatybilności renderera;
- kopiowanie `schedule_export.py` do `ordinary_schedule_export.py` jako niezależnego pipeline.

Dozwolone jest wyłącznie wydzielenie prywatnej warstwy prezentacyjnej, jeśli wspólne gates i źródła danych pozostają pojedyncze.

## 18. Preimplementation audit

Codex ma przed CHECKPOINT A/produkcją sfalsyfikować:

1. czy brief zachowuje jeden publiczny lifecycle eksportu;
2. czy ORDINARY może korzystać z zapisanych Assignment + ShiftDemand bez nowego snapshotu;
3. czy `SitePrintSettings` da się uczynić regime-aware bez drugiego ownera;
4. czy zakres nie wymusza zmiany solvera/planningu;
5. czy dwa work items jednego dnia można obsłużyć prezentacyjnie bez omijania istniejących LAW/provenance gates;
6. czy OCHRONA może pozostać regresyjnie niezmieniona;
7. czy CHECKPOINT A jest rzeczywiście izolowany od produkcyjnej implementacji.

PASS preimplementation nie zatwierdza wyglądu. Wygląd zatwierdza OWNER na próbce.

WHERE_MAP: REQUIRED
- rota/application/schedule_export.py :: `generate_schedule_pdf`, assembly, cell mapping, render — przed CHECKPOINT B potwierdzić wszystkich istniejących callerów/helperów i nie tworzyć drugiego export ownera.
- rota/persistence/site_repository.py :: `SitePrintSettings`, `validate_site_print_settings`, read/write — przed CHECKPOINT B potwierdzić regime-aware walidację w jednym ownerze.
- api/routers/export.py :: modele oraz GET/PUT ustawień/entry export — przed CHECKPOINT B potwierdzić istniejący endpoint i brak drugiej ścieżki API.
- frontend/src/screens/PrintSettings.tsx :: target plikowy UI — przed CHECKPOINT B potwierdzić warunkową prezentację po `planning_regime` bez drugiego ekranu ustawień wydruku.

Mapa WHERE_MAP jest wymagana przed CHECKPOINT B. Nie jest wymagana do izolowanego CHECKPOINT A w `tasks/ROTA-T065-PRINT-GAP/prototype/**`.

TASK_SCOPE:
- tasks/ROTA-T065-PRINT-GAP/**
- rota/application/schedule_export.py
- rota/persistence/site_repository.py
- rota/persistence/db.py
- api/routers/export.py
- frontend/src/api/client.ts
- frontend/src/screens/PrintSettings.tsx
- tests/test_t020.py
- tests/test_t056.py

### Scope restrictions

Przed OWNER ACCEPTED CHECKPOINT A dozwolone są zmiany wyłącznie pod `tasks/ROTA-T065-PRINT-GAP/**` oraz raport/BOARD auditora. Produkcyjne pliki z TASK_SCOPE są odblokowane dopiero w CHECKPOINT B.

`rota/planning/**`, solver, validator, `rota/balance.py`, `rota/domain.py`, schedule lifecycle i T065 role/planning implementation są poza scope. Jeżeli produkcyjna implementacja wymaga ich zmiany, CC zatrzymuje się i zgłasza finding zamiast rozszerzać Task.
