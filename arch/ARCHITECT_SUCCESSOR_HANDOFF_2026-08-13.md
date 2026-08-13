# Brief dla następnej instancji architekta — Rota

DATA: 2026-08-13
ROLA: architekt produktu/systemu
REPO: `paweltpietraszko-ship-it/elnath-rota`

## 1. Twoja odpowiedzialność

Jesteś architektem Rota. Nie wymyślasz produktu za właściciela i nie implementujesz za CC.

Twoje zadania:

- utrzymywać spójny kontrakt produktu i architektury;
- przekładać decyzje właściciela na małe, testowalne zadania;
- podejmować decyzje techniczne, jeśli nie zmieniają zachowania produktu;
- wykrywać sprzeczności między decyzją właściciela, dokumentacją i kodem;
- pilnować reuse istniejących mechanizmów i jednego źródła prawdy;
- korzystać z Codexa jako niezależnego audytora, ale samemu odpowiadać za ocenę architektoniczną;
- po implementacji sprawdzać, czy kod rzeczywiście spełnia zaakceptowany kontrakt;
- wydawać jednoznaczną akceptację architektoniczną albo zwracać minimalny zakres poprawki.

Jeżeli pytanie dotyczy realnej organizacji pracy ludzi, NIE zgaduj. Właściciel pracuje w tym środowisku i jest źródłem prawdy. Zapytaj go prostym polskim językiem. Jeżeli dwa rozsądne warianty dają inny efekt produktu, decyzja należy do właściciela.

Nie pytaj właściciela o techniczne szczegóły, które nie zmieniają produktu.

## 2. Role

**Właściciel** — właściciel produktu i ekspert operacyjny. Rozstrzyga produkt.

**Architekt — Ty** — tworzy kontrakty, dzieli zakres, podejmuje decyzje techniczne, pilnuje spójności i po implementacji ocenia zgodność.

**CC** — implementer. Nie powinien sam rozstrzygać luk produktowych. Gdy odkryje brak decyzji, zatrzymuje się i zwraca pytanie.

**Codex** — niezależny audytor/tester. Testy nie ustanawiają produktu. Finding musi wynikać z kontraktu, a nie z preferowanej przez Codexa architektury.

## 3. Najważniejsze zamrożone zasady produktu

- Rota nie ocenia, nie dopuszcza i nie odsuwa pracownika z własnej inicjatywy. Wykonuje jawne decyzje koordynatora.
- `READY_FOR_PRIMARY` / `NOT_READY` są informacyjne i nie uczestniczą w eligibility.
- Szkolenie `S` koordynator wstawia ręcznie do konkretnego grafiku.
- HARD jest bezwzględne. SOFT solver może naruszyć, jeśli inaczej nie ułoży grafiku. INFORMATIONAL nie ogranicza planowania.
- Parser języka naturalnego został usunięty. Nie buduj parsera, DSL ani systemu „rozumienia intencji”.
- Docelowe okno konfiguracji nazywa się **Panel Sterowania**.
- Panel Sterowania nie może dostać własnej kopii logiki lub danych. Jeśli funkcja istnieje, przyszłe UI ma ją wywołać przez application layer.
- Pierwsza konfiguracja i późniejsza edycja korzystają z tych samych danych i operacji. Nie ma osobnego onboardingu z własnym stanem.
- Nie kasujemy historii pracownika. Usunięcie z bieżącej obsady wyłącza go z nowych planowań, ale stare grafiki pozostają odtwarzalne.
- Wszystkie ptaszki dostępności mają jedno znaczenie: `✓` = solver może użyć pracownika w tym wymiarze, `☐` = nie może w obowiązującym okresie.
- `NN` oznacza wyłącznie niewykonaną, wcześniej zaplanowaną zmianę.
- `target_hours` pozostaje SOFT i nie tworzy dodatkowej pracy.
- Redukujemy zakres, nie jakość.

## 4. Styl architektury

Nie twórz bez realnej potrzeby command busa, mediatorów, workflow engine, event busa, DI frameworka, uniwersalnego edytora reguł, drugich DTO, drugich modeli tych samych danych ani serwisów będących tylko przekazywaniem wywołań.

Jeżeli zadanie zbliża się rozmiarem do T009, podziel je wcześniej na małe, użyteczne i osobno testowalne części.

**Duplikacja istniejącej logiki w Panelu Sterowania lub nowej warstwie jest błędem architektonicznym, nie refaktorem „na później”.**

## 5. Stan T010 — zaakceptowany kontrakt

Gałąź dokumentacji:

`arch/rota-t010-panel-sterowania-2026-08-13`

Zaakceptowany kontrakt po korektach R1:

`2de74063909a1c2b207c2170855b835571d378b0`

Codex wykonał R2 i wydał:

**PASS — READY_FOR_IMPLEMENTATION**

Raport PASS R2:

`405d2414483d2a2c7cafccc14a0e4cf070341937`

Plik:

`tasks/ROTA-T010/round_01/tests/tests_r2.txt`

**T010 JEST ZAAKCEPTOWANY DO IMPLEMENTACJI. Nie projektuj go od początku i nie otwieraj ponownie zamkniętych decyzji bez konkretnego konfliktu z kodem albo nowej decyzji właściciela.**

T010 implementacyjnie dzieli się na:

- **A** — pierwszy kontekst, wznowienie konfiguracji, gotowość konkretnego miesiąca i bieżąca obsada;
- **B** — jedna matryca dostępności i wąski wyjątek czasowego N dla `day_only`;
- **D** — trwałe `NN` na konkretnej niewykonanej zmianie.

**C nie jest produkcyjną implementacją.** To tylko regresja potwierdzająca, że readiness nie wpływa na eligibility.

Wiążący wąski wyjątek `day_only`:

`arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`

Wyjątek może uchylić wyłącznie `DAY_ONLY-01` dla N właściwego pracownika/Site/dat. Nie uchyla żadnego innego HARD i nie może stać się ogólnym mechanizmem override.

Dla NN zatwierdzono minimalny model: opcjonalne `Assignment.operational_code`, w T010 wartość `NN`; w child niewykonany PRIMARY ma `CANCELLED + NN`, parent zachowuje wcześniejszy `PLANNED`; NN daje 0 do planned i 0 do realized; demand pozostaje i zwykła walidacja coverage działa dalej; bez osobnej tabeli NN i bez automatycznego REPLAN.

## 6. Twoje najbliższe zadania

### 1. Nie przepisywać T010

Przeczytaj zaakceptowany aneks, brief A/B/C/D, addendum `day_only` i raport R2. Nie poprawiaj ich stylistycznie i nie dodawaj funkcji „na wszelki wypadek”. Kontrakt ma PASS.

### 2. Pilnować implementacji CC

CC powinien implementować kolejno A, B i D, nie jako jeden wielki commit. Sprawdzaj szczególnie, czy nie powstaje:

- nowy stan onboardingu;
- druga tabela/lista dostępności;
- drugi `day_only`;
- ogólny mechanizm override HARD;
- osobny subsystem NN;
- forwarding facade bez potrzebnej orkiestracji;
- bezpośredni zapis przyszłego UI do repository.

### 3. Zlecić Codexowi audyt implementacji

Audyt ma sprawdzać kod względem zaakceptowanego T010, a nie projektować nową wersję produktu. Ma objąć A/B/D oraz regresję C i macierz z raportu R2.

### 4. Samodzielnie ocenić zgodność po implementacji

To jest obowiązek następcy architekta. PASS Codexa nie wystarcza.

Po implementacji:

1. zapisz dokładne SHA A/B/D i raportów audytu;
2. porównaj diff z kontraktem `2de7406...`;
3. sprawdź, czy reuse jest rzeczywisty i czy nie powstało drugie źródło prawdy;
4. sprawdź brak rozszerzenia produktu poza kontrakt;
5. tam gdzie HARD wykonują solver i validator, potwierdź ich zgodność;
6. sprawdź trwałość/restart dla nowych danych;
7. sprawdź zachowanie historii ScheduleVersion i pracowników;
8. przeczytaj findings Codexa i oddziel defekt od propozycji architektonicznej;
9. jeśli kod spełnia kontrakt — wydaj jednoznaczną **ARCHITECT ACCEPTANCE T010**;
10. jeśli nie — zwróć CC najmniejszy zakres poprawki; jeżeli brakuje decyzji produktowej, zapytaj właściciela zamiast zgadywać.

Pytanie końcowe architekta brzmi:

**Czy zaimplementowane T010 robi dokładnie to, co zaakceptowano, bez drugiego źródła prawdy, bez duplikacji i bez ukrytego rozszerzenia produktu?**

## 7. Minimalna kontrola zgodności T010

**A:** pusta/częściowa/pełna konfiguracja, restart bez duplikacji, kontrola po utworzeniu association, pełny i niepełny CalendarDay, miesiąc A gotowy / B niegotowy, brak target_hours nie blokuje PLAN, membership disabled/re-enabled bez utraty historii.

**B:** jedno znaczenie ptaszków, granice `od–do`, noc kotwiczona datą startu, nakładanie HARD przez AND, SICK/LEAVE/UNAVAILABLE bez podwójnego zapisu, `day_only` bez wyjątku/z wyjątkiem/po wygaśnięciu, inny HARD nadal blokuje, korekta dat i wcześniejsze `✓`, restart, zgodność eligibility i validatora.

**C:** tylko regresja — readiness nie zmienia eligibility i solver nie tworzy szkolenia sam.

**D:** PLANNED -> CANCELLED+NN w child, parent bez zmian, restart, 168 -> 156 w istniejących polach WorkBalance, NN bez i z ręcznym zastępstwem, brak Availability/SiteRule i brak automatycznego REPLAN.

## 8. Co po T010

Po zaakceptowaniu implementacji T010:

- ustal aktualny SHA main i zmergowanego T010;
- zaktualizuj roadmapę, bo dawny parser T010 został usunięty;
- nie zaczynaj od razu kolejnego ogromnego kontraktu;
- historycznie kolejne zakresy to backend/application E2E oraz desktop T012, ale przed briefem sprawdź aktualne repo i decyzje właściciela;
- T012 ma używać application layer. Panel Sterowania nie może implementować własnej prawdy ani zapisywać bezpośrednio do repository.

## 9. Repo i komunikacja

Nie zapisuj do `main` bez wyraźnej zgody właściciela. Dokumentację/taski przygotowuj na właściwych gałęziach. Raportów audytu nie nadpisuj; kolejne rundy są append-only. Przed podaniem SHA sprawdź faktyczny HEAD.

Mów właścicielowi po polsku i zwyczajnie. Angielską nazwę techniczną podawaj dopiero, gdy pomaga. Nie pytaj go o znaczenie własnego żargonu. Gdy poda przykład z realnej pracy, nie zastępuj go własnym przypuszczeniem.

## 10. Dokumenty startowe

Przed pierwszą decyzją przeczytaj:

- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md`;
- `arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md`;
- `tasks/ROTA-T010/brief.md`;
- `tasks/ROTA-T010/part_a_bootstrap_roster.md`;
- `tasks/ROTA-T010/part_b_availability.md`;
- `tasks/ROTA-T010/part_c_training_readiness.md`;
- `tasks/ROTA-T010/part_d_nn.md`;
- `tasks/ROTA-T010/round_01/tests/tests_r2.txt`;
- `arch/spec.md` i istniejące frozen addenda.

Jeżeli implementacja T010 już istnieje, przeczytaj jej diff i raport audytu implementacji przed wydaniem oceny.

---

**Najważniejsze zdanie na przejęcie:** T010 jest zaakceptowany do implementacji. Twoim najbliższym zadaniem nie jest projektować go ponownie, tylko dopilnować implementacji, zlecić niezależny audyt i następnie samodzielnie ocenić, czy wykonanie jest zgodne z zaakceptowanym kontraktem oraz zasadą jednego źródła prawdy.
