# ROTA-T010-B — jedna matryca dostępności pracownika

STATUS: DRAFT FOR CODEX AUDIT

Bazowo zwykły nowy pracownik ma ✓ dla: Ogólna dostępność, Dniówka, Nocka i Pon–Nd. `✓` zawsze znaczy „solver może”, `☐` zawsze znaczy „solver nie może” w obowiązującym okresie. `od–do` jest włączne, a po `do` wraca stan bazowy.

Dla czasowych zakazów reuse istniejącego `SiteRuleVersion` + `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`:
- Ogólna ☐ bez powodu: weekdays 1..7, forbidden D,N;
- D ☐: weekdays 1..7, forbidden D;
- N ☐: weekdays 1..7, forbidden N;
- dni tygodnia ☐: wskazane weekdays, forbidden D,N.

Choroba i udzielony urlop korzystają wyłącznie z istniejącego `AvailabilityRecord` (`SICK_LEAVE`, `LEAVE_GRANTED`), a zwykła znana wcześniej pełna niedostępność może użyć `UNAVAILABLE_24H`. Nie dublować tego SiteRule. `NN` nie jest preplanning availability.

`Employee.day_only` pozostaje bazowym źródłem Nocka ☐. Czasowe Nocka ✓ dla `day_only=true` podlega zamrożonemu `DAY-ONLY-TEMP-N-EXCEPTION-01` i nowemu rodzajowi `EMPLOYEE_DAY_ONLY_N_EXCEPTION`. Wyjątek uchyla tylko `DAY_ONLY-01` dla N tego pracownika/Site/dat. Nie uchyla membership, aktywności Employee, Availability, REST, LOAD, coverage ani innych HARD SiteRule. Wszystkie pozostałe HARD nadal łączą się przez AND. Eligibility i validator muszą być zgodne. Po `effective_to` `day_only` znów blokuje N.

## Edycja ograniczenia

Jedno zapisane ograniczenie/wyjątek ma jedną rodzinę reguły. Zmiana dat lub wcześniejsze przywrócenie ✓ tworzą kolejną decyzję w tej samej rodzinie; historia nie jest mutowana i stara wersja nie pozostaje równoległym aktywnym źródłem. Przywrócenie ✓ obowiązuje od jawnie podanej daty. Nowy niezależny okres może dostać nową rodzinę. Restart musi odtworzyć identyczną projekcję.

Dodać cienką projekcję application layer składającą Employee + AvailabilityRecord + SiteRuleVersion do bazowego stanu i datowanych zmian. Projekcja niczego nie zapisuje.

Testy: wszystkie bazowo ✓; Ogólna/D/N/Piątek ☐; SICK/LEAVE/UNAVAILABLE bez duplikacji; `day_only` + N ✓: dzień przed, obie granice, środek, dzień po, inny zakaz N, choroba/urlop, disabled membership, zgodność validator/eligibility; korekta od/do; wcześniejsze ✓; dwa niezależne okresy; restart.

FAIL za drugi stan dostępności, drugi `day_only`, ogólny override HARD, mutowanie historii albo nową rodzinę przy zwykłej edycji istniejącego ograniczenia.