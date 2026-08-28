# CODEX REVIEW R4 — ZAKRES AUDYTU OPARTY NA DOWODACH

**Reviewed branch:** `docs/audit-1-baseline-brief`  
**Reviewed exact SHA:** `60a0012542b852bb21e802785b0535bfaf3a7dce`  
**PR #9 source:** `f2eba6ce97d19d03fbef3c7bd4fe3c417ff55a05`  
**Reviewer:** Codex, independent tester/auditor  
**Status:** `WYMAGA JEDNEJ KONSOLIDACJI BRIEFU PRZED WYKONANIEM`

## 1. Co w komentarzu CC jest trafne

- Warstwa C musi mieć jawny, skończony zakres.
- Priorytet ma wynikać z reprodukowanego incydentu, nie wyłącznie z etykiety
  MUST/USEFUL/SUSPECT w PR #9.
- Pełne pionowe wykonanie Warstwy B ma realny koszt CP-SAT i ten koszt należy
  jawnie raportować.
- Autor kodu nie powinien sam klasyfikować własnych warstw jako potrzebnych.

## 2. Rozdzielenie Warstwy C od Warstwy D

Propozycja „wszystkie pozycje SUSPECT w pierwszej Warstwie C” nadal jest za
szeroka i dubluje Warstwę D.

- **Warstwa C** rozlicza konkretne, odtwarzalne incydenty: TRACE, ENTRYPOINT,
  REPRO, USER EFFECT, OWNER i CLASS.
- **Warstwa D** wykonuje strukturalny remanent wszystkich pozycji SUSPECT:
  reachability, konsumenci, ownership, duplikacja i koszt odpowiedzialności.

Pozycja SUSPECT bez odtwarzalnego incydentu nie potrzebuje sztucznego REPRO w
Warstwie C. Jeżeli Warstwa D ujawni konkretny błąd, wtedy powstaje nowy wiersz
Warstwy C z dowodem, nie wcześniej.

## 3. Pierwszy, zamknięty zakres Warstwy C

Na podstawie dowodów istnieją dziś cztery odrębne incydenty:

### C-01 — H24 fałszywie niewykonalne

- wejście: zwykły obiekt H24, pięciu LOCAL, wrzesień 2026;
- objaw: PLAN zwraca DECISION_REQUIRED mimo istniejącego HARD-valid świadka;
- potwierdzona przyczyna: `fairness.add_dn_rhythm_reward()` używa licznika
  occupancy `2*x` jak Boolean i tworzy przypadkowy zakaz HARD;
- mylące etykiety NIGHT-STREAK-01/REST-01 są skutkiem tego samego UNSAT, nie
  osobnym incydentem do podwójnego policzenia.

### C-02 — SICK_LEAVE znane przed pierwszym PLAN kończy jako HTTP 500

- potwierdzony pionowy reproduktor istnieje w
  `ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md`;
- incydent należy rozliczyć, ale nie wolno z góry uznać go za dowód przerostu
  `absence_reference_repository.py`. Może oznaczać defekt, brak kontraktu lub
  konieczną złożoność; CLASS wynika dopiero z TRACE/ownership.

### C-03 — legalne nakładające się demandy dają fałszywy COVERAGE-01 excess

- generator katalogu jawnie dopuszcza niezależne nakładające się occurrence;
- validator liczy geometryczne nakładanie assignmentów dla każdego demandu;
- T039 odtworzył fałszywy nadmiar. To osobny incydent validatora/kontraktu
  coverage, niezwiązany z C-01.

### C-04 — zapis katalogu po utworzeniu WORKING nie odświeża readbacku

- potwierdzone na produkcyjnym przepływie i wydzielone w
  `ARCHITECT_BRIEF_SHIFT_CATALOG_STALE_WORKING_VERSION_2026-08-28.md`;
- PLAN liczy na świeżym stanie w pamięci, ale bieżąca wersja nadal odczytuje
  stare persisted demands;
- oczekiwane zachowanie wymaga OWNER_DECISION, ale sam rozjazd read/write jest
  odrębnym, udokumentowanym incydentem i nie może zniknąć z kolejki.

To jest cały pierwszy zakres Warstwy C. Pozostałe pozycje SUSPECT z PR #9
wchodzą do Warstwy D, nie do C.

## 4. Warstwa B — koszt kontrolowany, bez obniżenia dowodu

Jedenaście CM0/CM1 należy wykonać pionowo, ale wolno podzielić je na jawne
partie i zapisywać wynik po każdej partii. Każdy scenariusz nadal wymaga
produkcyjnego entry pointu i właściwego readback/validate; czas wykonania nie
jest powodem, aby zastąpić go wyszukaniem testu o podobnej nazwie.

Nieudany scenariusz zapisuje się i przechodzi do następnego. Brak pokrycia nie
uruchamia automatycznie pisania testu lub poprawki.

## 5. Baseline H24 musi pozostać FAIL na swoim exact SHA

AUDIT-1 deklaruje baseline na main sprzed T040. Jeżeli scenariusz 11 zostanie
wykonany na tym exact SHA, oczekiwanym zebranym faktem jest obecny FAIL/
DECISION_REQUIRED. Późniejsze zamknięcie i merge T040 nie może retrospektywnie
zmienić wyniku baseline'u.

Po T040 wolno wykonać osobne porównanie before/after, ale nie wolno uruchomić
AUDIT-1 na nowszym kodzie i nadal opisać go starym BASE_SHA.

## 6. Pozostały blocker mechaniczny

Pierwotny brief wciąż zawiera nieistniejący pełny SHA
`d445ee6244e4e43f504ef44b9b5a290f05a21b7`. Rzeczywisty base main to
`d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`. Finding A1-R2-01 pozostaje
otwarty do mechanicznej korekty.

## 7. Wymagana konsolidacja

Nie potrzeba kolejnej rundy projektowania. Należy raz mechanicznie przepisać
brief wykonawczy tak, aby zawierał:

1. poprawny istniejący BASE_SHA;
2. Warstwę A jako baseline, nie werdykt produktu;
3. Warstwę B: 11 pionowych scenariuszy, wykonywanych partiami;
4. Warstwę C: dokładnie C-01..C-04 powyżej;
5. Warstwę D: wszystkie SUSPECT z PR #9 jako reachability/ownership inventory;
6. Warstwę E: plan redukcji bez zmian kodu;
7. zero napraw, nowych testów i refaktoryzacji w trakcie zbierania dowodów.

Po tej konsolidacji brief może przejść do wykonania bez kolejnej rundy
architektonicznej, o ile nie pojawi się nowe zachowanie widoczne dla
właściciela.
