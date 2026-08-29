# ROTA-T041 — stabilizacja codziennej pracy z grafikiem

Status: **PROJEKT KONTRAKTU DO SPRAWDZENIA PRZEZ CC — BEZ IMPLEMENTACJI**

BASE_MAIN_SHA: `a919a8244cc592e6b12f35b9c8e08b40803e07ec`

Źródła ustaleń:

- `audit/ROTA-AUDIT1` @ `e67f57b292d7a44e460e693e5c44350da5843315`,
  raport `tasks/ROTA-AUDIT1/round_01/tests/tests_r1.txt`;
- decyzje OWNER, Paweł, 2026-08-29, zapisane w sekcji 2;
- obecne zamrożone kontrakty, w szczególności `arch/spec.md`, ROTA-T012,
  ROTA-T022, ROTA-T037 i ROTA-T040.

ROTA-T040 jest już scalone do `main`. T041 nie naprawia ponownie H24. Zachowuje
jedynie mały test, że poprawka H24 nadal działa po zmianach T041.

## 1. Cel opisany zwykłym językiem

Po T041:

1. program rozdziela pracę możliwie sprawiedliwie także wtedy, gdy
   koordynator zapomniał wpisać miesięczną liczbę godzin jednej lub kilku
   osobom;
2. dwie legalne, nakładające się potrzeby obiektu nie powodują fałszywego
   komunikatu o nadmiarowej obsadzie;
3. zwolnienie chorobowe znane przed pierwszym planowaniem liczy po 8 godzin za
   każdy roboczy dzień od poniedziałku do piątku, z pominięciem świąt;
4. po zmianie katalogu zmian kolejne **Plan** pracuje na nowym katalogu i
   tworzy nową wersję roboczą. Stara wersja pozostaje w historii bez zmian;
5. ostrzeżenie o brakującej miesięcznej liczbie godzin naprawdę dociera do
   koordynatora;
6. ręczna korekta i wydruk są jednym ekranem grafiku. Podgląd pokazuje dokładnie
   ten sam plik PDF, który użytkownik może pobrać.

To jest jeden task organizacyjny, ale **nie jeden wielki patch**. Składa się z
trzech kolejnych checkpointów A, B i C. Każdy checkpoint ma osobny logiczny
commit i mały test pionowy. Pełna regresja repozytorium jest uruchamiana raz,
na końcowym SHA.

## 2. Zamrożone decyzje OWNER

### OWNER-T041-01 — sprawiedliwość przy brakującym target_hours

Jeżeli choć jedna dostępna osoba LOCAL nie ma wpisanego `target_hours`, program
nie blokuje przycisku **Plan**, nie zgaduje brakującej wartości i niczego nie
zapisuje za koordynatora.

W takim miesiącu solver ma mimo to rozdzielić rzeczywiste godziny możliwie
równo pomiędzy wszystkie dostępne osoby LOCAL. Techniczna miara tego wyniku to
jak najmniejsza różnica pomiędzy największą i najmniejszą liczbą rzeczywistych
godzin PRIMARY w tej grupie.

- Jeżeli twarde ograniczenia pozwalają na pełną równość, wynik ma być równy.
- Jeżeli urlop, choroba, dyspozycyjność albo inna reguła twarda uniemożliwia
  równość, solver wybiera najmniejszą osiągalną różnicę.
- EXTERNAL_SUPPORT nie uczestniczy w tym porównaniu.
- Osoba całkowicie niedopuszczona do żadnej zmiany przez istniejące twarde
  reguły nie staje się sztucznym uczestnikiem porównania.
- Gdy wszystkie dostępne osoby LOCAL mają target, dotychczasowe bilansowanie
  według targetów działa bez zmian.

Koordynator dostaje po polsku widoczne ostrzeżenie: komu i za jaki miesiąc
brakuje targetu oraz że program użył awaryjnego, równego podziału godzin.

### OWNER-T041-02 — zwolnienie przed pierwszym PLAN

Zwolnienie chorobowe znane przed pierwszym planowaniem miesiąca liczy dokładnie
tak jak obecny urlop przed planowaniem:

- 8 godzin za poniedziałek–piątek, jeżeli dzień nie jest świętem;
- 0 godzin za sobotę, niedzielę i święto.

Zwolnienie wpisane po istniejącym zaakceptowanym grafiku nadal liczy godziny z
rzeczywiście zaplanowanej pracy. T041 nie zmienia tej obecnej zasady.

### OWNER-T041-03 — katalog zmian i nowa wersja robocza

Jeżeli katalog zmian został materialnie zmieniony po utworzeniu bieżącej wersji
roboczej (WORKING), następne użycie **Plan** nie może planować starego obrazu
zapotrzebowania.

Ma powstać świeża wersja robocza z zapotrzebowaniami wyliczonymi z aktualnego
katalogu. Poprzednia wersja i jej zapotrzebowania pozostają w historii bez
mutowania. Nie powstaje przycisk „Odśwież”.

T041 zamyka potwierdzony przypadek C-04: istniejący WORKING nie ma przypisań i
ma pusty albo nieaktualny obraz zapotrzebowania. Istniejące zasady ochrony FINAL,
REALIZED i frozen pozostają bez zmian. Jeżeli wykonawca uzna, że zamknięcie C-04
wymaga zmiany tych zasad, ma zatrzymać implementację i zgłosić konkretną
sprzeczność zamiast wymyślać migrację historii.

### OWNER-T041-04 — korekta i wydruk razem

Ręczna korekta oraz wydruk są jednym ekranem grafiku. Zachowujemy istniejące
skróty nawigacyjne „Ręczna korekta” i „Wydruk Grafiku”, ale oba prowadzą do tego
samego istniejącego ekranu planowania:

- wejście przez „Ręczna korekta” pokazuje prostą polską instrukcję i od razu
  udostępnia istniejącą korektę przez kliknięcie wpisu w grafiku;
- wejście przez „Wydruk Grafiku” otwiera ten sam ekran z widoczną istniejącą
  częścią wydruku;
- pozostałe ekrany i pozycje nawigacji nie są łączone, usuwane ani zmieniane w
  T041.

Podgląd PDF ma używać tych samych bajtów z jednego wywołania istniejącego
generatora, co pobierany plik. Kliknięcie „Pobierz” nie może po cichu generować
drugiego, potencjalnie innego PDF.

## 3. Dlaczego jeden task, ale trzy checkpointy

Oddzielne taski zwiększyłyby liczbę przekazań i audytów, choć wszystkie cztery
decyzje stabilizują ten sam codzienny przebieg: ustawienia → Plan → korekta →
wydruk. Jeden monolityczny commit byłby jednak trudny do sprawdzenia i łatwo
ukryłby przyczynę regresji.

Dlatego obowiązuje kolejność:

1. **Checkpoint A — wynik solvera:** sprawiedliwe godziny i nakładające się
   zapotrzebowania;
2. **Checkpoint B — dane wejściowe i wersja robocza:** zwolnienie przed PLAN i
   świeży WORKING po zmianie katalogu;
3. **Checkpoint C — to, co widzi koordynator:** ostrzeżenie, wspólny ekran
   korekty/wydruku i podgląd dokładnie pobieranego PDF.

CC nie zaczyna następnego checkpointu, dopóki mały test pionowy bieżącego nie
jest zielony. Bez refaktoryzacji pomiędzy checkpointami.

## 4. Checkpoint A — poprawny i sprawiedliwy wynik

### 4.1 Brak targetu

Wykorzystać istniejących właścicieli:

- assembler nadal wykrywa brak targetu;
- solver/fairness nadal są jedynym miejscem wyboru sprawiedliwszego kandydata;
- żadna warstwa nie tworzy zastępczego targetu.

Minimalna macierz:

- **T41-A01:** 5 dostępnych LOCAL, 720 godzin pracy, cztery targety i jeden
  brakujący; jeżeli HARD pozwala, wynik to 144/144/144/144/144;
- **T41-A02:** brakuje więcej niż jednego targetu — wszystkie dostępne LOCAL
  nadal uczestniczą w równym podziale;
- **T41-A03:** wszystkim wpisano target — obecne TARGET-01 i targetowa equity
  zachowują wyniki;
- **T41-A04:** jedna osoba ma twardą niedostępność — solver osiąga najmniejszą
  możliwą różnicę, ale nie łamie niedostępności;
- **T41-A05:** EXTERNAL_SUPPORT nie jest wliczany do lokalnego rozkładu;
- **T41-A06:** wynik każdego przypadku przechodzi produkcyjne `validate()`.

Test nie może wpisywać wynikowego grafiku ręcznie ani wybierać wygodniejszej
liczby pracowników. Ma przejść przez realne składanie stanu i solver.

### 4.2 Legalne nakładanie zapotrzebowań

AUDIT-1 C-03 potwierdził błąd: 10 legalnych demandów, 10 różnych pracowników,
każde przypisanie dokładnie do własnego demandu; obecny validator zgłaszał dla
każdego fałszywy nadmiar 2/1 tylko dlatego, że przedziały czasowe się
nakładały.

T041 nie może naprawić tego przez ślepe zaufanie do samego
`covers_demand_id`. ROTA-T022 wymaga, aby ręczne/spanning PRIMARY nadal było
sprawdzane według rzeczywiście pokrytego czasu, a fałszywy tag nie mógł ukryć
H24 albo reguł obiektu.

Wymagane wyniki:

- **T41-A07:** dwa legalne, nakładające się demandy po jednej osobie i dwie
  różne, prawidłowo przypisane osoby — PASS;
- **T41-A08:** te same dwa demandy i tylko jedna osoba — undercoverage, FAIL;
- **T41-A09:** jeden demand wymagający jednej osoby i dwie równoczesne osoby
  PRIMARY pokrywające go — excess coverage, FAIL;
- **T41-A10:** fałszywy `covers_demand_id`, którego przedział przypisania nie
  pokrywa — FAIL;
- **T41-A11:** zaakceptowane przez ROTA-T022 ręczne PRIMARY obejmujące
  sąsiadujące segmenty nadal jest oceniane według rzeczywistego czasu;
- **T41-A12:** zabezpieczenie ROTA-T022 dla dwóch połówek H24 i złośliwego tagu
  pozostaje zielone.

Brief zamraża wyniki tej macierzy, nie nowy algorytm. Validator pozostaje jednym
właścicielem COVERAGE-01; nie wolno budować drugiego walidatora w API ani UI.

## 5. Checkpoint B — L4 i świeża wersja robocza

### 5.1 Zwolnienie chorobowe przed PLAN

Należy rozszerzyć istniejący mechanizm referencji urlopu przed planowaniem,
zamiast tworzyć nowy kalkulator chorobowego.

Minimalna macierz:

- **T41-B01:** SICK w zwykły poniedziałek przed pierwszym PLAN = 8 h;
- **T41-B02:** SICK w sobotę albo niedzielę = 0 h;
- **T41-B03:** SICK w święto przypadające pon.–pt. = 0 h;
- **T41-B04:** zakres wielodniowy jest sumą powyższych dni;
- **T41-B05:** zapis dyspozycyjności przez prawdziwy endpoint, a następnie
  pierwszy PLAN, nie kończy się HTTP 500;
- **T41-B06:** SICK po istniejącym planie nadal używa godzin rzeczywiście
  zaplanowanych;
- **T41-B07:** obecne pierwszeństwo SICK względem LEAVE i odczyt po restarcie
  pozostają bez zmian;
- **T41-B08:** wydruk nadal rozpoznaje rodzaj nieobecności jako chorobowe; T041
  nie dodaje oznaczeń do solvera.

Wewnętrzna historyczna nazwa źródła `PRE_PLAN_LEAVE` może pozostać dla zgodności
danych. Nie powstaje nowa wartość w bazie, migracja ani nowy rodzaj DTO tylko z
powodu nazwy technicznej.

### 5.2 Nowy WORKING po zmianie katalogu

Należy wykorzystać istniejące wersjonowanie ScheduleVersion oraz istniejące
generowanie demandów z katalogu.

Minimalna macierz:

- **T41-B09:** pierwszy PLAN przy pustym katalogu tworzy pusty WORKING;
- **T41-B10:** koordynator zapisuje zwykły katalog D/N; następny PLAN tworzy
  nowy WORKING z demandami aktualnego katalogu i daje się zaplanować;
- **T41-B11:** stary WORKING nadal istnieje w historii i nadal ma swój stary
  snapshot; żadnego jego wiersza nie zmieniono;
- **T41-B12:** ponowne PLAN bez materialnej zmiany katalogu nie tworzy kolejnej
  wersji tylko dla samego numeru wersji;
- **T41-B13:** zachowanie FINAL pozostaje dotychczasowe — PLAN nie mutuje FINAL,
  a ścieżka wymagająca REPLAN nadal wymaga REPLAN;
- **T41-B14:** w przypadku błędu utworzenie nowego WORKING nie zostawia
  przesuniętego current pointer ani częściowo zapisanej historii.

Nie wolno dodawać przycisku/endpointu „Odśwież”, fingerprintu w bazie ani
mutować demandów w starej wersji.

## 6. Checkpoint C — informacja, korekta i wydruk

### 6.1 Ostrzeżenie o brakującym targecie

Istnieją już `warnings` w odpowiedzi miesiąca i istnieje miejsce na banner we
frontendzie. Najpierw trzeba naprawić rzeczywiste przejście istniejącej
wiadomości przez produkcyjny łańcuch. Nie dodawać drugiego pola odpowiedzi.

- **T41-C01:** po PLAN z brakującym targetem koordynator widzi polski komunikat
  z osobą, miesiącem i informacją o awaryjnym równym podziale;
- **T41-C02:** komunikat jest widoczny również po odświeżeniu strony;
- **T41-C03:** po uzupełnieniu wszystkich targetów komunikat znika, a solver
  wraca do targetowego bilansowania;
- **T41-C04:** ostrzeżenie nie jest fałszywie pokazywane dla EXTERNAL_SUPPORT.

### 6.2 Jeden ekran grafiku

Należy wykorzystać istniejący `MonthlyPlanning`, istniejące operacje ręcznej
korekty i istniejący osadzony fragment `Export`.

- **T41-C05:** oba skróty nawigacyjne otwierają ten sam ekran i ten sam wybrany
  obiekt/miesiąc;
- **T41-C06:** wejście przez „Ręczna korekta” pokazuje instrukcję i pozwala
  wykonać istniejącą korektę przez produkcyjny endpoint; historia wersji działa
  jak dotychczas;
- **T41-C07:** wejście przez „Wydruk Grafiku” pokazuje na tym samym ekranie
  część wydruku bez tworzenia osobnego ekranu;
- **T41-C08:** podgląd PDF i pobranie używają jednego zestawu bajtów z jednego
  wywołania istniejącego endpointu eksportu;
- **T41-C09:** błąd generowania pokazuje istniejący komunikat i pozwala ponowić;
  nie pozostawia starego podglądu podpisanego jako nowy;
- **T41-C10:** ustawienia wydruku pozostają w „Panel sterowania → Obiekt”;
- **T41-C11:** pozostałe ekrany nawigacji są niezmienione.

Nie powstaje nowy backend korekty, nowy generator PDF, nowy model ustawień ani
nowa lista okien wsparcia.

## 7. PREIMPLEMENTATION REDUCTION GATE — wynik

| Proponowany element | Źródło w PRODUCT_TRUTH | Dlaczego jest konieczny | Wynik redukcji |
|---|---|---|---|
| Fallback równego podziału | OWNER-T041-01 + AUDIT C-05 | wynik widoczny dla koordynatora | mała zmiana w istniejącym ownerze fairness/solver; bez targetu zastępczego |
| Poprawka COVERAGE-01 | spec/T012/T022 + AUDIT C-03 | walidator dziś odrzuca legalny grafik | jeden owner w validatorze; bez walidacji w API/UI |
| SICK przed PLAN | OWNER-T041-02 + AUDIT C-02 | zapis L4 dziś może skończyć się 500 | rozszerzyć istniejący mechanizm pre-plan; bez kalkulatora i migracji |
| Świeży WORKING | OWNER-T041-03 + AUDIT C-04 | PLAN używa starego snapshotu | minimalny adapter w plan_ops do istniejącego generatora i lifecycle |
| Ostrzeżenie | OWNER-T041-01 + AUDIT C-05 | koordynator musi wiedzieć o braku danych | wykorzystać istniejące `warnings` i banner; zero nowego pola DTO |
| Tryb wejścia ekranu | OWNER-T041-04 | dwa skróty mają otwierać tę samą treść | mały stan UI/parametr do istniejącego MonthlyPlanning |
| Podgląd PDF | OWNER-T041-04 | użytkownik ma obejrzeć dokładnie pobierany plik | zachować jeden istniejący response jako Blob; bez nowego endpointu |
| Testy T041 | ten brief | dowód nowych szwów i klas błędów | po jednym module na checkpoint; nie kopiować pełnych macierzy niższych warstw |

### Elementy świadomie usunięte z propozycji

- nowe encje, tabele, migracje i pola API;
- nowy target wyliczany albo zapisywany przez generator;
- blokowanie PLAN z powodu brakującego targetu;
- osobny kalkulator SICK;
- przycisk lub endpoint „Odśwież katalog”;
- mutowanie starego WORKING lub FINAL;
- drugi ekran ręcznej korekty, drugi ekran wydruku i drugi generator PDF;
- zmiana COVERAGE oparta wyłącznie na ślepym zaufaniu do tagu;
- refaktoryzacja solvera, validatora, routingu albo komponentów „przy okazji”;
- nowe benchmarki, generator załogi lub syntetyczne dane użytkownika.

## 8. TASK_SCOPE

TASK_SCOPE:
- rota/application/assembler.py
- rota/planning/fairness.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/application/plan_ops.py
- rota/persistence/absence_reference_repository.py
- frontend/src/screens/Room.tsx
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/screens/Export.tsx
- tests/test_t041_checkpoint_a.py
- tests/test_t041_checkpoint_b.py
- frontend/e2e/t041-daily-workflow.spec.ts

To jest maksymalny dozwolony zakres, a nie polecenie dotknięcia każdego pliku.
Wykonawca ma usuwać niepotrzebne pliki z własnego planu, nie poszerzać zakres.

Dozwolone jest pozostawienie danego pliku bez zmian, jeżeli istniejący seam
wystarcza. Zmiana jakiegokolwiek innego pliku produktu wymaga zatrzymania i
krótkiego wskazania konkretnego blokera przed edycją.

## 9. Zakres zabroniony

- schema/domain i migracje bazy;
- nowe endpointy oraz zmiana publicznych kształtów odpowiedzi;
- `rota/planning/constraints.py`, work-period/H24, REST, NIGHT-STREAK i T040;
- nowe typy nieobecności albo oznaczenia U/C w solverze;
- EXTERNAL_SUPPORT i jego okna;
- pozostałe ekrany analityczne/audytowe/decyzyjne;
- zmiana znaczenia FINAL, REALIZED albo frozen;
- benchmarki i property generator/symulator koordynatora;
- porządki, przenoszenie plików, zmiany nazw i szeroki refaktor.

## 10. Sposób wykonania i dowody

### Commit A

Tylko Checkpoint A. Uruchomić `tests/test_t041_checkpoint_a.py` oraz wąskie
istniejące regresje T022 coverage/H24 i T040 H24. Nie uruchamiać pełnej suity.

### Commit B

Tylko Checkpoint B. Uruchomić `tests/test_t041_checkpoint_b.py` oraz wąskie
istniejące testy referencji nieobecności i lifecycle. Nie uruchamiać pełnej
suity.

### Commit C

Tylko Checkpoint C. Uruchomić `frontend/e2e/t041-daily-workflow.spec.ts`,
TypeScript check i frontend build. Repo ma już Playwright, więc test C ma przejść
przez prawdziwy router i realny frontendowy przepływ; nie wolno dowodzić funkcji
samym sprawdzaniem tekstu źródła.

### Końcowy SHA

Na końcu:

1. wszystkie trzy moduły T041;
2. wskazane wąskie regresje właścicieli;
3. jeden pion: backendowe ustawienia → PLAN → validate/select → odczyt miesiąca
   z warningiem → ręczna korekta → eksport tych samych bajtów PDF;
4. pełna suita repozytorium dokładnie raz.

AUDIT-1 na starym baseline miał 3 znane, sklasyfikowane stare failures i 1228
passed. Końcowa bramka wymaga braku **nowych** regresji względem dokładnie
udokumentowanego baseline'u; nie wolno przepisywać starych oczekiwań tylko po
to, aby uzyskać napis „0 failed”. Po ROTA-T040 baseline mógł się zmienić, więc
raport ma podać dokładne nazwy każdej pozostałej porażki i jej klasyfikację.

Stare benchmarki nie są dowodem T041 i nie mają być uruchamiane. Symulator
koordynatora również nie jest potrzebny do odbioru tego tasku.

## 11. Warunki zatrzymania

CC ma zatrzymać pracę przed implementacją i zgłosić problem, jeżeli:

- którakolwiek sekcja wymaga nowego zachowania widocznego dla użytkownika,
  którego nie ma w OWNER-T041-01..04;
- C-03 nie da się naprawić bez złamania ROTA-T022;
- świeży WORKING wymaga mutacji historii albo zmiany ochrony FINAL/REALIZED;
- prawdziwy warning wymaga nowego publicznego pola zamiast istniejącego
  `warnings`;
- wspólny ekran wymaga nowego backendu zamiast istniejących operacji;
- przewidywany zakres wychodzi poza `TASK_SCOPE`.

Nie należy zamieniać tych blokad w kolejne rundy projektowania przez CC.

## 12. Pytania do CC przed implementacją

CC ma sprawdzić kontrakt, nie pisać jeszcze kodu, i odpowiedzieć krótko:

1. Czy każdy punkt da się zrealizować przez wskazanych istniejących ownerów bez
   nowej encji, endpointu, pola DTO albo migracji?
2. Czy macierz A07–A12 jednocześnie naprawia legalne nakładanie i zachowuje
   wcześniejsze zabezpieczenia ROTA-T022?
3. Czy B09–B14 da się zamknąć istniejącym lifecycle dla potwierdzonego pustego
   WORKING bez zmiany FINAL/REALIZED/frozen?
4. Czy `warnings` i obecny banner rzeczywiście wystarczają po naprawieniu seam?
5. Czy oba skróty mogą użyć istniejącego MonthlyPlanning i Export bez drugiego
   ekranu oraz backendu?
6. Czy któryś dozwolony plik można usunąć z zakresu?

Oczekiwana odpowiedź:

- `CONTRACT_OK — READY FOR CODEX PREIMPLEMENTATION AUDIT`, albo
- krótka lista konkretnych sprzeczności z `plik:linia` i numerem punktu briefu.

Do tego czasu: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.
