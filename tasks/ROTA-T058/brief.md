# ROTA-T058 — HARD zakaz trzeciej kolejnej służby + 24h pasmo equity

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASE_MAIN_SHA: `298ddb9557455a574959876c38be1ebd7493319a`
SOURCE_FINDING: `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md` @ `c174c2e`

## 1. Cel

Naprawić priorytety solvera bez zmiany znaczenia TARGET-01:

1. każda trzecia kolejna służba tego samego pracownika na trzech kolejnych datach rozpoczęcia staje się bezwzględnym HARD;
2. ogólny rytm D/N/W/W pozostaje SOFT;
3. equity dostaje dopuszczalne pasmo 24h między pracownikami, wewnątrz którego solver nie ma psuć rytmu D/N/W/W tylko po to, aby dalej wyrównywać godziny;
4. istniejące TARGET-01 pozostaje bez zmian.

## 2. Zamrożony kontrakt OWNERA

### 2.1 Trzecia kolejna służba = HARD

Dla jednego pracownika każda sekwencja służb rozpoczynających się na trzech kolejnych datach kalendarzowych jest zabroniona.

Zakaz dotyczy wszystkich kombinacji rodzaju służby, nie tylko nocy. W szczególności obejmuje wzorce, które obecny T034 traktuje jako SOFT, np. D/D/D, D/D/N i D/N/N, oraz każde inne trzy kolejne daty rozpoczęcia z realną służbą pracownika.

Nie wolno tworzyć wyjątku przez `DECISION_REQUIRED`. Nie wolno zapisać, zaakceptować ani wyeksportować grafiku naruszającego ten zakaz.

Jeżeli bez naruszenia zakazu nie istnieje obsada spełniająca pozostałe HARD, PLAN/REPLAN/Przelicz Plan nie produkuje akceptowalnego grafiku. Koordynator dostaje czytelny komunikat, że trzeba zmienić obsadę lub dostępność i uruchomić planowanie ponownie.

Istniejący `NIGHT-STREAK-01` pozostaje własnym, węższym HARD dla nocy. T058 nie rozszerza jego ścieżki `DECISION_REQUIRED` na ogólny zakaz trzech kolejnych służb.

### 2.2 Granice miesiąca i fixed facts

Zakaz musi działać także przez granicę miesiąca. Służby już istniejące/fixed/boundary są faktami i uczestniczą w ocenie trzech kolejnych dat rozpoczęcia tak samo jak nowe zmienne solvera.

Jeżeli dwa wcześniejsze dni są już fixed i nowa służba trzeciego dnia tworzyłaby zabronioną sekwencję, solver musi jej zabronić. Nie wolno ignorować okna tylko dlatego, że jego część pochodzi z poprzedniej wersji/miesiąca.

### 2.3 Rytm D/N/W/W

Ogólny rytm D/N/W/W pozostaje SOFT. Nie staje się HARD i nie dostaje osobnego `DECISION_REQUIRED`.

Nowy HARD trzech kolejnych służb ma pierwszeństwo przed rytmem D/N/W/W nawet wtedy, gdy wymusza mniej estetyczny wzorzec.

### 2.4 TARGET-01

Nie zmieniać semantyki TARGET-01 ani jego obecnej dominacji nad zwykłymi SOFT. Minimalizacja sumarycznej odchyłki od target_hours pozostaje obowiązująca.

T058 nie zmienia sposobu liczenia target_hours, effective_targets ani fallbacku dla brakujących targetów.

### 2.5 Equity z pasmem 24h

Obecne equity nie może dalej wymuszać drobnego wyrównywania godzin kosztem rytmu D/N/W/W, jeśli różnica rzeczywistych godzin między pracownikami mieści się w 24h.

24h jest martwą strefą/tolerancją rankingu SOFT, a nie HARD:
- różnica <=24h nie generuje przewagi dla dalszego wyrównywania equity;
- różnica >24h może nadal wpływać na ranking rozwiązań;
- rozwiązanie z różnicą >24h jest nadal legalne, jeśli wynika z HARD/TARGET-01 i pozostałej struktury problemu.

Nie zamieniać tego w zakaz `max_hours - min_hours <= 24`.

Architekt preferuje jeden owner actual-hours/equity, bez drugiego równoległego liczenia godzin.

## 3. Wymagane zachowanie użytkowe

Scenariusz A — możliwy grafik:
- istnieje rozwiązanie bez trzech kolejnych służb;
- solver zwraca legalny wynik;
- żadna osoba nie ma służb na trzech kolejnych datach rozpoczęcia.

Scenariusz B — niemożliwy grafik:
- pełne pokrycie wymagałoby trzeciej kolejnej służby;
- solver nie zwraca akceptowalnego grafiku łamiącego zakaz;
- UI/API pokazuje czytelny komunikat o braku możliwości ułożenia bez naruszenia tego HARD;
- brak ścieżki zatwierdzenia wyjątku.

Scenariusz C — equity wewnątrz 24h:
- dwa legalne warianty mają tę samą jakość TARGET-01;
- jeden ma lepszy D/N/W/W, drugi tylko ciaśniejsze equity wewnątrz 24h;
- wariant z lepszym rytmem nie może przegrać wyłącznie przez dalsze wyrównanie equity wewnątrz tolerancji.

Scenariusz D — equity poza 24h:
- przy równej jakości wyższych priorytetów equity może preferować wariant zmniejszający różnicę >24h;
- nie jest to HARD i nie może unieważnić jedynego legalnego grafiku.

Scenariusz E — granica miesiąca:
- dwie fixed służby końca poprzedniego/obecnego zakresu + kandydat na trzeci kolejny dzień;
- kandydat jest zabroniony niezależnie od statusu/frozen/eligibility tych wcześniejszych faktów.

## 4. Zakaz rozszerzania zakresu

Poza T058:
- zmiana REST-01, LOAD-01, MEMBERSHIP-01;
- zmiana NIGHT-STREAK-01 poza niezbędnym współistnieniem z nowym szerszym HARD;
- zmiana TARGET-01 lub jego danych wejściowych;
- nowe ustawienie w Control Panel do wyłączania zakazu;
- wyjątek koordynatora/`DECISION_REQUIRED` dla trzech kolejnych służb;
- przebudowa całej funkcji celu;
- poprawki historycznych testów niezwiązane bezpośrednio z tym kontraktem;
- refaktoryzacje „przy okazji”.

## 5. PREIMPLEMENTATION WHERE_MAP — obowiązkowy Codex

Przed implementacją Codex ma wykonać wąski audyt i wskazać minimalne seamy oraz literalny `TASK_SCOPE`.

WHERE_MAP:
- MODE: REQUIRED
- IMPLEMENTATION: HOLD
- VERIFY:
  1. gdzie dokładnie powstaje jeden wspólny `day_kind_terms`/klasyfikacja realnej służby i jak obejmuje fixed/boundary facts;
  2. czy nowy HARD powinien być zbudowany w `constraints.py`, `solver.py` czy przez przeniesienie logiki z obecnego `add_third_consecutive_shift_penalty`;
  3. gdzie niezależny validator musi dostać ten sam kontrakt bez kopiowania drugiego klasyfikatora D/N;
  4. jak obecny engine mapuje INFEASIBLE bez `DECISION_REQUIRED` na czytelny komunikat i czy potrzebny jest mały, deterministyczny reason owner;
  5. gdzie najlepiej wprowadzić 24h deadband equity przy zachowaniu jednego ownera actual-hours i bez zmiany TARGET-01;
  6. które istniejące testy T034/T032/NIGHT-STREAK/fairness trzeba zmienić lub zachować i jakie nowe testy są konieczne;
  7. czy jakikolwiek plik poza proponowanym minimalnym zestawem jest rzeczywiście wymagany.

Codex ma zwrócić PASS/FAIL preimplementation oraz proponowany literalny TASK_SCOPE. Nie projektować nowego subsystemu.

## 6. Acceptance do późniejszej implementacji

T58-01: żadna zaakceptowana propozycja solvera nie zawiera trzech służb tego samego pracownika na trzech kolejnych datach rozpoczęcia.

T58-02: zakaz działa dla kombinacji D/N oraz innych realnych służb klasyfikowanych przez istniejącego ownera, a nie tylko dla trzech nocy.

T58-03: zakaz działa przez granicę miesiąca i wobec fixed/boundary facts.

T58-04: brak legalnej obsady nie prowadzi do wyjątku `DECISION_REQUIRED`; użytkownik dostaje czytelny komunikat i brak akceptowalnego grafiku.

T58-05: NIGHT-STREAK-01 pozostaje poprawne i nie jest osłabione.

T58-06: D/N/W/W pozostaje SOFT.

T58-07: TARGET-01 zachowuje dotychczasową semantykę i priorytet.

T58-08: equity nie daje dodatkowej korzyści za zmniejszanie różnicy godzin, jeśli wynikowa różnica między porównywanymi pracownikami mieści się w 24h tolerancji.

T58-09: różnica >24h pozostaje legalna; equity może ją preferencyjnie zmniejszać tylko jako SOFT.

T58-10: solver i validator zgadzają się co do nowego HARD na reprezentatywnych scenariuszach, bez wspólnego błędnego drugiego klasyfikatora.

T58-11: brak nowego ustawienia/wyjątku pozwalającego ominąć zakaz.

## 7. TASK_SCOPE

Nie jest jeszcze zamrożony. Implementacja HOLD do preimplementation PASS Codexa i dopisania literalnego `TASK_SCOPE` przez Architekta.

READ_ONLY_EVIDENCE:
- `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md`
- `BOARD.md`
