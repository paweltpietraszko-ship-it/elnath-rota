# ROTA — decyzja właściciela: T010 / konfiguracja i Panel Sterowania

DATA: 2026-08-13
STATUS: OWNER DECISION / skonsolidowany aneks po audycie R1
BAZA: main `51b71725186fa30be23219e94aa135bb69bc5bce`

## 1. Kierunek

T010 nie dotyczy parsera języka naturalnego. Sterowanie Rotą swobodnym tekstem jest usunięte z produktu. Koordynator przekazuje decyzje jawnie; program nie zgaduje intencji.

T010 przygotowuje trwałe operacje aplikacyjne i odczyty konfiguracji. Nie tworzy UI. Docelowe okno T012 nazywa się **Panel Sterowania**.

Panel Sterowania jest jednym miejscem pierwszej konfiguracji i późniejszej edycji tych samych danych. Nie ma osobnego onboardingu, własnego stanu panelu ani bezpośrednich zapisów UI do repository.

Jeżeli funkcja lub stan już istnieje w Rota, należy go wykorzystać. Duplikacja istniejącej logiki albo trwałego stanu jest błędem architektonicznym.

## 2. Pierwsza konfiguracja i późniejsza edycja

Pierwszy kontekst obejmuje:

`Coordinator -> SiteProfile -> Site -> CoordinatorSiteAssociation`

a następnie konfigurację zmian i pracowników.

Pierwszy zapis i późniejsza edycja używają tych samych źródeł prawdy. Nie tworzyć tabel onboardingowych, flagi `onboarding_in_progress`, numeru kroku ani szkicu konfiguracji.

Konfiguracja może zostać przerwana. Poprawnie zapisane dane pozostają zwykłymi danymi programu, a po restarcie program rozpoznaje istniejący stan i wskazuje braki.

Utworzenie pierwszego kontekstu może mieć wyłącznie najmniejsze odstępstwo potrzebne przed powstaniem pierwszego `CoordinatorSiteAssociation`. Po jego utworzeniu zwykłe operacje znów wymagają normalnej kontroli koordynator–obiekt. Bootstrap nie może stać się słabiej chronioną ścieżką edycji istniejącego obiektu.

## 3. Kompletność obiektu i gotowość miesiąca

Należy rozróżnić:

1. **kompletność stałego kontekstu obiektu** — aktywne Coordinator, SiteProfile, Site, CoordinatorSiteAssociation, co najmniej jedna poprawna zmiana standardowa, wymagane stałe parametry profilu oraz bieżąca obsada;
2. **gotowość do PLAN dla konkretnego miesiąca** — kompletny kontekst plus pełny `CalendarDay` dla każdego dnia wskazanego miesiąca.

Gotowość liczona jest osobno dla każdego miesiąca. Ten sam obiekt może być gotowy dla miesiąca A i niegotowy dla miesiąca B.

Brak `target_hours` nie blokuje PLAN. Pozostaje brakującą daną dla istniejącego SOFT/bilansu i nie może być zgadywany.

## 4. Bieżąca obsada

Koordynator może dodać pracownika do bieżącej obsady i usunąć go z niej.

Usunięcie z bieżącej obsady nie kasuje Employee ani historii. Stare ScheduleVersion, Assignment i bilanse pozostają odtwarzalne i nadal wskazują pracownika.

Pracownik usunięty z bieżącej obsady nie może być użyty w nowym planowaniu tego Site. Ponowne dodanie może ponownie włączyć istniejące membership zamiast tworzyć równoległy rekord.

## 5. Jedna matryca dostępności

Dla pracownika konfiguracja udostępnia:
- **Ogólna dostępność**;
- **Dniówka**;
- **Nocka**;
- **Dni tygodnia**: Pon, Wt, Śr, Czw, Pt, Sob, Nd.

Nie ma osobnej pozycji **Święta** ani przełącznika **Szkolenie**.

Dla zwykłego nowego pracownika wszystkie powyższe pozycje są domyślnie zaznaczone.

Każdy ptaszek ma dokładnie jedno znaczenie:
- `✓` = solver może korzystać z pracownika w tym wymiarze;
- `☐` = solver nie może korzystać z pracownika w tym wymiarze w obowiązującym okresie.

Nie istnieje kontrolka, w której zaznaczenie oznacza zakaz.

Odznaczenie z zakresem `od–do` tworzy HARD. Obie daty są włączne. Po `do` automatycznie wraca stan bazowy bez przyszłej operacji przywracającej.

Dla danego ShiftDemand muszą jednocześnie pozwalać: Ogólna dostępność, właściwy typ zmiany oraz dzień tygodnia startu demandu. Jedno właściwe `☐` wystarcza do blokady.

Przykład: `Piątek ☐ | od 01.09.2026 | do 31.10.2026` oznacza brak D i N rozpoczynających się w każdy piątek tego okresu; pozostałe dni są bez zmian.

## 6. `day_only` i czasowe N

`Employee.day_only` pozostaje istniejącym bazowym źródłem Nocka ☐. Nie tworzyć drugiego stałego pola o tym samym znaczeniu.

Koordynator może czasowo zaznaczyć Nocka ✓ dla pracownika z `day_only=true`. W tym okresie solver może użyć go na N, a po końcu okresu bazowy zakaz automatycznie wraca.

To zachowanie jest jednym wąskim wyjątkiem od `DAY_ONLY-01`, zamrożonym w `FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`. Wyjątek nie może uchylać żadnego innego HARD.

## 7. Niedostępność znana przed planowaniem

Znana wcześniej niedostępność jest wejściem do planowania: solver omija wskazane terminy i może rozłożyć pracę na inne dni, nadal respektując pozostałe HARD.

Jeżeli koordynator zna powód potrzebny do grafiku i godzin, może wskazać:
- chorobę;
- urlop.

Inna znana wcześniej pełna niedostępność pozostaje zwykłą niedostępnością. **Nie używa kodu NN.**

## 8. NN — jedno znaczenie

`NN` oznacza wyłącznie fakt, że pracownik **nie wykonał konkretnej, wcześniej zaplanowanej zmiany**.

NN nie jest preplanning availability, nie jest SiteRule i nie jest decyzją kadrową.

Po korekcie bieżącego grafiku:
- wcześniejsza wersja zachowuje pierwotny plan;
- niewykonana zmiana jest widoczna jako `NN`;
- wnosi 0 godzin pracy;
- program nie tworzy sztucznej wykonanej pracy;
- brak zastępstwa pozostawia zwykły problem coverage, a faktyczne zastępstwo zapisuje istniejący mechanizm ręcznej korekty;
- nie uruchamia się automatycznie REPLAN.

Przykład: wcześniej ułożony grafik 168 h, jedna niewykonana zmiana 12 h -> bieżący stan uwzględnia z tej zmiany 0 h, więc suma godzin wynikających z bieżących PLANNED/REALIZED wynosi 156 h.

Konsekwencje kadrowe NN są poza Rota.

## 9. Szkolenie i readiness

Szkolenie `S` koordynator wstawia ręcznie do konkretnego grafiku. Solver nie decyduje, czy pracownik potrzebuje szkolenia.

`READY_FOR_PRIMARY` / `NOT_READY` mogą pozostać informacyjną etykietą. Etykieta nie blokuje ani nie dopuszcza do grafiku. Istniejące automatyczne przestawienie samej etykiety po policzeniu szkoleń może pozostać, dopóki nie wpływa na eligibility. T010 nie ma tego mechanizmu usuwać ani rozbudowywać.

Program nie może na podstawie historii, liczby szkoleń ani readiness samodzielnie dopuszczać, odsuwać ani oceniać pracownika.

## 10. TARGET-01

Zapotrzebowanie obiektu określa liczbę potrzebnych zmian. `target_hours` pozostaje istniejącym SOFT pomagającym rozdzielać istniejącą pracę i obserwować saldo.

Target nie może:
- naruszyć HARD;
- utworzyć dodatkowej pracy;
- stać się decyzją kadrową.

T010 nie zmienia semantyki TARGET-01.

## 11. Granica T010

T010 ma wykorzystać istniejące SiteProfile, Employee, SiteMembership, AvailabilityRecord, SiteRuleVersion/SiteMemory, Site, Coordinator, CoordinatorSiteAssociation oraz T009 application layer.

T010 implementuje tylko brakujące podpięcia potrzebne do:
- pierwszego kontekstu i jego wznowienia;
- odczytu kompletności obiektu i gotowości miesiąca;
- bieżącej obsady bez kasowania historii;
- jednej matrycy dostępności i jej zmian okresowych;
- czasowego, wąskiego zawieszenia `day_only` dla N;
- zapisu NN jako faktu konkretnej niewykonanej zmiany.

T010 nie tworzy UI, parsera, DSL, uniwersalnego edytora reguł, workflow, osobnego systemu onboardingu ani osobnego systemu kadrowego.

Jeżeli istniejący kod zapewnia zachowanie, T010 ma go użyć. Jeżeli potrzebna byłaby nowa decyzja produktowa, implementer ma ją zwrócić właścicielowi zamiast zgadywać.

## 12. Obowiązkowe klasy testów

- pusta baza, częściowa konfiguracja, restart i wznowienie;
- kompletny kontekst bez kalendarza, kalendarz niepełny i pełny dla wskazanego miesiąca;
- miesiąc A gotowy / miesiąc B niegotowy;
- brak target_hours nie blokuje PLAN;
- usunięcie pracownika z obsady bez utraty historii;
- wszystkie ptaszki bazowo ✓;
- Ogólna/D/N/dzień tygodnia ☐ od–do i powrót stanu bazowego;
- korekta dat i wcześniejsze przywrócenie ✓ bez mutowania historii;
- `day_only=true` + czasowe N ✓ z pełną macierzą innych HARD;
- `NOT_READY` i `READY_FOR_PRIMARY` mają identyczne eligibility;
- NN na zaplanowanej zmianie: historia, 0 godzin, coverage i restart;
- target_hours pozostaje wyłącznie SOFT.

Ten aneks jest podstawą briefu T010, nie zgodą na implementację przed PASS Codexa.