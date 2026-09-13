# ROTA-T065-PRINT-GAP — PDF dla ORDINARY bez drugiego eksportu

STATUS: CHECKPOINT A OWNER_ACCEPTED — CHECKPOINT B PREIMPLEMENTATION HOLD UNTIL LITERAL CODEX RE-CHECK + ROLE SOURCE READY

BASELINE: `main@3085f6f`

SOURCE:
- `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r1.txt`
- `tasks/ROTA-T065-PRINT-GAP/round_01/tests/tests_r2.txt`
- preimplementation PASS `task/ROTA-T065-PRINT-GAP@18665e3`
- OWNER_ACCEPTED prototype `task/ROTA-T065-PRINT-GAP@66c7c23a9d96b4fe4e87c18b3086b2f7b9818f77`
- CHECKPOINT A handoff audit R4 `task/ROTA-T065-PRINT-GAP@75710f1`
- T065 implementation PASS `42740118e838d704cb9679716efb7cdfb51b6083`
- istniejący eksport T020/T056/T052 oraz późniejsze zabezpieczenie LAW acknowledgement
- zależność semantyczna roli: `ROTA-T065-CONFIGURABLE-ROLES`

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

CHECKPOINT A został zaakceptowany przez OWNERA. Ten brief zamraża wynik A jako PRODUCT_TRUTH i projektuje CHECKPOINT B.

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
- modelu ról, hierarchii ani zastępstw;
- istniejącej semantyki i zaakceptowanego wydruku `OCHRONA`.

Eksporter jest konsumentem już zapisanej prawdy. Nie wolno mu wyliczać legalności, rekonstruować ról z bieżącej obsady ani tworzyć własnego bilansu czasu.

## 3. Jedno źródło danych historycznych

Dla `ORDINARY` wydruk bierze pracę z tej samej efektywnej historycznej wersji grafiku, z której dziś korzysta T020.

Dla PRIMARY Assignment:

- konkretne godziny pochodzą z `Assignment.start_datetime/end_datetime`;
- wersja grafiku/lineage pozostaje źródłem pracy historycznej;
- rola wykonywanej pracy z demandu NIE jest etykietą stanowiska człowieka;
- renderer nie może użyć bieżącego `SiteMembership.allowed_roles` ani innej bieżącej konfiguracji do zgadywania historycznego stanowiska.

Zmiana dzisiejszej obsady, katalogu zmian albo późniejsza zmiana roli nie może zmienić starego reprintu.

### 3.1. Historyczne stanowisko pod nazwiskiem — jawna zależność

OWNER zaakceptował jedną stałą etykietę rzeczywistego stanowiska pod nazwiskiem pracownika.

Przykład: osoba organizacyjnie będąca `Kierownikiem`, która pokryła pracę sprzedawcy, nadal drukuje się jako `Kierownik`.

T065-PRINT-GAP NIE może sam wprowadzić pola/encji/tabeli stanowiska tylko dla wydruku.

Historyczne źródło tej etykiety ma pochodzić z docelowego, audytowanego modelu `ROTA-T065-CONFIGURABLE-ROLES`, który rozdziela:

1. stanowisko organizacyjne pracownika;
2. rolę wymaganej/wykonywanej pracy;
3. ewentualne jawne dopuszczenie zastępstwa.

Do czasu gdy ten owner udostępnia jednoznaczne historyczne stanowisko dla drukowanej wersji, CHECKPOINT B pozostaje IMPLEMENTATION HOLD. To jest zależność danych, nie zgoda na rozszerzenie scope PRINT-GAP.

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

## 5. CHECKPOINT A — OWNER_ACCEPTED PRODUCT TRUTH

Poniższe decyzje są zamrożone i nie są już otwartymi pytaniami implementacyjnymi.

1. **Godziny** — literalny zakres z Assignment, bez zer wiodących, np. `5–12`.
2. **Stanowisko** — pełna nazwa stanowiska drukowana dokładnie raz pod nazwiskiem pracownika; nie zmienia się dzień do dnia tylko dlatego, że osoba pokrywa pracę zwykle przypisaną innej roli.
3. **Komórki dni** — pokazują godziny pracy, nie stanowisko/rolę.
4. **Wiele zmian jednego dnia** — osobne linie w tej samej komórce, chronologicznie.
5. **Zmiana przez północ** — godzina końcowa z `(+1)`, np. `22–6(+1)`, zakotwiczona na dacie startu.
6. **PLAN/WYK** — jeden wiersz pracownika/dzień dla ORDINARY; nie tworzyć ochroniarskiego duetu PLAN/WYK.
7. **Absencje** — pełne słowa `Urlop` i `L4`; bez wypełnienia. `Urlop` = pogrubiona pełna ramka, `L4` = przerywana ramka.
8. **Zwykły dzień bez pracy** — `–`, bez specjalnej ramki.
9. **Tło strony** — zawsze białe, niezależnie od trybu UI/systemu.
10. **Wypełnienie komórek pracy** — szarość jest wyłącznie dodatkową podpowiedzią stanowiska, nie jedynym nośnikiem informacji.
11. **Role konfigurowalne** — język wizualny ma działać dla dowolnych nazw stanowisk; nie hardcodować dwóch wartości ani przykładowego `Uczeń`. Dokładne przypisanie odcieni do N stanowisk może być deterministyczne, lecz nie może zmieniać znaczenia danych.

Nie wolno implementerowi zmieniać tych decyzji `dla wygody` bez nowej jawnej decyzji OWNERA.

## 6. ORDINARY — prezentacja pracy

`ORDINARY` nie mapuje Assignment do D/N ani do kodu pracy.

Komórka pracy jest budowana z rzeczywistych przedziałów czasu tego pracownika w danym dniu.

Przykłady:

- `05:00–12:00` -> `5–12`;
- `12:00–19:00` -> `12–19`;
- `22:00–06:00` następnego dnia -> `22–6(+1)`;
- dwa niezależne, niepokrywające się Assignments tego samego dnia -> dwie linie w jednej komórce.

Eksporter ORDINARY obsługuje te przypadki bez `WORK_CODE_MAPPING_REQUIRED`, bez D/N i bez ochroniarskiego 24h collapse.

## 7. Wiele zmian jednego dnia

Obecny błąd `MULTIPLE_WORK_ITEMS_PER_CELL` jest założeniem ochroniarskiej prezentacji i nie może blokować legalnego ORDINARY.

Dla ORDINARY wszystkie niepokrywające się realne przedziały danego pracownika w danym dniu trafiają do jednej komórki w deterministycznej kolejności `(start_datetime, end_datetime, assignment_id)`.

T065-PRINT-GAP nie zmienia walidacji overlap. Eksporter nie staje się drugim validatorem.

## 8. Zmiana przez północ

Zmiana przechodząca przez północ pozostaje jednym faktem pracy zakotwiczonym w dacie rozpoczęcia.

Format jest zamrożony: `start–end(+1)`, bez D/N i bez dzielenia Assignment na dwa dni.

## 9. Stanowisko pracownika na wydruku

Stanowisko jest informacją o człowieku, nie o każdym Assignment.

Renderer pokazuje jedną pełną nazwę stanowiska pod nazwiskiem pracownika. Nie pokazuje roli przy godzinach i nie buduje etykiety typu `Kierownik/Sprzedawca`.

Jeżeli pracownik pokrył demand innej roli, komórka nadal pokazuje wyłącznie godziny, a stanowisko pod nazwiskiem pozostaje jego rzeczywistym stanowiskiem organizacyjnym.

Renderer nie może:

- wyprowadzać stanowiska z `ShiftDemand.required_role`;
- scalać historycznie wykonanych ról w listę stanowisk;
- wybierać arbitralnie jednego elementu z `allowed_roles`;
- używać nazwy `Kierownik`, `Sprzedawca` lub innych wartości jako hardcode.

## 10. PLAN/WYK, absencje, podsumowania

ORDINARY ma jeden wiersz na pracownika.

Źródłem absencji pozostają istniejące kanoniczne fakty T020 / `canonical_site_absence_days` / `absence_reference_snapshot`.

Renderer nie może:

- inaczej liczyć godzin urlopu/L4;
- tworzyć Assignment dla nieobecności;
- rozkładać absencji na fikcyjne sklepowe zmiany;
- rekonstruować nieobecności z layoutu.

Wyświetlanie:

- `Urlop` — pełne słowo, pogrubiona pełna ramka;
- `L4` — pełne słowo, przerywana ramka;
- brak pracy/absencji — `–`.

## 11. SitePrintSettings — jeden owner, regime-aware

`SitePrintSettings` pozostaje jedynym właścicielem ustawień wydruku per Site. Nie powstaje `OrdinaryPrintSettings`, drugi repository ani drugi endpoint ustawień.

Wspólne dla obu reżimów pozostają co najmniej:

- `company_print_name`;
- `site_print_name`.

Pola ochroniarskie (`base_regime`, `work_code_intervals`, `reserve_hours`, D6+/N6+, ustawienia S1) nie mogą być wymagane ani prezentowane jako konfiguracja ORDINARY.

Walidacja odczytu i zapisu zna `planning_regime`; nie zgaduje reżimu z obecności kodów.

## 12. PrintSettings UI

`Panel sterowania -> Obiekt -> Ustawienia wydruku` pozostaje jednym ekranem/komponentem.

Dla ORDINARY użytkownik widzi tylko ustawienia mające sens dla tego reżimu. Nie pokazujemy:

- `Reżim bazowy 12h/24h`;
- tabeli D1..D5/N1..N5;
- miesięcznych D6+/N6+;
- ochroniarskich rezerw U/C jako wymaganej konfiguracji.

Nazwa firmy i nazwa obiektu pozostają dostępne.

Nie tworzyć osobnego ekranu `Store Print Settings`.

## 13. Jeden entry point eksportu

`generate_schedule_pdf()` pozostaje jedynym publicznym application entry pointem.

Kształt B:

1. wspólne pre-gates i LAW acknowledgement;
2. wspólne przypięcie CURRENT/lineage;
3. odczyt `Site.planning_regime`;
4. wspólne pobranie kanonicznych danych;
5. prywatne assembly prezentacyjne OCHRONA albo ORDINARY;
6. wspólny publiczny export result, document revision, provenance i race checks.

Dozwolone są prywatne helpery/typy prezentacyjne. Niedozwolone:

- `generate_ordinary_pdf()` jako drugi publiczny pipeline;
- drugi API endpoint;
- osobna tabela/export lifecycle;
- alternatywna walidacja LAW;
- alternatywna provenance/revision.

## 14. CHECKPOINT A — ZAMKNIĘTY

CHECKPOINT A został OWNER_ACCEPTED na prototypie `66c7c23`.

Prototyp pozostaje izolowanym artefaktem projektowym pod `tasks/ROTA-T065-PRINT-GAP/prototype/**` i nie może być importowany przez kod produkcyjny.

Nie powtarzamy audytu prototypu. R4 wymaga wyłącznie literalnego re-checku korekty kontraktu.

## 15. CHECKPOINT B — projekt produkcyjny

CHECKPOINT B odtwarza zaakceptowany layout w istniejącym produkcyjnym eksporcie.

B obejmuje wyłącznie:

1. uczynienie istniejącego `SitePrintSettings` regime-aware;
2. rozszerzenie istniejącego assembly o model ORDINARY;
3. prywatne mapowanie ORDINARY Assignment -> komórki rzeczywistych godzin;
4. jedną etykietę historycznego stanowiska pod nazwiskiem pracownika, pobraną z autoryzowanego ownera modelu ról;
5. layout ORDINARY zgodny 1:1 z decyzjami §5;
6. warunkowe UI `PrintSettings` po `planning_regime`;
7. testy regresji OCHRONA oraz testy nowego ORDINARY.

B NIE obejmuje modelowania stanowisk/ról. Jeżeli `ROTA-T065-CONFIGURABLE-ROLES` nie udostępnia wymaganego historycznego stanowiska, CC zatrzymuje implementację i zgłasza zależność — nie dodaje print-only role source.

Po PASS literalnego re-checku tego briefu architektura B jest zaakceptowana. Implementacja produkcyjna może rozpocząć się dopiero, gdy zależność stanowiska jest technicznie dostępna na branchu implementacyjnym.

## 16. Acceptance funkcjonalne

T65P-01 — ten sam publiczny endpoint/generate path drukuje OCHRONA i ORDINARY zależnie od `Site.planning_regime`.

T65P-02 — reprezentatywny OCHRONA PDF zachowuje istniejące kody/layout/legendę i wszystkie gates.

T65P-03 — ORDINARY `05:00–12:00` drukuje `5–12`, bez D/N i bez `WORK_CODE_MAPPING_REQUIRED`.

T65P-04 — pod nazwiskiem ORDINARY drukuje się jedna pełna historyczna nazwa stanowiska z autoryzowanego modelu ról; rola wykonywanej pracy nie zastępuje stanowiska.

T65P-05 — kierownik pokrywający pracę sprzedawcy nadal drukuje się jako `Kierownik`; komórka pokazuje tylko godziny.

T65P-06 — dwie niepokrywające się prace jednego dnia drukują się chronologicznie jako osobne linie w jednej komórce zamiast `MULTIPLE_WORK_ITEMS_PER_CELL`.

T65P-07 — zmiana przez północ jest jednym faktem zakotwiczonym w dacie startu i ma format `22–6(+1)`.

T65P-08 — ORDINARY ma jeden wiersz pracownika, nie osobne PLAN/WYK.

T65P-09 — `Urlop` i `L4` używają kanonicznych danych; mają zaakceptowane teksty/ramki; zwykły dzień bez pracy to `–`.

T65P-10 — tło PDF jest białe niezależnie od trybu UI/systemu.

T65P-11 — język szarości działa dla dowolnej liczby/nazw stanowisk bez hardcode dwóch ról; tekst stanowiska pozostaje podstawowym nośnikiem znaczenia.

T65P-12 — historyczny reprint nie rekonstruuje stanowiska z bieżącego membershipu ani z ról wykonywanych prac.

T65P-13 — ORDINARY PrintSettings zapisują/odczytują wspólne pola bez wymuszania ochroniarskiego base_regime/kodów/rezerw.

T65P-14 — UI ORDINARY nie pokazuje ochroniarskich ustawień D/N/D1..N5/D6+/N6+.

T65P-15 — świeża LAW validation, acknowledgement fingerprint, CURRENT race checks, provenance i document revision działają identycznym wspólnym mechanizmem dla obu reżimów.

T65P-16 — multipage ORDINARY zachowuje czytelność i nagłówki zgodnie z OWNER_ACCEPTED prototypem.

## 17. Guardrails przeciw duplikacji

Zakazane:

- drugi solver;
- drugi export endpoint;
- drugi export lifecycle;
- drugi LAW validator;
- drugi system revision/provenance;
- drugi owner PrintSettings;
- print-only model stanowiska;
- odczyt bieżącego `allowed_roles` do historycznego PDF;
- przeliczanie absencji od zera;
- sklepowe D/N albo D1/N1 tylko dla kompatybilności renderera;
- kopiowanie `schedule_export.py` do `ordinary_schedule_export.py` jako niezależnego pipeline.

Dozwolone jest wyłącznie wydzielenie prywatnej warstwy prezentacyjnej przy zachowaniu pojedynczych gates i źródeł danych.

## 18. Wąski re-check Codexa

Po R4 Codex NIE powtarza audytu prototypu ani pełnego preimplementation review.

Sprawdza literalnie tylko:

1. czy 11 zaakceptowanych decyzji CHECKPOINT A znajduje się w briefie jako PRODUCT_TRUTH;
2. czy stary kontrakt `required_role przy godzinach` został usunięty;
3. czy jedna etykieta stanowiska ma jawnego ownera/dependency i PRINT-GAP nie tworzy bocznego modelu ról;
4. czy acceptance B odpowiada zaakceptowanej próbce;
5. czy jeden export lifecycle pozostaje zachowany.

WHERE_MAP: REQUIRED
- rota/application/schedule_export.py :: `generate_schedule_pdf`, `_assemble_export_model`, cell mapping, `_render_pdf` — zachować wspólne gates/result; regime branch tylko w prywatnym assembly/render modelu.
- rota/persistence/site_repository.py :: `SitePrintSettings`, `validate_site_print_settings`, read/write — regime-aware w jednym ownerze.
- api/routers/export.py :: istniejące modele oraz GET/PUT ustawień/entry export — bez drugiej ścieżki API.
- frontend/src/screens/PrintSettings.tsx :: warunkowa prezentacja po `planning_regime`, bez drugiego ekranu.
- ROTA-T065-CONFIGURABLE-ROLES owner/history API :: tylko read dependency dla historycznego stanowiska; bez implementacji modelu ról w tym Tasku.

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

`rota/planning/**`, solver, validator, `rota/balance.py`, `rota/domain.py`, schedule lifecycle oraz implementacja modelu ról są poza scope PRINT-GAP.

PRINT-GAP może wyłącznie odczytać autoryzowane historyczne stanowisko dostarczone przez zależność `ROTA-T065-CONFIGURABLE-ROLES`. Jeżeli do tego potrzebna byłaby zmiana modelu domeny po stronie PRINT-GAP, CC zatrzymuje się i zgłasza finding zamiast rozszerzać Task.
