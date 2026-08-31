# ROTA-T044 — Symulator Koordynatora Wariant B (prawdziwa zmienność zachowania)

Status: **CC AUTOR (OWNER 2026-08-30/31), KOREKTA R7 — DO WĄSKIEGO RE-AUDYTU CODEX (kalkulator bez marginesu, required_primary_count per obiekt), POTEM DO TASKU CZATGPT**

Pipeline dla tego Tasku, ustalony wprost przez OWNERA: CC pisze ten brief →
Codex audytuje → ChatGPT pisze Task na jego podstawie → **CC dostanie na końcu
wyraźne polecenie "adwokata diabła" i ma podważyć gotowy Task do podłogi**,
zanim cokolwiek zostanie zaimplementowane. To jest świadome odwrócenie
zwykłego zakazu self-review: zamiast liczyć, że CC przypadkiem nie będzie
bronić własnej roboty, CC dostaje wprost zadanie ją atakować.

Ta wersja (R7) zastępuje R6 (`a90f433`) po tym, jak OWNER, weryfikując R6
wynik na własnym referencyjnym obiekcie, złapał kolejny błąd: R6's margines
urlopowy (24h/mies.) windował wynik dla dokładnie tego obiektu z 5 do 6 osób
— czyli sztucznie zawyżał obsadę. OWNER: "mój obiekt jest referencyjny dla
wyliczenia obsady i ma 5 osób, jeśli sztucznie zawyzysz obsadę to dasz fory
solverowi [...] wyliczenie obsady jest krytycznie ważne, za mało, to solver
będzie rządać wciąż wsparcia za dużo będzie mieć fory." Margines jest
całkowicie usunięty z kalkulatora (patrz sekcja 0, korekta R7, i 1.1) —
"maksimum po 12 miesiącach" z R6 zostaje jako mechanizm na niestabilność
wynikającą z realnego kalendarza (np. wzory asymetryczne typu "tylko dni
robocze"), ale już bez marginesu, więc referencyjny obiekt OWNERA (D/N 12h,
required_primary_count=1) wraca do stabilnych 5, dokładnie jak być powinno.

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

**Korekta R4, po tym jak pierwsza próba naprawy R3-01 (jeden stały
`REFERENCE_MONTH`) sama okazała się błędem:**

> "nie może być jeden referencyjny miesiąc bo wracamy do odtwarzania
> scenariusza. W 2026 ilość godzin w miesiącu to 160, 168, 176, 184 i z tych
> ma losować symulator." — CC zweryfikował bezpośrednim przeliczeniem:
> dokładnie te cztery wartości (i tylko te) faktycznie występują w 2026.
> **Poprzednia wersja tej sekcji (jeden stały miesiąc) była błędna i została
> zastąpiona: kalkulator liczy zawsze na faktycznie wylosowanym miesiącu
> obiektu, nigdy na jednym stałym (patrz 1.1).** Wcześniejsze "kalkulator
> musi przyjmować maksymalną długość miesiąca czyli 31" (cytat R3 wyżej) jest
> tym samym zastąpione — zamiast zakładać zawsze najgorszy przypadek,
> kalkulator liczy dokładnie na tym miesiącu, który obiekt naprawdę dostał,
> co eliminuje ryzyko niedoboru bez poświęcania zmienności.

**Korekta R6, po tym jak Codex R4-01 znalazł realną niespójność w R5:**
liczenie na faktycznie wylosowanym miesiącu (R5) dawało RÓŻNY wynik dla tego
samego kształtu obiektu w zależności od miesiąca — H24×1/×2 dawało 5/10 w
większości miesięcy, ale 6/11 w styczniu/maju/sierpniu/listopadzie/grudniu
(dowód: `tests_r4.txt`, reproduktor na exact SHA). To przeczyło briefu R5's
własnemu twierdzeniu "wynik jest identyczny niezależnie od miesiąca".

> [rozstrzygnięcie OWNERA] "jeśli kalkulator daje odpowiedzi, że ilość
> obsady to między 10 a 11 zawsze ustawia wyższą liczbę." — kalkulator
> liczy bezpieczne MAKSIMUM po wszystkich 12 miesiącach 2026 dla danego
> kształtu zapotrzebowania (patrz 1.1), nie wynik dla jednego konkretnego
> wylosowanego miesiąca. To daje stały, bezpieczny wynik (nigdy niedobór)
> niezależnie od tego, który miesiąc faktycznie trafi do obiektu przy
> PLAN/REPLAN — `month` nadal jest losowany (prawdziwa zmienność w tym, jaki
> kalendarz/święta widzi solver), tylko już nie decyduje o rozmiarze załogi.

> [druga decyzja OWNERA, na granicę zgłoszoną przez Codexa: R3-02 pomijało
> urlop przy 1 LOCAL, więc nigdy nie testowano ścieżki "jedyny LOCAL idzie na
> urlop → DECISION_REQUIRED → EXTERNAL"] "jeśli jest tylko 1 LOCAL to
> oczywiście musi czasem dostać urlop lub L4" — wyjątek "brak bloku
> urlopowego przy liczba_LOCAL==1" z R3-02 był błędny i jest usunięty (patrz
> 1.2a): jedyny LOCAL dostaje blok urlopowy na tych samych zasadach co
> reszta, właśnie po to żeby ta ścieżka była testowana, nie pomijana.

**Korekta R7, po tym jak OWNER zweryfikował R6's wynik na własnym
referencyjnym obiekcie i złapał kolejny błąd — margines urlopowy zawyżał
dokładnie ten obiekt z 5 do 6 osób:**

> "mój obiekt jest referencyjny dla wyliczenia obsady i ma 5 osób, jeśli
> sztucznie zawyzysz obsadę to dasz fory solverowi. Mój obiekt to 12 h D/N
> jedną osoba na zmianie, jedna tylko dzień." — zweryfikowane przeliczeniem:
> bez marginesu urlopowego, D/N 12h z `required_primary_count=1` daje
> stabilne 5 przez wszystkie 12 miesięcy 2026 (margines, nie liczenie
> per-miesiąc, był przyczyną zawyżenia do 6).

> [po dopytaniu, czy to nadal dotyczy Symulatora, nie logiki solvera] "Tylko
> Symulator" (CC) — potwierdzone: `required_primary_count` to pole
> WYGENEROWANEGO fikcyjnego katalogu zmian (dane wejściowe, które Symulator
> sam tworzy), nie analiza prawdziwego kodu solvera; kalkulator to nadal
> tylko arytmetyka Symulatora sprzed pierwszego PLAN.

> "wyliczenie obsady jest krytycznie ważne, za mało, to solver będzie
> rządać wciąż wsparcia za dużo będzie mieć fory." — dokładne uzasadnienie,
> dlaczego margines jest usunięty CAŁKOWICIE (nie zmniejszony): jedyny sposób
> żeby test miał sens to ciasna, prawdziwa obsada — nieobecności (1.2a) mają
> realnie czasem pchać solver w stronę DECISION_REQUIRED/EXTERNAL, nie trafiać
> zawsze w wygodny zapas, którego margines by gwarantował.

**Zmiana wzoru (1.1):** margines urlopowy (`DNI_URLOPU_ROCZNIE`,
`margines_urlopowy_h`) usunięty całkowicie z kalkulatora. `required_primary_count`
staje się cechą CAŁEGO obiektu (losowany raz, {1,2}), nie osobno per wiersz
katalogu — upraszcza matematykę (nie trzeba rozstrzygać co gdy D i N mają
różne wymagane liczby) i pasuje do referencyjnego przykładu OWNERA, gdzie D i
N mają tę samą wartość. Kalkulator liczy jedną "warstwę" (poziom
`required_primary_count=1`) i mnoży przez wylosowaną wartość — to
odtwarza 5/10 stabilnie, bez marginesu. "Maksimum po 12 miesiącach" z R6
zostaje, ale teraz jako mechanizm WYŁĄCZNIE na niestabilność wynikającą z
realnego kalendarza przy wzorach asymetrycznych (np. "tylko dni robocze"),
nie jako ogólny margines bezpieczeństwa.

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
(sekcja 1.2) — **bez żadnego marginesu bezpieczeństwa** (poprawka R7, patrz
niżej). To NIE jest solver ani drugi algorytm układający dyżury z
uwzględnieniem odpoczynku — to prosta arytmetyka kadrowa, jaką realny
koordynator robi ręcznie, zanim w ogóle otworzy Rotę.

**Wzór (poprawiony po Codex R3-01/R4-01 i trzech kolejnych korektach OWNERA
2026-08-31 — patrz cytaty w sekcji 0, korekty R4/R6/R7).** Historia: R5
liczyła na faktycznie wylosowanym miesiącu, co Codex R4-01 udowodnił jako
niestabilne (5/10 vs 6/11 zależnie od miesiąca). R6 to poprawiło marginesem
urlopowym + maksimum po 12 miesiącach — ale OWNER zweryfikował wynik na
własnym referencyjnym obiekcie (D/N 12h, `required_primary_count=1`, 5 osób)
i złapał, że margines sam windował ten obiekt do 6: **"jeśli sztucznie
zawyzysz obsadę to dasz fory solverowi [...] za mało, to solver będzie
rządać wciąż wsparcia za dużo będzie mieć fory."** R7 usuwa margines
CAŁKOWICIE. Zostają dwa niezależne mechanizmy: (a) `required_primary_count`
to teraz cecha CAŁEGO obiektu (losowana raz, {1,2}), nie per wiersz katalogu
— kalkulator liczy jedną "warstwę" i mnoży przez tę wartość, co odtwarza
5/10 stabilnie, bez marginesu; (b) "maksimum po 12 miesiącach" z R6 zostaje,
ale teraz wyłącznie jako mechanizm na niestabilność wynikającą z realnego
kalendarza dla wzorów ASYMETRYCZNYCH (np. "tylko dni robocze") — nie jako
ogólny margines. `month` (pole `ObjectSpec`) nadal jest losowany, jeden z 12
miesięcy 2026 — służy do tego, JAKI realny kalendarz/święta widzi solver
przy PLAN/REPLAN, nie do ustalenia rozmiaru załogi.

```
# `month` to pole ObjectSpec, losowane jeden z 12 miesięcy 2026 -- używane
# przy PLAN/REPLAN (kalendarz, święta), NIE przy liczeniu rozmiaru załogi.
# `required_primary_count` (1 albo 2) to cecha CAŁEGO obiektu, losowana raz
# -- NIE osobno per wiersz katalogu (R7: upraszcza matematykę, D i N mają tę
# samą wartość, jak w referencyjnym przykładzie OWNERA)

def zapotrzebowanie_jednej_warstwy(katalog, m: date) -> int:
    # katalog opisuje AKTYWNE dni/godziny (1.2), bez required_primary_count
    # -- liczone jakby całe zapotrzebowanie obsługiwała jedna warstwa (1 osoba
    # naraz), required_primary_count mnoży dopiero na końcu
    return sum(
        godziny_zmiany(wiersz) * liczba_wystapien_dnia_tygodnia(dzień, m)
        for wiersz in katalog for dzień in wiersz.aktywne_dni_tygodnia
    )

WSZYSTKIE_MIESIACE_2026 = [date(2026, m, 1) for m in range(1, 13)]

# Bezpieczne maksimum po 12 miesiącach -- ZERO marginesu, tylko realny
# kalendarz/normy; różnica między miesiącami istnieje WYŁĄCZNIE dla wzorów
# asymetrycznych (nie dla "cały tydzień", gdzie każdy miesiąc daje ten sam
# wynik po zaokrągleniu -- patrz przypadki kontrolne niżej)
liczba_jednej_warstwy = max(
    ceil(zapotrzebowanie_jednej_warstwy(wygenerowany_katalog, m)
         / nominal_monthly_hours_kp(m, POLISH_2026_HOLIDAYS))
    for m in WSZYSTKIE_MIESIACE_2026
)
liczba_LOCAL = required_primary_count * liczba_jednej_warstwy
```

**Przypadki kontrolne, przeliczone dla WSZYSTKICH 12 miesięcy 2026, bez
marginesu (Codex R2-01 wymagał: jedna warstwa, dwie pełne warstwy, obiekt
mieszany robocze/weekend):**

| Przypadek | Wynik per miesiąc (I-XII, 2026) | MAKSIMUM = wynik kalkulatora |
|---|---|---|
| D/N 12h, `required_primary_count=1`, cały tydzień | 5,5,5,5,5,5,5,5,5,5,5,5 | **5** (zgadza się z referencyjnym obiektem OWNERA) |
| D/N 12h, `required_primary_count=2`, cały tydzień | 10,10,10,10,10,10,10,10,10,10,10,10 | **10** (= 2×5, zawsze, żadnej niestabilności) |
| D+N 12h, tylko dni robocze, `required_primary_count=1` | 4,3,3,4,4,4,3,4,3,3,4,4 | **4** (jedyny przypadek z realną rozbieżnością — asymetryczny wzór, stąd maksimum) |

Zauważ: przypadek "cały tydzień" (referencyjny obiekt OWNERA i jego
podwójna wersja) jest stabilny na WSZYSTKICH 12 miesiącach bez żadnej
pomocy — margines nie był tam nigdy potrzebny, tylko szkodliwy. Maksimum
faktycznie coś robi wyłącznie dla wzorów asymetrycznych (trzeci wiersz).
Implementer odtwarza powyższe trzy wartości (5/10/4) jako testy jednostkowe
kalkulatora PRZED podłączeniem go do losowego generatora — zgodność z
powyższym jest warunkiem koniecznym, nie orientacyjnym.

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

**Miesiąc (`month`, pole `ObjectSpec`) jest losowany, jeden z 12 miesięcy
2026** (ten sam rok co `POLISH_2026_HOLIDAYS`, żaden nowy kalendarz) — nadal
prawdziwa zmienność, ale (poprawka R6, po Codex R4-01) używana przy
PLAN/REPLAN (realny kalendarz/święta, jakie widzi solver), NIE przy liczeniu
rozmiaru załogi — kalkulator w 1.1 liczy bezpieczne maksimum po wszystkich 12
miesiącach, nie na tym jednym wylosowanym.

Generator losuje NIEZALEŻNIE, dla każdego rodzaju zmiany (D/N/24h), każdego
dnia tygodnia z osobna: czy ta zmiana występuje tego dnia i o jakich
godzinach. `required_primary_count` NIE jest losowany per wiersz (poprawka
R7) — to cecha CAŁEGO obiektu, losowana raz i stosowana jednolicie do
wszystkich wierszy katalogu tego obiektu (patrz 1.1: kalkulator liczy jedną
warstwę i mnoży przez tę jedną wartość). Osobne losowanie per wiersz (wersja
R3-R6) tworzyłoby niejednoznaczność, której referencyjny przykład OWNERA nie
ma (D i N mają tę samą wartość) i której kalkulator nie musiałby rozstrzygać
bez zamieniania się w mini-solver.

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
- **Poprawka R6 — załoga jednoosobowa DOSTAJE urlop, celowo.** R3-02
  wprowadziło wyjątek pomijający blok urlopowy przy `liczba_LOCAL == 1`;
  Codex R4-01 słusznie zauważył, że to wyklucza z testowania dokładnie
  ścieżkę "jedyny LOCAL idzie na urlop → produkt zwraca `DECISION_REQUIRED`
  → EXTERNAL" — realny, ważny przypadek. OWNER wprost: "jeśli jest tylko 1
  LOCAL to oczywiście musi czasem dostać urlop lub L4." **Wyjątek jest
  usunięty**: przy `liczba_LOCAL == 1` jedyny LOCAL dostaje blok urlopowy na
  tych samych zasadach co reszta (ta sama rotacja z seeda — dla jednej osoby
  to po prostu pierwsza pozycja w cyklu, np. zawsze 2-tygodniowy blok).
  Reguła "bloki nigdy się nie pokrywają między pracownikami" jest trywialnie
  spełniona, bo nie ma z kim się nakładać. Implementer NIE dodaje po cichu
  drugiego LOCAL, żeby "zmieścić" wcześniejszą regułę — to nadal naruszałoby
  wynik kalkulatora; poprawka polega na usunięciu wyjątku, nie na obejściu
  liczby osób.
- **Poprawka R7 — kalkulator (1.1) już w ogóle nie ma marginesu urlopowego**,
  więc "budżet 36 dni/rok" nie jest już częścią matematyki kalkulatora —
  36 dni pozostaje wyłącznie uzasadnieniem, SKĄD biorą się realistyczne
  długości bloków (10/5 dni roboczych) w tej sekcji, nie liczbą do
  zbilansowania z czymkolwiek. Świadomie **nie ma kontroli sumy dni w roku**:
  generator absencji tylko odgrywa realistyczne zachowanie koordynatora i
  sprawdza jak solver sobie z tym radzi, na CIASNEJ (bez marginesu) obsadzie
  z 1.1 — to jest właśnie mechanizm, który ma realnie sprawdzić, czy solver
  poprawnie zwraca `DECISION_REQUIRED`/potrzebuje EXTERNAL, a nie trafiać
  zawsze w wygodny zapas (OWNER: "wogóle nie patrzymy na budżet urlopu na
  cały rok, patrzymy jak poradzi sobie solver gdy będą te urlopy"; "za mało,
  to solver będzie rządać wciąż wsparcia za dużo będzie mieć fory").

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
  EXTERNAL — działa tak samo przy `liczba_LOCAL == 1`, jak i przy każdej
  innej liczbie) implementer dobiera sam w ramach TASK_SCOPE — kontrakt tego
  briefu wymaga tylko: prawdziwe losowanie Hypothesis, ~25% szans RAZ na
  obiekt, blok 5-dniowy, nigdy sztywny licznik/harmonogram.

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
| kalkulator obsady BEZ marginesu urlopowego, `required_primary_count` per CAŁY obiekt (nie per wiersz), MAKSIMUM po 12 miesiącach tylko dla wzorów asymetrycznych | OWNER 2026-08-31 R3→R7, poprawia Codex R2-01/R3-01/R4-01 | naga suma godzin/norma dawała 9 zamiast 10; margines z R6 sam zawyżał referencyjny obiekt OWNERA (5→6) — "dasz fory solverowi" | jedna warstwa × `required_primary_count`, zero marginesu; `max()` po 12 miesiącach zostaje wyłącznie dla wzorów asymetrycznych |
| realistyczne bloki urlopowe (2 tyg./tydzień, bez nakładania) zamiast losowej absencji "z sufitu" | OWNER 2026-08-31 R3 | testuje jak solver radzi sobie z zachowaniem koordynatora, nie z budżetem godzin | deterministyczna rotacja bloków z seeda, osobna od kalkulatora |
| L4 losowane probabilistycznie (~25%), nie sztywny licznik | OWNER 2026-08-31 R3 (odrzucił "co 4. grafik") | sztywny licznik to powrót do scenariusza-replay | jeden dodatkowy rzut losowy w generatorze |
| `required_primary_count` zawężony do {1,2} | OWNER 2026-08-31 R3, rozstrzyga Codex R2-02 | szerszy zakres nie testuje nowej ścieżki, tylko wydłuża realny solve i psuje tani profil | stałe dwuwartościowe losowanie |
| jedyny LOCAL TEŻ dostaje blok urlopowy (wyjątek z R3-02 usunięty w R6), L4 losowane raz na obiekt (nie per krok) | Codex R3-02/R4-01, OWNER 2026-08-31 R6 | pierwsza wersja (wyjątek dla 1 osoby) wykluczała testowanie ścieżki "jedyny LOCAL na urlopie → EXTERNAL"; "~25% per obiekt/krok" dawało ~82% nie 25% | usunięcie wyjątku (ta sama rotacja działa dla 1 osoby) + jedno miejsce losowania L4 zamiast dwóch |
| pomiar (nie zgadywanie) liczb profilu Hypothesis, jawne `database=None`, limit EXTERNAL = liczba_LOCAL | Codex R2-03/R3-03 | niezmierzone 20/6 nie miało dowodu taniości (Wariant A: ~750s/20 obiektów) | implementer mierzy mały realny przebieg przed zamrożeniem liczb |
| asercja deklaracja=kalkulacja + zamknięty świat | OWNER 2026-08-30 + Codex R2 (poprawia błędną wersję) | zapobiega "8 osób na obiekcie 5-osobowym" bez fałszywych FAIL | dwa sprawdzenia po każdym przypadku |
| swobodne dni tygodnia/rodzaj zmiany, `required_primary_count` per CAŁY obiekt | OWNER 2026-08-30 + Codex R3, poprawione R7 | usuwa gotowe kształty i nieaktualny zakaz overlapów; `required_primary_count` per wiersz tworzyłby niejednoznaczność bez odpowiednika w referencyjnym przykładzie OWNERA | losowanie niezależne per (dzień, rodzaj), `required_primary_count` losowany raz na obiekt |
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

- **Kalkulator to przybliżenie testowe, nie model kadrowy — i celowo NIE ma
  żadnego marginesu bezpieczeństwa (poprawka R7).** Wcześniejsza wersja
  (R6) dodawała margines urlopowy (24h/mies.), ale OWNER to odrzucił jako
  sztuczne zawyżanie dające solverowi "fory": "za mało, to solver będzie
  rządać wciąż wsparcia za dużo będzie mieć fory" — kalkulator ma dać
  CIASNĄ, prawdziwą obsadę, nie zapas. OWNER wprost: "liczymy jak najlepiej
  potrafimy [...] sprawdzamy poprawność działania mechanizmu", nie
  odtwarzamy realnej polityki kadrowej ZPCh co do dnia.
- **Kalkulator bierze bezpieczne MAKSIMUM po 12 miesiącach (1.1) TYLKO dla
  wzorów asymetrycznych** (np. "tylko dni robocze") — dla symetrycznych,
  "cały tydzień" wzorów (w tym referencyjnego obiektu OWNERA) wynik jest już
  identyczny we wszystkich 12 miesiącach bez potrzeby maksimum, więc to nie
  jest ukryte zawyżanie. Zasada ("zawsze wyższa liczba przy niejednoznaczności")
  to wprost decyzja OWNERA, zastosowana wyłącznie tam, gdzie realny kalendarz
  faktycznie daje różne wyniki — nie jako ogólny margines.
- **Kalkulator (1.1) nie uwzględnia ŻADNEJ absencji — ani urlopu, ani L4**
  (poprawka R7, wcześniej tylko L4 było pominięte, urlop miał margines).
  Świadomie: obie kategorie mają być pokrywane przez losowy generator W
  TRAKCIE przebiegu (1.2a) jako stres-test ciasnej obsady, nie przez
  jednorazowe zawyżenie rozmiaru załogi na starcie.
- **Realne bloki urlopowe (1.2a, 10/5 dni z uzasadnieniem "36 dni/rok ZPCh")
  nie mają żadnego odpowiednika w kalkulatorze (1.1) do zbilansowania** — to
  dwie celowo niezależne rzeczy: 36 dni to wyłącznie uzasadnienie realistycznej
  DŁUGOŚCI bloków, kalkulator o tej liczbie nic nie wie. OWNER wprost:
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
- **Liczby profilu Hypothesis nie są zamrożone w tym briefie** (poprawka po
  Codex R3-03) — implementer je MIERZY na małym realnym przebiegu przed
  zamrożeniem (patrz 1.3), zamiast dostać od autora briefu zgadnięte
  wartości. To świadoma decyzja, nie brakujący element: Codex R3-03 słusznie
  odrzucił wcześniejsze niezmierzone `20/6` jako "profil tani" bez dowodu.

## 8. Pytania do wąskiego re-audytu Codexa (kalkulator bez marginesu, R7)

Zgodnie z `tests_r4.txt`: OWNER podjął obie decyzje z tej rundy, ale po
weryfikacji na własnym referencyjnym obiekcie zmienił jedną z nich ponownie
(margines usunięty całkowicie — R7). R3-03 pozostaje zamknięte. Re-audyt
sprawdza WYŁĄCZNIE poniższe punkty — nie otwierać ponownie zamkniętych
ustaleń (`{1,2}`, granica Symulatora, limit EXTERNAL, profil Hypothesis).

1. **Kalkulator bez marginesu, `required_primary_count` per obiekt (1.1):**
   czy `liczba_LOCAL = required_primary_count × max(...)` (maksimum po 12
   miesiącach 2026 tylko dla jednej-warstwy zapotrzebowania, bez żadnego
   marginesu) jest teraz jednoznaczne, deterministyczne, i czy trzy
   przeliczone wartości (5/10/4) są poprawnie policzone — w szczególności
   czy referencyjny obiekt OWNERA (D/N 12h, `required_primary_count=1`)
   faktycznie daje stabilne 5 na wszystkich 12 miesiącach?
2. **Przeniesienie `required_primary_count` z "per wiersz katalogu" na "per
   cały obiekt" (1.2):** czy ta zmiana jest teraz jednoznaczna i nie
   wprowadza nowej niejasności (np. co z generatorem, który wcześniej miał
   je losować per wiersz — czy TASK_SCOPE/WHERE_MAP nadal się zgadzają)?
3. **Granica `liczba_LOCAL==1` (1.2a, z poprzedniej rundy, bez zmian):** czy
   usunięcie wyjątku — jedyny LOCAL też dostaje blok urlopowy na tych samych
   zasadach co reszta — jest nadal jednoznaczne po zmianach w 1.1/1.2?

Do zamknięcia audytu: **implementacja czeka na PASS Codexa na tym briefie,
potem na Task napisany przez ChatGPT, potem na jawne polecenie "adwokat
diabła" dla CC przed jakimkolwiek kodowaniem.**
