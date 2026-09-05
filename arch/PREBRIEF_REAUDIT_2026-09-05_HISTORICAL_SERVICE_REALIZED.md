# PRE-BRIEF REAUDIT — historyczna służba i `AssignmentState.REALIZED`

AUDITED_SHA: `146318808fba72df5391e11d4814e9e887f68920`

Zakres: wąska weryfikacja uzupełnienia CC dopisanego do
`ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT` w `BOARD.md`.

To jest audyt definicji problemu przed briefem. Kod produktu nie został
zmieniony.

## Wynik

CC znalazł istniejący, użyteczny bezpiecznik, ale opis w `BOARD.md` nie jest
kompletny. `validate_realized_preserved()` może być częścią rozwiązania, lecz
nie jest gotową ochroną historycznych służb i nie może być jedyną podstawą
briefu.

Po poniższej korekcie problem ochrony historycznej służby jest dostatecznie
określony, aby architekt napisał brief. Brief nie może jednak zamrozić
automatycznego oznaczania wszystkich zwykłych służb jako `REALIZED`, bo OWNER
nie wybrał takiego mechanizmu. Zamrożony jest wynik widoczny dla człowieka,
nie techniczny sposób jego osiągnięcia.

## Co CC potwierdził poprawnie

- Każde utworzenie wersji-dziecka wywołuje
  `schedule_validation.validate_realized_preserved()`.
- Jeżeli bezpośredni rodzic zawiera Assignment w stanie `REALIZED`, dziecko
  musi zachować go bajt w bajt, poza technicznym `schedule_version_id`.
- Jest to blokada backendowa, więc nie da się jej ominąć samym wywołaniem
  innego przycisku w tym samym ekranie.
- Mechanizm warto ponownie wykorzystać jako dodatkowy bezpiecznik, jeżeli
  architekt wybierze rozwiązanie oparte na istniejącym stanie Assignmentu.

## Korekty do opisu CC

### 1. Stan `REALIZED` nie jest całkowicie nieużywany

Produkcja ma operację `training.mark_training_realized()`, która przez zwykłą
ręczną korektę oznacza zrealizowane szkolenie `TRAINEE`. Stan jest też czytany
przez bilans godzin, historię pracy w święta i sprawiedliwość planowania.

Prawdziwa luka jest węższa: nie ma kontrolowanego właściciela przejścia zwykłej
służby `PRIMARY` z planowanej na odbytą.

### 2. Zwykła korekta ufa stanowi przysłanemu przez klienta

`AssignmentIn.state` jest wejściem publicznego endpointu ręcznej korekty.
`apply_manual_correction()` nie sprawdza, kto, kiedy i dla jakiej roli może
utworzyć `REALIZED`.

Niezależny reproduktor przez produkcyjny application owner zapisał jako
`REALIZED` zwykłą służbę rozpoczynającą się dopiero 1 października 2026:

```text
start=2026-10-01T05:00:00
saved_state=REALIZED
```

To ważne także dlatego, że validator świadomie nie stosuje części świeżych
kontroli kwalifikacji do zaufanych wpisów `REALIZED`. `select_candidate()` ma
osobną ochronę przed sfabrykowaniem tego stanu, ale ogólna ręczna korekta jej
nie ma.

### 3. Blokada działa tylko w jednej gałęzi wersji

`validate_realized_preserved()` porównuje wyłącznie dziecko z jego
bezpośrednim rodzicem. `restore()` może ustawić jako bieżącą starszą wersję
sprzed przejścia na `REALIZED`, a następna korekta lub REPLAN tworzy od niej
nową gałąź. Późniejszy fakt `REALIZED` nie jest wtedy przodkiem i walidator go
nie widzi.

Niezależny reproduktor na exact SHA:

```text
V1: ASG-1 = PLANNED / EMP-1
V2 (dziecko V1): ASG-1 = REALIZED / EMP-1
restore(V1)
V3 (dziecko V1): ASG-1 = PLANNED / EMP-2

wynik: V3 zostało zapisane
```

Zatem samo `REALIZED` nie chroni faktów przed istniejącą ścieżką
„Przywróć wersję”.

### 4. Bezwzględna niezmienność koliduje z zaakceptowanym wyjątkiem

OWNER dopuścił po rozpoczęciu służby jedną zmianę: zapisanie innego pracownika,
który faktycznie wykonał całą służbę, z obowiązkową przyczyną i historią.
Jeżeli Assignment został wcześniej oznaczony `REALIZED`, obecny walidator
odrzuci również tę dozwoloną zmianę pracownika.

Architekt musi więc zachować wąski, kontrolowany wyjątek dla korekty osoby
faktycznie pracującej. Nie wolno osiągnąć tego przez ogólne poluzowanie
`validate_realized_preserved()`, bo przywróciłoby swobodną edycję historycznych
faktów.

### 5. Istnieje drugi częściowy mechanizm ochronny

`plan_ops._replan_cutover_violations()` już blokuje zmianę rozpoczętych
PRIMARY przy wyborze kandydata po REPLAN. Ochrona jest atomowo sprawdzana przed
zapisem, ale dotyczy tylko tej ścieżki. Ręczna korekta i przywracanie wersji nie
są nią objęte.

Architekt powinien wykorzystać wspólną semantykę granicy czasu, zamiast
tworzyć drugą sprzeczną definicję „służba już rozpoczęta”. Nie oznacza to
obowiązku zachowania obecnej nazwy lub dokładnej postaci helpera.

## Zamrożony wynik, który brief ma zapewnić

Źródłem jest decyzja OWNERA z 2026-09-05 zapisana w
`arch/PREBRIEF_AUDIT_2026-09-05_T056_FOLLOWUPS.md`:

1. Przed rozpoczęciem służby działają zwykłe korekty planu, a data skutku
   wynika z daty początku Assignmentu.
2. Po rozpoczęciu nie można zmienić kodu, czasu, demandu, stanu ani freeze.
3. Jedynym wyjątkiem jest zapisanie innej osoby, która faktycznie wykonała
   całą służbę; wymagane są przyczyna i trwała historia przed/po.
4. Ta sama zasada obowiązuje wszystkie ścieżki mogące zmienić wynik, w tym
   ręczną korektę, REPLAN/wybór kandydata i przywrócenie starszej wersji.
5. Przywrócenie wersji, które zmieniłoby rozpoczętą służbę, ma zostać
   odrzucone czytelnym komunikatem; koordynator zachowuje bieżący grafik i
   może użyć jawnej korekty faktycznie pracującej osoby.
6. Backend jest ownerem blokady. UI ma ją wyjaśnić i ograniczyć niedostępne
   akcje, ale nie jest granicą bezpieczeństwa.

## Granice dla architekta

- `REALIZED` jest kandydatem do ponownego użycia, nie narzuconym rozwiązaniem.
- Nie wolno automatycznie zmienić wszystkich PRIMARY na `REALIZED` bez
  wykazania, że nie zmienia to zamrożonej analityki, historii świąt,
  sprawiedliwości i dozwolonej korekty osoby faktycznie pracującej.
- Publiczna ręczna korekta nie może samodzielnie deklarować dowolnego
  `REALIZED`.
- Ochrona musi obejmować restore i rozgałęzienia historii, nie tylko
  bezpośrednie dziecko.
- Nie tworzyć drugiego rejestru wykonanej pracy, jeżeli istniejący Assignment,
  historia wersji i historia akcji wystarczą.
- Acceptance matrix musi zawierać co najmniej: przyszła korekta; moment
  dokładnie przed/równo/po początku; dozwolona zmiana faktycznego pracownika;
  niedozwolona zmiana pozostałych pól; REPLAN/select; restore starszego planu;
  bezpośredni endpoint z fałszywym `REALIZED`; restart i wydruk/rozliczenie
  zachowujące faktycznego pracownika.

## Wykonana niezależna kontrola

- statyczny pion: router korekty → application manual edit → validator →
  lifecycle/persistence;
- wszystkie produkcyjne odczyty `AssignmentState.REALIZED`;
- ścieżki `REPLAN/select_candidate` i `restore`;
- wąski test istniejącej produkcyjnej korekty PLANNED→REALIZED:
  `1 passed in 45.76s`;
- dwa niezależne reproduktory: przyszłe `PRIMARY` oznaczone jako `REALIZED`
  oraz obejście przez restore/nową gałąź.

Nie uruchamiano pełnej regresji repozytorium: to audyt definicji problemu bez
zmiany kodu produktu.
