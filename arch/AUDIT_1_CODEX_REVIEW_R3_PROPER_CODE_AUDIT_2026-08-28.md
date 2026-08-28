# CODEX REVIEW R3 — JAK PRAWIDŁOWO ZAUDYTOWAĆ KOD

**Branch:** `docs/audit-1-baseline-brief`  
**Autor oceny:** Codex, independent tester/auditor  
**Status:** korekta wcześniejszej oceny zakresu AUDIT-1

## 1. Korekta stanowiska Codexa

W rundach 1–2 Codex prawidłowo ograniczył CC do mechanicznego zbierania
dowodów i wykrył błędny exact SHA, ale zbyt łatwo zaakceptował tezę, że
pełny pytest i dwa istniejące benchmarki stanowią właściwą treść AUDIT-1.

Po uwadze właściciela Codex wykonał zbyt szybkie wahnięcie w przeciwną
stronę, sugerując niemal odrzucenie baseline'u. To również byłoby błędne.

Prawidłowa granica:

- pełny pytest jest potrzebną siatką regresji i fotografią stanu;
- nie jest dowodem poprawności zachowania aplikacji;
- istniejące benchmarki są tylko dowodem pomocniczym, dopóki ich wejścia i
  oracle nie zostaną porównane z PRODUCT_TRUTH;
- główną treścią audytu musi być niezależna weryfikacja działania oraz
  konkretnych findings z PR #9.

## 2. Pytania, na które audyt ma odpowiedzieć

1. Które zatwierdzone czynności koordynatora działają pionowo przez
   produkcyjny łańcuch?
2. Które konkretne findings z PR #9 są odtwarzalne i jaki mają skutek dla
   użytkownika?
3. Który kod jest osiągalny z UI/API/application entry points?
4. Które warstwy są jedynym właścicielem odpowiedzialności, a które ją
   powielają?
5. Który kod można usunąć lub scalić bez zmiany PRODUCT_TRUTH, bezpieczeństwa,
   recovery i audytowalności?

Liczba zielonych testów nie odpowiada na żadne z tych pytań samodzielnie.

## 3. Warstwa A — mechaniczny baseline, tylko raz

Na jednym istniejącym exact SHA zebrać:

- pełny pytest;
- status istniejących benchmarków;
- czas, komendy, środowisko i surowe wyniki;
- aktualne produkcyjne entry points i stan drzewa.

Wynik tej warstwy nie otrzymuje werdyktu „program poprawny”. Oznacza tylko:
„tak zachowuje się obecna siatka testowa przed zmianami”. Benchmark FAIL/PASS
jest wynikiem benchmarku, nie PRODUCT_TRUTH.

## 4. Warstwa B — pionowy audyt zachowania produktu

Każdy zaakceptowany scenariusz CM0/CM1 należy rzeczywiście wykonać przez
odpowiedni produkcyjny łańcuch, nie tylko odnaleźć test o podobnej nazwie:

`durable input/API -> assembler -> PLAN/REPLAN -> validate -> select ->
reopen/export/readback`, w zakresie właściwym dla danego scenariusza.

Dla każdego scenariusza zapisać:

- dokładne wejścia koordynatora;
- źródło oczekiwania w spec/task/OWNER ruling;
- produkcyjny entry point;
- rzeczywisty status i kandydat/decision payload;
- wynik niezależnego validate/readback;
- komendę i minimalny reproduktor.

Istniejący test wolno uznać za pokrycie dopiero po przeczytaniu jego asercji
i potwierdzeniu, że nie omija produkcyjnego właściciela. Brak pokrycia jest
wynikiem `BRAK`; nie uruchamia automatycznie pisania kolejnego testu.

## 5. Warstwa C — rozliczenie PR #9 finding po findingu

PR #9 jest listą hipotez do niezależnego sprawdzenia, nie materiałem do
zastąpienia kolejnym zestawem ogólnych testów. Dla każdego findingu powinna
powstać jedna pozycja:

| Pole | Wymagany dowód |
|---|---|
| CLAIM | dokładne twierdzenie z PR #9 |
| TRACE | spec/task/OWNER ruling albo brak źródła |
| ENTRYPOINT | UI/API/application path, z którego kod może zostać użyty |
| REACHABILITY | konkretna ścieżka wywołań/importów; test-only nie wystarcza |
| REPRO | minimalny efekt na exact SHA |
| USER EFFECT | co widzi lub czego nie może zrobić koordynator |
| OWNER | moduł, który posiada odpowiedzialność |
| CLASS | KEEP / DUPLICATE / DEAD / DEFECT / OWNER_DECISION |

Bez TRACE, ownership i reprodukcji nie wolno zmieniać kodu na podstawie
samej opinii o jego wyglądzie.

## 6. Warstwa D — audyt odpowiedzialności i rozdęcia

Dla podejrzanych modułów, endpointów, helperów, pól response i stanów UI
ustalić:

- kto jest jedynym właścicielem reguły;
- ilu ma konsumentów produkcyjnych;
- czy istnieje równoległa implementacja tej samej decyzji;
- czy kod służy wyłącznie testom/benchmarkowi;
- czy usunięcie naruszyłoby safety, recovery, auditability lub zapobieganie
  błędom.

Klasyfikacja:

- `KEEP` — konieczne do zatwierdzonego zachowania lub ochrony;
- `DUPLICATE` — odpowiedzialność ma już innego właściciela;
- `DEAD` — brak produkcyjnej ścieżki i trwałego kontraktu;
- `TEST_ONLY` — używane tylko przez test/benchmark, wymaga osobnej oceny;
- `DEFECT` — odtwarzalnie szkodzi zachowaniu;
- `OWNER_DECISION` — usunięcie zmieniłoby widoczne zachowanie.

Zielony test nie zmienia kodu DEAD w KEEP. Może jedynie pokazywać, że test
broni martwego lub historycznego szczegółu implementacji.

## 7. Warstwa E — plan redukcji, nadal bez zmian w kodzie

Dopiero po warstwach B–D przygotować kolejność małych zmian:

1. kod DEAD bez konsumentów i bez kontraktu;
2. duplikaty, gdy wskazano jednego istniejącego właściciela;
3. nieużywane response fields/endpoints/UI state;
4. zbędne testy source-shape/historyczne po usunięciu ich przedmiotu;
5. większe połączenia odpowiedzialności wyłącznie po decyzji właściciela.

Każda porcja redukcji musi mieć:

- dokładny zakres plików;
- zachowanie, które ma pozostać identyczne;
- jeden lub kilka pionowych reproduktorów przed/po;
- pełną regresję jako końcową siatkę, nie jako dowód architektury;
- brak jednoczesnego dodawania funkcji produktowych.

## 8. Podział ról

- CC może mechanicznie zebrać surowe wyniki i kandydatów wywołań.
- Codex niezależnie sprawdza TRACE, reachability, reprodukcję i klasyfikację.
- Architekt proponuje docelową granicę ownership dopiero na podstawie
  potwierdzonych faktów.
- Właściciel rozstrzyga każdą zmianę widocznego zachowania.

Autor kodu nie klasyfikuje sam własnych warstw jako potrzebnych. Audytor nie
tworzy nowych wymagań ani nie zamienia preferencji architektonicznej w FAIL.

## 9. Wniosek dla obecnego briefu AUDIT-1

Obecny mechaniczny baseline może zostać zachowany jako **Warstwa A**, ale nie
może zamknąć AUDIT-1 ani zastąpić rozliczenia PR #9. Właściwy audyt kodu musi
obejmować warstwy B–D przed jakąkolwiek decyzją o kolejnym klejeniu lub
refaktoryzacji. Warstwa E jest osobnym wynikiem decyzyjnym, nie implementacją.

To podejście nie odrzuca istniejących testów i nie ufa im bezwarunkowo. Używa
ich jako siatki regresji, a prawdę o produkcie sprawdza pionowo i rozlicza kod
na podstawie produkcyjnej osiągalności oraz jednoznacznego ownership.
