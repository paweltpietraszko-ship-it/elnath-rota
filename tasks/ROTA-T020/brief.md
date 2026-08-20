# ROTA-T020 — printable schedule PDF — CHECKPOINT A contract

STATUS: READY FOR CODEX CHECKPOINT-A PREIMPLEMENTATION AUDIT — CHECKPOINT B BLOCKED — NOT READY FOR PRODUCTION CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
BASE_BRANCH: main
BASE_SHA: d9c87185e3051aa65df3234c8db2d703fe32c5d8
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
OWNER_SOURCE: arch/T020_schedule_export_architect_brief.md
DEPENDS_ON: T012 + T018 + T019 + T019b merged on main
FOLLOWED_BY: T020 Checkpoint B after explicit owner acceptance of Checkpoint A

## 1. CEL TEGO KONTRAKTU

Ten kontrakt otwiera WYŁĄCZNIE Checkpoint A z owner briefu.

Wynikiem Checkpoint A są dwa prawdziwe, otwieralne i drukowalne statyczne PDF-y demonstracyjne, zbudowane na kontrolowanych danych demonstracyjnych:

1. reprezentatywny miesiąc Site w podstawowym reżimie 12h;
2. reprezentatywny miesiąc Site w podstawowym reżimie 24h.

Checkpoint A nie czyta bazy Roty, nie zmienia produkcyjnego kodu i nie tworzy jeszcze aplikacyjnego read modelu eksportu.

Jego celem jest uzyskanie jawnej akceptacji właściciela dla realnego wyglądu i konwencji wydruku przed zamrożeniem integracji produkcyjnej.

## 2. TWARDY GATE A -> B

Checkpoint B jest zabroniony do czasu jawnej akceptacji właściciela Checkpoint A.

Bez tej akceptacji NIE wolno:

- dodawać produkcyjnego generatora PDF;
- dodawać produkcyjnego read modelu eksportu;
- dodawać migracji/settings table dla T020;
- zmieniać pyproject.toml;
- integrować z ScheduleVersion, Availability, WorkBalance albo Site persistence;
- projektować UI eksportu;
- uznawać próbki za frozen visual contract.

Akceptacja Checkpoint A musi później zostać zapisana w repo jako architect/owner amendment wskazujący exact zaakceptowane artefakty PDF i otwierający Checkpoint B.

## 3. ŹRÓDŁA WIZUALNE

`Grafiki/7442.jpg` jest wyłącznie realnym źródłem konwencji branżowej. Nie kopiować go 1:1.

Zewnętrzny mockup HTML z owner briefu nie jest źródłem kontraktu i nie jest wymagany do audytu.

Trwałym materiałem do dalszego B staną się dopiero PDF-y z Checkpoint A po jawnej akceptacji właściciela.

## 4. ARTEFAKTY CHECKPOINT A

Wymagane pliki:

- `tasks/ROTA-T020/checkpoint_a/render_samples.py`
- `tasks/ROTA-T020/checkpoint_a/requirements.txt`
- `tasks/ROTA-T020/checkpoint_a/schedule_12h.pdf`
- `tasks/ROTA-T020/checkpoint_a/schedule_24h.pdf`
- `tasks/ROTA-T020/checkpoint_a/README.md`

Wszystkie są pipeline/prototype artifacts. Żaden nie jest importowany przez `rota/*`.

`render_samples.py` może używać biblioteki PDF wyłącznie lokalnie dla Checkpoint A; nie autoryzuje to jeszcze zależności produkcyjnej.

## 5. KONTROLOWANE DANE DEMONSTRACYJNE

Próbki nie mogą zawierać realnych danych pracowników.

Obie próbki używają:

- miesiąca 31-dniowego;
- około 10 fikcyjnych pracowników;
- co najmniej jednego dnia z podwójną obsadą;
- osobnego wiersza PLAN i WYK dla każdego pracownika;
- co najmniej jednego przypadku urlopu;
- co najmniej jednego przypadku chorobowego;
- co najmniej jednego przypadku zmiany planu/korekty zilustrowanego wyłącznie jako finalny poprawny widok, bez prezentowania "winnego" wcześniejszego pracownika;
- podsumowań godzin i legendy.

Nazwy przykładowe mają być jawnie demonstracyjne, np. `Pracownik 01`, nigdy kopiowane z `Grafiki/*.jpg`.

## 6. PROTOTYPOWY UKŁAD DO OCENY — NIE JEST JESZ BINDING DLA B

Pierwsza próbka ma użyć A3 landscape jako świadomego kandydata do oceny, ponieważ 31 dni + PLAN/WYK + podsumowania muszą pozostać czytelne przy około 10 pracownikach.

To NIE zamraża A3 dla produkcji. Właściciel może po obejrzeniu prawdziwego PDF zażądać innego papieru/paginacji przed otwarciem B.

Minimalny układ:

- nagłówek dokumentu;
- tabela z pracownikami w wierszach;
- dni miesiąca w kolumnach;
- dwa podwiersze `PLAN` / `WYK` na pracownika;
- kolumny podsumowań po prawej;
- legenda pod tabelą;
- footer/provenance.

Nie zakładać dokładnie 7 osób ani stałej wysokości wynikającej z jednego mockupu.

## 7. NAGŁÓWEK I PROWENIENCJA W PRÓBCE

Każdy PDF Checkpoint A musi wizualnie pokazać miejsce i format dla:

- nazwy firmy;
- nazwy Site/obiektu;
- edytowalnego tytułu okresu;
- prawdziwego zakresu dat, np. `2026-08-01 — 2026-08-31`;
- proweniencji schedule state;
- identyfikatora rewizji dokumentu;
- czasu wygenerowania.

W A użyć demonstracyjnych wartości, np.:

- `Firma: ELNATH DEMO`;
- `Obiekt: SITE-DEMO-12H` / `SITE-DEMO-24H`;
- `Okres: Sierpień 2026 — DEMO`;
- `Schedule provenance: DEMO-SV-LINEAGE-*`;
- `Revision: DEMO-REV-*`.

Nie udawać, że to realne ScheduleVersion IDs z bazy.

## 8. CZARNO-BIAŁY WYDRUK

Znaczenie żadnej komórki nie może zależeć wyłącznie od koloru.

Próbka musi zachować znaczenie po konwersji do skali szarości poprzez kombinację:

- tekstu kodu;
- wyraźnych obramowań;
- zróżnicowanych jasnych wypełnień / patternów lub typografii;
- wyraźnego labela PLAN/WYK.

Weekend/święto może mieć inne szare tło, ale kod i tekst pozostają wystarczające bez koloru.

## 9. LEGENDA — WARTOŚCI FROZEN OWNERA

W obu PDF-ach legenda musi jawnie prezentować niesymetryczną tabelę ownera:

- D1=12h, D2=4h, D3=24h, D4=2h, D5=24h;
- N1=12h, N2=16h, N3=24h, N4=24h, N5=24h;
- U1=12h, U2=16h, U3/U4/U5=rezerwa;
- C1=12h, C2=16h, C3/C4/C5=rezerwa.

Nie normalizować numerów i nie sugerować, że np. D2/U2/C2 mają wspólną wartość.

W 24h próbce wolno pokazać jawnie oznaczoną DEMO konfigurację jednego wolnego slotu, np. `U3=24h` / `C3=24h`, aby właściciel mógł ocenić sposób prezentacji skonfigurowanej rezerwy. Musi być opisane jako `konfiguracja demo`, nie nowy default.

## 10. 12H SAMPLE — WIĄŻĄCY PRZYKŁAD 40H

`schedule_12h.pdf` musi zawierać dokładnie owner example 40h urlopu:

PLAN na pierwszych kwalifikujących dniach absencji:

`D1 / D1 / N2` = `12 + 12 + 16 = 40h`

WYK pod tymi samymi pozycjami:

`U1 / U1 / U2` = `12 + 12 + 16 = 40h`

Nie wolno użyć 24h code na 12h sample wyłącznie dla skrócenia zapisu.

`can_work_24h` nie jest w A potrzebne jako pole danych; próbka ma jedynie wizualnie utrwalić zasadę, że podstawowy reżim 12h kontroluje konwencję absencji.

## 11. 24H SAMPLE — PROTOTYPOWA KONWENCJA DO OCENY

`schedule_24h.pdf` musi pokazać co najmniej jeden pełny 24h okres pracy jako JEDEN czytelny symbol w kolumnie dnia rozpoczęcia, nie dwa przypadkowe, niezależne symbole 12h.

To jest kandydat techniczny do wizualnej oceny w A, wynikający z istniejącej T012 identity jednego WorkPeriod złożonego z komponentów. Nie staje się produkcyjnym mappingiem do czasu owner acceptance.

Legenda musi wyjaśnić wartość użytego 24h kodu.

## 12. PLAN / WYK — PROTOTYPOWA SEMANTYKA W A

W próbce:

- PLAN pokazuje prawidłową, aktualną obsadę dla dnia;
- WYK pokazuje wykonanie/absencję, nie historię błędu pracownika;
- wcześniej zastąpiona osoba nie jest oznaczana jako "nie przyszła";
- przykład korekty pokazuje wyłącznie finalnego właściwego pracownika w aktualnym PLAN/WYK.

Nie używać NN jako publicznego piętnującego symbolu na wydruku.

To odzwierciedla owner brief. Szczegółowy produkcyjny mapping `Assignment.state -> PLAN/WYK cell` zostanie zamrożony dopiero w B po ocenie A i audycie istniejących state semantics.

## 13. PODSUMOWANIA W A

Każdy pracownik ma miejsce na co najmniej:

- PLAN h;
- WYK h;
- URLOP h;
- L4 h.

Sumy w kontrolowanych danych muszą arytmetycznie odpowiadać symbolom widocznym w tabeli.

Nie dodawać:

- overtime qualification;
- płac;
- kar;
- KPI pracownika;
- management metrics.

## 14. STATIC PDF ONLY

PDF Checkpoint A:

- nie zawiera formularzy edytowalnych;
- nie zawiera importu;
- nie jest XLSX;
- nie zapisuje nic do Roty;
- nie jest źródłem danych;
- nie zawiera makr ani osadzonych workflow.

## 15. CHECKPOINT-A ACCEPTANCE MATRIX

A1. Oba pliki są prawidłowymi PDF i dają się otworzyć standardowym czytnikiem.

A2. 12h sample ma miesiąc 31-dniowy, około 10 osób, PLAN/WYK i podwójną obsadę.

A3. 24h sample ma miesiąc 31-dniowy, około 10 osób, PLAN/WYK i co najmniej jeden pełny 24h work-period symbol.

A4. Oba mają nagłówek, prawdziwy zakres dat, demonstracyjną proweniencję, revision id i generated-at.

A5. Legenda zawiera wszystkie D1..D5, N1..N5, U1..U5, C1..C5 z exact frozen values/rezerwa.

A6. 12h sample pokazuje 40h urlopu dokładnie jako PLAN `D1/D1/N2` i WYK `U1/U1/U2`.

A7. 12h sample nie używa 24h code do tej dekompozycji.

A8. W co najmniej jednym przypadku chorobowego PLAN/WYK i L4 summary są arytmetycznie spójne.

A9. Znaczenie pozostaje czytelne po wydruku w skali szarości.

A10. Brak realnych danych pracowników.

A11. Brak production imports / DB access / `rota.*` imports w sample rendererze.

A12. Brak edytowalnego XLSX/form workflow/import path.

A13. `git diff --check` PASS dla tekstowych artefaktów.

A14. Existing production suite pozostaje bez zmian; Checkpoint A nie wymaga adaptacji legacy testów.

A15. Owner może jednoznacznie zaakceptować lub odrzucić: papier/paginację, gęstość tabeli, PLAN/WYK visual, 24h visual, legendę i grayscale readability.

## 16. TASK_SCOPE — CHECKPOINT A ONLY

TASK_SCOPE:
- arch/T020_schedule_export_architect_brief.md
- tasks/ROTA-T020/brief.md
- tasks/ROTA-T020/checkpoint_a/render_samples.py
- tasks/ROTA-T020/checkpoint_a/requirements.txt
- tasks/ROTA-T020/checkpoint_a/schedule_12h.pdf
- tasks/ROTA-T020/checkpoint_a/schedule_24h.pdf
- tasks/ROTA-T020/checkpoint_a/README.md

Żaden inny plik nie jest autoryzowany w Checkpoint A.

W szczególności poza scope:

- `rota/**`;
- `tests/**`;
- `pyproject.toml`;
- schema/migrations;
- `arch/spec.md`;
- `arch/FROZEN.lock`.

## 17. CHECKPOINT B — PRE-DESIGN FINDINGS, NIE KONTRAKT

Poniższe punkty są świadomie pozostawione poza implementacją A. Nie są autoryzacją B.

### B-PD-01 — site-local absence hours for shared Employee — OWNER DECISION REQUIRED BEFORE B

Obecny T018/WorkBalance model liczy kwalifikowane LEAVE_GRANTED/SICK_LEAVE jako globalne Employee absence hours (8h za kwalifikowany workday), bez Site ownership.

Owner brief T020 wymaga natomiast, aby podsumowania PLAN/WYK/urlop/chorobowe wydruku dotyczyły wyłącznie jednego Site.

Dla Employee modelowanego na więcej niż jednym Site obecny model nie definiuje, któremu Site przypisać globalne 8h urlopu/L4. T020 B nie może zgadnąć ani podwójnie wykazać tych samych godzin na kilku Site.

Przed B właściciel musi zamknąć regułę site-allocation dla urlopu/L4 albo jawnie ograniczyć site-local absence summary do zdefiniowanego przypadku.

### B-PD-02 — employee row population / EXTERNAL_SUPPORT — OWNER DECISION REQUIRED BEFORE B

Wydruk nie może pominąć osoby faktycznie obsadzonej na Site, ale owner brief nie rozstrzyga, czy pusty w danym miesiącu enabled EXTERNAL_SUPPORT ma dostać własny wiersz jak LOCAL roster member.

Bezpieczny kandydat techniczny do późniejszej decyzji:

- enabled LOCAL -> row;
- każdy Employee z efektywnym Assignment na Site -> row niezależnie od membership_kind;
- EXTERNAL_SUPPORT bez żadnego efektywnego Assignment -> brak pustego wiersza.

Nie zamrażać tego bez owner/architect closure przed B.

### B-TECH-01 — daily ScheduleVersion lineage

Istniejące repo ma `list_schedule_versions`, `get_schedule_version_header`, `get_schedule_snapshot`, parent lineage i explicit `effective_from`.

Kandydat B powinien czytać lineage od current version i dla każdego dnia wybierać obowiązujący snapshot przez explicit `effective_from`, zamiast używać jednego current snapshot dla całego miesiąca albo fałszywego `parent=PLAN / child=WYK`.

Legacy/contradictory lineage z brakującą datą potrzebną do jednoznacznego odtworzenia powinno fail closed zamiast zgadywać po `created_at`.

### B-TECH-02 — print base regime must be explicit persistent setting

`can_work_24h` jest per-Employee kwalifikacją, a SiteProfile może zawierać możliwości H12/H24. Nie jest bezpiecznym źródłem wyższego-rzędu "podstawowego reżimu wydruku".

Kandydat B powinien mieć explicit per-Site print setting `H12` / `H24`, bez `INNY` w pierwszym zakresie.

### B-TECH-03 — legend interval mapping

Kandydat B powinien mapować shift/work-period do D/N code po exact skonfigurowanym interwale (start/end + crossing-midnight + hours/work-period identity), nigdy tylko po długości.

Dla 24h T012 work period kandydatem jest klasyfikacja całego work-period i render jednego symbolu na start date; finalnie zależy to od owner acceptance A.

### B-TECH-04 — absence decomposition must preserve full-code values

Ponieważ pełne kody mają niezależne wartości, B nie może mapować `D2 -> U2` wyłącznie po numerze slotu.

Kandydat algorytmu:

1. zbudować dozwolone pary PLAN(D/N)-WYK(U albo C) o identycznej wartości godzin;
2. odrzucić 24h denominacje dla podstawowego H12;
3. znaleźć exact sum z minimum liczby symboli;
4. tie-break: leksykograficznie po jawnej kolejności kodów;
5. rozmieścić wynik po pierwszych kwalifikowanych dniach absencji;
6. brak exact sum -> jawny config/decision problem, bez zaokrągleń.

40h default H12 ma wtedy deterministycznie prowadzić do `D1,D1,N2` + `U1,U1,U2` dla leave.

### B-TECH-05 — revision without export-history subsystem

Minimalny kandydat B: revision identifier jako deterministic hash canonical export snapshot/provenance/config, plus osobny generated_at.

Zmiana ScheduleVersion lineage, nagłówka, legendy lub period label zmienia revision id; identyczne dane mogą regenerować tę samą revision id. PDF nie wymaga wtedy nowej tabeli "document history" tylko po to, by mieć revision provenance.

To jest techniczny kandydat, nie frozen B contract.

## 18. CODEX PREIMPLEMENTATION AUDIT — CHECKPOINT A

Codex ma audytować exact contract HEAD i odpowiedzieć wyłącznie dla A:

1. Czy kontrakt nie autoryzuje żadnej integracji produkcyjnej przed owner acceptance?
2. Czy wymagane dwa PDF-y pokrywają wszystkie owner-required visual cases dla Checkpoint A?
3. Czy 40h example jest literalnie zachowany?
4. Czy legenda zachowuje niesymetryczne wartości i rezerwy?
5. Czy 24h visual nie przenosi logiki do solvera ani nie udaje produkcyjnego mappingu?
6. Czy grayscale requirement jest testowalny/ocenialny?
7. Czy TASK_SCOPE jest wyłącznie pipeline/prototype i nie dotyka `rota/**`, `tests/**`, pyproject ani DB?
8. Czy B-PD-01/B-PD-02 są prawdziwymi niezamkniętymi owner decisions, a nie problemami do zgadnięcia przez implementera?
9. Czy jakikolwiek punkt A wymaga nowej decyzji właściciela przed wygenerowaniem próbek? Jeśli tak, FAIL z exact powodem.

Required verdict:

`PASS — CHECKPOINT_A_READY_FOR_SAMPLE_GENERATION`

Do tego PASS nie generować próbek jako zaakceptowanego checkpointu.

## 19. CHECKPOINT A COMPLETION GATE

Po preimplementation PASS wykonawca generuje tylko artefakty z Section 16.

Następnie:

1. Codex sprawdza mechanicznie/strukturalnie A1-A14;
2. właściciel ogląda oba realne PDF-y i podejmuje jawne decyzje visual z A15;
3. architekt zapisuje accepted visual reference + decyzje ownera;
4. dopiero wtedy powstaje właściwy contract amendment Checkpoint B.

Bez punktu 2 i 3:

**T020 CHECKPOINT B MUST NOT START.**
