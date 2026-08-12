# ELNATH ROTA — CHECKPOINT 2026-08-09

STATUS: punkt wznowienia projektu po zamknięciu architektury v0.3  
JĘZYK: skrót decyzyjny / dokumentacja robocza

---

## 1. CEL PRODUKTU

Elnath Rota ma być prostym lokalnym programem do układania i korygowania grafików pracy małych firm.

Pierwszy pilot:
- ochrona;
- jeden realny obiekt;
- lokalny Windows desktop;
- praca offline / lokalna baza;
- bez AI w rdzeniu planowania;
- koordynator pozostaje ostatecznym decydentem.

Program ma zastąpić ręczne / Excelowe grafiki bez odbierania koordynatorowi kontroli.

---

## 2. ZAMROŻONE ŹRÓDŁA

Produkt:
- `ELNATH_ROTA_SPEC_PRODUKTOWA_v0.17_PL_CANDIDATE.md`

Architektura:
- `ELNATH_ROTA_ARCHITEKTURA_v0.3_CANDIDATE.md`
- wynik ostatniego kontraktowego audytu DeepSeek: PASS
- BLOCKERS: 0
- MAJORS: 0

Architektury dalej nie audytujemy, dopóki rzeczywisty przypadek produktu jej nie sfalsyfikuje.

---

## 3. ZASADA ARCHITEKTURY

Szkielet:

```text
ROTA CORE
    ↓
SITE PROFILE
    ↓
SITE
```

Dla pilota:
- `SiteProfile = OCHRONA`
- jeden Site
- jeden Coordinator w UI

Architektura nie koduje jednak kardynalności = 1.

Znane rozszerzenia, które konstrukcja ma przyjąć bez przebudowy Core:
- drugi obiekt OCHRONA;
- kilku koordynatorów;
- przyszły profil SKLEP.

Nie budujemy teraz:
- uniwersalnego solvera branżowego;
- plugin systemu;
- mikroserwisów;
- event busa;
- enterprise permission hierarchy;
- SaaS;
- ogólnego rule engine;
- systemu HR/płacowego.

---

## 4. PRAWO I AUTORYTET KOORDYNATORA

Nie ma wymagania typu „lista kwalifikowanych pracowników ochrony” dla pierwszego obiektu.

Rota:
- ma automatycznie układać grafik zgodnie z obowiązującymi regułami prawa pracy;
- nie projektuje solvera do automatycznego łamania prawa;
- ma wykrywać konflikt prawny;
- ma pokazywać koordynatorowi, dlaczego przypisanie jest problematyczne.

Koordynator może ręcznie zapisać decyzję naruszającą regułę.
Program:
- nie blokuje takiej ręcznej decyzji;
- ostrzega;
- zapisuje odstępstwo;
- wymaga świadomego potwierdzenia przy finalizacji wersji z odstępstwami.

To jest narzędzie decyzyjne, nie nadrzędny decydent.

---

## 5. PODSTAWOWY MODEL PILOTA OCHRONA

Standardowy automat planuje:
- `D` = 05:00–17:00;
- `N` = 17:00–05:00 następnego dnia;
- jedna PRIMARY obsada na wymagany przedział.

Zapotrzebowanie obiektu jest pierwsze.
Solver nie tworzy godzin po to, aby dobić pracownikom normę.

Rozróżniamy:
- `CEL_GODZIN`;
- `GODZINY_ZAPLANOWANE`;
- `GODZINY_ZREALIZOWANE`;
- miesięczny / kwartalny bilans operacyjny.

Cel godzin jest parametrem planistycznym, nie bezwzględnym limitem.

---

## 6. REALNE WYJĄTKI, KTÓRE MODEL MUSI OBSŁUŻYĆ

### TYLKO_DNIÓWKI
- przełączalne ograniczenie pracownika;
- automat nie daje N;
- koordynator może wyłączyć lub świadomie odstąpić.

### Wolne / niedostępność
- `DAY_SHIFT_OFF`: automat nie daje D, N może być możliwe;
- `UNAVAILABLE_24H`: automat nie daje żadnego kolidującego Assignment;
- ręczne odstępstwo pozostaje możliwe.

### Urlop
- `LEAVE_PLAN`: informacja / ostrzeżenie, nie automatyczna blokada;
- `LEAVE_GRANTED`: automat nie przypisuje;
- ręczne odstępstwo koordynatora jest możliwe i jawne.

### Szkolenie S
- S nie jest trzecią normalną zmianą;
- trainee jest dodatkową osobą;
- nie pokrywa PRIMARY;
- godziny S liczą się do czasu pracy trainee;
- koordynator dopisuje S do istniejącej zmiany PRIMARY mentora i określa konkretne godziny szkolenia; dzień/D/N/mentor wynikają z wybranej zmiany;
- dwa ZREALIZOWANE S → domyślnie gotowy do samodzielnej pracy;
- koordynator może nadpisać gotowość;
- REPLAN nie przesuwa szkolenia samodzielnie.

### Wsparcie X/Y
- pracownicy z innego obiektu;
- nie modelujemy ich macierzystego HR/grafiku;
- stają się kandydatami wyłącznie w potwierdzonych zakresach;
- jeden pracownik może mieć kilka zakresów dostępności;
- automat nie dodaje X/Y poza potwierdzonym zakresem.

### Ręczne rzeczywiste godziny
Rota musi zapisać stan faktyczny, np.:
- A 05:00–13:00;
- B 13:00–17:00;
albo nawet:
- A 05:00–13:00;
- 13:00–17:00 brak obsady.

Brak pokrycia jest wynikiem walidacji / odstępstwem, nie zakazem zapisania rzeczywistości.

---

## 7. WERSJONOWANIE

`ScheduleVersion` = kompletny stan miesiąca jednego obiektu.

Zasady:
- FINAL jest niemutowalny;
- materialna zmiana lub REPLAN po FINAL tworzy nowy WORKING child;
- poprzednia wersja pozostaje w historii;
- zrealizowane Assignments przechodzą semantycznie bez zmian;
- zamrożone przyszłe Assignments pozostają;
- planowane szkolenia S pozostają;
- przyszłe niezrealizowane i niezamrożone PRIMARY mogą być rozdzielone ponownie;
- jedna wersja jest current dla `(site, month)`.

Godziny operacyjne liczymy z current versions, nie sumujemy historycznych kopii.

---

## 8. WYNIK PLANOWANIA

PlanningEngine ma trzy operacje:

### precheck
Wczesne wykrycie oczywistego braku ludzi.
Nie ogłasza FEASIBLE.

### plan
Status:
- `FEASIBLE`;
- `DECISION_REQUIRED`;
- `TECHNICAL_ERROR`.

`FEASIBLE` może zawierać:
- N,N;
- D,D;
- przekroczenie celu godzin;
- inne dopuszczone kompromisy / ostrzeżenia.

Musi zwracać rzeczywiste proponowane Assignments.

### validate
Sprawdza istniejący / ręczny grafik bez przebudowywania go.

Ręczna decyzja koordynatora nie jest automatycznie cofana.

---


## 8A. DOMKNIĘCIE KONTRAKTU SOLVERA PO RĘCZNYCH PRZEBIEGACH 2026-08-10

Ręczne przebiegi grafiku potwierdziły podstawową pipeline planowania i ujawniły miejsca wymagające jawnych decyzji właściciela. Ustalenia:

- pilotowy obiekt planuje podstawową obsadę z puli 5 pracowników A–E;
- każda wymagana D/N musi być pokryta w 100%;
- N,N jest dopuszczalne; brak osobnego limitu „liczby zmian w tygodniu”;
- minimum odpoczynku operacyjnie przyjęte dla kontraktu: 11 h między zmianami;
- solver może zwrócić do 3 pełnych poprawnych propozycji zamiast sam wybierać jeden ostateczny grafik;
- koordynator wybiera propozycję w UI;
- weekend fairness jest SOFT: im bliżej idealnie równego podziału pracy weekendowej, tym lepsza ocena wariantu;
- holiday fairness jest SOFT i historyczne: solver automatycznie korzysta z `CalendarDay(holiday=true)` oraz zapisanej historii `Assignment` i preferuje warianty zmniejszające nierówność pracy świątecznej; nie jest to zasada prawa pracy;
- `PlanningEngine` nie odczytuje sam CSV/JSON z kalendarzem; warstwa kalendarza rozwiązuje święta przed planowaniem i przekazuje gotowe dane w `PlanningState`;
- S jest dopisywane do już istniejącej zmiany PRIMARY mentora; REPLAN nie może sam rozbić tej decyzji szkoleniowej;
- kontrola ekstremalnego obciążenia działa w KAŻDYM ruchomym oknie 7 kolejnych dni, nie w tygodniu kalendarzowym;
- `>60 h` pracy pracownika w dowolnych 7 kolejnych dniach uruchamia bramkę decyzji koordynatora; `60 h` samo w sobie jej nie uruchamia;
- solver sumuje rzeczywiste godziny Assignment w oknie, nie wyłącznie liczbę D/N;
- X/Y, ściągnięcie z wolnego/urlopu, wyłączenie chronionego ograniczenia i akceptacja krytycznego obciążenia są decyzjami koordynatora, nie solvera.

### Pipeline krytyczna

```text
PlanningState
    ↓
precheck
    ↓
plan
    ├─ FEASIBLE → 1..3 pełne propozycje → wybór Koordynatora → zapis/finalizacja
    ├─ DECISION_REQUIRED → blokery + opcje odblokowania HARD
    │                       ↓
    │                  decyzja Koordynatora
    │                       ↓
    └──────────────────── ponowny plan

TECHNICAL_ERROR = rzeczywista awaria techniczna, nie brak obsady.
```

`DECISION_REQUIRED` nie jest terminalnym FAIL. Oznacza granicę autonomii deterministycznego solvera. Solver ma wyjaśnić, dlaczego aktualna obsada nie daje akceptowalnego pełnego grafiku, i przedstawić wyłącznie dozwolone drogi odblokowania. Nie wybiera żadnej sam.

Najważniejszy przypadek akceptacyjny: 5-osobowa obsada, jednocześnie 1 osoba na urlopie, 1 na wolnym i 1 wypada około tygodnia przez chorobę. Jeżeli pozostali mogą technicznie pokryć 100% zmian tylko przez przekroczenie 60 h w ruchomych 7 dniach, solver zwraca `DECISION_REQUIRED`, nie zwykłe `FEASIBLE`.

### Pełna wersja / PWA

Najczęstszą przyczyną REPLAN w praktyce jest choroba; sporadycznie no-show. Pełna wersja produktu ma mieć PWA pozwalające koordynatorowi poza biurem co najmniej: wprowadzić nagłą niedostępność, uruchomić REPLAN, zobaczyć FEASIBLE candidates albo DECISION_REQUIRED, podjąć decyzję i zatwierdzić wariant. PWA pozostaje poza zakresem pierwszego pilota desktopowego.

## 9. REALNE GRAFIKI — NOWE ŹRÓDŁO PROJEKTOWE

### Lipiec 2026
Zdjęcie rzeczywistego grafiku:
- norma / etat 184 h;
- korekta 15.07.2026;
- widoczne D/N;
- widoczne szkolenia S;
- liczba osób większa niż testowe A–E;
- okres urlopowy powoduje użycie większej puli ludzi;
- grafik jest nieregularny i zmieniany w trakcie miesiąca.

Wniosek:
UI nie może być projektowane pod pięć równych syntetycznych wierszy.

### Kwiecień 2026 — ROYALPACK / APEXIM
To jest przykład DOMYŚLNEGO firmowego formatu Excelowego.

Poprzedni lipcowy arkusz był przygotowany przez osobę zastępującą koordynatora i nie reprezentuje standardowego firmowego układu.

Kwietniowy arkusz pokazuje:
- miesięczną macierz: pracownik × dzień;
- rozbudowaną legendę kodów;
- warianty D/N;
- U = urlop;
- C = chorobowe;
- różne warianty godzinowe kodów;
- podsumowania godzin;
- układ nastawiony na wydruk / dokument firmowy.

Najważniejszy problem UX:
legenda zawiera pełny słownik funkcjonujący w firmie, przez co zajmuje dużo miejsca i utrudnia odczyt.

ZAMROŻONA ZASADA ROTA:
> Legenda miesięcznego widoku / wydruku pokazuje WYŁĄCZNIE symbole faktycznie użyte w tej konkretnej wersji grafiku.

Pełny słownik symboli może istnieć w konfiguracji obiektu, ale nie jest drukowany automatycznie.

---

## 10. UI — KIERUNEK

Głównym ekranem Rota ma być GRAFIK, nie dashboard.

Mentalny model koordynatora:

```text
pracownicy ↓  ×  dni miesiąca →
```

Główny widok powinien zachować znajomy układ macierzy miesięcznej.

Informacje dodatkowe:
- Godziny;
- Wolne / urlopy;
- Zasady obiektu;
- Konflikty / odstępstwa;
- Wersje.

Nie powinny wypierać głównego grafiku.

Wydruk:
- znajomy dla firmy;
- czytelny;
- legenda tylko użytych kodów;
- bez listy odstępstw, powodów i historii decyzji.

---

## 11. FRONT DO REUSE — CONTINUITY AI

Repo:
`paweltpietraszko-ship-it/continuity-ai`

Sprawdzony branch:
`ui/project-report-polish-v0.4`

Istniejący desktop:
- React 18;
- TypeScript;
- Vite;
- Tauri 2.

Elementy potencjalnie do reuse:
- App shell;
- topbar;
- `← Workspace`;
- Workspace jako HUB;
- lista obiektów;
- page shell;
- przyciski;
- panele / drawers;
- ogólny język wizualny.

Mapowanie:

```text
Continuity AI           -> Elnath Rota
Workspace               -> Obiekty
Project                 -> Obiekt
Current Report          -> Miesiąc / aktualny grafik
Project state           -> stan grafiku
Sources/rules drawer    -> zasady / dane wejściowe
Finding/attention       -> konflikty / odstępstwa
```

Nie przenosimy:
- Conversation AI drawer;
- Vault UI;
- filmowego modelu raportu Continuity.

Środek aplikacji Continuity ma zostać zastąpiony miesięczną macierzą grafiku.

---

## 12. RZECZYWISTE GRAFIKI JAKO FIXTURES

Kolejne zdjęcia prawdziwych grafików są potrzebne nie po to, by rozszerzać architekturę, lecz żeby sprawdzić UI i przypadki akceptacyjne.

Najbardziej wartościowe:
- zwykły spokojny miesiąc;
- miesiąc urlopowy;
- choroba / korekta w trakcie;
- brak obsady / zastępstwa;
- nietypowe warianty godzin;
- różne zestawy symboli używane w praktyce.

Kryterium:
> Rota ma umieć odwzorować rzeczywisty miesiąc bez specjalnego kodu pod konkretny arkusz.

---

## 13. NASTĘPNY ETAP

NIE:
- dalszy audyt architektury;
- kolejna wersja v0.4 bez falsyfikacji;
- projektowanie Ward;
- wybór solvera;
- rozbudowa pod enterprise.

TAK:
1. zebrać kilka rzeczywistych grafików;
2. wyciągnąć z nich realny język pracy koordynatora;
3. przygotować `UI CONTRACT v0.1`:
   - mapa widoków;
   - główna macierz;
   - kliknięcia / edycje;
   - konflikty;
   - wersje;
   - wydruk;
4. przygotować mały zestaw rzeczywistych acceptance scenarios;
5. dopiero potem przekazać zamrożony pakiet implementacyjny do Elnath Ward.

---

## 14. PAKIET DO PÓŹNIEJSZEGO WARD

Docelowo:
- Spec produktowa v0.17;
- Architektura v0.3 PASS;
- UI Contract v0.1;
- rzeczywiste fixtures / scenariusze akceptacyjne;
- potwierdzone reguły prawne wpływające bezpośrednio na przypisanie do zmiany.

Ward później rozbija wykonanie na taski.
Ta rozmowa projektuje produkt, nie workflow implementatorów.

---

## 15. ZASADA PROJEKTOWA NA DALSZY CIĄG

> Jeśli czysta konstrukcja obsługuje znane przypadki, nie ulepszamy jej bez konkretnego przypadku domenowego, który pokazuje brak.

> Model ma być wystarczająco jednoznaczny, żeby implementator nie zgadywał w sprawach wpływających na grafik — ale nie bardziej formalny niż wymaga rzeczywista praca koordynatora.
