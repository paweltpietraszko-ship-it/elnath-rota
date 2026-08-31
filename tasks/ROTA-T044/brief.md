# ROTA-T044 — Symulator Koordynatora Wariant B (prawdziwa zmienność zachowania)

Status: **CC AUTOR (OWNER 2026-08-30/31), KOREKTA R4 — DO WĄSKIEGO RE-AUDYTU CODEX (tylko R3-01/R3-02/R3-03), POTEM DO TASKU CZATGPT**

Pipeline dla tego Tasku, ustalony wprost przez OWNERA: CC pisze ten brief →
Codex audytuje → ChatGPT pisze Task na jego podstawie → **CC dostanie na końcu
wyraźne polecenie "adwokata diabła" i ma podważyć gotowy Task do podłogi**,
zanim cokolwiek zostanie zaimplementowane. To jest świadome odwrócenie
zwykłego zakazu self-review: zamiast liczyć, że CC przypadkiem nie będzie
bronić własnej roboty, CC dostaje wprost zadanie ją atakować.

Ta wersja (R4) zastępuje R3 (`f69c0ae`) po wąskim re-audycie Codexa
(`tasks/ROTA-T044/round_01/tests/tests_r3.txt`, WYMAGA_KOREKTY — R2-02 i
limit EXTERNAL z R2-03 zamknięte, ale trzy nowe mechaniczne luki: R3-01 brak
jednego kalendarza referencyjnego dla kalkulatora, R3-02 kontrakt urlopu
niewykonalny dla załogi jednoosobowej + niejednoznaczna częstość L4, R3-03
niezmierzony profil Hypothesis + brak jawnego `database`). Wszystkie trzy
poprawione poniżej — R2-01's wcześniejsze rozmowy z OWNER (kalkulator,
margines urlopowy, bloki, L4, required_primary_count) pozostają aktualne,
R4 tylko domyka ich mechaniczną wykonywalność.

Base: `main@1b6bfbf` (po merge ROTA-T043).

## 0. Skąd to się wzięło

ROTA-T043 dało **Wariant A**: Symulator Koordynatora, deterministyczny, stały
zestaw 20 obiektów (seedy 0-19). OWNER, po przejrzeniu realnych wyników,
zidentyfikował to jako **czujnik regresji**, wartościowy, ale niewystarczający
do testowania programu w szerszym sensie — bo zawsze daje ten sam wynik.
Wariant A **zostaje bez zmian**, ten Task go nie dotyka.

Rozmowa z OWNER (2026-08-30) — cytaty dosłowne, bo to są rozstrzygnięcia, nie
streszczenia:

> "Ta wersja może byc tylko jako wariant A wykrywający regresję [...]. Ale do
> testowania programu musi być generatorem scenariuszy obsada/obiekt."

> "Nie rozumiem, gdzie powiedziałem, że obsada 5/10 jest sztywna. Ona miała
> wynikać z kalkulatora godzin, który miał być w Symulatorze A, jest?"

(Odpowiedź: NIE JEST. `tests/property/coordinator_simulator.py:212`:
`employee_count = 5 * layer_count  # R4 frozen rule -- never derived from
workload`. Żaden kalkulator obsady nie istnieje w Wariancie A. Zweryfikowane
wprost w kodzie.)

> "Kalkulator to podstawa [...]. Jeśli kalkulator godzin i obsady będzie
> zły/nieużywany przez Hypothesis, to dostaniemy stos bzdurnych grafików jak w
> benchmarkach. Wpisze 8 osób na obiekt 5 osobowym i wesoło napisze, że
> wszystko jest zielone."

> "To ja chyba nie rozumiem ptaszków. Bo ja myślałem, że wystarczy odhaczyć
> dostepność w dni tygdnia w obiekcie i przy obsadzie i masz taki rytm pracy
> jaki chcesz." — potwierdzone: `frontend/src/screens/SiteShiftCatalog.tsx`
> ma dokładnie to, checkbox per dzień tygodnia per wiersz zmiany. Produkt jest
> w porządku; Wariant A tego mechanizmu po prostu nie używa swobodnie.

> "No w końcu. Sama nazwa mówi o co chodzi to Symulator zachowania
> koordynatora w programie, a wy napisaliście 20 testowych przejść przez
> solver."

> "Ok, przesadziłem, klikalne ekrany odłożymy na inny Symulator, bo sie
> zakopiemy w kodzie." — pełny UI/przeglądarka świadomie POZA zakresem,
> zostaje na osobny, przyszły Symulator.

**Kluczowa korekta R2, po dalszej rozmowie z OWNER:**

> "CC kalkulator wylicza tylko raz dla obiektu: ile jest na obiekcie godzin
> słuzby i dzieli je na według kodeksu pracy na ilość obsady. Symulator
> wpisuje je w panelu sterowania w zakładce obiekty wraz z innymi danymi [...],
> jego rola kończy sie na Plan/Replan i automatycznym potwierdzeniu EXTERNAL,
> bo ktoś MUSI byc na zmianie. Jeśli solver cos źle policzy to to jest wynik
> naszego testu, mamy co poprawiać. [...] SYMULATOR NICZEGO NIE LICZY POZA
> KALKULACJĄ OBSADY."

> "Evaluator jako zewnętrzny model, który odciąży nas od pisania naszego
> programu to mój pomysł." — osobny, późniejszy, poza tym Taskiem.

> [po sprawdzeniu surowych danych Wariantu A dla Q3 2026] "Czyli mamy
> sprawdzone, że Rota liczy kwartały, czyli w Symulatorze B nie musimy sie
> tym martwic." — CC ręcznie zweryfikował arytmetykę `month_balance`/
> `quarter_balance` z `tasks/ROTA-T043/round_01/tests/coordinator_report.json`
> dla wszystkich 5 osób przez lipiec-sierpień-wrzesień: w 100% spójna.
> Mechanizm `rota/balance.py` jest generyczny (liczy z godzin przypisań i
> absencji, nie z kształtu zmian), więc to jest dowód na poprawność
> mechanizmu, nie tylko jednego przypadku. **Wariant B nie buduje żadnej
> maszynerii kwartalnej ani oceny bilansu — to już zweryfikowane, poza
> zakresem.**

> [o strukturalnym deficycie godzin wykrytym w tych samych danych — 5 osób
> zawsze poniżej targetu, bo zapotrzebowanie/osobę < norma pełnoetatowa]
> "Nie, bo to sprawa kadrowa nie nasza, koordynator musi pamiętać o urlopach
> nie Rota, Rota mu podaje narastająco bilans poprawnie." — Rota liczy
> poprawnie; co koordynator z tym zrobi, to jego sprawa kadrowa. Nie Task.

**Korekta R3, po ograniczonym re-audycie Codexa (`tests_r2.txt`) —
rozstrzygnięcia OWNERA z 2026-08-31, cytaty dosłowne:**

> [R2-01, na przykładzie podwójnej obsady 24h dającym sprzeczne wyniki 9 vs
> wcześniej ustalone 10] "kalkulator musi przyjmować maksymalna długość
> miesiąca czyli 31. Jeśli LOCAL ma 10 osob to w ochronie jest to 360 dni
> urlopu w roku na obiekt. Na pewno przy 9 osobach kalkulator nie wziął pod
> uwagę urlopów, ewentualnych L4, musimy dobrze napisać ten algorytm bo
> będziesz mieć bzdury"

> "ochrona to zakłady pracy chronionej, a my jesteśmy niepełnosprawni, czyli
> mamy wszyscy po 36 dni urlopu, z małymi wyjątkami. ale pamiętaj my nie
> robimy programu kadrowego, to koordynator w zakladce Obiekt ustala ilość
> załogi. czyli liczymy jak najlepiej potrafimy ale to tylko symulacja czy
> solver poprawnie liczy na zadanych warunkach a nie czy poprawnie odtwarza
> warunki kadrowe prawdziwej ochrony. My sprawdzamy poprawność działania
> mechanizmu" — kalkulator jest świadomym, udokumentowanym przybliżeniem, nie
> próbą odtworzenia realnej kadrowości.

> [o realistycznym wpisywaniu urlopów w Panelu Sterowania, nie o ich
> matematycznym budżecie] "tak, wogóle nie patrzymy na budżet urlopu na cały
> rok, patrzymy jak poradzi sobie solver gdy będą te urlopy" — margines
> urlopowy z kalkulatora (poniżej) ustala TYLKO rozmiar załogi; realnie
> wpisywane bloki urlopowe (poniżej) nie muszą się sumować do dokładnie tej
> samej liczby dni w roku.

> [o kształcie realnych urlopów] "żeby było najbardziej realne jedna osoba ma
> 2 tygodnie wolnego a druga tydzień. [...] w życiu koordynator stara się
> tylko by daty urlopów się nie pokrywały. tylko CC pamiętaj nie rozmawiamy o
> solverze tylko o zachowaniu koordynatora w panelu sterowania."

> [R2-02, zakres `required_primary_count`] "dla sprawdzenia solvera chyba
> wystarczy 1-2 osoby, ale w życiu są obiekty, które mają więcej i np nawet
> 20 pracowników. ale to nam zakłóci badanie?" — po wyjaśnieniu, że większy
> zakres zmienia głównie czas rozwiązania (realny CP-SAT solve), nie
> mechanizm, i zepsułby tani/częsty profil Hypothesis: **"zostaje wąski
> zakres"** (1-2, patrz 1.2).

> [R2-03, propozycja CC: zamiast sztywnego "co 4. wygenerowany grafik ma
> L4", losowe prawdopodobieństwo] "tak, twój pomysł jest dobry" — sztywny
> licznik odrzucony jako powrót do scenariusza-replay; L4 losowane
> probabilistycznie (patrz 1.2a).

## 1. Czym Symulator jest i czym nie jest — fundament, nie szczegół

**Symulator automatyzuje wyłącznie decyzje koordynatora.** Nie jest drugim
solverem, nie jest benchmarkiem, nie ocenia poprawności gotowego grafiku.
Jego jedyna odpowiedzialność obliczeniowa to kalkulator obsady (sekcja 1.1) —
poza tym **niczego nie liczy**. Jeśli solver źle policzy grafik, bilans albo
sprawiedliwość — to jest WYNIK testu, realny reproduktor do naprawy produktu,
nie coś, co Symulator ma sam wykryć oceną. To jest odwrócenie tego, co T043
Checkpoint B zbudował (evaluator fairness + oracle kwartalny) — Wariant B
świadomie tego nie powtarza. (Fakt, że Wariant A w main już łamie tę zasadę,
jest osobno zgłoszony OWNEROWI, nie jest częścią tego Tasku.)

### 1.1 Kalkulator obsady — jedno proste liczenie, raz, na starcie

Kalkulator liczy **dokładnie jedną rzecz, raz, przy tworzeniu obiektu**:
liczbę LOCAL potrzebną do pokrycia wygenerowanego wzoru zapotrzebowania
(sekcja 1.2), ze świadomym, udokumentowanym marginesem na urlop — nie próbą
odtworzenia realnej kadrowości (patrz cytat OWNERA wyżej: "liczymy jak
najlepiej potrafimy [...] sprawdzamy poprawność działania mechanizmu", nie
zgodność z prawdziwą polityką kadrową ZPCh). To NIE jest solver ani drugi
algorytm układający dyżury z uwzględnieniem odpoczynku — to prosta
arytmetyka kadrowa, jaką realny koordynator robi ręcznie, zanim w ogóle
otworzy Rotę.

**Wzór (poprawiony po Codex R3-01 — "31 dni" samo nie wystarczało: nie mówiło
ile w tym okresie jest weekendów/świąt, a różne 31-dniowe miesiące mają różną
normę KP; formuła musi mieć JEDEN jawny kalendarz referencyjny, nie
abstrakcyjną liczbę dni):**

```
REFERENCE_MONTH = date(2026, 7, 1)   # jeden ustalony, jawny miesiąc: 31 dni,
                                      # ZERO świąt w POLISH_2026_HOLIDAYS,
                                      # już używany jako pierwszy miesiąc
                                      # kwartału w Wariancie A (QUARTER_MONTHS)
                                      # -- ten sam kalendarz, nie nowy wymysł
# Rozkład dni tygodnia w REFERENCE_MONTH (zweryfikowane, lipiec 2026):
# Pon 4, Wt 4, Śr 5, Czw 5, Pt 5, Sob 4, Nd 4 -- 23 dni robocze, 8 weekendowych
norma_kp = nominal_monthly_hours_kp(REFERENCE_MONTH, POLISH_2026_HOLIDAYS)
           # = 184h, zweryfikowane -- zero świąt w tym miesiącu więc bez
           # odjęć, deterministyczne
DNI_URLOPU_ROCZNIE = 36                  # ZPCh/niepełnosprawni, ustalone OWNER
margines_urlopowy_h = DNI_URLOPU_ROCZNIE / 12 * 8   # = 24h/mies., średnia,
                                          # NIE liczona per konkretny miesiąc
dostepne_h_na_osobe = norma_kp - margines_urlopowy_h   # = 160h

# Zapotrzebowanie liczone PER WIERSZ katalogu (rodzaj zmiany, godziny,
# required_primary_count, aktywne dni tygodnia z 1.2) -- każdy wiersz mnoży
# swoje godziny_zmiany * required_primary_count przez LICZBĘ DNI TEGO
# KONKRETNEGO dnia tygodnia w REFERENCE_MONTH (nie przez płaskie "31") --
# inaczej wzór "tylko weekend" policzyłby się tak, jakby trwał cały miesiąc
zapotrzebowanie_h = sum(
    godziny_zmiany(wiersz) * required_primary_count(wiersz)
    * liczba_wystapien_dnia_tygodnia(dzień, REFERENCE_MONTH)
    for wiersz in wygenerowany_katalog for dzień in wiersz.aktywne_dni_tygodnia
)
liczba_LOCAL = ceil(zapotrzebowanie_h / dostepne_h_na_osobe)
```

`margines_urlopowy_h` jest tu **wyłącznie do ustalenia rozmiaru załogi** —
nie jest to budżet, który reszta Symulatora musi "wydać" co do godziny (patrz
1.2a: realnie wpisywane urlopy nie muszą się sumować do tej samej liczby).

**Przypadki kontrolne, ręcznie policzone na REFERENCE_MONTH (Codex R2-01
wymagał: jedna warstwa, dwie pełne warstwy, obiekt mieszany
robocze/weekend):**
- H24×1, `required_primary_count=1`, aktywna cały tydzień:
  `24h × 1 × 31 dni = 744h` → `ceil(744/160) = 5 LOCAL` (zgadza się z
  pierwotnym ustaleniem OWNERA dla pojedynczej obsady).
- H24×2 (dwie pełne warstwy), `required_primary_count=2`, cały tydzień:
  `24h × 2 × 31 dni = 1488h` → `ceil(1488/160) = 10 LOCAL` (zgadza się z
  pierwotnym ustaleniem OWNERA dla podwójnej obsady — R2-01 rozstrzygnięte
  poprawnie, bez zgadywania, wynika wprost ze wzoru z marginesem).
- Obiekt mieszany: D+N 12h (`24h/dzień` łącznie) tylko w dni robocze
  (23 dni), `required_primary_count=1`: `24h × 1 × 23 = 552h` →
  `ceil(552/160) = 4 LOCAL`.

Te trzy wartości implementer odtwarza jako testy jednostkowe kalkulatora
PRZED podłączeniem go do losowego generatora — zgodność z powyższym jest
warunkiem koniecznym, nie orientacyjnym.

**Warunek zawsze sprawdzany po wygenerowaniu obiektu** (poprawiony po
audycie Codexa R2 z `tests_r1.txt` — poprzednia wersja żądała fałszywej
równości):
- zadeklarowana liczba LOCAL == wynik kalkulatora dla wygenerowanego wzoru
  zapotrzebowania;
- **zamknięty świat**: każdy Assignment w dowolnym zwróconym wyniku należy
  do zadeklarowanego LOCAL albo do EXTERNAL utworzonego przez dozwoloną
  reakcję (sekcja 1.4) — nigdy do kogoś innego.

Nie wymaga się, żeby KAŻDY zadeklarowany LOCAL dostał Assignment w każdym
gotowym grafiku (Codex R2: absencja, DAY_ONLY, DECISION_REQUIRED bez grafiku
to normalne, poprawne wyniki, w których nie każdy się pojawia). To
zabezpiecza dokładnie przed obawą OWNERA ("8 osób na obiekcie 5-osobowym,
wesoło zielone") bez fałszywych FAIL-i na poprawnych wynikach.

### 1.2 Swobodne generowanie wzoru zapotrzebowania, nie gotowe kształty

Generator losuje NIEZALEŻNIE, dla każdego rodzaju zmiany (D/N/24h), każdego
dnia tygodnia z osobna: czy ta zmiana występuje tego dnia, o jakich godzinach,
i jaki jest `required_primary_count` (poprawka po Codex R3 — poprzednia
wersja o tym nie wspominała, mimo że to pole decyduje o liczbie równoległych
stanowisk i jest konieczne dla obiektów z podwójną obsadą).

**Zakres `required_primary_count` (Codex R2-02, rozstrzygnięcie OWNERA
2026-08-31): wąski, `{1, 2}`.** Realne obiekty bywają większe (OWNER: "nawet
20 pracowników"), ale większy zakres nie testuje innej ścieżki kodu — zmienia
tylko czas realnego solve CP-SAT per przykład, co zepsułoby tani/częsty
profil Hypothesis (1.3). Duże obiekty świadomie POZA zakresem tego Tasku, bez
osobnego profilu eksploracyjnego na razie — nie zgadywać szerszego zakresu.

To ma naturalnie
wytwarzać "tylko weekend", "tylko dni robocze", "tylko noce", i kombinacje,
których nikt nie nazwał z osobna — bez enumerowania ich jako oddzielne
"kształty". `SiteShiftCatalog.tsx`'s checkboxy per dzień tygodnia to
dokładnie ten sam mechanizm w prawdziwym UI, potwierdzone działające.

**Poprawka po Codex R3**: `rota/planning/shift_catalog.py:250` (na exact SHA)
mówi wprost, że wielokrotne wpisy i nakładanie się zmian w katalogu są
LEGALNE i tworzą niezależne occurrence — to jest przeciwieństwo tego, co
poprzednia wersja tego briefu twierdziła ("nakładające się zmiany to znany,
nieobsługiwany przypadek"). Ten Task nie odrzuca legalnych overlapów.
Jedyny przypadek do odrzucenia PRZED budową obiektu (nie po, jako "błąd
produktu") to wzór dający **zero pokrycia w całym miesiącu** (nic do
zaplanowania w ogóle) — to nie jest błąd produktu, to bezużyteczny obiekt
testowy, generator ma go odrzucić/przelosować, nie budować.

### 1.2a Nieobecności realistyczne — urlop blokowy + L4 losowe

Generator (odgrywający koordynatora wpisującego dane w Panelu Sterowania,
przez prawdziwe API — nie inny mechanizm niż istniejący
`POST /workspace/employees/{id}/availability`) wpisuje dwie oddzielne
warstwy nieobecności, każdą wygenerowaną obiektowi:

**Urlop (deterministyczny, blokowy, nie budżetowy):**
- Bloki mają dwie realistyczne długości: **10 dni roboczych (2 tygodnie)**
  albo **5 dni roboczych (tydzień)** — nigdy rozdrobnione na mniejsze kawałki
  (OWNER: "żeby było najbardziej realne jedna osoba ma 2 tygodnie wolnego a
  druga tydzień").
- Który LOCAL dostaje 2 tygodnie, a który tydzień — deterministycznie
  wyprowadzone z seeda: rotacja naprzemienna po KOLEJNOŚCI zadeklarowanego
  LOCAL (1. osoba → 2 tyg., 2. osoba → tydzień, 3. osoba → 2 tyg., 4. osoba →
  tydzień, itd. — wzór cykliczny, działa dla dowolnej liczby LOCAL ≥ 2), nie
  losowane od nowa za każdym razem.
- **Bloki nigdy się nie pokrywają w czasie między różnymi pracownikami** —
  generator układa je jeden po drugim w kalendarzu, odzwierciedlając to, jak
  realny koordynator świadomie unika nakładania się urlopów (OWNER: "w życiu
  koordynator stara się tylko by daty urlopów się nie pokrywały").
- **Poprawka po Codex R3-02 — załoga jednoosobowa:** jeśli kalkulator (1.1)
  zwrócił `liczba_LOCAL == 1`, blok urlopowy deterministyczny **w ogóle nie
  jest generowany** dla tego obiektu. Nie ma drugiej osoby do zachowania
  reguły "bez nakładania się urlopów", a jednoosobowa załoga na urlopie to z
  definicji sytuacja wymagająca EXTERNAL (1.4), nie coś, co ten mechanizm ma
  próbować obsłużyć. Implementer nie dodaje po cichu drugiego LOCAL, żeby
  "zmieścić" regułę — to naruszyłoby wynik kalkulatora (Codex R3-02 wprost
  tego zakazał).
- Świadomie **nie ma kontroli sumy dni w roku** względem marginesu 36
  dni/rok z 1.1 — to są dwie niezależne rzeczy: kalkulator używa marginesu
  tylko do ustalenia rozmiaru załogi, generator absencji tylko odgrywa
  realistyczne zachowanie koordynatora i sprawdza jak solver sobie z tym
  radzi (OWNER: "wogóle nie patrzymy na budżet urlopu na cały rok, patrzymy
  jak poradzi sobie solver gdy będą te urlopy").

**L4 (losowe, probabilistyczne, nie sztywny licznik):**
- Blok 5-dniowy, **losowany DOKŁADNIE RAZ na wygenerowany obiekt (nie per
  krok stateful), z prawdopodobieństwem ~25%** — poprawka po Codex R3-02:
  poprzednia wersja mówiła "per obiekt/krok" jednocześnie, co przy 6 krokach
  dawałoby ~82% szans na co najmniej jedno L4, nie 25%. Rzut następuje raz,
  w momencie tworzenia obiektu (ten sam moment co przydział bloków
  urlopowych), nie osobno przy każdym PLAN/REPLAN.
- Nie sztywna reguła w stylu "co 4. wygenerowany grafik" (OWNER odrzucił
  sztywny licznik jako powrót do scenariusza-replay, zaakceptował losowanie
  probabilistyczne: "tak, twój pomysł jest dobry").
- Dokładny mechanizm losowania (np. `st.booleans()` ważone) i moment
  przypisania osoby do L4 (musi być ktoś z zadeklarowanego LOCAL, nie
  EXTERNAL; przy `liczba_LOCAL == 1` L4 nadal może wystąpić — to nie ma tego
  samego problemu co blok urlopowy, bo nie wymaga drugiej osoby) implementer
  dobiera sam w ramach TASK_SCOPE — kontrakt tego briefu wymaga tylko:
  prawdziwe losowanie Hypothesis, ~25% szans RAZ na obiekt, blok 5-dniowy,
  nigdy sztywny licznik/harmonogram.

### 1.3 Hypothesis (stateful) — prawdziwa zmienność, jawny kontrakt

Zamiast `for seed in range(20)` (Wariant A, zostaje bez zmian, osobny plik):
silnik oparty o Hypothesis (`RuleBasedStateMachine`), losujący przy KAŻDYM
uruchomieniu nowy zestaw obiektów/sekwencji działań koordynatora.

**Poprawka po Codex R5/R2-03/R3-03** (kontrakt nie był wykonywalny w
poprzednich wersjach — R3-03 słusznie odrzucił niezmierzone `20/6` jako
"profil tani": realny pomiar Wariantu A to ~750s dla 20 obiektów, a Wariant B
robi więcej PLAN/REPLAN na przykład, więc dostępny dowód wskazuje że 20/6
NIE jest tanie, nie że jest):
- `hypothesis` jako jawna zależność w `pyproject.toml` (nie ma jej dziś);
- **`database=None` (jawnie wyłączone)** — zapisane przez Hypothesis
  przykłady nie mogą po cichu zmieniać zadeklarowanej semantyki "nowe
  wejścia przy każdym uruchomieniu" (Codex R2/R3-03); odtwarzalność
  znalezionych naruszeń zapewnia WYŁĄCZNIE jawny artefakt reprodukcji
  (`failures/**`, niżej), nie wewnętrzna baza Hypothesis;
- `deadline=None` (realne wywołania API+CP-SAT solve nie mieszczą się w
  domyślnym timeout-cie Hypothesis, sztuczny deadline dawałby fałszywe
  FAIL-e), `derandomize=False` (prawdziwa losowość ma być realna, nie
  odtwarzalna sama z siebie);
- **implementer NIE zgaduje `max_examples`/`stateful_step_count` — mierzy
  je.** Przed zamrożeniem liczb implementer uruchamia jeden mały, realny
  przebieg (rząd wielkości: 1-2 przykłady, kilka kroków) przez prawdziwe
  API+solver, mierzy rzeczywisty czas na przykład/krok, i na tej podstawie
  dobiera `max_examples`/`stateful_step_count` dla **profilu domyślnego**
  (uruchamianego w zwykłym `pytest`) tak, żeby całość mieściła się w czasie
  odpowiednim dla codziennego, częstego uruchamiania — rząd wielkości
  pojedynczych dziesiątek sekund do niskich minut, wyraźnie poniżej ~750s
  pełnego portfela Wariantu A, nie zbliżony do niego. Zmierzony czas i
  wybrane liczby, wraz z metodą pomiaru, trafiają do
  `tasks/ROTA-T044/round_01/tests/**` jako dowód, nie są zgadywane z góry
  (Codex R3-03: "nie narzucam nowych liczb bez pomiaru" — implementer
  wykonuje ten pomiar, nie autor briefu);
- **profil eksploracyjny (opt-in, env var** `ROTA_SIM_VARIANT_B_FULL=1`**,
  analogicznie do `ROTA_SIM_FULL_PORTFOLIO` w Wariancie A):** wyraźnie
  większe `max_examples`/`stateful_step_count` niż profil domyślny (dokładna
  wartość: ta sama zasada pomiaru, nie zgadywanie) — do ręcznego
  uruchomienia przed dostarczeniem, nie w normalnym biegu testów;
- jawny artefakt reprodukcji per znalezione naruszenie (seed/przykład +
  gotowa komenda), zapisany tak jak Wariant A to robi (`failures/**`);
- jawny, deterministyczny sposób sprawdzenia realnej zmienności: test
  porównuje kanoniczne wygenerowane obiekty z dwóch RÓŻNYCH, jawnie
  podanych identyfikatorów przebiegu — nie polega na "zwykle wychodzi
  inaczej".

Warunek zatrzymania (dodane do sekcji 7): jeśli zmierzony czas pojedynczego
przykładu jest na tyle duży, że żaden rozsądny `max_examples`/
`stateful_step_count` nie mieści profilu domyślnego w czasie odpowiednim dla
codziennego użycia — implementer zgłasza to z danymi pomiaru, nie zaniża
progu "codziennego użycia" po cichu.

**Poprawka po Codex R6**: każdy przykład stateful dostaje świeżą SQLite
`:memory:` i nowy Site — bez tego shrinking może odtwarzać przypadek na
stanie pozostawionym przez poprzedni przykład. Brief wymaga jawnych
warunków stanu (precondition) dla każdej reguły: np. REPLAN wymaga
istniejącego current_version, select_candidate wymaga wyniku FEASIBLE z
poprzedniego kroku. Zły wynik PRODUKTU (np. solver zwraca coś dziwnego)
pozostaje wynikiem badania; tylko generator próbujący nielegalnej kolejności
akcji (np. REPLAN bez istniejącego grafiku) jest błędem narzędzia.

Gdy Hypothesis znajdzie naruszenie niezmiennika z 1.1 (jedynego niezmiennika,
jaki Symulator w ogóle sprawdza), automatycznie skraca je do najmniejszego
przykładu (wbudowana funkcja Hypothesis).

### 1.4 EXTERNAL — automatyczna, powtarzalna reakcja

Pierwszy PLAN zawsze używa wyłącznie wygenerowanych LOCAL. Jeżeli produkt
zwróci prawdziwy, niepusty `DECISION_REQUIRED`:
1. pierwszy wynik zostaje zachowany, niezmieniony;
2. Symulator automatycznie tworzy jedną syntetyczną osobę `EXTERNAL_SUPPORT`
   i okno przez istniejące produkcyjne operacje (ten sam porządek zapisów co
   Wariant A: create-person niesie decision id, kolejne zapisy null);
3. ponawia PLAN;
4. jeśli produkt PONOWNIE zwróci realny `DECISION_REQUIRED` żądający
   dalszego wsparcia, powtarza krok 2-3 (kolejny EXTERNAL) — **limit prób
   zamrożony (Codex R2-03): maksymalnie tyle EXTERNAL, ile wynosi
   `liczba_LOCAL` z kalkulatora (1.1) dla tego obiektu** — wystarczy żeby
   zastąpić całą chorą/nieobecną załogę, ale nie tworzy nieskończonej liczby
   syntetycznych osób na wadliwym obiekcie testowym;
5. jeśli nawet to nie da grafiku, Symulator zachowuje wynik jako
   ograniczenie/błąd produktu. Nie tworzy Assignmentów ręcznie.

Uzasadnienie: obiekt musi zostać obsadzony — kimś. W testowej automatyzacji
tę rolę reprezentuje syntetyczny EXTERNAL, tak jak w produkcie reprezentuje
ją realny coordinator, wsparcie albo w ostateczności właściciel.

### 1.5 Kwartał — więcej działań koordynatora, zero nowej oceny

Wariant B może kontynuować ten sam Site/roster przez kolejne miesiące (więcej
kroków stateful sekwencji: kolejny miesiąc, kolejny PLAN), ale **nie liczy
niczego samodzielnie** — to jest już zweryfikowane jako poprawne w Wariancie A
(sekcja 0 wyżej, ręcznie sprawdzone przez CC na surowych danych Q3 2026).
Jeśli Wariant B naturalnie wygeneruje sekwencję obejmującą kilka miesięcy
tego samego obiektu, po prostu odczytuje i zapisuje to, co realna Analityka
i bilanse już zwraca — bez budowania własnego oracle'a.

### 1.6 Evaluator zewnętrzny — poza zakresem tego Tasku

OWNER ma pomysł na osobny, późniejszy krok: eksport anonimowego, kompletnego
pakietu JSON (konfiguracja obiektu, roster, targety, nieobecności, decyzje,
Assignmenty, validate, analityka) przekazywany zewnętrznemu modelowi do
diagnostycznej oceny — żeby odciążyć OWNERA od ręcznego przeglądania setek
surowych grafików. To NIE jest częścią Wariantu B — Symulator ma tylko
zapisywać kompletne, surowe dane w formacie, który taki eksport mógłby
później skonsumować (to znaczy: raport JSON ma być kompletny i czytelny
maszynowo, nic więcej). Sam mechanizm eksportu/oceny to osobny, przyszły
Task.

## 2. Co NIE wchodzi w zakres tego Tasku

- **Pełny UI/przeglądarka** — świadomie odłożone na osobny, przyszły
  Symulator. Ten Task zostaje na poziomie API (`TestClient` + prawdziwy
  backend), jak Wariant A.
- **Jakakolwiek ocena wyniku przez Symulator** (fairness, jakość grafiku,
  poprawność bilansu) — usunięte całkowicie z Wariantu B, nie tylko
  "odłożone". Symulator liczy TYLKO kalkulator obsady (1.1).
- **Maszyneria kwartalna/oracle bilansu** — już zweryfikowane w Wariancie A
  jako poprawne (sekcja 0), nie duplikować.
- **Evaluator jako funkcja produktu** ani jako eksport do zewnętrznego
  modelu — oba osobne tematy (patrz 1.6 i
  `arch/REQUEST_SYMULATOR_WARIANT_B_2026-08-30.md`), nie mieszać z tym
  Taskiem.
- **Wariant A sam w sobie** — zostaje jako czujnik regresji, bez zmian.
- **Rozliczenie z Codexem** za wcześniejsze zignorowanie instrukcji o
  replay — OWNER świadomie to odpuszcza ("już mi wyjaśnił, zostawmy to").
- Wszystko, co T043 sekcja 9 już zakazywało (`rota/**`, `api/**`,
  `frontend/src/**`, `benchmarks/**`, drugi solver/validator, Cross-Site,
  wsparcie przed pierwszym PLAN, sieć w runtime). **Doprecyzowanie dla
  Wariantu B**: "własny rachunek urlopu/L4" oznacza zakaz duplikowania
  arytmetyki bilansu (`rota/balance.py`) — nie zakaz generowania realnych
  rekordów urlopu/L4 przez prawdziwe API, co 1.2a wprost wymaga. Generator
  wpisuje nieobecności jako dane wejściowe (jak realny koordynator); nie
  liczy z nich żadnego własnego bilansu godzin.

## 3. Zamrożone decyzje z Wariantu A, które nadal obowiązują

Prawdziwe produkcyjne ścieżki API (bez monkeypatchowania PLAN/REPLAN/
validate/analityki), target_hours jako prawdziwe wejście, nieobecności przez
prawdziwy endpoint, zły grafik jako wynik badania (nie sygnał do zmiany
wejścia), granica twierdzeń o prawie (produkcyjny `validate()` to stan HARD
zaimplementowany w produkcie, nie certyfikat całego Kodeksu pracy).

## 4. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Konieczność | Redukcja |
|---|---|---|---|
| kalkulator obsady z marginesem urlopowym, liczony na 31-dniowym miesiącu | OWNER 2026-08-31 R3, poprawia Codex R2-01 | naga suma godzin/norma dawała 9 zamiast ustalonych 10 i mogła być deficytowa w długich miesiącach | jedno dodatkowe odjęcie stałego marginesu (24h/mies. z 36 dni urlopu/rok) przed dzieleniem |
| realistyczne bloki urlopowe (2 tyg./tydzień, bez nakładania) zamiast losowej absencji "z sufitu" | OWNER 2026-08-31 R3 | testuje jak solver radzi sobie z zachowaniem koordynatora, nie z budżetem godzin | deterministyczna rotacja bloków z seeda, osobna od kalkulatora |
| L4 losowane probabilistycznie (~25%), nie sztywny licznik | OWNER 2026-08-31 R3 (odrzucił "co 4. grafik") | sztywny licznik to powrót do scenariusza-replay | jeden dodatkowy rzut losowy w generatorze |
| `required_primary_count` zawężony do {1,2} | OWNER 2026-08-31 R3, rozstrzyga Codex R2-02 | szerszy zakres nie testuje nowej ścieżki, tylko wydłuża realny solve i psuje tani profil | stałe dwuwartościowe losowanie |
| jeden jawny kalendarz referencyjny (REFERENCE_MONTH = 2026-07) dla kalkulatora, per-wiersz liczenie zamiast płaskiego ×31 | Codex R3-01 | dwie poprawne implementacje dawały różny wynik bez tego | jeden ustalony, już-używany miesiąc (QUARTER_MONTHS[0]), 3 ręcznie policzone przypadki kontrolne (5/10/4 LOCAL) |
| brak bloku urlopowego przy liczba_LOCAL==1, L4 losowane raz na obiekt (nie per krok) | Codex R3-02 | reguła "2 tyg. + tydzień" była niewykonalna dla 1 osoby; "~25% per obiekt/krok" dawało ~82% nie 25% | jawny wyjątek + jedno miejsce losowania zamiast dwóch |
| pomiar (nie zgadywanie) liczb profilu Hypothesis, jawne `database=None`, limit EXTERNAL = liczba_LOCAL | Codex R2-03/R3-03 | niezmierzone 20/6 nie miało dowodu taniości (Wariant A: ~750s/20 obiektów) | implementer mierzy mały realny przebieg przed zamrożeniem liczb |
| asercja deklaracja=kalkulacja + zamknięty świat | OWNER 2026-08-30 + Codex R2 (poprawia błędną wersję) | zapobiega "8 osób na obiekcie 5-osobowym" bez fałszywych FAIL | dwa sprawdzenia po każdym przypadku |
| swobodne dni tygodnia/rodzaj/required_primary_count | OWNER 2026-08-30 + Codex R3 | usuwa gotowe kształty i nieaktualny zakaz overlapów | losowanie niezależne per (dzień, rodzaj, required_primary_count) |
| Hypothesis stateful z jawnym kontraktem | OWNER 2026-08-30 + Codex R5/R6 | prawdziwa zmienność, wykonywalny kontrakt | jeden stateful engine, jawny profil, izolacja per przykład, reużywa produkcyjne helpery Wariantu A |
| WHERE_MAP: REQUIRED | Codex R7 | nowy właściciel kalkulatora/generatora | mapa na `coordinator_simulator.py` + nową zależność `hypothesis` |
| brak oceny fairness/kwartału | OWNER 2026-08-30 R2 (fundamentalna korekta) | Symulator nie jest sędzią | usunięte całkowicie, nie "opcjonalne" |

Nie powstają: pełny UI/Playwright, jakikolwiek evaluator wbudowany w
Symulator, drugi solver/validator, zmiana Wariantu A.

## 5. TASK_SCOPE

TASK_SCOPE:
- `tests/property/coordinator_simulator.py` (nowe funkcje: kalkulator,
  swobodny generator wzoru zapotrzebowania, stateful engine — istniejące
  funkcje Wariantu A nietknięte/reużywane, nie kasowane)
- `tests/property/test_coordinator_simulator_variant_b.py` (nowy plik,
  osobny od Wariantu A)
- `pyproject.toml` (wyłącznie dodanie zależności `hypothesis`)
- `tasks/ROTA-T044/brief.md`
- `tasks/ROTA-T044/round_01/tests/**`

Zabronione: `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`,
modyfikacja istniejących funkcji Wariantu A poza dodaniem nowych,
addytywnych funkcji które Wariant B reużywa.

## 6. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: `tests/property/coordinator_simulator.py`
- REASON: Task dodaje nowego właściciela (kalkulator obsady, swobodny
  generator wzoru zapotrzebowania) do pliku już współdzielonego z Wariantem
  A; mapa ma ujawnić, czy coś poza `test_coordinator_simulator.py` i nowym
  `test_coordinator_simulator_variant_b.py` go konsumuje.

## 7. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:
- kalkulator obsady nie da się zweryfikować ręcznie na małym zestawie
  przypadków kontrolnych przed podłączeniem go do losowania;
- generowany wzór zapotrzebowania wymaga rozstrzygnięcia, którego dziś nie
  ma (np. nowa klasa "niesensownego" wzoru poza "zero pokrycia w miesiącu")
  — zgłosić, nie zgadywać nowej reguły;
- Hypothesis stateful wymaga symulowania czegoś, co dziś nie ma
  odpowiednika w prawdziwym produkcyjnym API;
- limit prób EXTERNAL (1.4) okazuje się za niski/wysoki dla realnych
  wygenerowanych obiektów — zgłosić z danymi, nie zgadywać liczby;
- zmierzony czas pojedynczego przykładu Hypothesis (1.3) jest na tyle duży,
  że żaden rozsądny `max_examples`/`stateful_step_count` mieści profil
  domyślny w czasie odpowiednim dla codziennego użycia — zgłosić z danymi
  pomiaru, nie zaniżać po cichu progu "codziennego użycia".

## 7a. Świadomie przyjęte uproszczenia — zaakceptowane, nie luki

To nie są przeoczenia. OWNER i CC świadomie wybrali te uproszczenia po
rozmowie ważącej alternatywy — audyt ma sprawdzać ich WYKONYWALNOŚĆ i
WEWNĘTRZNĄ SPÓJNOŚĆ, nie kwestionować same decyzje jako niedociągnięcia:

- **Kalkulator to przybliżenie testowe, nie model kadrowy.** Margines
  urlopowy (24h/mies.) to średnia roczna, nie dokładny rachunek per
  konkretny miesiąc/pracownika. OWNER wprost: "liczymy jak najlepiej
  potrafimy [...] sprawdzamy poprawność działania mechanizmu", nie
  odtwarzamy realnej polityki kadrowej ZPCh co do dnia.
- **Kalkulator nie uwzględnia L4 w ogóle** (tylko urlop) — świadomie, bo L4
  jest z natury nieprzewidywalne i ma być pokrywane przez losowy generator
  W TRAKCIE przebiegu (1.2a), nie przy jednorazowym ustalaniu rozmiaru
  załogi na starcie.
- **Realne bloki urlopowe (1.2a) nie muszą sumować się do budżetu 36
  dni/rok z kalkulatora.** To dwie celowo niezależne rzeczy — margines
  ustala rozmiar załogi, bloki testują zachowanie solvera. OWNER wprost:
  "wogóle nie patrzymy na budżet urlopu na cały rok".
- **`required_primary_count` zawężony do {1,2}, mimo że realne obiekty
  bywają większe** (OWNER: "nawet 20 pracowników"). Świadomie odrzucone —
  szerszy zakres nie testuje innej ścieżki kodu, tylko wydłuża czas solve i
  psuje tani profil Hypothesis. Duże obiekty to świadomie osobny,
  nieotwarty temat, nie brakujący element tego briefu.
- **Dokładny mechanizm losowania L4 (~25%)** (np. konkretna dystrybucja
  Hypothesis) celowo zostawiony implementerowi w ramach TASK_SCOPE — kontrakt
  wymaga tylko: prawdziwe losowanie, ~25% szans, blok 5-dniowy. To nie jest
  ten sam rodzaj luki, jaką Codex R5/R2-03 zgłaszał wcześniej (tam brakowało
  JAKIEJKOLWIEK liczby; tu liczba jest, tylko implementacja mechanizmu
  losowania — nie jego parametr — zostaje szczegółem kodu).
- **Konkretne liczby profilu Hypothesis (20/6, 50/10) to szacunek CC**, nie
  zweryfikowany empirycznie na prawdziwym API+solverze — audyt może je
  zakwestionować jako nierealistyczne (za drogie/za płytkie), ale sam fakt,
  że są to liczby "wymyślone przez autora briefu, nie zmierzone" nie jest
  sam w sobie błędem — dokładnie to zlecił Codex R5/R2-03 (zamrożenie
  jakichkolwiek konkretnych liczb zamiast "implementer wybierze").

## 8. Pytania do wąskiego re-audytu Codexa (tylko R3-01/R3-02/R3-03)

Zgodnie z zapowiedzią w `tests_r3.txt`: re-audyt sprawdza WYŁĄCZNIE poniższe
trzy punkty. R2-02 (zakres `{1,2}`), limit EXTERNAL i granice Symulatora są
już zamknięte (`tests_r3.txt`: "Nie otwierać ponownie") — proszę nie
otwierać ich ponownie.

1. **R3-01 (kalendarz referencyjny kalkulatora):** czy `REFERENCE_MONTH =
   date(2026, 7, 1)` + liczenie per-wiersz-katalogu (godziny × wymagana
   liczba × liczba wystąpień danego dnia tygodnia w tym miesiącu) jest teraz
   jednoznaczne, deterministyczne, i czy trzy przypadki kontrolne (5 / 10 / 4
   LOCAL) są poprawnie policzone?
2. **R3-02 (kontrakt urlopu + L4):** czy jawny wyjątek dla `liczba_LOCAL==1`
   (brak bloku urlopowego deterministycznego) i jednoznaczne "L4 losowane
   RAZ na obiekt, ~25%" (nie per krok) usuwają obie niewykonalności, bez
   nowych niejasności?
3. **R3-03 (profil Hypothesis + `database`):** czy wymóg zmierzenia (nie
   zgadywania) liczb `max_examples`/`stateful_step_count` przed ich
   zamrożeniem, jawne `database=None`, i jawne kryterium "wyraźnie poniżej
   ~750s pełnego portfela Wariantu A" są teraz wystarczające, żeby
   implementer nie musiał projektować kontraktu samodzielnie?

Do zamknięcia audytu: **implementacja czeka na PASS Codexa na tym briefie,
potem na Task napisany przez ChatGPT, potem na jawne polecenie "adwokat
diabła" dla CC przed jakimkolwiek kodowaniem.**
