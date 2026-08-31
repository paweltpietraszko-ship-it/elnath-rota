# Codex — ręczna ocena, seedy 60–89 (Wariant B, batch2, post-T045)

Status: **RĘCZNY PRZEGLĄD — BRAK NOWEGO ZNALEZISKA**

Źródło: `docs/variant-b-joint-evaluation-batch2@2e7776e`, pliki
`tasks/ROTA-T044/round_01/tests/reports/batch2/seed60.json` … `seed89.json`.

## Zasady oceny

Zastosowano uzgodniony format:

- `BRAK_UWAG` oznacza tylko brak konkretnej, uzasadnionej anomalii w
  dostarczonym raporcie — nie PASS ani dowód poprawności grafiku;
- bez ponownego liczenia HARD, bilansów i prawa pracy;
- bez własnych progów liczbowych;
- bez automatycznego tworzenia Tasku.

Do pierwszego przeglądu użyto wyłącznie zapisanych przez produkt statusów,
ostrzeżeń, decyzji, odchyleń i pól analityki. Szczegółowo obejrzano odstające
układy godzinowe oraz reprezentantów: 60, 61, 62, 66, 69, 70, 71, 79, 83 i
89. Nie uruchamiano solvera ponownie ani nie zmieniano wejść.

## Wynik 30 raportów

- 30/30: `final_result.status = FEASIBLE`;
- 30/30: co najmniej jeden finalny kandydat oraz `selected = true`;
- 0 nierozwiązanych `decision_required` po zakończeniu;
- 0 zapisanych deviations;
- 0 `error_message`;
- 0 nieoczekiwanych ostrzeżeń;
- 13/30 obiektów przeszło przez produkcyjne `DECISION_REQUIRED` i otrzymało
  łącznie 18 osób EXTERNAL; każdy zakończył się FEASIBLE;
- 10 wyników FEASIBLE miało `optimization_complete = false`. To jawny,
  obsługiwany stan produktu: poprawny kandydat może być pokazany bez dowodu
  pełnego optimum. Sam ten bool nie jest anomalią;
- REPLAN: 9 razy FEASIBLE, 21 razy NARROW_SEARCH_EXHAUSTED. W tych raportach
  REPLAN nie następował po zmianie parametrów obiektu, więc nie jest to
  reproduktor wcześniejszej zasady OWNERA o pełnym zbilansowaniu po zmianie.

Wynik per seed:

```text
60 BRAK_UWAG   61 BRAK_UWAG   62 BRAK_UWAG   63 BRAK_UWAG   64 BRAK_UWAG
65 BRAK_UWAG   66 BRAK_UWAG   67 BRAK_UWAG   68 BRAK_UWAG   69 BRAK_UWAG
70 BRAK_UWAG   71 BRAK_UWAG   72 BRAK_UWAG   73 BRAK_UWAG   74 BRAK_UWAG
75 BRAK_UWAG   76 BRAK_UWAG   77 BRAK_UWAG   78 BRAK_UWAG   79 BRAK_UWAG
80 BRAK_UWAG   81 BRAK_UWAG   82 BRAK_UWAG   83 BRAK_UWAG   84 BRAK_UWAG
85 BRAK_UWAG   86 BRAK_UWAG   87 BRAK_UWAG   88 BRAK_UWAG   89 BRAK_UWAG
```

## Ważna granica: miesięczny niedobór nie jest nowym findingiem

W części raportów pracownicy bez absencji mają ujemny `month_balance`, czasem
wyraźny (np. seed 79: pełny effective target 176 h, planned 106 h,
month_balance -70 h dla EMP-2 i EMP-3). Nie kwalifikuję tego jako nowe
`DO_SPRAWDZENIA`, ponieważ ta dokładna klasa zachowania została już jawnie
rozstrzygnięta przez OWNERA w kontrakcie T044:

- `tasks/ROTA-T044/brief.md:102-106`: strukturalny deficyt, gdy
  zapotrzebowanie na osobę jest niższe od miesięcznej normy, jest informacją
  bilansową dla koordynatora i sprawą późniejszego rozliczenia/kadrową —
  „Nie Task”;
- `tasks/ROTA-T044/brief.md:91-100` oraz `555-563`: Wariant B nie buduje
  wielomiesięcznego kontekstu ani własnego oracle kwartalnego;
- `tasks/ROTA-T044/brief.md:680-703`: kalkulator ma dawać ciasną obsadę bez
  marginesu urlopowego, a absencje są celowym stresem po utworzeniu obiektu.

Nie wolno więc ponownie otwierać zaakceptowanego zachowania za pomocą nowego,
nieuzgodnionego progu typu `month_balance <= -20 h`. Same raporty miesięczne
nie odpowiadają też, jak niedobór rozłoży się w pełnym kwartale.

To oznacza, że `CC_JOINT_EVAL_SEEDS_30-59` finding
„systematyczny niedobór godzin bez absencji” wymaga w konsolidacji
sklasyfikowania jako **wcześniej rozstrzygnięte zachowanie / nie nowy defekt**,
a nie automatycznej promocji do Tasku. Gdyby OWNER chciał zmienić tę wcześniejszą
decyzję produktową, potrzebna byłaby nowa jawna decyzja, nie wynik evaluatora.

## BRAK_DOWODU

Brak osobnych przypadków. Ograniczenie kwartalne dotyczy całej paczki i
ogranicza zakres twierdzeń, ale nie powoduje, że technicznie kompletne raporty
60–89 stają się uszkodzone. `BRAK_UWAG` nadal nie zawiera twierdzenia o wyniku
pełnego kwartału.
