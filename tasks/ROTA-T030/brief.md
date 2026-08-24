# ROTA-T030 — Panel sterowania → Obiekt: katalog zmian

Status: **READY FOR IMPLEMENTATION**

Base implementation SHA: `f2ba515d701ee41f325a58a7711169a640d49ade`
(`task/ROTA-T029`). T030 musi zachować całe zachowanie T029.

Owner decisions: Paweł, 2026-08-24. Konsolidacja zamyka audyt
`round_01/tests/tests_r1.txt`.

TASK_SCOPE:
- api/main.py
- api/errors.py
- api/routers/site_profile.py
- frontend/src/api/client.ts
- frontend/src/screens/ControlPanel.tsx
- frontend/src/App.css
- frontend/src/screens/SiteShiftCatalog.tsx
- tests/test_t030_shift_catalog_api.py
- frontend/e2e/shift-catalog.spec.ts

(dokumentacyjne domknięcie punktu 1 z round_01/tests/tests_r4.txt — maszynowa
transkrypcja już zamrożonej listy z §7, bez zmiany zakresu).

## 1. Wynik dla właściciela

Zakładka „Obiekt” w Panelu sterowania przestaje być wyszarzonym placeholderem.
Koordynator może w niej utworzyć i później poprawić katalog zmian danego
obiektu: D/N, godziny, liczbę potrzebnych osób i dni tygodnia.

Po zapisaniu pierwszej poprawnej zmiany Workspace nie zgłasza już braku
standardowej zmiany. Zrealizowane grafiki nie są przepisywane.

## 2. Istniejący backend jest właścicielem

T030 używa bez zmian:

- `get_site_profile` — aktualny profil i `standard_shifts`;
- `update_site_profile` — atomowy zapis pełnego profilu, audyt i invalidacja;
- `validate_standard_shift` — pełna walidacja wiersza;
- `shift_duration_hours` i `normalized_catalog_kind` — czas trwania oraz
  klasyfikacja 12h/24h/INNY;
- `coordinator_context_completeness` — informacja o brakującym katalogu.

Nie wolno zmieniać `rota/**`, tworzyć drugiego repozytorium, walidatora,
wersjonowania profilu ani identyfikatora wiersza zmiany.

## 3. Zamknięte decyzje formularza

1. Wiersz można dodać, edytować i usunąć. Usunięcie wymaga potwierdzenia.
   Ostatniego wiersza nie można usunąć; błędny ostatni wiersz należy edytować.
2. `active_weekdays` jest widoczne i edytowalne jako Pon–Nd. Co najmniej jeden
   dzień musi pozostać zaznaczony.
3. `required_rest_hours` nie jest polem UI. Każdy wiersz zapisany przez T030
   otrzymuje `11`.
4. Godziny wybiera się z pełnych godzin `00:00`–`23:00`; minuty nie istnieją
   w formularzu.
5. `end_next_day` jest wyliczane: `end_time <= start_time` oznacza następny
   dzień. Równe godziny oznaczają 24h, nie zmianę zerową.
6. `catalog_kind` nie jest przełącznikiem. UI pokazuje wyliczone
   `12h`, `24h` albo `INNY` oraz liczbę godzin.
7. `required_primary_count` jest dodatnią liczbą całkowitą widoczną jako
   „Potrzebnych osób”.

Reguły ochrony po 24h i odpoczynek tygodniowy pozostają automatycznymi HARD z
T023b. T030 nie daje koordynatorowi przełącznika do ich wyłączenia.

## 4. Jeden kontrakt API

### Odczyt

`GET /workspace/sites/{site_id}/shift-catalog`

Zwraca `site_id`, `profile_id` oraz uporządkowaną listę:

```json
{
  "kind": "D",
  "start_time": "06:00",
  "end_time": "18:00",
  "required_primary_count": 1,
  "active_weekdays": [1, 2, 3, 4, 5, 6, 7],
  "duration_hours": 12,
  "catalog_kind": "12h"
}
```

Pusty katalog jest poprawną odpowiedzią GET dla nowego, jeszcze niepełnego
obiektu.

### Zapis

`PUT /workspace/sites/{site_id}/shift-catalog`

Request zawiera tylko `shifts`. Każdy wiersz przyjmuje pięć pól wejściowych:
`kind`, `start_time`, `end_time`, `required_primary_count`, `active_weekdays`.
Nie przyjmuje `profile_id`, pól polityki profilu, `required_rest_hours`,
`end_next_day` ani `catalog_kind`.

Lista musi zawierać co najmniej jeden wiersz. Kolejność requestu jest trwałą
kolejnością katalogu.

Router dla każdego wiersza:

1. parsuje wyłącznie pełne godziny;
2. wylicza `end_next_day`;
3. ustawia `required_rest_hours=11` i `catalog_kind=None`;
4. buduje `StandardShift` i wywołuje istniejące `validate_standard_shift`.

Dopiero gdy wszystkie wiersze są poprawne, router pobiera najnowszy
`SiteProfile`, podmienia wyłącznie `standard_shifts` i raz wywołuje
`update_site_profile`. Request nie może nadpisać żadnego ukrytego pola, także
gdy zmieniło się ono po wcześniejszym GET w przeglądarce.

Odpowiedź to `204` — bez ponownego odczytu i bez `site_id`/`profile_id` w
body (Site identyfikuje już ścieżka). `req()` już obsługuje 204. Nie ma
osobnych endpointów POST/PATCH/DELETE dla pojedynczego wiersza.
(R3-1, runda 3: usunięty wcześniejszy wymóg drugiego GET po PUT.)

## 5. Granice zachowania

- Dozwolone są mnogie wiersze, INNY i nakładające się wystąpienia, bo obecna
  domena je dopuszcza. T030 nie dodaje nowego zakazu duplikatów/overlapów.
- PUT pustej listy jest odrzucany również przez API, nie tylko przez disabled
  button w UI.
- Błąd któregokolwiek wiersza oznacza brak zapisu całej listy.
- Materialna zmiana korzysta z istniejącego `SITE_PROFILE_CHANGED`, audytu i
  invalidacji. Identyczny zapis nie tworzy sztucznej akcji.
- Istniejące ScheduleVersion, ShiftDemand oraz REALIZED/CANCELLED Assignment
  nie są modyfikowane. Nowy katalog jest bieżącą konfiguracją dla następnego
  generowania/replanowania zgodnie z istniejącym pipeline.
- `planning_regime` pozostaje tylko do odczytu poza tym ekranem. T030 nie
  dodaje drogi jego zmiany.
- Pola `training_s_*`, `external_support_enabled` i `day_only_blocks_n` nie są
  zwracane do formularza ani przyjmowane w request.

## 6. UI zakładki „Obiekt” (zredukowane R3-2, runda 3)

- Dwie aktywne zakładki: „Obiekt” i istniejąca „Obsada (n)”.
- „Obiekt” pokazuje listę wierszy, przycisk „+ Dodaj zmianę” i jeden przycisk
  „Zapisz katalog”. Edycje są lokalnym draftem do jednego atomowego PUT.
- Wiersz zawiera: D/N, Początek, Koniec, Potrzebnych osób, Pon–Nd oraz
  wyliczony opis czasu/katalogu.
- „Usuń” wymaga potwierdzenia. Przy jednym wierszu jest disabled z informacją
  „Ostatnią zmianę popraw przez edycję”.
- Podczas zapisu przycisk jest disabled. Sukces oznacza wysłany draft jako
  zapisany (PUT kończy się 204 — nie ma czym go zastąpić); reload + GET
  dowodzi zapisu. Błąd pokazuje komunikat, zachowuje cały draft i nie
  pokazuje fałszywego sukcesu.
- Wszystkie akcje korzystają z istniejącego `data-diag-action` i klienta
  `req()`; bez drugiej diagnostyki i bez bezpośredniego `fetch` w komponencie.

UI nie eksponuje: minut, `end_next_day`, `catalog_kind`, odpoczynku, toggle'i
profilu ani zmiany rodzaju Site.

## 7. Dozwolony zakres plików

Produkt:

- `api/main.py`, `api/errors.py`;
- nowy `api/routers/site_profile.py`;
- `frontend/src/api/client.ts`, `frontend/src/screens/ControlPanel.tsx`,
  `frontend/src/App.css`;
- opcjonalnie jeden nowy komponent
  `frontend/src/screens/SiteShiftCatalog.tsx`.

Testy/delivery:

- nowy `tests/test_t030_shift_catalog_api.py`;
- nowy `frontend/e2e/shift-catalog.spec.ts` i tylko konieczna adaptacja
  istniejącego seeda E2E;
- `tasks/ROTA-T030/round_01/implementation/**`.

Brak nowych zależności. Nie modyfikować istniejących testów ani plików poza
listą; w plikach współdzielonych zachować całe zachowanie T029 poza koniecznym
osadzeniem zakładki. Jeżeli implementacja wymaga szerszego zakresu, zgłosić
blocker zamiast tworzyć connector lub nową warstwę.

## 8. Minimalna macierz odbioru (zredukowana R3-3, runda 3 — 8 grup)

Niższe warstwy (repository, application, diagnostyka `req()`) mają już własne
testy atomowości/reconnect/fault-injection/REQUEST_FAILED — T030 sprawdza, że
z nich korzysta, nie powtarza ich całych kontraktów.

T30-01 — GET pustego i istniejącego katalogu, trwała kolejność.

T30-02 — PUT i trwałe wyliczenie `end_next_day`/`catalog_kind` (12h/24h/INNY)
oraz `required_rest_hours=11`.

T30-03 — sparametryzowana walidacja: minuty, count<=0, puste/powtórzone dni,
dzień poza 1–7, w tym błędny DRUGI wiersz — brak zmiany stanu.

T30-04 — zachowanie najnowszych ukrytych pól przy PUT oraz odrzucenie
requestu z dodatkowym/nieoczekiwanym polem.

T30-05 — jeden materialny PUT: istniejący audyt/invalidacja się uruchamia,
completeness przestaje zgłaszać brak zmiany, żaden utrwalony grafik się nie
zmienia.

T30-06 — E2E: wejście w „Obiekt”, dodanie, zapis, reload, ten sam katalog;
edycja istniejącego wiersza.

T30-07 — E2E: usunięcie jednego z dwóch wierszy; ostatni wiersz chroniony w
UI i API; draft zachowany po błędzie zapisu.

T30-08 — build frontendu, pełna regresja Pythona (w tym T029), diff-scope
z §7, zero zmian w `rota/**`.

## 9. DELIVERY

Wykonawca przekazuje exact HEAD, diff od base SHA, raw `backend.py` stdout,
wynik `npm run build`, wynik E2E T030 oraz listę zmienionych plików.

Jeżeli istniejący backend nie pozwala spełnić kontraktu bez zmiany `rota/**`,
wykonawca zatrzymuje się i wskazuje dokładną lukę. Nie naprawia solvera,
assemblera ani domeny w T030.
