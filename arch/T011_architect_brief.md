# T011 (proponowane) — Backend/Application pipeline E2E

STATUS: PROPOZYCJA DO FORMALIZACJI PRZEZ ARCHITEKTA — nie jest to task
contract, tylko faktograficzny brief przygotowany przez CC na prośbę
Pawła, po zauważeniu realnej luki testowej podczas przeglądu stanu projektu
po merge T010.

Nazwa "T011" to PROPOZYCJA identyfikatora, nie zamrożone przypisanie —
stary roadmap nazywał T011 "Backend/Application E2E", ale ta cała
kolejność została zastąpiona `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md`,
która nie rozstrzyga, co (jeśli cokolwiek) ma wejść w miejsce T011.

## Fakt, który uzasadnia tę propozycję

Sprawdzone bezpośrednio w kodzie (`grep -rl "bootstrap_or_resume_coordinator_context" tests/`):
publiczne wejście aplikacyjne T010-A (`rota.application.bootstrap
.bootstrap_or_resume_coordinator_context`) jest wywoływane WYŁĄCZNIE we
własnych testach części A (`tests/test_t010_bootstrap_roster.py`,
`tests/test_audit_t010_r3.py`, `tests/test_audit_t010_r4_a.py`).

Każdy inny test w repo — łącznie z testem przekrojowym
`tests/test_audit_t010_r9_consistency.py`, który miał udowodnić spójność
A/B/C/D — zakłada kontekst (Coordinator/SiteProfile/Site/Association/
Employee/SiteMembership/CalendarDay) przez BEZPOŚREDNIE wywołania
`rota.persistence.*` (`save_coordinator`, `save_site_profile`,
`save_calendar_day` itd.), pomijając warstwę aplikacyjną, którą realnie
użyje przyszłe UI (T012).

Innymi słowy: żaden istniejący test nie dowodzi, że pełny łańcuch operacji
w kolejności, w jakiej faktycznie użyje go koordynator/UI — wyłącznie przez
publiczne funkcje `rota.application.*` — działa od pustej bazy do
gotowego, sfinalizowanego grafiku i z powrotem po restarcie.

## Dodatkowy fakt znaleziony przy tej okazji (CONTRACT_GAP, nie do
## rozstrzygnięcia przez CC)

`rota/application/durable_inputs.py` ma wrappery na Employee, SiteMembership,
target_hours, SiteProfile, ExternalSupportWindow i AvailabilityRecord — ale
ŻADEN publiczny moduł `rota.application.*` nie zapisuje `CalendarDay`.
`rota/application/assembler.py` i `rota/application/bootstrap.py` tylko
CZYTAJĄ `rota.persistence.calendar_repository` (`list_calendar_days`),
nigdy nie piszą. Każdy test w repo, który potrzebuje kalendarza, woła
`save_calendar_day` z warstwy persystencji wprost.

CC nie wie, czy to zamierzone (np. kalendarz ma docelowo pochodzić z
innego mechanizmu, nie od koordynatora) czy przeoczenie z T008/T009. Test
E2E poniżej to naturalnie ujawni — architekt/właściciel rozstrzyga, czy to
osobny finding do zamknięcia, czy świadomy brak na razie.

## Proponowany zakres: dokładnie dwa testy

### Test 1 — pełny happy path, zero warunków brzegowych

Jeden ciągły scenariusz, wyłącznie przez publiczne funkcje
`rota.application.*` (nie `rota.persistence.*`, poza jednym wyjątkiem
kalendarza opisanym wyżej, jeśli architekt zdecyduje, że to świadomy brak):

1. `bootstrap.bootstrap_or_resume_coordinator_context()` — Coordinator +
   SiteProfile + Site + Association, jednym lub kilkoma wywołaniami
   (dowód na "resume").
2. `durable_inputs.update_employee()` + `update_membership()` dla
   kilkuosobowej obsady LOCAL.
3. `durable_inputs.set_target_hours()` dla każdego.
4. `bootstrap.month_plan_readiness()` — musi zwrócić `ready=True` przed
   próbą PLAN (dowód, że odczyt gotowości faktycznie odzwierciedla to, co
   plan_month() zaraz zaakceptuje).
5. `plan_ops.plan_month()` — oczekiwany `FEASIBLE`.
6. `plan_ops.select_candidate()` — pierwszy `ScheduleVersion`.
7. `open_month.open_month()` — odczyt potwierdza bieżącą wersję i dane.
8. Jedna legalna ręczna korekta przez `manual_edit.apply_manual_correction()`
   lub `mark_not_worked()`.
9. `lifecycle_ops.revalidate()` → `lifecycle_ops.finalize()` z dokładnym
   zestawem potwierdzonych Deviation.
10. Zamknięcie połączenia i ponowne `connect()` do tego samego pliku —
    `open_month()` i `get_schedule_snapshot()` muszą zwrócić identyczny
    stan jak przed restartem.

Test NIE wprowadza żadnych błędów/kolizji — ma udowodnić, że sama
sekwencja "od zera do sfinalizowanego grafiku" przez publiczne API działa
bez żadnych skrótów przez warstwę persystencji.

### Test 2 — zatrzymanie na HARD i dwie legalne drogi dalej, żadnej trzeciej

Scenariusz, w którym `plan_month()` NIE jest w stanie osiągnąć `FEASIBLE`
z powodu realnej kolizji HARD (np. jedyny eligible pracownik na dany
demand ma aktywny `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` zakazujący
mu akurat tego dnia/rodzaju zmiany).

Ma udowodnić dokładnie trzy rzeczy, wszystkie już opisane w istniejącym
kontrakcie, ale nigdy nie połączone w jeden dowód:

1. **Silnik faktycznie się zatrzymuje, nie "przepycha" grafiku.**
   `plan_month()` zwraca `DECISION_REQUIRED` (nie `FEASIBLE` z ukrytym
   naruszeniem HARD); niezależny `validator.validate()` na ewentualnym
   kandydacie potwierdza `hard_pass=False`.
2. **Droga A — ręczny zapis.** Koordynator woła
   `manual_edit.apply_manual_correction()` z ręcznie dobranym Assignment.
   Jeśli to inny, faktycznie eligible pracownik — grafik przechodzi bez
   nowej Deviation. Jeśli koordynator uparcie zapisze coś, co nadal łamie
   ten sam HARD — walidacja materializuje Deviation (zapis się udaje, ale
   HARD pozostaje widoczny, nie znika po cichu).
3. **Droga B — jawna korekta reguły przez Decision Ledger.** Koordynator
   woła `rule_decisions.record_structured_rule_decision()` (`rel="corrects"`
   albo `"rejects"`) żeby faktycznie zmienić/wycofać blokującą
   `SiteRuleVersion` — to jest audytowana, historyczna decyzja, nie cichy
   bypass. Dopiero PO tej zmianie ponowne `plan_month()` zwraca `FEASIBLE`.

Test musi też wykazać, że NIE ISTNIEJE trzecia droga: nie ma żadnej opcji
"po prostu zignoruj ten HARD i zaplanuj i tak" bez jednej z powyższych
dwóch jawnych, opisanych w historii akcji koordynatora. To jest właściwy
przedmiot tego testu — nie sama mechanika PLAN, tylko dowód, że system nie
ma cichego wyłącznika bezpieczeństwa.

## Czego ten brief NIE rozstrzyga

- Dokładnego kształtu fixture/scenariusza (liczba pracowników, konkretny
  rule_kind użyty do zablokowania) — to szczegół implementacyjny.
- Czy CalendarDay dostaje wrapper aplikacyjny, czy zostaje świadomym
  wyjątkiem w Teście 1 — decyzja architekta/właściciela.
- Czy T011 to jeden plik testowy, czy dwa — nieistotne dla kontraktu.
- Czy to w ogóle powinno nazywać się "T011" — to najbliższy wolny numer
  w kolejności, nie decyzja.

## Źródła

- `rota/application/bootstrap.py`, `durable_inputs.py`, `plan_ops.py`,
  `manual_edit.py`, `lifecycle_ops.py`, `rule_decisions.py`,
  `open_month.py` — wszystkie funkcje cytowane powyżej istnieją dokładnie
  pod tymi nazwami, sprawdzone bezpośrednio w repo 2026-08-14.
- `tests/test_audit_t010_r9_consistency.py`, `tests/test_t010_bootstrap_roster.py`
  — dowód na brak istniejącego E2E przez samo API aplikacyjne.
