# ROTA-T010 — jawne operacje sterujące bez parsera i bez UI

STATUS: DRAFT FOR CODEX AUDIT
OWNER BASIS: `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md`
BASELINE: main `51b71725186fa30be23219e94aa135bb69bc5bce`

## 1. Cel

T010 przygotowuje trwałe operacje backend/application, które później wywoła T012 z okna **Panel Sterowania**.

T010 NIE tworzy UI, parsera, DSL, uniwersalnego edytora reguł ani drugiego źródła prawdy.

Najważniejsza zasada implementacyjna: **reuse first**. Jeśli zachowanie już istnieje, T010 dodaje tylko cienkie podpięcie. Skopiowanie istniejącej logiki do nowej warstwy oznacza FAIL audytu.

## 2. Inwentaryzacja reuse — obowiązkowa baza implementacji

T010 ma wykorzystać istniejące mechanizmy:

- `SiteMembership.enabled` — bieżące dopuszczenie pracownika do obiektu; solver już traktuje `enabled=false` jako HARD;
- `Employee.day_only` — stała reguła pracownika;
- `AvailabilityRecord` — wersjonowana nieobecność z zakresem dat;
- istniejące rodzaje `SICK_LEAVE`, `LEAVE_GRANTED`, `UNAVAILABLE_24H`;
- `SiteRuleVersion` + `effective_from/effective_to` + miesięczna aplikowalność;
- istniejące rule kinds `EMPLOYEE_ALLOWED_SHIFT_KINDS` oraz `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`;
- `record_structured_rule_decision()` — zapis jawnej, już rozstrzygniętej decyzji bez parsera;
- `apply_manual_correction()` — wersjonowana ręczna korekta grafiku;
- `AssignmentState.CANCELLED` — niewykonana praca nie liczy się jako PLANNED ani REALIZED;
- istniejący `WorkBalance`, który liczy bieżące PLANNED/REALIZED z current ScheduleVersion.

Nie wolno tworzyć tabel/kolumn typu `panel_can_day`, `panel_can_night`, `panel_available`, jeśli ten sam fakt jest już wyrażony przez powyższe dane.

## 3. Bieżąca obsada obiektu

Dodać cienkie operacje aplikacyjne dla T012:

- dodanie istniejącego lub nowego Employee do obiektu przez istniejący Employee + SiteMembership;
- usunięcie z bieżącej obsady przez `membership.enabled=false`;
- odczyt bieżącej obsady zwracający tylko aktywne membership dla danego Site.

MUST:

- brak fizycznego DELETE Employee;
- brak kasowania historycznych Assignment/ScheduleVersion;
- po `enabled=false` solver nie może użyć pracownika na tym Site;
- ponowne dodanie może ponownie włączyć istniejące membership zamiast tworzyć równoległy rekord.

## 4. Ogólna niedostępność przed planowaniem

Nie tworzyć nowego boolean `general_available`.

Jawna operacja koordynatora ma zapisywać istniejący `AvailabilityRecord` z zakresem od–do:

- choroba -> `SICK_LEAVE`;
- urlop -> `LEAVE_GRANTED`;
- inna pełna niedostępność -> `UNAVAILABLE_24H`.

Solver ma korzystać z istniejącej logiki HARD. Po końcu zakresu rekord nie blokuje późniejszych terminów.

## 5. Jedna matryca dostępności

Każda pozycja ma identyczną semantykę:

- `✓` = solver może korzystać;
- `☐` = solver nie może korzystać.

Dla nowego pracownika domyślnie zaznaczone są Ogólna dostępność, Dniówka,
Nocka oraz wszystkie dni Pon–Nd. Dla przydziału muszą być jednocześnie
dozwolone: dostępność ogólna, właściwy typ zmiany i dzień startu demandu.

Odznaczenie z `effective_from/effective_to` jest czasowym HARD i po
`effective_to` automatycznie wraca stan bazowy. Implementacja nie może mieć
odwróconego znaczenia checkboxa dla dni tygodnia.

`effective_from` i `effective_to` są inclusive. Ograniczenie obowiązuje przez
oba dni graniczne, a stan bazowy wraca następnego dnia po `effective_to`.

Nakładające się wymiary składają się przez AND: jedno obowiązujące `☐`
wystarcza do blokady właściwego przydziału. Ogólna dostępność ☐ blokuje D i N;
Dniówka ☐ tylko D; Nocka ☐ tylko N; dzień tygodnia ☐ blokuje D i N
rozpoczynające się tego dnia. Dniówka ☐ i Nocka ☐ razem oznaczają pełną
niedostępność na oba rodzaje zmian w okresie.

### D / N i stałe `day_only`

`Employee.day_only` pozostaje jedynym stałym źródłem zasady „ten pracownik jest tylko na dniówki”. Nie wolno lustrzanie zapisywać tej samej stałej reguły w nowym polu ani drugim trwałym mechanizmie.

Dla site-specific ograniczeń D/N użyć istniejącego `EMPLOYEE_ALLOWED_SHIFT_KINDS`.

`day_only=true` jest istniejącym źródłem bazowego stanu Nocka ☐, a nie drugą
widoczną kontrolką. Dla zwykłego pracownika bazowo Nocka ✓.

### Czasowa zmiana N

Koordynator może zapisać Nocka ☐ w zakresie od–do dla pracownika z bazowym
Nocka ✓. Solver blokuje N tylko w tym okresie i po nim wraca Nocka ✓.

Koordynator może także czasowo dopuścić Nocka ✓ dla pracownika z
`day_only=true` i bazowym Nocka ☐. Reprezentacja ma użyć istniejącego
`SiteRuleVersion` jako datowanej `CONFIRMED_EXCEPTION`, a nie zmieniać
`Employee.day_only` na czas wyjątku.

W okresie wyjątku eligibility i niezależny validator muszą zgodnie uznać N za dozwolone mimo `day_only=true`. Po `effective_to` wyjątek przestaje obowiązywać i bazowe `day_only` znów blokuje N bez tworzenia przyszłej operacji „przywróć”.

Nie wolno implementować czasowego wyjątku przez ręczne przełączanie `day_only` tam i z powrotem.

## 6. Niedostępność w wybrane dni tygodnia

Użyć istniejącego `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` jako HARD z:

- `weekdays` = odznaczone dni ISO;
- `forbidden_shift_kinds` = `["D", "N"]`;
- `effective_from` / `effective_to` = zakres koordynatora.

Wszystkie dni są bazowo zaznaczone, czyli dozwolone. Ograniczenie tworzy
odznaczony dzień z zakresem od–do: **Piątek ☐ = niedostępność w piątki**.

Przykład: Piątek ☐ + 2026-09-01..2026-10-31 blokuje D i N rozpoczynające się w każdy piątek tego okresu i nic poza tym.

## 7. Szkolenie i READY_FOR_PRIMARY

Nie dodawać ustawienia „Szkolenie” do żadnego backendowego modelu panelu.

`S` pozostaje zwykłą ręczną korektą TRAINEE na konkretnym grafiku.

Usunąć automatyczny side effect z `rota/application/training.py`, który po liczbie REALIZED TRAINEE zmienia `readiness_state` na `READY_FOR_PRIMARY`.

Po T010:

- REALIZED TRAINEE nie zmienia automatycznie readiness;
- `READY_FOR_PRIMARY` jest informacją i nie uczestniczy w eligibility;
- nie powstaje nowy algorytm oceny pracownika;
- specjalna operacja oznaczania szkolenia jako REALIZED, jeśli pozostaje dla kompatybilności API, ma być cienkim wywołaniem istniejącej manualnej korekty bez modyfikacji membership/readiness.

## 8. NN po zaplanowanej zmianie

NN nie jest preplanning availability. To wynik konkretnej wcześniej zaplanowanej zmiany.

Nie tworzyć REALIZED Assignment dla niewykonanej pracy.

Minimalny model ma pozostać przy istniejącym Assignment i wersjonowaniu grafiku:

- parent ScheduleVersion zachowuje pierwotny PLANNED Assignment;
- child ScheduleVersion, utworzony przez istniejącą manualną korektę, ma ten Assignment jako `CANCELLED` oraz trwały kod operacyjny `NN` związany z tym Assignment;
- kod `NN` ma być zapisany przy Assignment/version, nie jako globalna reguła pracownika;
- `NN` daje 0 godzin pracy, ponieważ nie jest PLANNED ani REALIZED w bieżącej wersji;
- późniejszy T012 może wyświetlić `NN` bez odtwarzania znaczenia z notatki tekstowej.

T010 może dodać **jedno opcjonalne strukturalne pole kodu operacyjnego do Assignment/persistence**, obsługujące na tym etapie wyłącznie `NN`. Nie tworzyć osobnej encji „HR event”, ledgeru kadrowego ani nowego workflow.

Dodać cienką operację aplikacyjną `mark_unexcused_absence` (nazwa techniczna może być równoważna), która:

1. wymaga istniejącego PLANNED Assignment w current ScheduleVersion;
2. tworzy child przez istniejący mechanizm manual correction;
3. zmienia ten Assignment na CANCELLED + `NN`;
4. nie uruchamia REPLAN automatycznie;
5. pozostawia normalną walidację/deviation mechanizmu manualnej korekty.

Przykład akceptacyjny: 14 zaplanowanych zmian po 12 h = 168 h. Jedna zostaje oznaczona NN. Bieżący stan liczy z tej zmiany 0 h i pracownik ma 156 h z pozostałych 13 zmian.

## 9. TARGET-01 bez zmian

T010 nie zmienia semantyki target_hours. Zapotrzebowanie generuje pracę; target_hours tylko pomaga rozdzielać istniejące zmiany i liczyć saldo. Nie wolno generować dodatkowej pracy ani naruszać HARD dla targetu.

## 10. Minimalne testy akceptacyjne

1. `membership.enabled=false` -> pracownik pozostaje w historii, ale solver nie może go użyć na tym Site.
2. SICK/LEAVE/UNAVAILABLE od–do -> istniejący HARD blokuje tylko właściwy okres.
3. Wszystkie checkboxy bazowo ✓ -> brak dodatkowego ograniczenia.
4. Piątek ☐ od–do -> D i N są zablokowane tylko w piątki zakresu; po `effective_to` reguła wygasa.
5. Nocka ☐ od–do -> N zablokowane tylko w zakresie; po nim wraca bazowe Nocka ✓.
6. Dniówka ☐ i Nocka ☐ w tym samym okresie -> pracownik nie może pokryć żadnego D ani N w okresie.
7. nakładające się ustawienia -> jedno właściwe ☐ blokuje; inne ✓ nie odblokowuje przydziału.
8. `day_only=true` -> bazowe Nocka ☐; Nocka ✓ dozwolone wewnątrz jawnego datowanego wyjątku; po nim wraca zakaz; solver i validator zgadzają się.
9. REALIZED TRAINEE -> brak automatycznej zmiany readiness.
10. readiness nie wpływa na eligibility.
11. NN -> parent zachowuje PLANNED, child ma CANCELLED + NN, 0 godzin z tej zmiany, brak sztucznego REALIZED.
12. pełna regresja dotychczasowych testów poza testami jawnie usuwanej automatycznej promocji readiness.

## 11. Zakazy

T010 FAIL, jeśli implementacja wprowadzi którykolwiek z poniższych elementów:

- parser / LLM / interpretację swobodnego tekstu;
- UI lub tymczasowy Panel Sterowania;
- DSL;
- uniwersalny edytor reguł;
- kopię istniejącego stanu dostępności/reguł;
- drugi mechanizm `day_only`;
- automatyczną ocenę/dopuszczanie pracownika;
- automatyczny REPLAN po zmianie danych;
- logikę kadrowych konsekwencji NN;
- forwarding facade/service nieposiadający żadnej potrzebnej orkiestracji.

Codex ma traktować duplikację logiki jako FAIL architektoniczny, nie jako sugestię refaktoru.
