# PROPOZYCJA DO ARCHITEKTA — luka w `benchmarks/rota_stress.py`: syntetyczny skład zespołu zamiast obsady realnego obiektu

Status: PROPOZYCJA / OTWARTE PYTANIA DO ARCHITEKTA — nie zmienia kodu produkcyjnego, nie rozstrzyga rozwiązania.
Data: 2026-08-13
Zgłaszający: CC (implementator), na wyraźne polecenie właściciela, w trakcie audytu ROTA-T008.
Baza: `main` @ `e010f004e90a1e4f426bb72298e7307045d32b56`.

## Kontekst

W trakcie audytu ROTA-T008 właściciel zauważył, że `benchmarks/rota_stress.py`
(dodany w commicie `0c5978e`) bierze z obiektu reguły zmianowe (długość
zmiany, próg LOAD-01 itd.), ale **nie** bierze z obiektu składu zespołu —
generuje własną, syntetyczną liczbę pracowników niezależnie od tego, ilu
ludzi obiekt faktycznie ma. Właściciel poprosił o wersje benchmarku dla
konkretnych warunków realnego obiektu (5 osób, w tym 1 wyłącznie dniówki);
dostał warunki obiektu, ale nierealną obsadę.

## Fakt ustalony w kodzie

`benchmarks/rota_stress.py:_employees(month, count)`:

```python
pool_size = count * 2
ids = [f"E{i:02d}" for i in range(pool_size * 2 + 2)]
```

Dla `count=1` (większość generowanych przypadków, `count = 2 if index % 3
== 2 else 1`) daje to **6** pracowników (`day_pool=2`, `night_pool=2`, `+2`
nieużywane w rotacji świadka — czysty zapas). `count` sam jest deterministyczną
funkcją indeksu przypadku, nie żadnym parametrem realnego obiektu.

## Weryfikacja empiryczna wykonana w tej sesji

Uwaga: poniższe to doraźne, niezacommitowane skrypty uruchomione ręcznie w
tej sesji — nie są częścią suity testów i nie przeszły przez Codexa ani
architekta. Zapisane tu jako materiał źródłowy dla decyzji, nie jako
zweryfikowany wynik regresyjny.

### 1. Sztywny podział 5-osobowy (2 dzień / 3 noc)

Na tych samych 67 przypadkach benchmarku, gdzie `required_primary_count=1`,
z pulą ograniczoną do technicznego minimum LOAD-01 (2 os./typ zmiany), bez
żadnego zapasu ponad to minimum: **67/67 czysto FEASIBLE** (zweryfikowane
przez `candidate_errors()` z benchmarku, tak jak oryginalne przypadki).

To obala najsilniejszą wersję hipotezy "bez 6. osoby testy by nie
przeszły" — dla tego konkretnego, uproszczonego kształtu 5-osobowego
różnicy nie ma.

### 2. Wierny kształt realnego obiektu

5 osób, dokładnie 1 DAY_ONLY, pozostali w pełni elastyczni D/N — struktura
zgodna z `tests/regression/oracle_rota_reg_001.md` (A–E, C=DAY_ONLY), nie
ze sztywnym podziałem dzień/noc z punktu 1. Narastające spiętrzenie
perturbacji: 2→3→4 nieobecności/osobę, plus wymuszone nakładanie się 1→2→3
dni z dwiema osobami naraz nieobecnymi. 30 miesięcy × 3 poziomy spiętrzenia
= 72 przypadki, granica z poprzednim miesiącem generowana z REALIZED
przypisaniami (6 dni wstecz).

Wynik:

- **57/72 FEASIBLE**
- **15/72 DECISION_REQUIRED** (proporcjonalnie do spiętrzenia: 1/24 przy
  najlżejszym wariancie → 4/24 średnim → 10/24 najcięższym)
- **0 TECHNICAL_ERROR, 0 nielegalnych "FEASIBLE"** — żaden zwrócony
  grafik nie złamał twardej reguły; przy przeciążeniu system poprawnie
  zwracał `DECISION_REQUIRED` z konkretnym `Blocker` (np.
  `condition='LOAD-01'`, `employee_id='B'`) zamiast fałszywego sukcesu lub
  awarii.

### Metodologiczna uwaga (ważna dla wiarygodności powyższego)

Pierwsza wersja testu z punktu 2 miała błąd we własnym generatorze danych
granicznych: ten sam pracownik trafiał jako D i N tego samego dnia w danych
o poprzednim miesiącu (0h odpoczynku), co samo w sobie łamało REST-01 jeszcze
zanim solver dostał dane. Dawało to `0/72` i fałszywy sygnał awarii
solvera. Błąd wykryty i naprawiony (dodana jawna weryfikacja czystości
granicy przed wywołaniem `plan()`) przed wyciągnięciem jakichkolwiek
wniosków — powtórzony przebieg dał wynik opisany wyżej.

## Otwarte pytania dla architekta (nierozstrzygane w tym zgłoszeniu)

1. Czy `benchmarks/rota_stress.py` ma zostać przypięty na stałe do jednego
   konkretnego, realnego składu obiektu (imiona/role/kto DAY_ONLY), czy
   pozostaje generyczny (stress test dla wielu kształtów), a obok powstaje
   osobny, dedykowany benchmark dla realnego obiektu?
2. Jakie jest właściwe, aktualne źródło prawdy o realnym składzie — czy
   `tests/regression/oracle_rota_reg_001.md` (A–E, C=DAY_ONLY) jest tym
   źródłem na stałe, czy istnieje inny, bardziej aktualny rejestr do
   wskazania?
3. Czy `15/72 DECISION_REQUIRED` przy spiętrzonych perturbacjach to
   akceptowalne, oczekiwane zachowanie produktu, czy sygnał do przeglądu
   (np. czy SOFT ranking powinien mieć więcej swobody przed eskalacją do
   DECISION_REQUIRED)?
4. Czy korekta wchodzi jako poprawka istniejącego benchmarku, czy jako
   osobny task z własnym numerem i kontraktem.

## Zakres tego dokumentu

Ten dokument zapisuje ustalone fakty i wyniki do decyzji architekta/
właściciela. Nie proponuje rozwiązania, nie projektuje nowego kształtu
benchmarku, nie zmienia kodu produkcyjnego ani `benchmarks/rota_stress.py`,
i nie jest zgodą na implementację.
