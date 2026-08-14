# ROTA-T010-D — NN

STATUS: DRAFT FOR CODEX AUDIT

`NN` dotyczy wyłącznie jednej konkretnej, wcześniej zaplanowanej zmiany PRIMARY, której pracownik nie wykonał. Nie jest Availability ani SiteRule.

## Trwała reprezentacja

Najmniejsze rozszerzenie obecnego modelu: `Assignment` dostaje opcjonalne pole `operational_code`; w T010 jedyną dozwoloną wartością jest `NN`.

Przy oznaczeniu NN:
- wcześniejsza ScheduleVersion pozostaje bez zmian i zachowuje pierwotny `PLANNED`;
- child powstaje przez istniejące `apply_manual_correction()`;
- ten sam Assignment w child ma `state=CANCELLED` i `operational_code="NN"`;
- zachowuje identyfikator pracownika, interval i powiązanie z demandem potrzebne do historii/wyświetlenia;
- nie powstaje sztuczny `REALIZED`.

Persistence i odczyt ScheduleVersion muszą zachować `operational_code` po restarcie. Nie tworzyć osobnej tabeli NN ani HR-event.

## Godziny

Assignment `CANCELLED + NN` nie wchodzi ani do `planned_hours`, ani do `realized_hours`.

Przykład akceptacyjny bez innych zmian stanu: 14 `PLANNED` zmian po 12 h daje `planned_hours=168`, `realized_hours=0`. Po NN jednej zmiany bieżący child ma `planned_hours=156`, `realized_hours=0`; suma `planned_hours + realized_hours` wynosi 156. Nie dodajemy pola `effective_hours`.

W stanie mieszanym NN zawsze wnosi 0 do obu pól; suma planned+realized spada o czas niewykonanej zmiany względem tego samego snapshotu bez NN.

## Coverage i zastępstwo

Demand nie znika. Child przechodzi zwykłą niezależną walidację manualnej korekty:
- NN bez zastępstwa pozostawia niepokryty demand i istniejący mechanizm materializuje `COVERAGE` Deviation;
- jeżeli koordynator ręcznie zapisze rzeczywiste zastępstwo/split coverage, coverage jest oceniane normalnie na podstawie faktycznych Assignmentów;
- brak automatycznego REPLAN.

Testy: NN bez zastępstwa; NN z ręcznym zastępstwem; restart; wcześniejsza wersja bez zmian; 168→156 na polach WorkBalance; brak AvailabilityRecord/SiteRule; brak automatycznego REPLAN.