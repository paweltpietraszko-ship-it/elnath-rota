# Odpowiedź Codexa — SHIFT-24-PAIR-01 w Wariancie B

Status: **POTWIERDZONY DEFEKT PRODUKTU — do małego briefu naprawczego**

Data: 2026-08-31
Audytowany materiał: `docs/variant-b-shift24-pair-finding@f281f83`

## Wniosek

Symulator nie jest tu winny. Nie należy dodawać do niego filtra zabraniającego
nakładających się zmian. Produkt wprost dopuszcza wiele niezależnych,
nakładających się wpisów katalogu (`rota/planning/shift_catalog.py:246-251`),
a Wariant B ma odtwarzać ustawienia koordynatora, nie poprawiać ich przed
przekazaniem do produktu.

Solver ma już twarde ograniczenie wymagające tej samej osoby na obu połówkach
normalnej zmiany 24 h. Wywołuje je w `rota/planning/solver.py:964`, a właściwe
równanie znajduje się w `rota/planning/constraints.py:496-544`. Hipoteza, że
solver w ogóle nie pilnuje tej reguły, jest więc obalona.

Defekt znajduje się w niezależnym walidatorze. Przy sprawdzaniu każdej połówki
24 h `validator.py:470-471` zbiera wszystkich pracowników pracujących w tym
czasie, także przypisanych do innych, niezależnych demandów. Dlatego osoba z
legalnie nakładającej się krótszej zmiany zostaje błędnie uznana za osobę z
pierwszej połowy zmiany 24 h. Druga połowa jej nie obejmuje i walidator zgłasza
fałszywe `SHIFT-24-PAIR-01`.

## Niezależny, minimalny reproduktor

Na `main@c9f2404` zbudowałem trzy poprawnie oznaczone przypisania:

- E1 na obu połówkach tej samej zmiany 24 h;
- E2 na osobnej zmianie 10 h, nakładającej się tylko na pierwszą połowę;
- oba demandy mają wymaganą obsadę i E1 rzeczywiście pozostaje tą samą osobą
  przez całe 24 h.

Produkcyjny `validate()` zwrócił:

```text
hard_pass= False
SHIFT-24-PAIR-01: template AUDIT-H24-shift0-2026-10-01 mismatch ['E1', 'E2'] vs ['E1']
```

To spełnia bramkę defektu:

- TRACE: nakładanie wpisów jest legalne, a reguła dotyczy osoby na dwóch
  częściach jednej zmiany 24 h;
- OWNERSHIP: wynik tworzy `_check_24h_same_person()` w produkcyjnym walidatorze;
- REPRO: błąd odtworzony niezależnie na aktualnym `main`.

## Zalecany podział dalszej pracy

1. Jeden mały Task produktu: uzgodnić walidator `SHIFT-24-PAIR-01` z istniejącą
   tożsamością demandów i legalnym nakładaniem zmian. Minimalna macierz powinna
   obejmować: poprawną parę z niezależnym overlapem, prawdziwie różne osoby na
   dwóch połówkach oraz ochronę przed nieprawdziwym tagiem demandu.
2. Nie zmieniać generatora Wariantu B. Seed 0 jest wartościowym reproduktorem.
3. Nie łączyć z tym automatycznie zmiany diagnostyki `TECHNICAL_ERROR`.
   Pokazywanie odrzuconego, niepoprawnego kandydata jest nowym zachowaniem
   widocznym dla użytkownika i wymaga osobnej decyzji OWNERA. Nie blokuje
   naprawy, bo obecny komunikat i minimalny reproduktor wystarczają do niej.

Wynik `20/30` pokazuje duży praktyczny wpływ na ten konkretny przebieg, ale nie
jest miarą częstości błędu w realnych obiektach. Do udowodnienia defektu nie
potrzeba większej próby.
