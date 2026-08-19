# Handoff brief for architect: solver returns multiple schedule variants (T017)

## Status

**OWNER DECISIONS CLOSED — READY FOR ARCHITECT CONTRACT.**

Pierwotny brief był czysto faktograficzny i pozostawiał otwartą liczbę wariantów, zachowanie przy 1–2 wariantach oraz techniczną definicję progu 15%. Właściciel domknął brakujące decyzje 2026-08-19.

Aktualna baza architektoniczna: `main` po T013, exact SHA `d1a0ec0438718b1b7fd91e5c146e67b58c4eb4f9`.

## Skąd to zadanie

Właściciel (Paweł), przy okazji pytania „co się dzieje, jeśli koordynatorowi nie spodoba się wynik PLAN” (2026-08-16), przypomniał wcześniejszy kierunek: solver ma przedstawiać **kilka wariantów** poprawnego grafiku do wyboru, nie jeden.

W referencyjnej, niezamrożonej specyfikacji v0.19 było: solver może zwrócić do 3 pełnych propozycji spełniających HARD; koordynator wybiera ostateczny wariant. Frozen v0.4 i `arch/spec.md` nie zamroziły tej funkcji, dlatego wymaga osobnego addendum.

## Stan techniczny przed T017

`PlanningResult.candidates` jest już `list[list[Assignment]]`, więc publiczny wynik planowania ma strukturę zdolną przenieść kilka pełnych grafików. Obecny engine na FEASIBLE wypełnia tę listę dokładnie jednym kandydatem.

Warstwa aplikacyjna już ma `select_candidate(...)`, które przyjmuje konkretną listę Assignment i zapisuje wybór koordynatora. T017 nie potrzebuje automatycznego wyboru ani nowego lifecycle.

Solver pozostaje deterministyczny (`num_search_workers = 1`, `random_seed = 0`); przed T017 ponowne PLAN na tym samym wejściu zwracało ten sam pojedynczy wynik.

## DECYZJA WŁAŚCICIELA — minimalna różnica wariantów (2026-08-16)

Każdy kolejny grafik przedstawiany jako odrębny wariant musi różnić się o **co najmniej 15% rzeczywistej obsady**.

15% jest minimalnym progiem odrębności, nie celem optymalizacyjnym.

Różnicy nie wolno uzyskiwać przez zmianę technicznych identyfikatorów Assignment, kolejności elementów listy ani innych danych, które nie zmieniają rzeczywistej obsady widzianej przez koordynatora.

Architekt ma zdefiniować mechaniczną metrykę, mianownik i zaokrąglenie tak, aby próg był jednoznaczny i testowalny.

## DECYZJA WŁAŚCICIELA — liczba wariantów i brak pełnej trójki (2026-08-19)

1. Solver zwraca **do 3** pełnych, poprawnych wariantów grafiku.
2. Jeżeli istnieje tylko **1** wariant spełniający wszystkie obowiązujące wymagania i próg odrębności, `FEASIBLE` zwraca 1 kandydat.
3. Jeżeli istnieją tylko **2**, `FEASIBLE` zwraca 2 kandydatów.
4. Brak drugiego albo trzeciego wariantu **nie jest** sam w sobie `DECISION_REQUIRED` ani `TECHNICAL_ERROR`.
5. Jeżeli istnieją co najmniej 3 kwalifikujące się warianty, zwracane są maksymalnie 3.
6. Każdy zwracany element `PlanningResult.candidates` jest kompletnym grafikiem i niezależnie spełnia HARD.
7. Program nie wybiera wariantu za koordynatora. `select_candidate(...)` pozostaje świadomym wyborem konkretnego kandydata.

## GRANICE ZAMROŻONYCH WCZEŚNIEJ KONTRAKTÓW

T017 nie może osłabić ani przeorganizować istniejących priorytetów i fallbacków:

- T006 / REPLAN-MIN-01: minimum reshuffle pozostaje pierwszym priorytetem leksykograficznym w REPLAN.
- T018: normal capped -> DAY_ONLY fallback capped -> DAY_ONLY + emergency 24h capped -> uncapped LOAD diagnosis pozostaje literalną kolejnością.
- T018: minimum `exceptional_n_count` pozostaje przed TARGET/fairness.
- T012: emergency 24h i jego provenance pozostają bez zmian.
- T013: końcowy DECISION_REQUIRED pozostaje komunikacją po wyczerpaniu automatycznych prób; T017 nie tworzy wariantów DECISION_REQUIRED.
- TARGET/fairness/pozostałe SOFT nadal wyłącznie rankują legalne rozwiązania i nie mogą naruszać HARD.

## OTWARTE WYŁĄCZNIE TECHNICZNIE — NALEŻĄ DO ARCHITEKTA

Po decyzji właściciela nie ma już otwartego pytania produktowego o liczbę kandydatów ani o status przy 1–2 wariantach.

Architekt wybiera i zamraża:
- jednostkę porównania i mianownik progu 15%;
- zasadę zaokrąglania;
- czy próg jest sprawdzany względem wszystkich wcześniejszych wariantów;
- mechanikę CP-SAT wykluczającą warianty zbyt podobne;
- zachowanie istniejących leksykograficznych minimów podczas szukania wariantów;
- deterministyczną kolejność kandydatów;
- budżet obliczeniowy dla dodatkowych wariantów;
- techniczne skojarzenie istniejących warningów z kandydatem bez tworzenia nowego subsystemu persistence.

Te wybory nie mogą zmienić decyzji właściciela: maksymalnie 3, minimum 15% realnej różnicy i 1–2 kwalifikujące się warianty są poprawnym `FEASIBLE`, nie błędem.
