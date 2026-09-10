# ROTA-T063 — SCENARIO_PACK v0.1 PROPOSED

STATUS: OWNER APPROVAL REQUIRED — NIE IMPLEMENTOWAĆ

Ten plik jest konkretnym kandydatem do zatwierdzenia przez OWNERA. Daty i nazwy pracowników są syntetyczne i służą wyłącznie deterministyczności testu. Reguły operacyjne, liczebność i oczekiwane zachowanie muszą zostać jawnie zaakceptowane przez OWNERA przed zwolnieniem IMPLEMENTATION HOLD.

## Wspólna baza wszystkich scenariuszy

Miesiąc: `2026-10` — wykonanie zależne od T064; bez podrobienia zegara przeglądarki.

Obiekt: syntetyczny `T063-24H`.

Zapotrzebowanie:
- jedna służba D każdego dnia, `05:00–17:00`;
- jedna służba N każdego dnia, `17:00–05:00`;
- pełne 100% pokrycia D+N;
- brak dodatkowych zmian poza literalnie wskazanymi w tym pliku.

LOCAL roster — dokładnie 5 osób:
- `A` — D/N;
- `B` — D/N;
- `C` — DAY_ONLY;
- `D` — D/N;
- `E` — D/N.

Test ani helper nie może utworzyć szóstej osoby LOCAL. External może powstać tylko w scenariuszu S02 i tylko w liczbie wskazanej w danym wariancie.

Wszystkie osoby, w tym external, podlegają normalnym regułom produktu. Test nie może tworzyć Assignmentów ręcznie ani omijać zwykłych operacji koordynatora.

## S01 — bazowy pełny grafik bez absencji

Stan wejściowy:
- dokładnie LOCAL A–E;
- C = DAY_ONLY;
- brak urlopu, choroby i innych ograniczeń poza zwykłymi regułami produktu;
- external = NONE.

Operacja:
1. Koordynator konfiguruje obiekt i roster przez normalne operacje produktu.
2. Koordynator uruchamia PLAN.

Oczekiwany wynik:
- dokładnie `FEASIBLE`;
- powstaje niepusty kandydat pełnego grafiku D/N;
- po wyborze zgodnie z aktualnym lifecycle istnieje zapisany grafik;
- wszystkie wymagane D/N są obsadzone wyłącznie przez A–E;
- po reloadzie grafik nadal jest widoczny;
- PDF istnieje i odpowiada widocznemu grafikowi.

Dowody:
- zamknięty roster A–E przed PLAN;
- wynik PLAN;
- lista employee użytych w assignmentach;
- screenshot grafiku po reloadzie;
- PDF.

## S02 — external support dopiero po wyczerpaniu zamrożonej drogi wewnętrznej

Cel: jeden kontrolowany scenariusz, w którym test może odgrywać literalną decyzję koordynatora dotyczącą external support. Nie jest to ogólny fallback.

Wspólny stan przed pierwszym PLAN:
- LOCAL A–E jak wyżej;
- okres krytyczny: `2026-10-12` do `2026-10-18` włącznie — 7 kolejnych dat startu służby;
- `C`: zatwierdzony urlop obejmujący cały okres krytyczny;
- `D`: choroba / niedostępność obejmująca cały okres krytyczny;
- `E`: choroba / niedostępność obejmująca cały okres krytyczny;
- w okresie krytycznym faktycznie dostępni LOCAL są więc tylko `A` i `B`;
- external przed pierwszym PLAN = NONE.

Twardy fakt testowy:
- okres krytyczny wymaga 14 służb × 12 h = 168 h pokrycia;
- dwie dostępne osoby A+B mogą przy limicie >60 h w dowolnych 7 dniach dostarczyć maksymalnie 120 h bez naruszenia tego ograniczenia;
- test nie zakłada więc, że dwie osoby mogą legalnie pokryć okres krytyczny.

Pierwszy krok:
1. PLAN uruchamiany bez external.
2. Oczekiwany wynik: nie powstaje pełny grafik przy tym stanie.
3. Jeżeli istniejąca guidance wskazuje możliwość skorygowania zatwierdzonego urlopu C, test zachowuje ten fakt jako poprawny krok pośredni i NIE dodaje external przed jego odnotowaniem.
4. Literalna decyzja koordynatora dla tego scenariusza: `NIE COFAJ URLOPU C` — wpis pozostaje bez zmian.
5. Test nie interpretuje innych możliwych działań i nie tworzy pętli poszukiwania rozwiązania.

### S02-V1 — dokładnie 1 external

Po kroku powyżej koordynator przez zwykłe operacje produktu dodaje dokładnie:
- `X1` — external, D/N, dostępny wyłącznie `2026-10-12`–`2026-10-18`.

Następnie ponownie uruchamia właściwe planowanie na aktualnych danych.

Oczekiwany wynik do zatwierdzenia przez OWNERA:
- `FEASIBLE`;
- pełne D/N w całym miesiącu;
- w okresie krytycznym solver używa wyłącznie A, B i istniejącego X1 spośród osób dostępnych do tych służb;
- żaden nieznany employee nie pojawia się w assignmentach;
- external użyty <= 1 osoba i wyłącznie w dozwolonym okresie;
- screenshot + PDF.

### S02-V2 — dokładnie 3 external

Scenariusz startuje ponownie od czystego stanu S02 przed pierwszym PLAN; nie dziedziczy X1 z V1.

Po literalnej decyzji `NIE COFAJ URLOPU C` koordynator dodaje przez zwykłe operacje dokładnie:
- `X1` — external, D/N, dostępny `2026-10-12`–`2026-10-18`;
- `X2` — external, D/N, dostępny `2026-10-12`–`2026-10-18`;
- `X3` — external, D/N, dostępny `2026-10-12`–`2026-10-18`.

Oczekiwany wynik do zatwierdzenia przez OWNERA:
- `FEASIBLE`;
- pełne D/N;
- solver może użyć dowolnego podzbioru X1–X3 zgodnie z normalnymi regułami, ale nie może użyć nikogo spoza zamkniętego rosteru;
- żadna osoba external nie jest używana poza zakresem swojej dostępności;
- test raportuje dokładnie, ilu external faktycznie użyto;
- screenshot + PDF.

Zakaz dla obu wariantów:
- brak automatycznego „dodaj jeszcze jednego i spróbuj ponownie”;
- brak zwiększania zakresu dostępności X;
- brak cofnięcia urlopu C po literalnej decyzji `NIE`;
- brak poluzowania choroby D/E;
- brak ręcznie tworzonych Assignmentów.

## S03 — zwykła absencja, którą istniejąca obsada ma przejąć bez external

Stan wejściowy:
- LOCAL A–E jak w S01;
- `D`: choroba / niedostępność `2026-10-12`–`2026-10-14`;
- pozostałe osoby bez dodatkowych ograniczeń;
- external = NONE.

Operacja:
1. Koordynator zapisuje absencję D przez normalną operację produktu.
2. Uruchamia PLAN na tym stanie.

Oczekiwany wynik do zatwierdzenia przez OWNERA:
- `FEASIBLE`;
- pełny, niepusty D/N;
- D nie ma assignmentu kolidującego z absencją;
- nie istnieje ani nie zostaje utworzona żadna osoba external;
- solver używa wyłącznie A–E;
- reload zachowuje grafik;
- screenshot + PDF.

Ten scenariusz nie twierdzi, że automat rozumie ogólną hierarchię decyzji. Sprawdza wyłącznie konkretny, zamrożony przypadek: przy tej krótkiej absencji oczekujemy poprawnego grafiku z istniejącego rosteru i bez external.

## Kryterium OWNER approval

OWNER zatwierdza albo koryguje łącznie następujące fakty:
1. bazowy roster `5 LOCAL`, z `C = DAY_ONLY`;
2. bazowe oczekiwanie S01 = `FEASIBLE`;
3. okres S02 i stan `C urlop + D/E choroba`, pozostawiający A/B jako jedynych dostępnych LOCAL w 7-dniowym oknie;
4. literalną decyzję S02: urlop C pozostaje, external dopiero po tym kroku;
5. S02-V1: dokładnie 1 external i oczekiwane `FEASIBLE`;
6. S02-V2: dokładnie 3 external i oczekiwane `FEASIBLE`;
7. S03: 3-dniowa choroba D bez external i oczekiwane `FEASIBLE`.

Do czasu jawnego zatwierdzenia tych siedmiu punktów plik pozostaje `PROPOSED`, a IMPLEMENTATION HOLD obowiązuje.
