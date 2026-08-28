# CODEX REVIEW — EMPLOYEE OMITTED FROM FAIRNESS OBJECTIVE

**Reviewed branch:** `docs/worker-omitted-from-fairness-objective`  
**Reviewed exact SHA:** `e4c73a511733a6b7f81ccd3187f3ccfacb5cbdbe`  
**Reviewer:** Codex, independent tester/auditor  
**Status:** `WYMAGA JEDNEJ KOREKTY FAKTÓW PRZED ARCHITEKTEM`

## 1. Co jest potwierdzone

Główny łańcuch techniczny jest prawdziwy:

- `assembler._assemble_work_balances()` pomija pracownika bez targetu dla
  planowanego miesiąca i tworzy ostrzeżenie (`assembler.py:138-149`);
- `_effective_targets()` buduje słownik wyłącznie ze
  `state.work_balances` (`solver.py:410-419`);
- `_worked_hours_by_employee()` oraz TARGET-01 i target equity iterują po
  tym słowniku (`solver.py:440-521`);
- taki pracownik pozostaje eligible do coverage, ale nie uczestniczy w
  targetowym celu ani target equity.

Reprodukcja 168/168/168/168/48 jest więc wiarygodnym, konkretnym skutkiem
istniejącej granicy. Zasadnie wymaga pracy architekta, ponieważ nie wolno
zgadywać brakującego `target_hours`, a jednocześnie właściciel wymaga
domyślnego uczciwego podziału także po pominięciu targetu.

## 2. Co w briefie jest nieprawdziwe

Nie jest prawdą, że ostrzeżenie jest „architektonicznie gwarantowane do
zgubienia” i że koordynator ma „zero szans” je zobaczyć.

- Wywołania w `plan_ops.py` rzeczywiście odrzucają drugi wynik assemblera
  (`plan_ops.py:134-148, 308, 374-375, 426, 449`). Dlatego ostrzeżenie nie
  trafia do `PlanningResult.warnings` z tych operacji.
- Jednak `open_month()` zachowuje ostrzeżenia w `OpenMonthView.warnings`
  (`open_month.py:49-58`).
- Endpoint miesiąca przekazuje je w `MonthViewOut.warnings`
  (`api/routers/schedule.py:240-255`).
- Ekran Planowania miesiąca wyświetla je w widocznym bannerze „Uwaga”
  (`frontend/src/screens/MonthlyPlanning.tsx:528-543`).

Brief musi więc odróżnić dwa fakty:

1. ostrzeżenie nie jest dołączane bezpośrednio do odpowiedzi PLAN/REPLAN;
2. to samo ostrzeżenie jest już osiągalne i wyświetlane przez osobny odczyt
   miesiąca używany na tym ekranie.

Drugi fakt obala obecne uzasadnienie „braku jakiegokolwiek sygnału”, choć
nie usuwa problemu słabego UX ani niesprawiedliwego wyniku.

## 3. To nie jest nowa przyczyna kodowa

`tasks/ROTA-T011-D/brief.md` już wprost dokumentuje, że brak targetu w
planowanym miesiącu usuwa pracownika z `state.work_balances`, a przez to z
TARGET-01. Ten sam dokument zachował to zachowanie poza zakresem T011-D.

Nowym dowodem są:

- rzeczywisty skutek 48 godzin przy 168 godzinach pozostałych osób;
- potwierdzenie, że trzy różne kandydaty zachowują ten sam zły bilans;
- wykazanie, że samo zwiększanie wagi equity nic nie zmienia;
- konflikt tego skutku z późniejszym wymaganiem właściciela dotyczącym
  domyślnego uczciwego podziału.

Brief powinien być przedstawiony architektowi jako **znana degradacja,
której realny skutek okazał się nieakceptowalny**, a nie jako wcześniej
nieznany mechanizm.

## 4. Właściwe pytanie dla architekta

Architekt ma zachować jednocześnie istniejące decyzje właściciela:

- brak targetu nie blokuje PLAN;
- program nie zgaduje ani nie tworzy brakującego targetu;
- target pozostaje SOFT;
- wynik może zostać pokazany i użyty;
- podział godzin ma pozostać domyślnie uczciwy także wtedy, gdy
  koordynator zapomniał targetu.

Do zaprojektowania pozostaje najmniejszy sposób objęcia każdego eligible
LOCAL jakimś target-independent sygnałem sprawiedliwości bez syntetyzowania
targetu. Ewentualne przeniesienie assembler warnings również do
`PlanningResult.warnings` jest osobnym pytaniem spójności UX, nie naprawą
przyczyny nierównego przydziału.

## 5. Konkluzja

Brief może i powinien trafić do architekta po jednej mechanicznej korekcie
sekcji 3-5:

1. usunąć twierdzenie, że wszystkie produkcyjne ścieżki gubią ostrzeżenie;
2. opisać istniejący banner miesiąca oraz węższą lukę PLAN/REPLAN;
3. wskazać T011-D jako wcześniejsze źródło znanej degradacji;
4. pozostawić realny wynik 168/168/168/168/48 jako główny dowód potrzeby
   zmiany.

Nie potrzeba kolejnego badania `rota_dev.db`, poprawki produktu ani nowego
testu przed przekazaniem skorygowanego dokumentu architektowi.
