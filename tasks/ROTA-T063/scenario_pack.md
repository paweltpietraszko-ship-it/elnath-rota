# ROTA-T063 — SCENARIO_PACK v0.2 OWNER APPROVED

STATUS: OWNER APPROVED 2026-09-10 — NORMATIVE TEST INPUT

Ten plik zastępuje `SCENARIO_PACK v0.1`. Daty, nazwy i wartości testowe są syntetyczne i służą deterministyczności acceptance. Nie są twierdzeniem o jednym rzeczywistym obiekcie. Implementer odwzorowuje scenariusze literalnie i nie rozszerza ich pod wynik testu.

## Wspólna baza

Miesiąc: `2026-10` — wykonanie zależne od T064; bez podrobienia zegara przeglądarki.

Obiekt: syntetyczny `T063-24H`.

Zapotrzebowanie:
- jedna służba D każdego dnia, `05:00–17:00`;
- jedna służba N każdego dnia, `17:00–05:00`;
- wymagane 100% pokrycia D+N.

LOCAL roster — dokładnie 5 osób:
- `A` — D/N;
- `B` — D/N;
- `C` — DAY_ONLY;
- `D` — D/N;
- `E` — D/N.

Test ani helper nie może utworzyć szóstej osoby LOCAL. External może zostać dodany tylko w S02 i tylko w liczbie wskazanej w wariancie. Solver może użyć wyłącznie osób istniejących przed danym uruchomieniem PLAN/Przelicz Plan.

## Zasada target_hours

T063 ma dowieść obu istniejących trybów bez mieszania ich w jednym scenariuszu:

- S01: `target_hours` są jawnie ustawione dla wszystkich LOCAL na syntetyczną wartość testową `168` godzin na osobę;
- S02 i S03: `target_hours = NULL` dla wszystkich LOCAL;
- osoby external w S02 pozostają bez targetu zgodnie z istniejącym produktem.

Wartość `168` jest wyłącznie deterministycznym wejściem testowym. T063 nie ustanawia nią reguły biznesowej dla innych miesięcy ani obiektów.

## S01 — bazowy pełny grafik, target_hours ustawione

Stan wejściowy:
- dokładnie LOCAL A–E;
- C = DAY_ONLY;
- `target_hours = 168` dla A, B, C, D, E;
- brak urlopu, choroby i innych dodatkowych ograniczeń;
- external = NONE.

Operacja:
1. Koordynator konfiguruje obiekt, roster, katalog D/N i target_hours przez normalne operacje produktu.
2. Uruchamia PLAN.
3. Wybiera dodatni kandydat zgodnie z aktualnym lifecycle.

Oczekiwany wynik:
- dokładnie `FEASIBLE`;
- niepusty pełny grafik D/N;
- wszystkie wymagane D/N są obsadzone wyłącznie przez A–E;
- po reloadzie grafik nadal jest widoczny;
- PDF odpowiada widocznemu grafikowi.

Dowody:
- roster A–E i target_hours przed PLAN;
- wynik PLAN;
- lista employee z assignmentów;
- screenshot po reloadzie;
- PDF.

## S02 — chorobowe po powstaniu grafiku, potem external support

Cel: sprawdzić realny lifecycle chorobowego i kontrolowane wsparcie zewnętrzne. Chorobowego nie planuje się z góry.

Stan do utworzenia bazowego grafiku:
- LOCAL A–E;
- `target_hours = NULL` dla A–E;
- C ma zatwierdzony urlop `2026-10-12`–`2026-10-18`;
- D i E są zdrowi i dostępni;
- external = NONE.

Krok bazowy:
1. Koordynator uruchamia PLAN.
2. Oczekiwany wynik: dokładnie `FEASIBLE`.
3. Koordynator wybiera/zapisuje grafik zgodnie z lifecycle.
4. Test potwierdza, że istnieje rzeczywisty current i niepusty D/N.

Zdarzenie po powstaniu grafiku:
- D otrzymuje `SICK_LEAVE` `2026-10-12`–`2026-10-18`;
- E otrzymuje `SICK_LEAVE` `2026-10-12`–`2026-10-18`;
- C pozostaje na wcześniej zatwierdzonym urlopie;
- w krytycznym oknie dostępni LOCAL pozostają A i B.

Twardy fakt scenariusza:
- 7 dni wymagają 14 służb × 12 h = 168 h pokrycia;
- A+B mogą przy granicy 60 h / dowolne 7 dni dostarczyć najwyżej 120 h bez przekroczenia ograniczenia;
- test nie może uznać A+B za wystarczających.

Pierwszy `Przelicz Plan` bez external:
1. Koordynator uruchamia `Przelicz Plan` na istniejącym grafiku po zapisaniu SICK_LEAVE D/E.
2. Oczekiwany rezultat biznesowy: dokładnie `DECISION_REQUIRED` oraz brak nowego zaakceptowanego pełnego current z tej próby.
3. TECHNICAL_ERROR, crash, timeout ani pusty sukces nie spełniają tego kroku.
4. Jeżeli guidance wskazuje możliwość skorygowania zatwierdzonego urlopu C, test zapisuje ten fakt jako oczekiwany krok przed external.
5. Literalna decyzja koordynatora: `NIE COFAJ URLOPU C`.
6. Dopiero po tej decyzji scenariusz może dodać external.

### S02-V1 — dokładnie 1 external

Scenariusz startuje od własnego czystego przebiegu S02.

Po `DECISION_REQUIRED` i literalnym `NIE COFAJ URLOPU C` koordynator dodaje przez normalne operacje produktu:
- `X1` — external, D/N, dostępny tylko `2026-10-12`–`2026-10-18`.

Następnie uruchamia właściwe `Przelicz Plan`.

Oczekiwany wynik:
- dokładnie `FEASIBLE`;
- pełne wymagane D/N;
- solver używa wyłącznie osób wpisanych przed próbą;
- X1 nie jest używany poza zakresem dostępności;
- brak nieznanego employee;
- screenshot + PDF.

### S02-V2 — dokładnie 3 external

Scenariusz startuje od osobnego czystego przebiegu S02 i nie dziedziczy X1 z V1.

Po `DECISION_REQUIRED` i literalnym `NIE COFAJ URLOPU C` koordynator dodaje:
- `X1` — external, D/N, `2026-10-12`–`2026-10-18`;
- `X2` — external, D/N, `2026-10-12`–`2026-10-18`;
- `X3` — external, D/N, `2026-10-12`–`2026-10-18`.

Następnie uruchamia `Przelicz Plan`.

Oczekiwany wynik:
- dokładnie `FEASIBLE`;
- pełne D/N;
- solver może użyć dowolnego podzbioru X1–X3 zgodnie z normalnymi regułami;
- nikt spoza zamkniętego rosteru nie pojawia się w assignmentach;
- external nie jest używany poza swoją dostępnością;
- test raportuje, ilu external faktycznie użyto;
- screenshot + PDF.

Zakazy S02:
- brak planowania chorobowego przed bazowym PLAN;
- brak automatycznego „dodaj jeszcze jednego i spróbuj ponownie”;
- brak zwiększania zakresu dostępności external;
- brak cofnięcia urlopu C po literalnym `NIE`;
- brak ręcznie budowanych Assignmentów.

## S03 — krótka choroba po zapisanym grafiku, bez external

Stan bazowy:
- LOCAL A–E;
- C = DAY_ONLY;
- `target_hours = NULL` dla A–E;
- brak urlopu i choroby;
- external = NONE.

Krok bazowy:
1. PLAN.
2. Oczekiwany wynik: dokładnie `FEASIBLE`.
3. Koordynator wybiera/zapisuje grafik.
4. Test potwierdza istniejący current i pełny D/N.

Zdarzenie:
- po powstaniu grafiku D otrzymuje `SICK_LEAVE` `2026-10-12`–`2026-10-14`.

Operacja:
1. Koordynator zapisuje SICK_LEAVE D przez normalną operację produktu.
2. Uruchamia `Przelicz Plan`.

Oczekiwany wynik:
- dokładnie `FEASIBLE`;
- pełny niepusty D/N;
- D nie ma assignmentu kolidującego z chorobowym w części podlegającej przeliczeniu;
- żadna osoba external nie istnieje ani nie zostaje dodana;
- solver używa wyłącznie A–E;
- lifecycle zachowuje odbyte/fixed służby zgodnie z istniejącym kontraktem;
- reload zachowuje grafik;
- screenshot + PDF.

## Zatwierdzone decyzje OWNERA — 2026-09-10

OWNER potwierdził:
1. chorobowego nie planuje się z góry; jeśli T063 używa SICK_LEAVE, musi najpierw istnieć grafik, a dalsza operacja to `Przelicz Plan`;
2. testy mają objąć oba tryby target_hours w osobnych scenariuszach: w jednym targety są ustawione, w innym jawnie nieustawione;
3. S01 używa jawnych target_hours `168` dla A–E jako syntetycznych danych testowych;
4. S02 i S03 używają `target_hours = NULL` dla A–E;
5. S02 po SICK_LEAVE D/E i bez external oczekuje dokładnie `DECISION_REQUIRED`; crash/TECHNICAL_ERROR nie jest akceptowalnym odpowiednikiem;
6. w S02 urlop C pozostaje zatwierdzony, a external może zostać dodany dopiero po literalnej decyzji `NIE COFAJ URLOPU C`;
7. S02-V1 używa dokładnie 1 external i oczekuje `FEASIBLE`;
8. S02-V2 używa dokładnie 3 external i oczekuje `FEASIBLE`;
9. S03 sprawdza trzydniowy SICK_LEAVE D po powstaniu grafiku, bez external, i oczekuje `FEASIBLE` po `Przelicz Plan`.

Implementer nie może zmienić tych danych ani kolejności pod wynik testu. Odkryta niezgodność produktu z oczekiwaniem daje FAIL/finding.