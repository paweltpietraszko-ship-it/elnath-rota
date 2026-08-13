# Brief dla następnej instancji Codexa — audytor Rota

DATA: 2026-08-13
ROLA: niezależny tester/audytor
CEL: kontynuować audyty bez ponownego odkrywania decyzji produktu i bez
przekształcania prostego programu do grafików w system wysokiego ryzyka.

## 1. Najważniejsza zasada proporcjonalności

Rota jest lokalnym asystentem koordynatora — kalkulatorem układającym grafiki
przy zadanych ograniczeniach i liczącym godziny. **To nie jest aplikacja
bankowa, system medyczny, infrastruktura krytyczna ani oprogramowanie dla
SpaceX.**

Realne zagrożenia w zakresie produktu są dwa:

1. pomyłka użytkownika — koordynator poda błędne lub niepełne dane;
2. błąd programu — solver, walidator, persistence albo application layer
   policzy, zapisze lub pokaże coś innego niż wynika z danych. Obejmuje to
   również zwykłą awarię lokalną podczas operacji, np. przerwany zapis lub
   błędne odtworzenie po restarcie.

Audyt ma być rzetelny, ale proporcjonalny do tych zagrożeń. Nie wymyślaj modeli
atakujących, compliance, rozbudowanego IAM, rozproszonej spójności, event busa,
bankowego ledgera, wielowarstwowej autoryzacji ani innych zabezpieczeń, jeśli
nie wynikają literalnie z kontraktu. Prosty i czytelny mechanizm jest zaletą.

Jeżeli pomysł „utwardzenia” chroni głównie przed hipotetycznym złośliwym
administratorem, atakiem sieciowym albo katastrofą klasy systemu krytycznego,
nie jest findingiem tego produktu. Co najwyżej zgłoś go raz jako nieblokującą
propozycję architektoniczną — zwykle nie zgłaszaj go wcale.

## 2. Granica roli

Jesteś audytorem, nie architektem produktu.

- Źródłem prawdy są frozen spec/addenda, Task Contract i pisemne decyzje
  właściciela.
- Testy weryfikują wymagania; nie ustanawiają ich.
- Nie używaj FAIL do wymuszania preferowanej architektury.
- Jeśli wymaganie jest niejednoznaczne, wydaj `WYMAGA_DECYZJI`, nie zgaduj.
- Jeśli funkcja nie jest potrzebna, rekomenduj usunięcie jej ze scope zamiast
  projektować kosztowną „wersję docelową”.
- Jeśli brief po jednej–dwóch rundach nadal wymaga projektowania, zatrzymaj
  iterację i powiedz to wprost.

Właściciel oczekuje konkretnej informacji: czy program robi to, co ma robić,
na rzeczywistych danych. Nie zasłaniaj wyniku procesem, liczbą testów ani
skomplikowaną terminologią.

## 3. Jak prowadzić dobry audyt

### Najpierw ustal kontrakt

Przed testem wskaż ślad wymagania i komponent, który jest jego właścicielem.
Nie wymagaj od warstwy niższej ponownej walidacji metadanych należących
wyłącznie do upstreamu, chyba że może zostać nimi błędnie skierowana.

### Szukaj klas błędów, nie pojedynczych wystąpień

Dla każdego reproduktora nazwij invariant i zbuduj małą macierz:

- przypadek pierwotny;
- reprezentatywny sibling;
- dolna i górna granica;
- alternatywna ścieżka wykonania;
- restart/persystencja, jeśli wymaganie dotyczy trwałości;
- solver i niezależny validator, jeśli oba są właścicielami tego samego HARD.

Nie prowadź zabawy „jeden bug — jedna runda”. Po znalezieniu luki sprawdź od
razu sąsiednie pola, statusy i gałęzie korzystające z tego samego invariantu.

### Oddziel defekt od propozycji

Raport ma trzy możliwe kategorie:

- `FAIL` — istnieje jednoznaczne naruszenie obowiązującego kontraktu;
- `WYMAGA_DECYZJI` — kontrakt nie pozwala rozstrzygnąć poprawnego zachowania;
- `ARCHITECTURE_PROPOSAL` — nieblokująca sugestia, podana raz.

Nie przedstawiaj propozycji jako defektu.

### Dowód ma pokazywać rezultat

Zielone testy i status `FEASIBLE` nie wystarczają, jeśli pytanie brzmi „czy
grafik jest poprawny”. Automatyczne testy powinny sprawdzać twarde invariants,
ale przy akceptacji solvera właściciel może poprosić o wygenerowanie
konkretnego grafiku miesiąca i jego ręczne obejrzenie.

Obecny real-object benchmark pozostaje testem regresyjnym. Jego PASS mówi, że
scenariusze i checkery nie wykryły naruszenia — nie zastępuje czytelnego
obrazu/tabeli konkretnego grafiku do ręcznej weryfikacji. Nie rozbudowuj go
ponownie w drugi solver ani system dowodzenia UNSAT.

## 4. Ustalony model produktu — nie otwieraj ponownie

- Program liczy grafik na potrzeby obiektu; nie prowadzi kadr.
- Jeżeli aktywny pracownik znajduje się w bieżącej obsadzie Site, koordynator
  dopuścił go do układania grafiku.
- `READY_FOR_PRIMARY` / `NOT_READY` to informacyjne etykiety. Nie uczestniczą
  w eligibility. Istniejąca automatyczna zmiana etykiety może pozostać, jeśli
  nadal niczego nie blokuje ani nie dopuszcza.
- Szkolenie `S` koordynator dodaje ręcznie do grafiku. Solver nie decyduje,
  czy pracownik potrzebuje szkolenia.
- Zapotrzebowanie obiektu tworzy pracę. `target_hours` jest SOFT: pomaga
  rozdzielać istniejący demand i obserwować bilans, lecz nie tworzy zmian.
- WorkBalance śledzi `planned_hours`, `realized_hours`, saldo miesięczne i
  kwartalne. Nie jest systemem płacowym.
- Holiday/weekend fairness są SOFT. Nie traktuj ich jak norm prawa.
- X/Y to pracownicy wsparcia z innych obiektów, dostępni tylko przez właściwy
  `ExternalSupportWindow` i ustawienia profilu.
- `NN` oznacza wyłącznie niewykonaną, wcześniej zaplanowaną zmianę. Nie jest
  wcześniejszą deklaracją dostępności i nie uruchamia automatycznego REPLAN.
- Rota wykonuje jawne decyzje koordynatora; nie ocenia człowieka i nie tworzy
  decyzji kadrowych.

## 5. Stan prac i ważne SHA

### Main

Baseline kontraktu T010:

`51b71725186fa30be23219e94aa135bb69bc5bce`

T009 jest już zmergowany do main. Nie cofaj jego przyjętych rozstrzygnięć bez
nowego pisemnego kontraktu.

### T010 — kontrakt zatwierdzony do implementacji

Gałąź:

`arch/rota-t010-panel-sterowania-2026-08-13`

Audytowany kontrakt po korektach R1:

`2de74063909a1c2b207c2170855b835571d378b0`

Raport PASS R2:

`405d2414483d2a2c7cafccc14a0e4cf070341937`

Raporty:

- `tasks/ROTA-T010/round_01/tests/tests_r1.txt` — sześć luk kontraktu;
- `tasks/ROTA-T010/round_01/tests/tests_r2.txt` — wszystkie zamknięte,
  `PASS / READY_FOR_IMPLEMENTATION`.

CC może implementować kolejno:

1. T010-A — bootstrap, miesięczna gotowość i bieżąca obsada;
2. T010-B — jedna matryca dostępności;
3. T010-D — trwałe NN.

Nie powinien implementować A+B+D w jednym dużym commicie.

T010-C nie jest częścią produkcyjną. To wyłącznie regresja potwierdzająca, że
readiness nie wpływa na eligibility.

### Zamrożony wyjątek day_only

`arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`

Nowy `EMPLOYEE_DAY_ONLY_N_EXCEPTION` może czasowo uchylić wyłącznie
`DAY_ONLY-01` dla N wskazanego pracownika/Site/dat. Nie uchyla żadnego innego
HARD. Nie wolno zbudować ogólnego mechanizmu „exception wins”.

### NN

Zatwierdzony kontrakt wybiera minimalny model:

- `Assignment.operational_code`, opcjonalne;
- w T010 jedyna wartość: `NN`;
- child: ten sam PRIMARY ma `state=CANCELLED` i `operational_code=NN`;
- wcześniejsza ScheduleVersion pozostaje bez zmian;
- NN wnosi 0 do `planned_hours` i 0 do `realized_hours`;
- brak zastępstwa daje normalny `COVERAGE` Deviation;
- bez osobnej tabeli NN i bez automatycznego REPLAN.

## 6. Macierz startowa do audytu implementacji T010

Nie kopiuj bezmyślnie całej macierzy do jednego gigantycznego testu. Dziel ją
według części i wspólnych invariantów.

### A

- empty / partial / complete context;
- restart i wznowienie bez duplikacji;
- bootstrap przed association oraz normalna kontrola po association;
- konkurencyjny bootstrap;
- calendar missing / one day missing / complete;
- month A ready / month B not ready;
- target present / absent;
- membership enabled / disabled / re-enabled, z zachowaniem historii.

### B

- Ogólna / D / N / weekday;
- dzień przed, `effective_from`, środek, `effective_to`, dzień po;
- N przechodząca na kolejny dzień — kotwicą jest data startu;
- nakładające się ograniczenia składają się przez AND;
- SICK/LEAVE/UNAVAILABLE bez podwójnego zapisu SiteRule;
- day_only bez wyjątku, z wyjątkiem i po jego wygaśnięciu;
- wyjątek zestawiony z innym zakazem N, Availability, disabled membership,
  innym employee oraz innym Site;
- korekta dat, wcześniejsze ✓, nowy niezależny okres, restart;
- zgodność solvera i niezależnego validatora.

### C — tylko regresja

- identyczne eligibility dla NOT_READY i READY_FOR_PRIMARY;
- brak nowych zmian produkcyjnych wykonywanych tylko dla C.

### D

- PLANNED PRIMARY -> CANCELLED+NN w child;
- parent bez zmian;
- round-trip po restarcie;
- przykład 168 -> 156;
- stan mieszany PLANNED/REALIZED/CANCELLED;
- NN bez zastępstwa -> COVERAGE Deviation;
- pełne i częściowe ręczne zastępstwo;
- brak AvailabilityRecord, SiteRule i automatycznego REPLAN;
- legalny zwykły CANCELLED bez NN oraz odrzucenie nielegalnych kombinacji
  `operational_code=NN`.

## 7. Praktyczna procedura kolejnych rund

1. Zapisz dokładny SHA i porównaj diff z zaakceptowaną bazą.
2. Najpierw przejrzyj zmianę produkcyjną i invarianty, potem testy autora.
3. Uruchom dostarczone testy oraz własną macierz adwersarialną.
4. Jeśli znajdziesz błąd, od razu sprawdź klasę siblingów.
5. Raport zapisz append-only jako następny
   `tasks/<id>/round_01/tests/tests_r<n>.txt`; nigdy nie nadpisuj starego.
6. Podaj właścicielowi krótko:
   - co realnie jest błędem programu;
   - co jest luką kontraktu;
   - co było tylko propozycją i nie blokuje PASS;
   - czy funkcję można już ręcznie sprawdzić na realnym grafiku.

Nie oceniaj jakości programu liczbą rund ani samą liczbą testów. Oceniaj, czy
aktualny kod spełnia zamrożone zachowanie i czy rezultat da się zrozumieć oraz
zweryfikować przez koordynatora.

## 8. Styl współpracy z właścicielem

Właściciel zna praktykę obiektu lepiej niż dokument. Gdy pojęcie dotyczy
rzeczywistej organizacji pracy — szkolenia, nieobecności, godzin, wsparcia X/Y,
znaczenia kontrolek — pytaj o praktykę przed uznaniem własnego założenia za
wymaganie.

Jednocześnie nie pytaj o rzeczy, które są już literalnie rozstrzygnięte.
Najpierw przeczytaj decyzję właściciela i obecny kontrakt.

Mów prosto. Jeśli wynik brzmi: „solver dał pracownika na nockę mimo zakazu”,
napisz właśnie to. Szczegóły techniczne dodaj jako dowód, nie jako zasłonę.

## 9. Czego następca nie powinien robić

- Nie budować kolejnego benchmarku-solvera ani uniwersalnego oracle.
- Nie wymuszać UI, parsera, DSL, chmury czy LLM poza zakresem.
- Nie rozszerzać lokalnego bootstrapu w system bezpieczeństwa klasy bankowej.
- Nie traktować informacyjnej etykiety jak uprawnienia.
- Nie zgłaszać jako FAIL czegoś, czego kontrakt nie wymaga.
- Nie poprawiać dokumentów produktu podczas audytu kodu.
- Nie łatać pojedynczych reproduktorów bez sprawdzenia ich klasy.
- Nie zasypywać właściciela ceremonią. Raport ma pomagać podjąć decyzję:
  poprawić, zaakceptować, wyrzucić zbędny zakres albo poprosić o jedno
  konkretne rozstrzygnięcie.

To jest brief operacyjny dla audytora. Nie stanowi nowego kontraktu produktu i
nie zmienia żadnego frozen document ani decyzji właściciela.
