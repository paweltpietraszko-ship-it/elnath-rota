# ELNATH ROTA — REGRESSION ORACLE ROTA-REG-001
Status: CANDIDATE DO WŁĄCZENIA DO SUITY TESTÓW
Data: 2026-08-10

## Cel

ROTA-REG-001 zamraża wynik rzeczywiście uruchomionego proof-of-concept OR-Tools CP-SAT dla października 2026.

Test ma wykryć sytuację, w której implementacja produkcyjna Claude Code zmienia semantykę solvera lub błędnie mapuje Frozen Product Contract.

## Wejście

Kanoniczne dane wejściowe znajdują się w:
`ELNATH_ROTA_REGRESSION_ROTA_REG_001.json`

Najważniejsze warunki:
- 5 pracowników A–E;
- codziennie dokładnie 1 D i 1 N;
- C = DAY_ONLY;
- A = DAY_SHIFT_OFF 6, 17, 26;
- B = LEAVE_GRANTED 12–18;
- D = UNAVAILABLE_24H 9, 23, 24;
- brak aktywnego ExternalSupportWindow dla X/Y;
- minimum odpoczynku = 11 h;
- >60 h w dowolnym ruchomym oknie 7 dni nie może być zwykłym FEASIBLE;
- S 8 października wymaga A jako PRIMARY D;
- target_hours: A 156, B 144, C 156, D 144, E 144.

## Zweryfikowany wynik referencyjny

Rzeczywiste uruchomienie minimalnego PoC na Windows:
- CP-SAT: `OPTIMAL`;
- niezależny validator: `HARD PASS`;
- minimum odpoczynku w znalezionym rozwiązaniu: 12 h;
- maksimum ruchomego obciążenia 7 dni: 60 h;
- godziny miesięczne:
  - A 156 h;
  - B 144 h;
  - C 156 h;
  - D 144 h;
  - E 144 h.
- dopuszczalne ostrzeżenie SOFT: poprzednia N A może wejść do 05:00 w dzień DAY_SHIFT_OFF.

## Oracle regresyjny

Implementacja produkcyjna przechodzi ROTA-REG-001 tylko wtedy, gdy:

1. zwraca kompletny grafik pokrywający 100% D/N;
2. wynik solvera jest sukcesem (`OPTIMAL` albo produktowo zaakceptowany odpowiednik pełnego `FEASIBLE`);
3. niezależny validator zwraca `HARD PASS`;
4. żaden Assignment nie narusza DAY_ONLY, DAY_SHIFT_OFF, LEAVE_GRANTED, UNAVAILABLE_24H, REST-01, EXTERNAL-01 ani LOAD-01;
5. A jest PRIMARY D 8 października dla zaplanowanego S;
6. każde ruchome okno 7 kolejnych dni ma <=60 h na pracownika;
7. miesięczne godziny wynoszą dokładnie:
   A=156, B=144, C=156, D=144, E=144.

## Co jest regresją

Regresją jest w szczególności:
- `INFEASIBLE`;
- `DECISION_REQUIRED`;
- `UNKNOWN` po normalnym limicie testowym;
- `TECHNICAL_ERROR`;
- częściowy grafik;
- jakikolwiek `HARD FAIL`;
- użycie X/Y;
- przekroczenie 60 h / 7 dni;
- odpoczynek <11 h;
- przypisanie B kolidujące z LEAVE_GRANTED;
- przypisanie D kolidujące z UNAVAILABLE_24H;
- N dla C;
- rozpoczęcie D lub N przez A w DAY_SHIFT_OFF;
- brak A jako PRIMARY D 8 października;
- inne sumy godzin niż wynik referencyjny, dopóki target_hours pozostają częścią tego samego objective/kontraktu.

## Co NIE jest regresją

Nie jest regresją:
- inny konkretny układ osób w dniach, jeżeli wszystkie powyższe warunki są spełnione;
- inna kolejność równorzędnych kandydatów;
- inna treść komunikatu dla użytkownika, jeżeli jego semantyka/status są zgodne z kontraktem;
- wystąpienie dopuszczalnego ostrzeżenia SOFT dotyczącego N kończącej się o 05:00 w DAY_SHIFT_OFF.

## Reguła dla CC

CC nie może zmienić oczekiwanego wyniku tego testu po to, aby dopasować test do nowej implementacji.

Jeżeli ROTA-REG-001 FAIL:
1. najpierw zakładamy regresję implementacji lub mapowania kontraktu;
2. poprawiamy kod;
3. zmiana oracle/fixture jest dozwolona wyłącznie po wcześniejszej jawnej zmianie Frozen Product Contract przez właściciela.

Test ma być uruchamiany co najmniej:
- po zmianie modelu CP-SAT;
- po zmianie constraints;
- po zmianie PlanningState;
- po zmianie mapowania solver -> PlanningResult;
- przed zaakceptowaniem audytowanego SHA.
